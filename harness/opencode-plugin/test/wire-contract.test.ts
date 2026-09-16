/**
 * Wire-contract test: do the plugin's keys land at the TOP LEVEL of the JSON body?
 *
 * It uses the exact SDK OpenCode pins (@ai-sdk/openai-compatible 2.0.41, with
 * provider 3.0.8 and provider-utils 4.0.23 per bun.lock) and a capturing fake
 * fetch. No network, no model, no inference.
 *
 * The SDK is not vendored into the repo. Point EPYC_OPENCODE_SDK_DIR at a
 * node_modules parent that has it installed, e.g.
 *   npm install --ignore-scripts --save-exact @ai-sdk/openai-compatible@2.0.41
 * With EPYC_OPENCODE_CONTRACT=1 a missing SDK is a FAILURE, not a skip. Use that in the
 * P0.3/P0.4 gate, so the contract is never "passed" vacuously.
 *
 * The namespacing step mirrors ProviderTransform.providerOptions for
 * @ai-sdk/openai-compatible at 350c726aa (provider/transform.ts:1450-1465):
 * key = providerID.split(".")[0].
 */
import { test } from "node:test"
import assert from "node:assert/strict"
import { createRequire } from "node:module"
import { join } from "node:path"
import { applyChatParams, parseOptions } from "../src/lib.ts"

const sdkDir = process.env.EPYC_OPENCODE_SDK_DIR
const required = process.env.EPYC_OPENCODE_CONTRACT === "1"

function loadSdk(): any | undefined {
  if (!sdkDir) return undefined
  try {
    const req = createRequire(join(sdkDir, "package.json"))
    const pkg = req("@ai-sdk/openai-compatible/package.json")
    assert.equal(pkg.version, "2.0.41", "wire contract must run against the OpenCode-pinned SDK")
    return req("@ai-sdk/openai-compatible")
  } catch (e) {
    if (required) throw e
    return undefined
  }
}

const sdk = loadSdk()

test("wire contract: x_* keys arrive top-level and unrenamed", { skip: !sdk && !required && "EPYC_OPENCODE_SDK_DIR not set" }, async () => {
  assert.ok(sdk, "SDK required (EPYC_OPENCODE_CONTRACT=1) but not loadable")
  const providerID = "epyc-orchestrator"
  const bodies: any[] = []
  const fakeFetch = async (_url: string, init: any) => {
    bodies.push(JSON.parse(init.body))
    return new Response(
      JSON.stringify({
        id: "x", object: "chat.completion", created: 0, model: "orchestrator",
        choices: [{ index: 0, message: { role: "assistant", content: "ok" }, finish_reason: "stop" }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    )
  }
  const provider = sdk.createOpenAICompatible({ name: providerID, baseURL: "http://fake.invalid/v1", fetch: fakeFetch })
  const model = provider.languageModel("orchestrator")

  const opts = parseOptions({ userId: "u1", staticKeys: { x_memory: "off", x_show_routing: true } })
  const output = { options: { reasoningEffort: "low" } as Record<string, unknown> }
  applyChatParams(opts, { sessionID: "ses_wire", model: { providerID } }, output)
  const providerOptions = { [providerID.split(".")[0]]: output.options }

  await model.doGenerate({
    prompt: [{ role: "user", content: [{ type: "text", text: "hi" }] }],
    providerOptions,
    maxOutputTokens: 32000,
  })

  assert.equal(bodies.length, 1)
  const body = bodies[0]
  assert.equal(body.x_session_id, "ses_wire")
  assert.equal(body.x_user_id, "u1")
  assert.equal(body.x_tool_mode, "client")
  assert.equal(body.x_memory, "off")
  assert.equal(body.x_show_routing, true)
  assert.equal(body.reasoning_effort, "low", "schema keys are mapped, not spread")
  assert.equal(body.reasoningEffort, undefined)
  assert.equal(body[providerID], undefined, "no nested namespace object")
  assert.equal(body.xSessionId, undefined, "no camelCase rename")
  assert.equal(body.max_tokens, 32000)
})

test("wire contract: a stream request carries the same keys", { skip: !sdk && !required && "EPYC_OPENCODE_SDK_DIR not set" }, async () => {
  assert.ok(sdk)
  const bodies: any[] = []
  const fakeFetch = async (_url: string, init: any) => {
    bodies.push(JSON.parse(init.body))
    const sse = 'data: {"id":"x","object":"chat.completion.chunk","created":0,"model":"m","choices":[{"index":0,"delta":{"role":"assistant","content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
    return new Response(sse, { status: 200, headers: { "content-type": "text/event-stream" } })
  }
  const provider = sdk.createOpenAICompatible({ name: "epyc-orchestrator", baseURL: "http://fake.invalid/v1", fetch: fakeFetch })
  const output = { options: {} as Record<string, unknown> }
  applyChatParams(parseOptions({ userId: "u2" }), { sessionID: "ses_s", model: { providerID: "epyc-orchestrator" } }, output)
  const { stream } = await provider.languageModel("orchestrator").doStream({
    prompt: [{ role: "user", content: [{ type: "text", text: "hi" }] }],
    providerOptions: { "epyc-orchestrator": output.options },
  })
  const reader = stream.getReader()
  while (!(await reader.read()).done) {}
  assert.equal(bodies[0].stream, true)
  assert.equal(bodies[0].x_session_id, "ses_s")
  assert.equal(bodies[0].x_user_id, "u2")
  assert.equal(bodies[0].x_tool_mode, "client")
})
