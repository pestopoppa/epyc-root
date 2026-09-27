import { test } from "node:test"
import assert from "node:assert/strict"
import {
  agentNameKey,
  applyChatParams,
  DYNAMIC_KEYS,
  EpycPluginConfigError,
  parseOptions,
  requestKeys,
  shouldStamp,
  stampToolArgs,
} from "../src/lib.ts"

const base = { userId: "daniele" }

test("parseOptions: defaults and required userId", () => {
  const o = parseOptions(base)
  assert.deepEqual(o.providerIDs, ["epyc-orchestrator"])
  assert.deepEqual(o.stampPrefixes, ["orchestrator_", "memory_"])
  assert.equal(o.toolMode, "client")
  assert.deepEqual(o.staticKeys, {})
  assert.throws(() => parseOptions({}), EpycPluginConfigError)
  assert.throws(() => parseOptions({ userId: "  " }), EpycPluginConfigError)
  assert.equal(parseOptions({}, { EPYC_USER_ID: "from-env" }).userId, "from-env")
  assert.equal(parseOptions(undefined, { EPYC_USER_ID: "u" }).userId, "u")
})

test("parseOptions: refuses unknown options, bad provider IDs, bad prefixes", () => {
  assert.throws(() => parseOptions({ ...base, userID: "typo" }), /unknown option "userID"/)
  assert.throws(() => parseOptions({ ...base, providerIDs: ["epyc.orch"] }), /providerID/)
  assert.throws(() => parseOptions({ ...base, providerIDs: ["opencode-x"] }), /opencode/)
  assert.throws(() => parseOptions({ ...base, providerIDs: [] }), /non-empty/)
  assert.throws(() => parseOptions({ ...base, stampPrefixes: ["orchestrator"] }), /stamp prefix/)
  assert.throws(() => parseOptions("nope"), /must be an object/)
})

test("parseOptions: static keys must be x_* scalars and cannot shadow dynamic keys", () => {
  const o = parseOptions({ ...base, staticKeys: { x_memory: "on", x_show_routing: true, x_max_n: 3 } })
  assert.deepEqual(o.staticKeys, { x_memory: "on", x_show_routing: true, x_max_n: 3 })
  for (const k of ["x_session_id", "x_user_id", "x_tool_mode"]) {
    assert.throws(() => parseOptions({ ...base, staticKeys: { [k]: "spoof" } }), /owned by the plugin/)
  }
  assert.throws(() => parseOptions({ ...base, staticKeys: { memory: "on" } }), /must match/)
  assert.throws(() => parseOptions({ ...base, staticKeys: { x_Memory: "on" } }), /must match/)
  assert.throws(() => parseOptions({ ...base, staticKeys: { x_obj: { a: 1 } } }), /string, finite number or boolean/)
  assert.throws(() => parseOptions({ ...base, staticKeys: { x_n: Number.NaN } }), /finite/)
})

test("requestKeys: dynamic keys present; empty session refused", () => {
  const o = parseOptions({ ...base, staticKeys: { x_memory: "off" } })
  assert.deepEqual(requestKeys(o, "ses_1"), {
    x_memory: "off",
    x_session_id: "ses_1",
    x_user_id: "daniele",
    x_tool_mode: "client",
  })
  assert.throws(() => requestKeys(o, ""), /empty sessionID/)
})

test("applyChatParams: mutates options for our provider only, preserves existing options", () => {
  const o = parseOptions(base)
  const output = { options: { reasoningEffort: "low" } as Record<string, unknown> }
  const before = output.options
  assert.equal(applyChatParams(o, { sessionID: "ses_A", model: { providerID: "epyc-orchestrator" } }, output), true)
  assert.equal(output.options, before, "same object (in-place)")
  assert.deepEqual(output.options, {
    reasoningEffort: "low",
    x_session_id: "ses_A",
    x_user_id: "daniele",
    x_tool_mode: "client",
  })

  const other = { options: {} as Record<string, unknown> }
  assert.equal(applyChatParams(o, { sessionID: "ses_A", model: { providerID: "anthropic" } }, other), false)
  assert.deepEqual(other.options, {})
})

test("applyChatParams: overwrites a pre-existing x_session_id (e.g. from per-model options)", () => {
  const o = parseOptions(base)
  const output = { options: { x_session_id: "stale" } as Record<string, unknown> }
  applyChatParams(o, { sessionID: "ses_B", model: { providerID: "epyc-orchestrator" } }, output)
  assert.equal(output.options.x_session_id, "ses_B")
})

test("shouldStamp: prefix = '<mcp server>_', matches OpenCode's MCP key format", () => {
  const o = parseOptions(base)
  assert.equal(shouldStamp(o, "orchestrator_orchestrator_chat"), true)
  assert.equal(shouldStamp(o, "memory_search"), true)
  assert.equal(shouldStamp(o, "orchestrator_"), false)
  assert.equal(shouldStamp(o, "bash"), false)
  assert.equal(shouldStamp(o, "read"), false)
  assert.equal(shouldStamp(o, "github_orchestrator_x"), false)
  assert.equal(shouldStamp(o, "memoryx_search"), false)
})

test("stampToolArgs: in place, overwrites model-supplied session_id, fails closed on bad args", () => {
  const o = parseOptions(base)
  const args = { query: "q", session_id: "model-chose-this" }
  const output = { args }
  assert.equal(stampToolArgs(o, { tool: "memory_search", sessionID: "ses_C" }, output), true)
  assert.equal(output.args, args, "same object")
  assert.equal(args.session_id, "ses_C")

  const untouched = { command: "ls" }
  assert.equal(stampToolArgs(o, { tool: "bash", sessionID: "ses_C" }, { args: untouched }), false)
  assert.deepEqual(untouched, { command: "ls" })

  assert.throws(() => stampToolArgs(o, { tool: "memory_search", sessionID: "ses_C" }, { args: null }), /not an object/)
  assert.throws(() => stampToolArgs(o, { tool: "memory_search", sessionID: "ses_C" }, { args: [] }), /not an object/)
  assert.throws(() => stampToolArgs(o, { tool: "memory_search", sessionID: "" }, { args: {} }), /empty sessionID/)
})

// ── HS-19a: stampAgentName (opt-in, default off) ─────────────────────────────────

test("stampAgentName: default false; must be a boolean", () => {
  assert.equal(parseOptions(base).stampAgentName, false)
  assert.equal(parseOptions({ ...base, stampAgentName: true }).stampAgentName, true)
  assert.equal(parseOptions({ ...base, stampAgentName: false }).stampAgentName, false)
  for (const bad of ["true", 1, null, {}]) {
    assert.throws(() => parseOptions({ ...base, stampAgentName: bad }), /stampAgentName must be a boolean/)
  }
})

test("stampAgentName absent: emitted keys are byte-identical to the pre-HS-19a set", () => {
  const o = parseOptions({ ...base, staticKeys: { x_show_routing: true } })
  const expected = '{"x_show_routing":true,"x_session_id":"ses_1","x_user_id":"daniele","x_tool_mode":"client"}'
  assert.equal(JSON.stringify(requestKeys(o, "ses_1")), expected)
  assert.equal(JSON.stringify(requestKeys(o, "ses_1", "general")), expected, "agent ignored when off")
  const output = { options: { reasoningEffort: "low", x_agent_name: "from-options" } as Record<string, unknown> }
  applyChatParams(o, { sessionID: "ses_1", agent: "general", model: { providerID: "epyc-orchestrator" } }, output)
  assert.equal(
    JSON.stringify(output.options),
    '{"reasoningEffort":"low","x_agent_name":"from-options","x_show_routing":true,"x_session_id":"ses_1","x_user_id":"daniele","x_tool_mode":"client"}',
    "with the option off, options pass through exactly as before",
  )
})

test("stampAgentName on: x_agent_name = chat.params agent, after the identity keys", () => {
  const o = parseOptions({ ...base, stampAgentName: true })
  assert.equal(
    JSON.stringify(requestKeys(o, "ses_child", "general")),
    '{"x_session_id":"ses_child","x_user_id":"daniele","x_tool_mode":"client","x_agent_name":"general"}',
  )
  const output = { options: {} as Record<string, unknown> }
  applyChatParams(o, { sessionID: "ses_P", agent: "build", model: { providerID: "epyc-orchestrator" } }, output)
  assert.equal(output.options.x_agent_name, "build")
  assert.equal(output.options.x_parent_session_id, undefined, "the plugin never sets the parent link")
})

test("stampAgentName on: a bad or empty agent name is omitted, never thrown, never stale", () => {
  const o = parseOptions({ ...base, stampAgentName: true })
  for (const bad of ["", " general", "-lead", "a/b", "x".repeat(65), "gen eral", undefined, 7, null]) {
    assert.equal(agentNameKey(bad), undefined, String(bad))
    const keys = requestKeys(o, "ses_1", bad)
    assert.equal("x_agent_name" in keys, false, String(bad))
    const output = { options: { x_agent_name: "stale" } as Record<string, unknown> }
    applyChatParams(o, { sessionID: "ses_1", agent: bad, model: { providerID: "epyc-orchestrator" } }, output)
    assert.equal("x_agent_name" in output.options, false, `stale value survived for ${String(bad)}`)
  }
  for (const good of ["build", "general", "a", "Agent_1.v2-x", "x".repeat(64)]) assert.equal(agentNameKey(good), good)
})

test("x_agent_name and x_parent_session_id are plugin-owned: config cannot set them", () => {
  assert.ok((DYNAMIC_KEYS as readonly string[]).includes("x_agent_name"))
  assert.ok((DYNAMIC_KEYS as readonly string[]).includes("x_parent_session_id"))
  for (const k of ["x_agent_name", "x_parent_session_id"]) {
    assert.throws(() => parseOptions({ ...base, staticKeys: { [k]: "spoof" } }), /owned by the plugin/)
    assert.throws(() => parseOptions({ ...base, stampAgentName: true, staticKeys: { [k]: "spoof" } }), /owned by the plugin/)
  }
})
