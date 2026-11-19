import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdtemp, readFile, rm, stat } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { captureTurn, createTurnCapture } from "../src/turn-capture.ts"

const user = (id = "u1") => ({ info: { id, sessionID: "s", role: "user", time: { created: 1 } },
  parts: [{ type: "text", text: "Compute 17+26" }] })
const answer = (id = "a1", extra = {}) => ({ info: { id, parentID: "u1", sessionID: "s",
  role: "assistant", time: { created: 2, completed: 3 }, ...extra },
  parts: [{ type: "text", text: "42" }] })

test("native parent identity, tool evidence and unknown correctness survive capture", () => {
  const tool = answer("tool", { time: { created: 1.5, completed: 2 } })
  tool.parts = [{ type: "tool", text: "observed check" }]
  const row = captureTurn("s", [answer(), user("wrong-user"), tool, user()])!
  assert.equal(row.status, "captured")
  assert.equal(row.parent_id, "u1")
  assert.equal(row.reference_satisfied, null)
  assert.equal(row.gate, false)
  assert.equal(row.messages.length, 3)
  assert.ok(row.messages.includes(tool))
})

test("missing parents, error turns, summaries and incomplete latest turns are not successes", () => {
  assert.equal(captureTurn("s", [user("other"), answer()])!.status, "missing_parent")
  assert.equal(captureTurn("s", [user(), answer("a", { error: { name: "abort" } })])!.status, "turn_error")
  assert.equal(captureTurn("s", [user(), answer("a", { summary: true })]), undefined)
  assert.equal(captureTurn("s", [user(), answer(), answer("new", { time: { created: 4 } })]), undefined)
})

test("default-off capture never reads the session", () => {
  const client = { session: { messages: async () => { throw new Error("must not call") } } }
  assert.equal(createTurnCapture(client, undefined).idle("s"), undefined)
})

test("bounded native read, private sink, duplicate suppression and oversize unknown", async () => {
  const dir = await mkdtemp(join(tmpdir(), "td2-capture-"))
  const sink = join(dir, "turns.jsonl")
  let messages = [user(), answer()]
  const client = { session: { messages: async (options: any) => {
    assert.deepEqual(options.path, { id: "s" })
    assert.equal(options.query.limit, 100)
    assert.ok(options.signal instanceof AbortSignal)
    return { data: messages }
  } } }
  try {
    const capture = createTurnCapture(client, sink)
    await capture.idle("s")
    await capture.idle("s")
    assert.equal((await readFile(sink, "utf8")).trim().split("\n").length, 1)
    assert.equal((await stat(sink)).mode & 0o777, 0o600)
    const huge = answer("a2", { time: { created: 5, completed: 6 } })
    huge.parts[0].text = "x".repeat(140000)
    messages = [user(), huge]
    await capture.idle("s")
    const rows = (await readFile(sink, "utf8")).trim().split("\n").map(JSON.parse)
    assert.equal(rows[1].status, "oversize")
    assert.deepEqual(rows[1].messages, [])
    assert.equal(rows[1].reference_satisfied, null)
  } finally { await rm(dir, { recursive: true }) }
})

test("four-read bound drops excess work without queueing or blocking", async () => {
  const release: Array<(value: any) => void> = []
  const warnings: string[] = []
  const client = { session: { messages: () => new Promise<any>(resolve => release.push(resolve)) } }
  const capture = createTurnCapture(client, "/unused", warning => warnings.push(warning))
  const jobs = ["1", "2", "3", "4"].map(s => capture.idle(s))
  assert.equal(capture.idle("1"), undefined)
  assert.equal(capture.idle("5"), undefined)
  assert.equal(release.length, 4)
  assert.equal(warnings.length, 1)
  release.forEach(resolve => resolve({ data: [] }))
  await Promise.all(jobs)
})

test("sink and transport failures remain non-gating and permit a subsequent attempt", async () => {
  const warnings: string[] = []
  let calls = 0
  const client = { session: { messages: async () => {
    if (++calls === 1) throw new Error("transport down")
    return { data: [user(), answer()] }
  } } }
  const capture = createTurnCapture(client, "/dev/null/no-file", warning => warnings.push(warning))
  await capture.idle("s")
  await capture.idle("s")
  assert.equal(warnings.length, 2)
  assert.equal(calls, 2)
})
