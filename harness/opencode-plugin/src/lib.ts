/**
 * Pure logic for the epyc-orchestrator OpenCode plugin (HS-4 P0.3).
 *
 * Kept free of OpenCode imports so the offline tests can exercise it with
 * plain objects. `index.ts` wires these functions into the OpenCode hooks.
 *
 * Audit basis: docs/reference/harness-candidates/opencode-p03-audit-20260916.md
 * (OpenCode @ 350c726aa, packages/opencode v1.18.31).
 */

export const PLUGIN_ID = "epyc-orchestrator"

/** Keys this plugin owns. Config may not set them as static keys. */
export const DYNAMIC_KEYS = ["x_session_id", "x_user_id", "x_tool_mode"] as const

export const DEFAULT_PROVIDER_IDS = ["epyc-orchestrator"]
/**
 * OpenCode names an MCP tool `sanitize(server) + "_" + sanitize(tool)`
 * (packages/opencode/src/mcp/catalog.ts:117-119). So a prefix here is an
 * MCP *server* name plus "_", and it matches every tool that server exposes.
 */
export const DEFAULT_STAMP_PREFIXES = ["orchestrator_", "memory_"]

export type Scalar = string | number | boolean

export interface EpycOptions {
  /** Provider IDs whose requests carry the x_* keys. Other providers are untouched. */
  readonly providerIDs: readonly string[]
  readonly userId: string
  readonly toolMode: "client"
  /** Static x_* keys copied into every request body (e.g. x_memory, x_show_routing). */
  readonly staticKeys: Readonly<Record<string, Scalar>>
  /** MCP tool-name prefixes whose arguments receive `session_id`. */
  readonly stampPrefixes: readonly string[]
}

export class EpycPluginConfigError extends Error {
  constructor(message: string) {
    super(`[${PLUGIN_ID}] invalid plugin configuration: ${message}`)
    this.name = "EpycPluginConfigError"
  }
}

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v)

const isScalar = (v: unknown): v is Scalar =>
  typeof v === "string" || typeof v === "boolean" || (typeof v === "number" && Number.isFinite(v))

// Our providerID is the providerOptions namespace (provider/transform.ts:1455-1458 and
// openai-compatible getArgs). A "." would be split away on both sides, and an
// "opencode*" id changes request headers and native-runtime eligibility (session/llm/request.ts:188,
// session/llm/native-runtime.ts:55). Refuse both instead of reasoning about them.
const PROVIDER_ID_RE = /^[a-z0-9][a-z0-9_-]*$/

function stringList(value: unknown, field: string, fallback: readonly string[]): string[] {
  if (value === undefined) return [...fallback]
  if (!Array.isArray(value) || value.length === 0 || !value.every((x) => typeof x === "string" && x.length > 0)) {
    throw new EpycPluginConfigError(`${field} must be a non-empty array of non-empty strings`)
  }
  return [...value]
}

/**
 * Parse plugin options (the second element of the `plugin` tuple in opencode.json).
 * `env` is injected for tests; it supplies EPYC_USER_ID when `userId` is absent.
 * Throws EpycPluginConfigError on any problem. Nothing is defaulted silently
 * except the documented list defaults.
 */
export function parseOptions(raw: unknown, env: Record<string, string | undefined> = {}): EpycOptions {
  const opts = raw === undefined ? {} : raw
  if (!isRecord(opts)) throw new EpycPluginConfigError("options must be an object")

  const known = new Set(["providerIDs", "userId", "staticKeys", "stampPrefixes"])
  for (const key of Object.keys(opts)) {
    if (!known.has(key)) throw new EpycPluginConfigError(`unknown option "${key}"`)
  }

  const providerIDs = stringList(opts.providerIDs, "providerIDs", DEFAULT_PROVIDER_IDS)
  for (const id of providerIDs) {
    if (!PROVIDER_ID_RE.test(id) || id.startsWith("opencode")) {
      throw new EpycPluginConfigError(
        `providerID "${id}" must match ${PROVIDER_ID_RE} and must not start with "opencode"`,
      )
    }
  }

  const userIdRaw = opts.userId ?? env.EPYC_USER_ID
  if (typeof userIdRaw !== "string" || userIdRaw.trim() === "") {
    throw new EpycPluginConfigError("userId is required (plugin option `userId` or env EPYC_USER_ID)")
  }

  const staticRaw = opts.staticKeys ?? {}
  if (!isRecord(staticRaw)) throw new EpycPluginConfigError("staticKeys must be an object")
  const staticKeys: Record<string, Scalar> = {}
  for (const [key, value] of Object.entries(staticRaw)) {
    if (!/^x_[a-z0-9_]+$/.test(key)) {
      throw new EpycPluginConfigError(`static key "${key}" must match ^x_[a-z0-9_]+$`)
    }
    if ((DYNAMIC_KEYS as readonly string[]).includes(key)) {
      throw new EpycPluginConfigError(`static key "${key}" is owned by the plugin and cannot be configured`)
    }
    if (!isScalar(value)) {
      throw new EpycPluginConfigError(`static key "${key}" must be a string, finite number or boolean`)
    }
    staticKeys[key] = value
  }

  const stampPrefixes = stringList(opts.stampPrefixes, "stampPrefixes", DEFAULT_STAMP_PREFIXES)
  for (const p of stampPrefixes) {
    if (!/^[a-zA-Z0-9_-]+_$/.test(p)) {
      throw new EpycPluginConfigError(`stamp prefix "${p}" must be a sanitized MCP server name followed by "_"`)
    }
  }

  return {
    providerIDs,
    userId: userIdRaw.trim(),
    toolMode: "client",
    staticKeys,
    stampPrefixes,
  }
}

export function appliesToProvider(opts: EpycOptions, providerID: string): boolean {
  return opts.providerIDs.includes(providerID)
}

/**
 * The x_* keys for one request. Static keys go first so the dynamic ones always win.
 * (parseOptions already refuses a collision; the ordering is defence in depth.)
 */
export function requestKeys(opts: EpycOptions, sessionID: string): Record<string, Scalar> {
  if (typeof sessionID !== "string" || sessionID === "") {
    throw new EpycPluginConfigError("chat.params delivered an empty sessionID; refusing to send an unkeyed request")
  }
  return {
    ...opts.staticKeys,
    x_session_id: sessionID,
    x_user_id: opts.userId,
    x_tool_mode: opts.toolMode,
  }
}

/**
 * Mutates `output.options` in place for chat.params.
 *
 * Why the keys go in `output.options`: session/llm/request.ts:114-131 passes these
 * options to ProviderTransform.providerOptions, which namespaces them under the
 * providerID (provider/transform.ts:1455-1465). @ai-sdk/openai-compatible@2.0.41
 * then spreads that namespace into the TOP LEVEL of the JSON body. It strips only
 * user/reasoningEffort/textVerbosity/strictJsonSchema
 * (openai-compatible-chat-language-model.ts:231-240).
 */
export function applyChatParams(
  opts: EpycOptions,
  input: { sessionID: string; model: { providerID: string } },
  output: { options: Record<string, unknown> },
): boolean {
  if (!appliesToProvider(opts, input.model.providerID)) return false
  if (!isRecord(output.options)) {
    throw new EpycPluginConfigError("chat.params output.options is not an object; OpenCode hook contract changed")
  }
  Object.assign(output.options, requestKeys(opts, input.sessionID))
  return true
}

export function shouldStamp(opts: EpycOptions, toolName: string): boolean {
  return opts.stampPrefixes.some((p) => toolName.startsWith(p) && toolName.length > p.length)
}

/**
 * Mutates `output.args` IN PLACE for tool.execute.before.
 *
 * It has to be in place. session/tools.ts:401-409 passes `{ args }` to the hook,
 * then calls `execute(args, opts)` with its own local `args` binding. Reassigning
 * `output.args` would be a silent no-op.
 *
 * The stamp overwrites any `session_id` the model supplied. The model does not
 * choose which session's memory it touches.
 */
export function stampToolArgs(
  opts: EpycOptions,
  input: { tool: string; sessionID: string },
  output: { args: unknown },
): boolean {
  if (!shouldStamp(opts, input.tool)) return false
  if (!isRecord(output.args)) {
    throw new EpycPluginConfigError(
      `tool ${input.tool}: arguments are not an object, so session_id cannot be stamped; refusing the call`,
    )
  }
  if (typeof input.sessionID !== "string" || input.sessionID === "") {
    throw new EpycPluginConfigError(`tool ${input.tool}: empty sessionID; refusing the call`)
  }
  output.args.session_id = input.sessionID
  return true
}
