/**
 * Config lint for the HS-4 P0.3 acceptance test: "Config lint (all required keys present)".
 * Pure and dependency-free. Returns a list of problems; an empty list means pass.
 *
 * Two profiles, always chosen explicitly by the caller (never auto-detected from the file):
 *   - "default"   the live shell (opencode.jsonc.template): no sub-agents at all.
 *   - "subagents" the HS-19a opt-in (opencode.subagents.jsonc.template): the `task` tool may
 *                 spawn ONE level of sub-agent on the SAME logical model, and the plugin stamps
 *                 x_agent_name. Everything else is as strict as the default.
 * Both profiles refuse any per-agent model pin: the orchestrator selects the model for every
 * call, parent or child. The only pin (x_force_model) is set by us on direct eval/debug calls,
 * never by the harness config.
 */
import { parseOptions, DEFAULT_PROVIDER_IDS } from "./lib.ts"

export const PLUGIN_SPEC_SUFFIX = "harness/opencode-plugin/src/index.ts"

/** Pinned OpenCode version (audit 350c726aa). The guard needs only the "opencode" substring. */
export const OPENCODE_PINNED_VERSION = "1.18.31"
export const EXPECTED_USER_AGENT = `opencode/${OPENCODE_PINNED_VERSION} epyc-orchestrator`
export const REQUIRED_USER_AGENT = /^opencode\/\d+\.\d+\.\d+ epyc-orchestrator$/

export const REQUIRED_ENV_FLAGS = [
  "OPENCODE_DISABLE_MODELS_FETCH",
  "OPENCODE_DISABLE_AUTOUPDATE",
  "OPENCODE_DISABLE_SHARE",
  "OPENCODE_DISABLE_CLAUDE_CODE",
  "OPENCODE_DISABLE_EXTERNAL_SKILLS",
] as const

/** Env settings that would silently defeat the plugin or the audit. */
export const FORBIDDEN_ENV_FLAGS = ["OPENCODE_PURE", "OPENCODE_EXPERIMENTAL_NATIVE_LLM"] as const

export const LINT_PROFILES = ["default", "subagents"] as const
export type LintProfile = (typeof LINT_PROFILES)[number]
export interface LintOptions {
  readonly profile?: LintProfile
}

/** OpenCode's native sub-agents at the pin (agent/agent.ts:182-210). */
export const NATIVE_SUBAGENTS = ["general", "explore"] as const
/** Native agents that are not task targets (primary or hidden side agents). */
const NATIVE_NON_SUBAGENTS = ["build", "plan", "title", "summary", "compaction"]
/** The subagents profile bound: a child may not spawn a grandchild (tool/task.ts:104-117). */
export const MAX_SUBAGENT_DEPTH = 1
/** Config maps OpenCode reads agents from: `agent`, the v2 `agents`, and the deprecated `mode`. */
const AGENT_MAPS = ["agent", "agents", "mode"] as const
/** Orchestrator pin keys. Any key with this prefix anywhere in the config is refused. */
const FORCE_KEY = /^x_force_/
/** 120 s MCP request budget plus 5 s response grace, in milliseconds. */
const MIN_ORCHESTRATOR_MCP_TIMEOUT_MS = 125_000

/** Strip // and /* *\/ comments outside strings. Trailing commas are not supported (keep the template strict). */
export function stripJsonc(text: string): string {
  let out = ""
  let i = 0
  let inString = false
  while (i < text.length) {
    const c = text[i]
    const n = text[i + 1]
    if (inString) {
      out += c
      if (c === "\\") {
        out += n ?? ""
        i += 2
        continue
      }
      if (c === '"') inString = false
      i++
      continue
    }
    if (c === '"') {
      inString = true
      out += c
      i++
      continue
    }
    if (c === "/" && n === "/") {
      while (i < text.length && text[i] !== "\n") i++
      continue
    }
    if (c === "/" && n === "*") {
      i += 2
      while (i < text.length && !(text[i] === "*" && text[i + 1] === "/")) i++
      i += 2
      continue
    }
    out += c
    i++
  }
  return out
}

const isRecord = (v: unknown): v is Record<string, any> => typeof v === "object" && v !== null && !Array.isArray(v)
const ENV_REF = /^\{env:[A-Z0-9_]+\}$/

export function lintConfig(cfg: unknown, options: LintOptions = {}): string[] {
  const profile = options.profile ?? "default"
  if (!(LINT_PROFILES as readonly string[]).includes(profile)) {
    return [`unknown lint profile ${JSON.stringify(profile)}; expected one of ${JSON.stringify(LINT_PROFILES)}`]
  }
  const errs: string[] = []
  if (!isRecord(cfg)) return ["config is not an object"]

  // Plugin entry
  const plugins: unknown[] = Array.isArray(cfg.plugin) ? cfg.plugin : []
  const entry = plugins.find(
    (p) => Array.isArray(p) && typeof p[0] === "string" && p[0].endsWith(PLUGIN_SPEC_SUFFIX),
  ) as [string, unknown] | undefined
  let providerIDs: readonly string[] = DEFAULT_PROVIDER_IDS
  if (!entry) {
    errs.push(`plugin: no [".../${PLUGIN_SPEC_SUFFIX}", {options}] tuple`)
  } else {
    const raw = isRecord(entry[1]) ? { ...entry[1] } : entry[1]
    // {env:VAR} is substituted by OpenCode at load. Lint the shape, not the secret.
    const env: Record<string, string> = {}
    if (isRecord(raw) && typeof raw.userId === "string" && ENV_REF.test(raw.userId)) {
      env.EPYC_USER_ID = "lint-placeholder"
      delete raw.userId
    }
    try {
      providerIDs = parseOptions(raw, env).providerIDs
    } catch (e) {
      errs.push(`plugin options: ${(e as Error).message}`)
    }
    if (profile === "subagents" && !(isRecord(entry[1]) && entry[1].stampAgentName === true)) {
      errs.push("plugin options: stampAgentName must be true in the subagents profile (child calls carry x_agent_name)")
    }
  }

  // Provider / model
  const pid = providerIDs[0]
  if (!Array.isArray(cfg.enabled_providers) || cfg.enabled_providers.length !== providerIDs.length ||
      !providerIDs.every((id) => cfg.enabled_providers.includes(id))) {
    errs.push(`enabled_providers must be exactly ${JSON.stringify(providerIDs)}`)
  }
  for (const key of ["model", "small_model"]) {
    if (typeof cfg[key] !== "string" || !providerIDs.some((id) => cfg[key].startsWith(`${id}/`))) {
      errs.push(`${key} must be set to a model of provider ${JSON.stringify(providerIDs)}`)
    }
  }
  const prov = isRecord(cfg.provider) ? cfg.provider[pid] : undefined
  if (!isRecord(prov)) {
    errs.push(`provider.${pid} missing`)
  } else {
    if (prov.npm !== "@ai-sdk/openai-compatible") errs.push(`provider.${pid}.npm must be "@ai-sdk/openai-compatible"`)
    if (!isRecord(prov.options) || typeof prov.options.baseURL !== "string" || prov.options.baseURL === "") {
      errs.push(`provider.${pid}.options.baseURL missing`)
    }
    const provOpts = isRecord(prov.options) ? prov.options : {}
    // The /v1 session guard recognises OpenCode by a User-Agent containing "opencode".
    // The generic openai-compatible SDK sets none of its own, so the config must set it,
    // or a plugin-less request is unrecognisable.
    const hdrs = isRecord(provOpts.headers) ? provOpts.headers : {}
    const uaKeys = Object.keys(hdrs).filter((k) => k.toLowerCase() === "user-agent")
    const ua = uaKeys.length === 1 ? hdrs[uaKeys[0]] : undefined
    if (typeof ua !== "string" || !REQUIRED_USER_AGENT.test(ua)) {
      errs.push(
        `provider.${pid}.options.headers["User-Agent"] must be exactly one header matching ${REQUIRED_USER_AGENT} ` +
          `(e.g. "${EXPECTED_USER_AGENT}")`,
      )
    }
    for (const k of Object.keys(provOpts)) {
      if (k.startsWith("x_")) errs.push(`provider.${pid}.options.${k}: x_* keys belong in the plugin's staticKeys`)
    }
    const models = isRecord(prov.models) ? prov.models : {}
    if (Object.keys(models).length === 0) errs.push(`provider.${pid}.models is empty`)
    for (const [mid, m] of Object.entries(models)) {
      const mo = isRecord(m) && isRecord((m as any).options) ? (m as any).options : {}
      for (const k of Object.keys(mo)) {
        if (k.startsWith("x_")) errs.push(`provider.${pid}.models.${mid}.options.${k}: x_* keys belong in the plugin's staticKeys`)
      }
      const limit = isRecord(m) ? (m as any).limit : undefined
      if (!isRecord(limit) || typeof limit.output !== "number" || limit.output > 32768) {
        errs.push(`provider.${pid}.models.${mid}.limit.output must be a number <= 32768 (orchestrator max_tokens cap)`)
      }
    }
  }

  // Shell-side autonomy off
  if (!isRecord(cfg.compaction) || cfg.compaction.auto !== false) errs.push("compaction.auto must be false")
  if (!isRecord(cfg.compaction) || cfg.compaction.prune !== false) errs.push("compaction.prune must be false")
  if (cfg.share !== "disabled") errs.push('share must be "disabled"')
  if (cfg.autoupdate !== false) errs.push("autoupdate must be false")
  if (cfg.agent?.title?.disable !== true) errs.push("agent.title.disable must be true (no title side call)")
  const orchestratorMcp = isRecord(cfg.mcp) ? cfg.mcp.orchestrator : undefined
  if (
    isRecord(orchestratorMcp) &&
    orchestratorMcp.enabled !== false &&
    (!Number.isSafeInteger(orchestratorMcp.timeout) || orchestratorMcp.timeout < MIN_ORCHESTRATOR_MCP_TIMEOUT_MS)
  ) {
    errs.push(`mcp.orchestrator.timeout must be an integer >= ${MIN_ORCHESTRATOR_MCP_TIMEOUT_MS} ms when MCP is enabled`)
  }
  if (profile === "default") {
    for (const sub of NATIVE_SUBAGENTS) {
      if (cfg.agent?.[sub]?.disable !== true) errs.push(`agent.${sub}.disable must be true (no sub-agents)`)
    }
    if (cfg.subagent_depth !== 0) errs.push("subagent_depth must be 0")
    if (!isRecord(cfg.permission) || cfg.permission.task !== "deny") errs.push('permission.task must be "deny"')
  } else {
    errs.push(...lintSubagents(cfg, providerIDs))
  }
  if (!Array.isArray(cfg.skills?.paths) || cfg.skills.paths.length === 0) errs.push("skills.paths must list the in-repo skills folder")
  if (Array.isArray(cfg.skills?.urls) && cfg.skills.urls.length > 0) errs.push("skills.urls must be empty (no remote skills)")
  errs.push(...lintNoModelPins(cfg))
  return errs
}

/**
 * Both profiles: the orchestrator owns model selection. OpenCode gives a task child
 * `next.model ?? <parent's model>` (tool/task.ts:181-184), so an agent without a `model` runs on
 * the one logical model. An agent `model` would pick another model client-side, and agent
 * `options` are merged into the request body (session/llm/request.ts:91), so an x_* key there is
 * a per-agent pin by another name.
 */
export function lintNoModelPins(cfg: Record<string, any>): string[] {
  const errs: string[] = []
  for (const mapKey of AGENT_MAPS) {
    const agents = cfg[mapKey]
    if (!isRecord(agents)) continue
    for (const [name, a] of Object.entries(agents)) {
      if (!isRecord(a)) continue
      if (a.model !== undefined) {
        errs.push(`${mapKey}.${name}.model: per-agent model pins are forbidden (the orchestrator selects the model)`)
        const native = (NATIVE_SUBAGENTS as readonly string[]).includes(name) || NATIVE_NON_SUBAGENTS.includes(name)
        if (!native && a.mode === undefined) {
          errs.push(
            `${mapKey}.${name}: a custom agent with no "mode" defaults to "all" (primary AND task target); ` +
              "it must not carry a model",
          )
        }
      }
      const opts = isRecord(a.options) ? a.options : {}
      for (const k of Object.keys(opts)) {
        if (k.startsWith("x_")) {
          errs.push(`${mapKey}.${name}.options.${k}: x_* keys on an agent are a per-agent pin; they belong in the plugin's staticKeys`)
        }
      }
    }
  }
  for (const path of findKeys(cfg, FORCE_KEY)) {
    errs.push(`${path}: x_force_* pins are forbidden in harness config (eval/debug sets them on direct calls only)`)
  }
  return errs
}

function findKeys(value: unknown, re: RegExp, path = ""): string[] {
  const out: string[] = []
  if (Array.isArray(value)) {
    value.forEach((v, i) => out.push(...findKeys(v, re, `${path}[${i}]`)))
  } else if (isRecord(value)) {
    for (const [k, v] of Object.entries(value)) {
      const here = path ? `${path}.${k}` : k
      if (re.test(k)) out.push(here)
      out.push(...findKeys(v, re, here))
    }
  }
  return out
}

/** Sub-agent names the config leaves enabled: native ones not disabled, plus custom task targets. */
export function enabledSubagents(cfg: Record<string, any>): string[] {
  const agents = isRecord(cfg.agent) ? cfg.agent : {}
  const out: string[] = NATIVE_SUBAGENTS.filter((n) => agents[n]?.disable !== true)
  for (const [name, a] of Object.entries(agents)) {
    if ((NATIVE_SUBAGENTS as readonly string[]).includes(name) || NATIVE_NON_SUBAGENTS.includes(name)) continue
    if (!isRecord(a) || a.disable === true) continue
    if (a.mode === undefined || a.mode === "subagent" || a.mode === "all") out.push(name)
  }
  return out
}

function lintSubagents(cfg: Record<string, any>, providerIDs: readonly string[]): string[] {
  const errs: string[] = []
  const enabled = enabledSubagents(cfg)
  if (enabled.length === 0) errs.push("subagents profile: at least one sub-agent (general/explore) must be enabled")
  // A child must not see the task tool. Agent permission rules are appended after the user
  // block (agent/agent.ts:293), so the sub-agent's own "task": "deny" hides the tool in the
  // child (permission/index.ts:204-214). subagent_depth is the second bound.
  for (const name of enabled) {
    if (cfg.agent?.[name]?.permission?.task !== "deny") {
      errs.push(`agent.${name}.permission.task must be "deny" (a sub-agent may not delegate further)`)
    }
  }

  const depth = cfg.subagent_depth
  if (!Number.isInteger(depth) || depth < 1 || depth > MAX_SUBAGENT_DEPTH) {
    errs.push(`subagent_depth must be the integer ${MAX_SUBAGENT_DEPTH} (one level of sub-agent, no grandchildren)`)
  }

  // Unmatched permission rules fall back to "ask", which `opencode run` auto-rejects, so the
  // task permission must be explicit. Rules are evaluated last-match-wins (permission/index.ts:32).
  const task = isRecord(cfg.permission) ? cfg.permission.task : undefined
  if (task === undefined || task === "deny") {
    errs.push('permission.task must not be "deny" (or missing) in the subagents profile')
  } else if (typeof task === "string") {
    if (task !== "allow") errs.push('permission.task must be "allow" or a scoped {"*": "deny", "<agent>": "allow"} map')
  } else if (isRecord(task)) {
    const allowed: string[] = []
    for (const [pattern, action] of Object.entries(task)) {
      if (!["allow", "ask", "deny"].includes(action as string)) {
        errs.push(`permission.task.${pattern} must be "allow", "ask" or "deny"`)
        continue
      }
      if (action !== "allow") continue
      if (pattern === "*") allowed.push(...enabled)
      else if (enabled.includes(pattern)) allowed.push(pattern)
      else errs.push(`permission.task.${pattern} allows an agent that is not an enabled sub-agent`)
    }
    if (allowed.length === 0) errs.push("permission.task allows no enabled sub-agent")
  } else {
    errs.push("permission.task must be a string or a pattern map")
  }

  // One logical model: every agent, parent and child, resolves to the same provider model.
  if (typeof cfg.model === "string" && cfg.small_model !== cfg.model) {
    errs.push("small_model must equal model (one logical model in the subagents profile)")
  }
  const pid = providerIDs[0]
  const models = isRecord(cfg.provider?.[pid]?.models) ? Object.keys(cfg.provider[pid].models) : []
  if (models.length !== 1 || cfg.model !== `${pid}/${models[0]}`) {
    errs.push(`provider.${pid}.models must hold exactly the one logical model that "model" names`)
  }
  return errs
}

/** Lint a shell env file: `export NAME=value` lines. */
export function lintEnv(text: string, options: LintOptions = {}): string[] {
  const errs: string[] = []
  const set = new Map<string, string>()
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*export\s+([A-Z0-9_]+)=("?)([^"#\s]*)\2/)
    if (m) set.set(m[1], m[3])
  }
  for (const flag of REQUIRED_ENV_FLAGS) {
    if (set.get(flag) !== "1") errs.push(`${flag} must be exported as 1`)
  }
  for (const flag of FORBIDDEN_ENV_FLAGS) {
    const v = set.get(flag)
    if (v !== undefined && v !== "0" && v !== "") errs.push(`${flag} must not be enabled`)
  }
  // Subagents profile: background children (task background:true, E9) stay off, explicitly.
  if (options.profile === "subagents" && set.get("OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS") !== "0") {
    errs.push("OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS must be exported as 0 (no background sub-agents)")
  }
  return errs
}
