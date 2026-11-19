import { test } from "node:test"
import assert from "node:assert/strict"
import { joinDispatchEvents } from "../src/dispatch-join.ts"

function fixture() {
  const row = (capture_id: string, kind: string, native: any, extra = {}) => ({
    schema_version: "hs_td1.native_event.v1", session_id: "s", capture_id,
    kind, native, status: "captured", ...extra })
  return [
    row("u", "request", { message: { id: "u1", sessionID: "s", role: "user" } },
      { phase: "pre_dispatch", turn_id: "u1" }),
    row("a", "assistant_parent", { type: "message.updated", properties: { info: {
      id: "a1", parentID: "u1", sessionID: "s", role: "assistant" } } }),
    row("p", "policy_event", { type: "permission.asked", properties: {
      id: "p1", sessionID: "s", tool: { messageID: "a1", callID: "c1" } } }),
    row("r", "policy_event", { type: "permission.replied", properties: {
      requestID: "p1", sessionID: "s", reply: "once" } }),
  ]
}

test("exact joins work out of order, preserve native payload and never choose latest user", () => {
  const input = fixture()
  const later = structuredClone(input[0])
  later.capture_id = "later"
  later.turn_id = later.native.message.id = "u2"
  input.push(later)
  const before = structuredClone(input)
  const results = joinDispatchEvents(input.reverse())
  const reply = results.find(r => r.capture_id === "r")!
  assert.equal(reply.turn_id, "u1")
  assert.equal(reply.decision, "permissive")
  assert.equal(reply.scope, "tool_permission")
  assert.deepEqual(new Set(reply.evidence_capture_ids), new Set(["r", "p", "a", "u"]))
  assert.equal(results.find(r => r.capture_id === "p")!.decision, null)
  assert.deepEqual(input, before.reverse())
})

for (const [reply, decision] of [["always", "permissive"], ["reject", "restrictive"]]) {
  test(`explicit ${reply} maps only the identified tool permission`, () => {
    const input = fixture()
    input[3].native.properties.reply = reply
    assert.equal(joinDispatchEvents(input)[1].decision, decision)
  })
}

for (const [index, reason] of [[0, "missing_user_request"], [1, "missing_parent"], [2, "missing_request"]] as const) {
  test(`missing evidence remains unknown: ${reason}`, () => {
    const input = fixture()
    input.splice(index, 1)
    const reply = joinDispatchEvents(input).find(r => r.capture_id === "r")!
    assert.equal(reply.status, "unknown")
    assert.equal(reply.reason, reason)
    assert.equal(reply.decision, null)
    assert.equal(reply.turn_id, null)
  })
}

for (const [index, reason] of [[0, "ambiguous_user_request"], [2, "ambiguous_request"], [3, "ambiguous_reply"]] as const) {
  test(`duplicate evidence remains unknown: ${reason}`, () => {
    const input = fixture()
    input.push({ ...structuredClone(input[index]), capture_id: "duplicate" })
    const reply = joinDispatchEvents(input).find(r => r.capture_id === "r")!
    assert.equal(reply.status, "unknown")
    assert.equal(reply.reason, reason)
    assert.equal(reply.decision, null)
  })
}

test("conflicting assistant parents and cross-session identities cannot join", () => {
  const input = fixture()
  const other = structuredClone(input[1])
  other.native.properties.info.parentID = "u2"
  input.push(other)
  assert.equal(joinDispatchEvents(input)[1].reason, "ambiguous_parent")
  input.pop()
  input[1].native.properties.info.sessionID = "other"
  assert.equal(joinDispatchEvents(input)[1].reason, "missing_parent")
  input[3].native.properties.sessionID = "other"
  assert.equal(joinDispatchEvents(input)[1].reason, "session_mismatch")
})

test("unknown replies, oversize requests, and legacy requests without tool IDs stay unknown", () => {
  const input = fixture()
  input[3].native.properties.reply = "allow"
  assert.equal(joinDispatchEvents(input)[1].reason, "unsupported_reply")
  input[0].status = "oversize"
  assert.equal(joinDispatchEvents(input)[1].reason, "missing_user_request")
  input[2].native.type = "permission.updated"
  delete input[2].native.properties.tool
  assert.equal(joinDispatchEvents(input)[1].reason, "missing_tool_identity")
})

test("repeated assistant updates with same parent are consistent; event absence gives no policy", () => {
  const input = fixture()
  input.push({ ...structuredClone(input[1]), capture_id: "a-update" })
  const reply = joinDispatchEvents(input)[1]
  assert.equal(reply.status, "joined")
  assert.ok(reply.evidence_capture_ids.includes("a-update"))
  assert.deepEqual(joinDispatchEvents(input.filter(r => r.kind !== "policy_event")), [])
})
