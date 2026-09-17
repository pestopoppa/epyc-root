/**
 * epyc-orchestrator: OpenCode server plugin (HS-4 P0.3).
 *
 * Stamps session identity onto every model request and onto orchestrator/memory
 * MCP tool calls. It is written against the documented v1 `Hooks` API
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
      applyChatParams(ready(), input, output)
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
