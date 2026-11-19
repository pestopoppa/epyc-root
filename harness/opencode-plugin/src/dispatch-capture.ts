/** HS-TD-1 raw native capture. No inferred turn policy and no model calls. */
import { constants } from "node:fs"
import { open } from "node:fs/promises"
import { isAbsolute } from "node:path"
import { randomUUID } from "node:crypto"

const TYPES = new Set(["permission.asked", "permission.updated", "permission.replied"])
const nonempty = (value: unknown): value is string => typeof value === "string" && value.length > 0

export function createDispatchCapture(sink: string | undefined,
  warn: (message: string) => void = console.warn) {
  let pending = 0
  async function write(row: Record<string, unknown>) {
    try {
      if (!isAbsolute(sink!)) throw new Error("capture path must be absolute")
      // Snapshot synchronously before the first await: subsequent hooks cannot change evidence.
      let payload = JSON.stringify({ schema_version: "hs_td1.native_event.v1",
        capture_id: randomUUID(), captured_at: new Date().toISOString(), gate: false, ...row })
      if (Buffer.byteLength(payload) > 131_072) {
        payload = JSON.stringify({ schema_version: "hs_td1.native_event.v1",
          capture_id: randomUUID(), captured_at: new Date().toISOString(), gate: false,
          session_id: row.session_id, turn_id: row.turn_id, kind: row.kind, status: "oversize" })
      }
      const file = await open(sink!, constants.O_WRONLY | constants.O_APPEND |
        constants.O_CREAT | constants.O_NOFOLLOW | constants.O_NONBLOCK, 0o600)
      try {
        const metadata = await file.stat()
        if (!metadata.isFile() || (metadata.mode & 0o777) !== 0o600 ||
            metadata.uid !== process.getuid?.()) throw new Error("capture sink must be owned private regular file")
        const bytes = Buffer.from(payload + "\n")
        const result = await file.write(bytes)
        if (result.bytesWritten !== bytes.length) throw new Error("short dispatch capture write")
        await file.sync()
      } finally { await file.close() }
    } catch (error) {
      // Never log private request/event contents or let diagnostics gate dispatch.
      try { warn(`[epyc-orchestrator] dispatch capture failed: ${String(error)}`) } catch {}
    } finally { pending-- }
  }
  function record(row: Record<string, unknown>) {
    if (!sink) return
    if (pending >= 4) {
      try { warn("[epyc-orchestrator] dispatch capture dropped: four writes pending") } catch {}
      return
    }
    pending++
    return write(row)
  }
  return {
    request(input: { sessionID: string }, output: { message: Record<string, any>; parts: unknown[] }) {
      if (!sink) return
      const message = output.message
      if (!nonempty(input.sessionID) || message?.sessionID !== input.sessionID ||
          !nonempty(message?.id) || message.role !== "user") return
      return record({ kind: "request", phase: "pre_dispatch", status: "captured",
        session_id: input.sessionID, turn_id: message.id, native: output })
    },
    event(event: { type: string; properties?: Record<string, any> }) {
      if (!sink || !TYPES.has(event.type) || !nonempty(event.properties?.sessionID)) return
      // Permission requests identify a tool/assistant message, not the user turn.
      // Preserve native IDs and the exact reply; never guess via the latest request.
      return record({ kind: "policy_event", status: "unjoined",
        session_id: event.properties!.sessionID, turn_id: null, native: event })
    },
  }
}
