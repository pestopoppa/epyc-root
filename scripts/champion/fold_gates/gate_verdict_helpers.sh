# BEGIN GATE VERDICT HELPERS
gate_set_verdict() {
  local rc=$1
  if [ "$rc" -eq 0 ]; then GATE_VERDICT=PASS; else GATE_VERDICT=FAIL; fail=1; fi
}
count_ok_lines() {
  sed -E 's/\x1B\[[0-9;]*m//g' "$1" | awk 'index($0, " OK") { n++ } END { print n+0 }'
}
count_matching_lines() {
  local pattern=$1 file=$2
  sed -E 's/\x1B\[[0-9;]*m//g' "$file" | awk -v pattern="$pattern" '$0 ~ pattern { n++ } END { print n+0 }'
}
# END GATE VERDICT HELPERS
