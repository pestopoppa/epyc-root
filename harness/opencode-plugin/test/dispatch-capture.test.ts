import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdtemp, readFile, rm, stat, chmod, symlink } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { createDispatchCapture } from "../src/dispatch-capture.ts"
import { server } from "../src/index.ts"

const request = () => ({ message: { id: "u1", sessionID: "s", role: "user" },
  parts: [{ type: "text", text: "Read README" }] })
const asked = { type: "permission.asked", properties: { id: "p1", sessionID: "s",
  tool: { messageID: "assistant1", callID: "call1" }, permission: "read", patterns: ["README"] } }
const replied = { type: "permission.replied", properties: { sessionID: "s", requestID: "p1", reply: "once" } }
const rows = async (path: string) => (await readFile(path, "utf8")).trim().split("\n").map(JSON.parse)

async function scratch(run: (dir: string) => Promise<void>) {
  const dir = await mkdtemp(join(tmpdir(), "td1-native-"))
  try { await run(dir) } finally { await rm(dir, { recursive: true }) }
}

test("default-off capture does not inspect payloads or create output", async () => {
  const capture = createDispatchCapture(undefined)
  assert.equal(capture.request({ sessionID: "s" }, null as any), undefined)
  assert.equal(capture.event(null as any), undefined)
})

test("raw request freezes before dispatch; exact permission IDs survive without invented turn join", async () => {
  await scratch(async dir => {
    const path = join(dir, "native.jsonl")
    const capture = createDispatchCapture(path)
    const output = request()
    const write = capture.request({ sessionID: "s" }, output)
    output.parts[0].text = "mutated after hook"
    await write
    await capture.event(asked)
    await capture.event(replied)
    const records = await rows(path)
    assert.equal(records.length, 3)
    assert.equal(records[0].phase, "pre_dispatch")
    assert.equal(records[0].turn_id, "u1")
    assert.equal(records[0].native.parts[0].text, "Read README")
    assert.deepEqual(records[1].native, asked)
    assert.deepEqual(records[2].native, replied)
    for (const row of records.slice(1)) {
      assert.equal(row.status, "unjoined")
      assert.equal(row.turn_id, null)
      assert.equal(row.harness_decision, undefined)
    }
    assert.equal(new Set(records.map(r => r.capture_id)).size, 3)
    assert.ok(records.every(r => r.gate === false))
    assert.equal((await stat(path)).mode & 0o777, 0o600)
  })
})

test("bad request identities and unrelated native events never create records", async () => {
  await scratch(async dir => {
    const path = join(dir, "native.jsonl")
    const capture = createDispatchCapture(path)
    await capture.request({ sessionID: "other" }, request())
    await capture.request({ sessionID: "s" }, { ...request(), message: { ...request().message, id: "" } })
    await capture.event({ type: "session.status", properties: { sessionID: "s" } })
    await capture.event({ ...asked, properties: {} })
    await assert.rejects(readFile(path), { code: "ENOENT" })
  })
})

test("native assistant parent updates retain exact lineage for offline permission joins", async () => {
  await scratch(async dir => {
    const path = join(dir, "native.jsonl")
    const capture = createDispatchCapture(path)
    const event = { type: "message.updated", properties: { info: {
      id: "assistant1", parentID: "u1", sessionID: "s", role: "assistant" } } }
    await capture.event(event)
    await capture.event({ ...event, properties: { info: { ...event.properties.info, role: "user" } } })
    const records = await rows(path)
    assert.equal(records.length, 1)
    assert.equal(records[0].kind, "assistant_parent")
    assert.equal(records[0].turn_id, null)
    assert.deepEqual(records[0].native, event)
  })
})

test("oversize requests remain explicit unknown metadata, with no partial private content", async () => {
  await scratch(async dir => {
    const path = join(dir, "native.jsonl")
    const capture = createDispatchCapture(path)
    const output = request()
    output.parts[0].text = "secret".repeat(30000)
    await capture.request({ sessionID: "s" }, output)
    const [row] = await rows(path)
    assert.equal(row.status, "oversize")
    assert.equal(row.turn_id, "u1")
    assert.equal(row.native, undefined)
  })
})

test("insecure sink, symlinks and relative paths are refused without rejecting dispatch", async () => {
  await scratch(async dir => {
    const path = join(dir, "native.jsonl")
    await createDispatchCapture(path).request({ sessionID: "s" }, request())
    const before = await readFile(path, "utf8")
    await chmod(path, 0o644)
    const warnings: string[] = []
    const warn = (s: string) => warnings.push(s)
    await createDispatchCapture(path, warn).event(replied)
    await symlink(path, join(dir, "link"))
    await createDispatchCapture(join(dir, "link"), warn).event(replied)
    await createDispatchCapture("relative.jsonl", warn).event(replied)
    assert.equal(warnings.length, 3)
    assert.equal(await readFile(path, "utf8"), before)
    await createDispatchCapture(path, () => { throw Error("bad logger") }).event(replied)
  })
})

test("four-write bound drops excess events and releases slots after failure", async () => {
  const warnings: string[] = []
  const capture = createDispatchCapture("/missing-td1-directory/native.jsonl", s => warnings.push(s))
  const jobs = Array.from({ length: 4 }, () => capture.event(asked))
  assert.equal(capture.event(replied), undefined)
  assert.ok(warnings[0].includes("four writes pending"))
  await Promise.all(jobs)
  await capture.event(replied)
  assert.equal(warnings.length, 6)
})

test("plugin chat.message and event hooks write before returning and leave native outputs unchanged", async () => {
  await scratch(async dir => {
    const previous = process.env.EPYC_DISPATCH_CAPTURE_LOG
    const path = join(dir, "native.jsonl")
    process.env.EPYC_DISPATCH_CAPTURE_LOG = path
    try {
      const hooks = await server({} as any, { userId: "u" }) as any
      const output = request()
      const original = structuredClone(output)
      await hooks["chat.message"]({ sessionID: "s" }, output)
      assert.equal((await rows(path)).length, 1)
      assert.deepEqual(output, original)
      await hooks.event({ event: asked })
      await hooks.event({ event: replied })
      assert.equal((await rows(path)).length, 3)
    } finally {
      if (previous === undefined) delete process.env.EPYC_DISPATCH_CAPTURE_LOG
      else process.env.EPYC_DISPATCH_CAPTURE_LOG = previous
    }
  })
})
