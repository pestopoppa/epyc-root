// Usage: node harness/opencode-plugin/scripts/lint-config.ts <opencode.jsonc> [opencode.env]
// Exit 0 = pass, 1 = lint problems, 2 = usage or parse error.
import { readFileSync } from "node:fs"
import { lintConfig, lintEnv, stripJsonc } from "../src/config-lint.ts"

const [cfgPath, envPath] = process.argv.slice(2)
if (!cfgPath) {
  console.error("usage: lint-config.ts <opencode.jsonc> [opencode.env]")
  process.exit(2)
}
let cfg: unknown
try {
  cfg = JSON.parse(stripJsonc(readFileSync(cfgPath, "utf8")))
} catch (e) {
  console.error(`parse error in ${cfgPath}: ${(e as Error).message}`)
  process.exit(2)
}
const errs = lintConfig(cfg)
if (envPath) errs.push(...lintEnv(readFileSync(envPath, "utf8")).map((e) => `${envPath}: ${e}`))
for (const e of errs) console.error(`FAIL ${e}`)
console.log(errs.length === 0 ? `PASS ${cfgPath}${envPath ? ` + ${envPath}` : ""}` : `${errs.length} problem(s)`)
process.exit(errs.length === 0 ? 0 : 1)
