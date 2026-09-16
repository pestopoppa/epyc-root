import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { lintConfig, lintEnv, stripJsonc } from "../src/config-lint.ts"

const here = (p: string) => fileURLToPath(new URL(p, import.meta.url))
const templateText = readFileSync(here("../config/opencode.jsonc.template"), "utf8")
const envText = readFileSync(here("../config/opencode.env"), "utf8")
const template = () => JSON.parse(stripJsonc(templateText))

test("stripJsonc keeps // inside strings", () => {
  const out = JSON.parse(stripJsonc('{"a": "http://x//y", /* c */ "b": 1 // tail\n}'))
  assert.deepEqual(out, { a: "http://x//y", b: 1 })
})

test("shipped template passes the lint", () => {
  assert.deepEqual(lintConfig(template()), [])
})

test("shipped env file passes the lint", () => {
  assert.deepEqual(lintEnv(envText), [])
})

const mutations: Array<[string, (c: any) => void, RegExp]> = [
  ["compaction.auto on", (c) => { c.compaction.auto = true }, /compaction\.auto/],
  ["compaction.prune missing", (c) => { delete c.compaction.prune }, /compaction\.prune/],
  ["share manual", (c) => { c.share = "manual" }, /share/],
  ["autoupdate notify", (c) => { c.autoupdate = "notify" }, /autoupdate/],
  ["title agent enabled", (c) => { delete c.agent.title }, /agent\.title/],
  ["explore enabled", (c) => { c.agent.explore.disable = false }, /agent\.explore/],
  ["subagent depth 1", (c) => { c.subagent_depth = 1 }, /subagent_depth/],
  ["task allowed", (c) => { c.permission.task = "allow" }, /permission\.task/],
  ["no skills paths", (c) => { delete c.skills }, /skills\.paths/],
  ["remote skills", (c) => { c.skills.urls = ["https://x"] }, /skills\.urls/],
  ["no small_model", (c) => { delete c.small_model }, /small_model/],
  ["small_model other provider", (c) => { c.small_model = "anthropic/haiku" }, /small_model/],
  ["extra provider enabled", (c) => { c.enabled_providers.push("openai") }, /enabled_providers/],
  ["no baseURL", (c) => { delete c.provider["epyc-orchestrator"].options.baseURL }, /baseURL/],
  ["wrong npm", (c) => { c.provider["epyc-orchestrator"].npm = "@ai-sdk/openai" }, /npm/],
  ["x_ in model options", (c) => { c.provider["epyc-orchestrator"].models.orchestrator.options = { x_memory: "on" } }, /staticKeys/],
  ["x_ in provider options", (c) => { c.provider["epyc-orchestrator"].options.x_memory = "on" }, /staticKeys/],
  ["output over cap", (c) => { c.provider["epyc-orchestrator"].models.orchestrator.limit.output = 64000 }, /limit\.output/],
  ["plugin missing", (c) => { c.plugin = [] }, /plugin/],
  ["plugin bad static key", (c) => { c.plugin[0][1].staticKeys = { x_session_id: "spoof" } }, /owned by the plugin/],
]

for (const [name, mutate, expected] of mutations) {
  test(`lint catches: ${name}`, () => {
    const c = template()
    mutate(c)
    const errs = lintConfig(c)
    assert.ok(errs.some((e) => expected.test(e)), `${name}: got ${JSON.stringify(errs)}`)
  })
}

test("env lint catches missing flags and OPENCODE_PURE", () => {
  const bad = envText.replace("export OPENCODE_DISABLE_SHARE=1", "") + "\nexport OPENCODE_PURE=1\n"
  const errs = lintEnv(bad)
  assert.ok(errs.some((e) => e.includes("OPENCODE_DISABLE_SHARE")))
  assert.ok(errs.some((e) => e.includes("OPENCODE_PURE")))
  assert.ok(lintEnv("export OPENCODE_EXPERIMENTAL_NATIVE_LLM=true\n").some((e) => e.includes("NATIVE_LLM")))
})
