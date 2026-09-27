// Usage: node harness/opencode-plugin/scripts/lint-config.ts [--profile default|subagents] <opencode.jsonc> [opencode.env]
// The profile is explicit and defaults to "default" (the live, no-sub-agent shell). It is never
// inferred from the file: a subagents config linted without --profile subagents FAILS.
// Exit 0 = pass, 1 = lint problems, 2 = usage or parse error.
import { readFileSync } from "node:fs"
import { LINT_PROFILES, type LintProfile, lintConfig, lintEnv, stripJsonc } from "../src/config-lint.ts"

const USAGE = `usage: lint-config.ts [--profile ${LINT_PROFILES.join("|")}] <opencode.jsonc> [opencode.env]`
const positional: string[] = []
let profile: string = "default"
const argv = process.argv.slice(2)
for (let i = 0; i < argv.length; i++) {
  const a = argv[i]
  if (a === "--profile") {
    profile = argv[++i] ?? ""
  } else if (a.startsWith("--profile=")) {
    profile = a.slice("--profile=".length)
  } else if (a.startsWith("--")) {
    console.error(`unknown flag ${a}\n${USAGE}`)
    process.exit(2)
  } else {
    positional.push(a)
  }
}
if (!(LINT_PROFILES as readonly string[]).includes(profile)) {
  console.error(`unknown profile ${JSON.stringify(profile)}\n${USAGE}`)
  process.exit(2)
}
const [cfgPath, envPath] = positional
if (!cfgPath || positional.length > 2) {
  console.error(USAGE)
  process.exit(2)
}
let cfg: unknown
try {
  cfg = JSON.parse(stripJsonc(readFileSync(cfgPath, "utf8")))
} catch (e) {
  console.error(`parse error in ${cfgPath}: ${(e as Error).message}`)
  process.exit(2)
}
const opts = { profile: profile as LintProfile }
const errs = lintConfig(cfg, opts)
if (envPath) errs.push(...lintEnv(readFileSync(envPath, "utf8"), opts).map((e) => `${envPath}: ${e}`))
for (const e of errs) console.error(`FAIL ${e}`)
console.log(
  errs.length === 0
    ? `PASS ${cfgPath}${envPath ? ` + ${envPath}` : ""} (profile ${profile})`
    : `${errs.length} problem(s) (profile ${profile})`,
)
process.exit(errs.length === 0 ? 0 : 1)
