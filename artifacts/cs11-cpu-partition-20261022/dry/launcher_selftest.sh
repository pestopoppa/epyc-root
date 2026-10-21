#!/bin/bash
# Self-test of chained_launch.sh gating logic on a stubbed copy (no inference, no locks).
set -u
R=/mnt/raid0/llm/tmp/cs11-20261022
T=$R/dry/lt
rm -rf "$T"; mkdir -p "$T/flags" "$T/dry" "$T/e"
for f in PREDECLARED.md cs11_harness.py analyze.py run_cs11.sh resolve_recipes.py dry/recipes.json chained_launch.sh; do echo "x$f" > "$T/$f"; done
sed -e "s#^D=/mnt/raid0/llm/tmp/cs11-20261022; F=#D=$T; F=#" -e "s#^E=.*#E=$T/e#" \
    -e "s#^NOT_BEFORE=.*#NOT_BEFORE=2020-01-01T00:00:00Z; HARD_STOP=2099-01-01T00:00:00Z; HARNESS_DEADLINE=2099-01-01T00:00:00Z#" \
    -e "s#^LATEST_START=.*#LATEST_START=2098-01-01T00:00:00Z#" "$R/chained_launch.sh" > "$T/chained_launch.sh"
printf '#!/bin/bash\necho stub run $1\nexit 7\n' > "$T/run_cs11.sh"; chmod +x "$T"/*.sh
grep -n "^D=\|^E=\|^NOT_BEFORE" "$T/chained_launch.sh"
echo "--- test1 no APPROVED (expect rc=4)"; bash "$T/chained_launch.sh"; echo "exit=$?"; cat "$T/flags/CS11_DONE"
echo "--- test2 approved + e.SKIPPED (expect run, rc=7)"
( cd "$T" && sha256sum PREDECLARED.md cs11_harness.py analyze.py run_cs11.sh resolve_recipes.py dry/recipes.json chained_launch.sh > APPROVED )
touch "$T/e/e.SKIPPED"; bash "$T/chained_launch.sh"; echo "exit=$?"; cat "$T/flags/CS11_DONE"; cat "$T/flags/run.out"
echo "--- test3 tampered file (expect rc=4)"; echo y >> "$T/analyze.py"; bash "$T/chained_launch.sh"; echo "exit=$?"; cat "$T/flags/CS11_DONE"
echo "--- test4 TERM while waiting for e (expect rc=143)"
echo x > "$T/analyze.py"; ( cd "$T" && sha256sum PREDECLARED.md cs11_harness.py analyze.py run_cs11.sh resolve_recipes.py dry/recipes.json chained_launch.sh > APPROVED )
rm -f "$T/e/e.SKIPPED"
setsid bash "$T/chained_launch.sh" < /dev/null > /dev/null 2>&1 &
P=$!; sleep 3; kill -TERM "$P"; sleep 2
cat "$T/flags/CS11_DONE"; if ps -p "$P" > /dev/null; then echo "STILL ALIVE"; kill -9 "$P"; else echo "dead"; fi
