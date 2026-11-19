/** Offline exact joins over a declared finite native capture window. No turn verdict. */
type Row = Record<string, any>
const nonempty = (value: unknown): value is string => typeof value === "string" && value.length > 0
const key = (...ids: string[]) => JSON.stringify(ids)

/** Keep every candidate: conflicting identities must never become last-write-wins. */
export function joinDispatchEvents(rows: Row[]) {
  const requests = new Map<string, Row[]>()
  const parents = new Map<string, Row[]>()
  const permissions = new Map<string, Row[]>()
  const insert = (map: Map<string, Row[]>, id: string, row: Row) => {
    map.set(id, [...(map.get(id) ?? []), row])
  }
  const valid = rows.filter(r => r.schema_version === "hs_td1.native_event.v1" &&
    nonempty(r.session_id) && nonempty(r.capture_id) && r.status !== "oversize")
  for (const row of valid) {
    const session = row.session_id
    if (row.kind === "request") {
      const message = row.native?.message
      if (row.phase === "pre_dispatch" && message?.role === "user" &&
          message.sessionID === session && nonempty(message.id) && row.turn_id === message.id)
        insert(requests, key(session, message.id), row)
    }
    if (row.kind === "assistant_parent" && row.native?.type === "message.updated") {
      const info = row.native.properties?.info
      if (info?.role === "assistant" && info.sessionID === session &&
          nonempty(info.id) && nonempty(info.parentID)) insert(parents, key(session, info.id), row)
    }
    if (row.kind === "policy_event" &&
        ["permission.asked", "permission.updated"].includes(row.native?.type)) {
      const props = row.native.properties
      if (props?.sessionID === session && nonempty(props.id)) insert(permissions, key(session, props.id), row)
    }
  }
  return rows.filter(r => r.kind === "policy_event").map(row => {
    const result: Row = { schema_version: "hs_td1.policy_join.v1", gate: false,
      scope: "tool_permission", session_id: row.session_id, capture_id: row.capture_id,
      status: "unknown", reason: "invalid_event", turn_id: null, decision: null,
      evidence_capture_ids: [row.capture_id], native: row.native }
    const unknown = (reason: string) => ({ ...result, reason })
    if (!valid.includes(row)) return unknown("invalid_event")
    const event = row.native
    const props = event?.properties
    if (props?.sessionID !== row.session_id) return unknown("session_mismatch")
    const reply = event?.type === "permission.replied"
    if (!reply && !["permission.asked", "permission.updated"].includes(event?.type))
      return unknown("unsupported_event")
    const id = reply ? props.requestID : props.id
    if (!nonempty(id)) return unknown("missing_request_id")
    const candidates = permissions.get(key(row.session_id, id)) ?? []
    if (candidates.length !== 1) return unknown(candidates.length ? "ambiguous_request" : "missing_request")
    const permission = candidates[0]
    const tool = permission.native.properties.tool
    if (!nonempty(tool?.messageID) || !nonempty(tool?.callID)) return unknown("missing_tool_identity")
    const messages = parents.get(key(row.session_id, tool.messageID)) ?? []
    const parentIDs = new Set(messages.map(m => m.native.properties.info.parentID))
    if (parentIDs.size !== 1) return unknown(parentIDs.size ? "ambiguous_parent" : "missing_parent")
    const parentID = messages[0].native.properties.info.parentID
    const users = requests.get(key(row.session_id, parentID)) ?? []
    if (users.length !== 1) return unknown(users.length ? "ambiguous_user_request" : "missing_user_request")
    result.turn_id = parentID
    result.permission_request_id = id
    result.assistant_message_id = tool.messageID
    result.call_id = tool.callID
    result.evidence_capture_ids = [...new Set([row.capture_id, permission.capture_id,
      ...messages.map(m => m.capture_id), users[0].capture_id])]
    result.status = "joined"
    // Asked is not an allow; a reply is scoped to this permission request only.
    result.reason = reply ? "explicit_reply" : "awaiting_reply"
    if (reply) {
      const replies = valid.filter(r => r.kind === "policy_event" &&
        r.native?.type === "permission.replied" && r.session_id === row.session_id &&
        r.native.properties?.sessionID === row.session_id && r.native.properties?.requestID === id)
      if (replies.length !== 1) return { ...result, status: "unknown", reason: "ambiguous_reply" }
      if (["once", "always"].includes(props.reply)) result.decision = "permissive"
      else if (props.reply === "reject") result.decision = "restrictive"
      else return { ...result, status: "unknown", reason: "unsupported_reply" }
    }
    return result
  })
}
