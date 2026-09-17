/**
 * Config lint for the HS-4 P0.3 acceptance test: "Config lint (all required keys present)".
 * Pure and dependency-free. Returns a list of problems; an empty list means pass.
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

export function lintConfig(cfg: unknown): string[] {
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
  for (const sub of ["general", "explore"]) {
    if (cfg.agent?.[sub]?.disable !== true) errs.push(`agent.${sub}.disable must be true (no sub-agents)`)
  }
  if (cfg.subagent_depth !== 0) errs.push("subagent_depth must be 0")
  if (!isRecord(cfg.permission) || cfg.permission.task !== "deny") errs.push('permission.task must be "deny"')
  if (!Array.isArray(cfg.skills?.paths) || cfg.skills.paths.length === 0) errs.push("skills.paths must list the in-repo skills folder")
  if (Array.isArray(cfg.skills?.urls) && cfg.skills.urls.length > 0) errs.push("skills.urls must be empty (no remote skills)")
  return errs
}

/** Lint a shell env file: `export NAME=value` lines. */
export function lintEnv(text: string): string[] {
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
  return errs
}
