/**
 * epyc-orchestrator: OpenCode server plugin (HS-4 P0.3).
 *
 * Stamps session identity onto every model request and onto orchestrator/memory
 * MCP tool calls. With `stampAgentName: true` (HS-19a subagents profile) it also sends the
 * OpenCode agent name as x_agent_name. It is written against the documented v1 `Hooks` API
 * (@opencode-ai/plugin 1.18.31), so it is an integration, not a patch.
 *
 * Load it from opencode.json(c) as a path plugin. Path plugins must export `id`
 * (packages/opencode/src/plugin/shared.ts:313-315):
 *   "plugin": [["/workspace/harness/opencode-plugin/src/index.ts", { "userId": "..." }]]
 *
 * FAIL-CLOSED DESIGN. OpenCode only LOGS a plugin that throws while loading, then
 * keeps running without it (packages/opencode/src/plugin/index.ts:222-240). The
 * result would be requests that silently lack x_* keys. So server() never throws.
 * A bad configuration is held, and every request to our provider then fails loudly
 * from chat.params, and every stamped tool call from tool.execute.before. A hook
 * rejection becomes an Effect defect, and the session processor surfaces it as a
 * turn error.
 *
 * The type import is dev-time only, erased at runtime, so the plugin loads with
 * no dependencies and no network access. Restart OpenCode after editing.
 */
import type { Hooks, Plugin, PluginModule } from "@opencode-ai/plugin"
import { applyChatParams, parseOptions, PLUGIN_ID, stampToolArgs, type EpycOptions } from "./lib.ts"

export const server: Plugin = async (_input, rawOptions) => {
  let opts: EpycOptions | undefined
  let configError: Error | undefined
  try {
    opts = parseOptions(rawOptions, process.env)
  } catch (err) {
    configError = err instanceof Error ? err : new Error(String(err))
    console.error(configError.message)
  }

  const ready = (): EpycOptions => {
    if (configError || !opts) throw configError ?? new Error(`[${PLUGIN_ID}] not configured`)
    return opts
  }

  const hooks: Hooks = {
    event: async ({ event }) => {
      // `session.status: idle` is an ordinary turn boundary, not session end;
      // keep its observed lineage until explicit deletion or the idle TTL.
      if (configError || !opts || event.type !== "session.deleted") return
      const properties = (event as { properties?: { info?: { id?: unknown } } }).properties
      const sessionID = properties?.info?.id
      if (typeof sessionID !== "string" || sessionID.length === 0) return

      const baseURL = (process.env.EPYC_ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000/v1")
        .replace(/\/+$/, "")
      try {
        const response = await fetch(`${baseURL}/chat/completions`, {
          method: "POST",
          headers: { "content-type": "application/json", "X-Session-Id": sessionID },
          body: JSON.stringify({
            model: "orchestrator",
            messages: [],
            x_session_id: sessionID,
            x_session_final: true,
            x_session_end_event: "deleted",
          }),
          // Do not hold the event hook open if the control endpoint stalls.
          // The server's idle TTL remains the recovery path.
          signal: AbortSignal.timeout(5_000),
        })
        if (!response.ok) {
          console.warn(`[${PLUGIN_ID}] session deletion signal was not accepted: HTTP ${response.status}`)
        }
      } catch (err) {
        // The server's declared idle TTL remains the recovery path when this
        // best-effort control request cannot reach the orchestrator.
        console.warn(`[${PLUGIN_ID}] session deletion signal failed: ${String(err)}`)
      }
    },
    "chat.params": async (input, output) => {
      // A config error must not break unrelated providers, but it must break ours.
      // With no valid options, the only safe test for "ours" is the default provider ID.
      if (configError) {
        const ids = Array.isArray((rawOptions as { providerIDs?: unknown } | undefined)?.providerIDs)
          ? ((rawOptions as { providerIDs: unknown[] }).providerIDs as unknown[])
          : ["epyc-orchestrator"]
        if (ids.includes(input.model.providerID)) throw configError
        return
      }
      // input.agent is the OpenCode agent name (session/llm/request.ts:118); it becomes
      // x_agent_name only with the stampAgentName option (HS-19a, default off).
      applyChatParams(ready(), { sessionID: input.sessionID, agent: input.agent, model: input.model }, output)
    },
    "tool.execute.before": async (input, output) => {
      if (configError) {
        // Without valid options we cannot tell which tools are ours. Refuse any
        // tool whose name uses a default prefix.
        if (/^(orchestrator|memory)_/.test(input.tool)) throw configError
        return
      }
      stampToolArgs(ready(), input, output)
    },
  }
  return hooks
}

const plugin: PluginModule & { id: string } = { id: PLUGIN_ID, server }
export default plugin
