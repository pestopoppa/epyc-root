/** HS-TD-2 native session capture. Observation only; no judge or permission gate. */
import { open } from "node:fs/promises"

type NativeMessage = { info: Record<string, any>; parts: Array<Record<string, any>> }
type Client = { session: { messages(options: any): Promise<{ data?: NativeMessage[]; error?: unknown }> } }

/** Never pair an answer with the nearest user: the native parent ID is authoritative. */
export function captureTurn(sessionID: string, messages: NativeMessage[]) {
  const assistants = messages.filter(m => m.info.role === "assistant" && !m.info.summary)
    .sort((a, b) => b.info.time.created - a.info.time.created || b.info.id.localeCompare(a.info.id))
  const answer = assistants[0]
  if (!answer || answer.info.sessionID !== sessionID || !answer.info.time.completed) return undefined
  const request = messages.find(m => m.info.id === answer.info.parentID &&
    m.info.role === "user" && m.info.sessionID === sessionID)
  const status = !request ? "missing_parent" : answer.info.error ? "turn_error" : "captured"
  return {
    schema_version: "hs_td2.turn_capture.v1", session_id: sessionID,
    turn_id: answer.info.id, parent_id: answer.info.parentID,
    captured_at: new Date().toISOString(), status, gate: false,
    // A bounded native window retains intervening tool calls, not just final text.
    messages: request ? messages.filter(m => m.info.sessionID === sessionID &&
      (m.info.id === request.info.id || m.info.parentID === request.info.id)) : [answer],
    reference_satisfied: null, // A handback is never a correctness label.
  }
}

/** Default off, four concurrent reads, no unbounded queue; failures never reject a hook. */
export function createTurnCapture(client: Client, sink: string | undefined,
  warn: (message: string) => void = console.warn) {
  let pending = 0
  const busy = new Set<string>()
  const seen = new Map<string, string>() // bounded process-local duplicate suppression
  async function record(sessionID: string) {
    try {
      const result = await client.session.messages({ path: { id: sessionID },
        query: { limit: 100 }, signal: AbortSignal.timeout(5_000) })
      if (result.error || !Array.isArray(result.data)) throw new Error("native messages unavailable")
      const row = captureTurn(sessionID, result.data)
      if (!row || seen.get(sessionID) === row.turn_id) return
      let payload = JSON.stringify(row)
      if (Buffer.byteLength(payload) > 131_072) {
        payload = JSON.stringify({ ...row, messages: [], status: "oversize" })
      }
      const file = await open(sink!, "a", 0o600)
      try {
        const bytes = Buffer.from(payload + "\n")
        const result = await file.write(bytes)
        if (result.bytesWritten !== bytes.length) throw new Error("short turn capture write")
      } finally { await file.close() }
      seen.delete(sessionID)
      seen.set(sessionID, row.turn_id)
      if (seen.size > 256) seen.delete(seen.keys().next().value!)
    } catch (error) {
      warn(`[epyc-orchestrator] turn capture failed: ${String(error)}`)
    } finally {
      pending--
      busy.delete(sessionID)
    }
  }
  return {
    idle(sessionID: string): Promise<void> | undefined {
      if (!sink || !sessionID || busy.has(sessionID)) return
      if (pending >= 4) {
        warn("[epyc-orchestrator] turn capture dropped: four reads pending")
        return
      }
      pending++
      busy.add(sessionID)
      return record(sessionID)
    },
  }
}
