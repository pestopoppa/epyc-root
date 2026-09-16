/**
 * Offline tests of the plugin module through OpenCode's hook-calling contract.
 *
 * OpenCode has no public plugin test harness (packages/plugin has no test dir, and
 * packages/opencode/test builds the whole Effect service graph). So these tests mock
 * the two call sites exactly as they are written at 350c726aa:
 *   - Plugin.trigger (plugin/index.ts:284-297): every hook gets the SAME output object,
 *     and trigger returns it.
 *   - session/llm/request.ts:114-131: `params = trigger("chat.params", …, {…, options})`,
 *     then `params.options` is read.
 *   - session/tools.ts:401-409: `trigger("tool.execute.before", {tool, sessionID, callID}, { args })`,
 *     then `execute(args, opts)` runs with the LOCAL `args` binding.
 *   - plugin/shared.ts:278-315: a path plugin default-exports { id, server }.
 */
import { test } from "node:test"
import assert from "node:assert/strict"
import plugin, { server } from "../src/index.ts"

type AnyHooks = Record<string, ((input: any, output: any) => Promise<void>) | undefined>

const fakeInput = {} as any // the plugin does not use client/$/directory

async function trigger(hooks: AnyHooks[], name: string, input: any, output: any) {
  for (const h of hooks) {
    const fn = h[name]
    if (fn) await fn(input, output)
  }
  return output
}

const model = (providerID: string) => ({ providerID, id: "orchestrator", api: { npm: "@ai-sdk/openai-compatible" } })

test("module shape matches OpenCode's path-plugin loader", () => {
  assert.equal(typeof plugin, "object")
  assert.equal(plugin.id, "epyc-orchestrator")
  assert.equal(plugin.server, server)
  assert.equal(typeof plugin.server, "function")
  assert.equal((plugin as any).tui, undefined)
})

test("chat.params: request.ts pattern yields x_* keys in params.options", async () => {
  const hooks = (await server(fakeInput, { userId: "u1", staticKeys: { x_memory: "on" } })) as AnyHooks
  const options = { someOther: 1 }
  const params = await trigger([hooks], "chat.params",
    { sessionID: "ses_main", agent: "build", model: model("epyc-orchestrator"), provider: {}, message: {} },
    { temperature: 0, topP: 1, topK: 0, maxOutputTokens: 32000, options })
  assert.deepEqual(params.options, {
    someOther: 1,
    x_memory: "on",
    x_session_id: "ses_main",
    x_user_id: "u1",
    x_tool_mode: "client",
  })
})

test("chat.params: title-style small call and retry re-trigger both get keys", async () => {
  const hooks = (await server(fakeInput, { userId: "u1" })) as AnyHooks
  // Title call: agent "title", small options (empty for openai-compatible), same session id.
  const first = await trigger([hooks], "chat.params",
    { sessionID: "ses_T", agent: "title", model: model("epyc-orchestrator"), provider: {}, message: {} },
    { options: {} })
  assert.equal(first.options.x_session_id, "ses_T")
  // Retry: SessionRetry re-runs llm.stream → prepare → a fresh trigger with fresh options.
  const retry = await trigger([hooks], "chat.params",
    { sessionID: "ses_T", agent: "title", model: model("epyc-orchestrator"), provider: {}, message: {} },
    { options: {} })
  assert.equal(retry.options.x_session_id, "ses_T")
})

test("chat.params: other providers untouched (built-in plugins co-exist)", async () => {
  const builtin: AnyHooks = {
    "chat.params": async (input, output) => {
      if (input.model.providerID !== "openai") return
      output.maxOutputTokens = undefined
    },
  }
  const hooks = (await server(fakeInput, { userId: "u1" })) as AnyHooks
  const out = await trigger([builtin, hooks], "chat.params",
    { sessionID: "s", agent: "build", model: model("openai"), provider: {}, message: {} },
    { maxOutputTokens: 5, options: {} })
  assert.deepEqual(out.options, {})
  assert.equal(out.maxOutputTokens, undefined)
})

test("tool.execute.before: tools.ts pattern, so execute() sees session_id", async () => {
  const hooks = (await server(fakeInput, { userId: "u1" })) as AnyHooks
  const seen: any[] = []
  const execute = async (a: any) => { seen.push({ ...a }) }

  for (const [tool, expectStamp] of [
    ["orchestrator_orchestrator_chat", true],
    ["memory_remember", true],
    ["bash", false],
    ["github_search", false],
  ] as const) {
    const args: Record<string, unknown> = { q: tool }
    await trigger([hooks], "tool.execute.before", { tool, sessionID: "ses_X", callID: "c1" }, { args })
    await execute(args)
    assert.equal(seen.at(-1).session_id, expectStamp ? "ses_X" : undefined, tool)
  }
})

test("fail-closed: bad options never throw at load, but break OUR requests loudly", async () => {
  const saved = process.env.EPYC_USER_ID
  delete process.env.EPYC_USER_ID
  const errSpy = console.error
  console.error = () => {}
  try {
    const hooks = (await server(fakeInput, {})) as AnyHooks // missing userId
    await assert.rejects(
      trigger([hooks], "chat.params",
        { sessionID: "s", agent: "build", model: model("epyc-orchestrator"), provider: {}, message: {} },
        { options: {} }),
      /userId is required/,
    )
    // Unrelated provider is not broken by our config error.
    const out = await trigger([hooks], "chat.params",
      { sessionID: "s", agent: "build", model: model("anthropic"), provider: {}, message: {} },
      { options: {} })
    assert.deepEqual(out.options, {})
    await assert.rejects(
      trigger([hooks], "tool.execute.before", { tool: "memory_x", sessionID: "s", callID: "c" }, { args: {} }),
      /userId is required/,
    )
    await trigger([hooks], "tool.execute.before", { tool: "bash", sessionID: "s", callID: "c" }, { args: {} })

    // A custom providerID list is honoured on the error path too.
    const hooks2 = (await server(fakeInput, { providerIDs: ["epyc-lab"] })) as AnyHooks
    await assert.rejects(
      trigger([hooks2], "chat.params",
        { sessionID: "s", agent: "build", model: model("epyc-lab"), provider: {}, message: {} },
        { options: {} }),
      /userId is required/,
    )
  } finally {
    console.error = errSpy
    if (saved !== undefined) process.env.EPYC_USER_ID = saved
  }
})
