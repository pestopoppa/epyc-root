import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { lintConfig, lintEnv, stripJsonc } from "../src/config-lint.ts"

const here = (p: string) => fileURLToPath(new URL(p, import.meta.url))
const templateText = readFileSync(here("../config/opencode.jsonc.template"), "utf8")
const envText = readFileSync(here("../config/opencode.env"), "utf8")
const template = () => JSON.parse(stripJsonc(templateText))
const subText = readFileSync(here("../config/opencode.subagents.jsonc.template"), "utf8")
const subTemplate = () => JSON.parse(stripJsonc(subText))
const SUB = { profile: "subagents" } as const

test("stripJsonc keeps // inside strings", () => {
  const out = JSON.parse(stripJsonc('{"a": "http://x//y", /* c */ "b": 1 // tail\n}'))
  assert.deepEqual(out, { a: "http://x//y", b: 1 })
})

test("shipped template passes the lint", () => {
  assert.deepEqual(lintConfig(template()), [])
})

test("enabled orchestrator MCP requires a timeout above the chat deadline", () => {
  const c = template()
  c.mcp.orchestrator.enabled = true
  delete c.mcp.orchestrator.timeout
  assert.ok(lintConfig(c).some((e) => e.includes("mcp.orchestrator.timeout")))

  c.mcp.orchestrator.timeout = 124_999
  assert.ok(lintConfig(c).some((e) => e.includes("mcp.orchestrator.timeout")))

  c.mcp.orchestrator.timeout = 125_000
  assert.deepEqual(lintConfig(c), [])
})

test("disabled orchestrator MCP may omit its timeout", () => {
  const c = template()
  c.mcp.orchestrator.enabled = false
  delete c.mcp.orchestrator.timeout
  assert.deepEqual(lintConfig(c), [])
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
  ["User-Agent header missing", (c) => { delete c.provider["epyc-orchestrator"].options.headers }, /User-Agent/],
  ["User-Agent without opencode", (c) => { c.provider["epyc-orchestrator"].options.headers = { "User-Agent": "curl/8" } }, /User-Agent/],
  ["User-Agent duplicated by case", (c) => { c.provider["epyc-orchestrator"].options.headers["user-agent"] = "opencode/1.0.0 epyc-orchestrator" }, /User-Agent/],
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

// ── HS-19a: subagents profile, and the no-model-pin rule in both profiles ────────────

test("shipped subagents template passes the lint under the subagents profile", () => {
  assert.deepEqual(lintConfig(subTemplate(), SUB), [])
  assert.deepEqual(lintEnv(envText, SUB), [])
})

test("live template passes under the explicit default profile, same as with no options", () => {
  assert.deepEqual(lintConfig(template(), { profile: "default" }), [])
  assert.deepEqual(lintConfig(template(), { profile: "default" }), lintConfig(template()))
})

test("profiles are not interchangeable: each template fails under the other profile", () => {
  const subUnderDefault = lintConfig(subTemplate())
  for (const re of [/agent\.general\.disable/, /subagent_depth must be 0/, /permission\.task must be "deny"/]) {
    assert.ok(subUnderDefault.some((e) => re.test(e)), `${re}: ${JSON.stringify(subUnderDefault)}`)
  }
  const liveUnderSub = lintConfig(template(), SUB)
  for (const re of [/stampAgentName/, /at least one sub-agent/, /subagent_depth/, /permission\.task must not be "deny"/]) {
    assert.ok(liveUnderSub.some((e) => re.test(e)), `${re}: ${JSON.stringify(liveUnderSub)}`)
  }
})

test("unknown profile is an error, not a silent default", () => {
  assert.match(lintConfig(template(), { profile: "sub" as any })[0], /unknown lint profile/)
})

test("the only differences between the templates are the HS-19a keys", () => {
  const live = template()
  const sub = subTemplate()
  sub.permission.task = live.permission.task
  sub.subagent_depth = live.subagent_depth
  sub.agent.general = live.agent.general
  delete sub.plugin[0][1].stampAgentName
  assert.deepEqual(sub, live)
})

const bothProfiles: Array<[string, () => any, typeof SUB | {}]> = [
  ["default", template, {}],
  ["subagents", subTemplate, SUB],
]
const pinMutations: Array<[string, (c: any) => void, RegExp]> = [
  ["per-agent model pin (build)", (c) => { c.agent.build = { model: "epyc-orchestrator/orchestrator" } }, /agent\.build\.model/],
  ["per-agent model pin (general)", (c) => { c.agent.general = { ...(c.agent.general ?? {}), model: "epyc-orchestrator/orchestrator" } }, /agent\.general\.model/],
  ["v2 agents map model pin", (c) => { c.agents = { build: { model: "epyc-orchestrator/orchestrator" } } }, /agents\.build\.model/],
  ["deprecated mode map model pin", (c) => { c.mode = { build: { model: "x/y" } } }, /mode\.build\.model/],
  ["mode-less custom agent with a model", (c) => { c.agent.scout = { model: "epyc-orchestrator/orchestrator" } }, /custom agent with no "mode"/],
  ["x_force_model on an agent's options", (c) => { c.agent.build = { options: { x_force_model: "coder" } } }, /agent\.build\.options\.x_force_model/],
  ["x_force_model in plugin staticKeys", (c) => { c.plugin[0][1].staticKeys.x_force_model = "coder" }, /x_force_model: x_force_\* pins are forbidden/],
  ["x_force_role in plugin staticKeys", (c) => { c.plugin[0][1].staticKeys.x_force_role = "architect" }, /x_force_role: x_force_\* pins are forbidden/],
  ["x_force_model in model options", (c) => { c.provider["epyc-orchestrator"].models.orchestrator.options = { x_force_model: "coder" } }, /x_force_\* pins are forbidden/],
]
for (const [profile, make, opts] of bothProfiles) {
  for (const [name, mutate, expected] of pinMutations) {
    test(`lint [${profile}] catches: ${name}`, () => {
      const c = make()
      mutate(c)
      const errs = lintConfig(c, opts)
      assert.ok(errs.some((e) => expected.test(e)), `${name}: got ${JSON.stringify(errs)}`)
    })
  }
}

const subMutations: Array<[string, (c: any) => void, RegExp]> = [
  ["depth 2", (c) => { c.subagent_depth = 2 }, /subagent_depth must be the integer 1/],
  ["depth 0", (c) => { c.subagent_depth = 0 }, /subagent_depth must be the integer 1/],
  ["depth missing", (c) => { delete c.subagent_depth }, /subagent_depth/],
  ["depth 1.5", (c) => { c.subagent_depth = 1.5 }, /subagent_depth/],
  ["task deny", (c) => { c.permission.task = "deny" }, /permission\.task must not be "deny"/],
  ["task missing (falls back to ask)", (c) => { delete c.permission.task }, /permission\.task must not be "deny" \(or missing\)/],
  ["task ask", (c) => { c.permission.task = "ask" }, /permission\.task must be "allow" or a scoped/],
  ["task allows a disabled agent", (c) => { c.permission.task = { "*": "deny", explore: "allow" } }, /permission\.task\.explore allows an agent/],
  ["task allows nothing", (c) => { c.permission.task = { "*": "deny" } }, /allows no enabled sub-agent/],
  ["compaction.auto on", (c) => { c.compaction.auto = true }, /compaction\.auto/],
  ["compaction.prune on", (c) => { c.compaction.prune = true }, /compaction\.prune/],
  ["share manual", (c) => { c.share = "manual" }, /share/],
  ["autoupdate on", (c) => { c.autoupdate = true }, /autoupdate/],
  ["title enabled", (c) => { delete c.agent.title }, /agent\.title/],
  ["all sub-agents disabled", (c) => { c.agent.general = { disable: true } }, /at least one sub-agent/],
  ["child may delegate", (c) => { delete c.agent.general.permission }, /agent\.general\.permission\.task must be "deny"/],
  ["stampAgentName off", (c) => { c.plugin[0][1].stampAgentName = false }, /stampAgentName must be true/],
  ["stampAgentName not boolean", (c) => { c.plugin[0][1].stampAgentName = "yes" }, /stampAgentName must be a boolean/],
  ["second model", (c) => { c.small_model = "epyc-orchestrator/fast"; c.provider["epyc-orchestrator"].models.fast = c.provider["epyc-orchestrator"].models.orchestrator }, /one logical model|exactly the one logical model/],
  ["extra provider", (c) => { c.enabled_providers.push("openai") }, /enabled_providers/],
  ["remote skills", (c) => { c.skills.urls = ["https://x"] }, /skills\.urls/],
  ["User-Agent missing", (c) => { delete c.provider["epyc-orchestrator"].options.headers }, /User-Agent/],
  ["output over cap", (c) => { c.provider["epyc-orchestrator"].models.orchestrator.limit.output = 64000 }, /limit\.output/],
]
for (const [name, mutate, expected] of subMutations) {
  test(`lint [subagents] catches: ${name}`, () => {
    const c = subTemplate()
    mutate(c)
    const errs = lintConfig(c, SUB)
    assert.ok(errs.some((e) => expected.test(e)), `${name}: got ${JSON.stringify(errs)}`)
  })
}

test("env lint [subagents] requires background sub-agents explicitly off", () => {
  const without = envText.replace("export OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=0", "")
  assert.deepEqual(lintEnv(without), [], "default profile does not require it")
  assert.ok(lintEnv(without, SUB).some((e) => e.includes("BACKGROUND_SUBAGENTS")))
  const on = envText.replace("OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=0", "OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=1")
  assert.ok(lintEnv(on, SUB).some((e) => e.includes("BACKGROUND_SUBAGENTS")))
})
