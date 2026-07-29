# Security Audit: Orchestration Stack

**Created:** 2026-01-22
**Updated:** 2026-01-27
**Priority:** High
**Status:** PARTIAL - API layer audited, P0 fix applied
**Estimated effort:** 1 hour remaining (llama.cpp CVE verification on prod)

---

## Context

Multiple critical vulnerabilities have been discovered in llama.cpp's GGUF parser (Talos 2024, GitHub advisories 2025). This system runs a multi-model orchestration stack with llama-server instances on ports 8080-8085. A full security audit is needed to assess exposure and implement mitigations.

### ⚠️ CRITICAL CONSTRAINT: production-consolidated Branch

The production llama.cpp at `/mnt/raid0/llm/llama.cpp` uses the `production-consolidated` branch which contains **cherry-picked optimizations** specific to this EPYC 9655 system. These include:
- Parallel tensor repack optimizations
- MoE expert reduction patches
- Speculative decoding tuning
- Patches in `/mnt/raid0/llm/claude/patches/`

**DO NOT simply update to upstream master.** Security patches must be:
1. Cherry-picked onto `production-consolidated`, OR
2. `production-consolidated` rebased onto a secure base (requires re-testing all optimizations)

See: `docs/reference/LLAMA_CPP_WORKTREES.md` for branch management details.

### Known Vulnerability Classes

| ID | Type | Vector | Severity |
|----|------|--------|----------|
| TALOS-2024-1912 | Heap buffer overflow | Malicious GGUF | Critical |
| TALOS-2024-1913 | Integer overflow (`gguf_fread_str`) | String length | Critical |
| TALOS-2024-1914 | Heap overflow (`n_dims`) | Tensor dimensions | Critical |
| TALOS-2024-1915 | Integer overflow (tensor alloc) | `n_tensors * sizeof()` | Critical |
| TALOS-2024-1916 | Integer overflow (KV alloc) | `n_kv * sizeof()` | Critical |
| GHSA-8wwf-w4qm-gpqr | Buffer overflow | Vocab loading | Critical |
| GHSA-8947-pfff-2f3c | OOB write | llama-server `n_discard` | Critical |
| CVE-2024-34359 | SSTI/RCE | llama-cpp-python Jinja2 | Critical |

---

## Audit Checklist

### Phase 1: Version & Patch Status

```bash
# 1.1 Check current production-consolidated base
cd /mnt/raid0/llm/llama.cpp
git log --oneline -1
git describe --tags --always
git log --oneline -10  # See recent history

# 1.2 Identify the upstream base commit
git merge-base production-consolidated origin/master

# 1.3 List local optimizations/patches on production-consolidated
git log $(git merge-base production-consolidated origin/master)..HEAD --oneline

# 1.4 Check which security fixes exist in upstream but NOT in production-consolidated
git fetch origin
git log production-consolidated..origin/master --oneline | grep -iE "security|CVE|overflow|gguf|buffer|TALOS"

# 1.5 Check local patches directory
ls -la /mnt/raid0/llm/claude/patches/
```

**Document findings:**
- [ ] Current production-consolidated HEAD: _______________
- [ ] Upstream base commit: _______________
- [ ] Number of local optimization commits: _______________
- [ ] Security patches missing: _______________

### Phase 2: Network Exposure Assessment

```bash
# 2.1 Check listening ports
ss -tlnp | grep -E "808[0-5]|llama"

# 2.2 Check firewall rules
sudo iptables -L -n | grep -E "808[0-5]"
sudo ufw status verbose 2>/dev/null

# 2.3 Check if servers are bound to localhost vs 0.0.0.0
ps aux | grep llama-server | grep -oE "\-\-host [^ ]+"

# 2.4 Check orchestrator stack config
grep -E "host|bind|0\.0\.0\.0|127\.0\.0\.1" /mnt/raid0/llm/claude/scripts/server/orchestrator_stack.py
```

**Document findings:**
- [ ] Ports exposed externally: _______________
- [ ] Servers bound to: localhost / 0.0.0.0 / specific IP
- [ ] Firewall rules in place: Yes / No
- [ ] API authentication enabled: Yes / No

### Phase 3: Model Provenance Audit

```bash
# 3.1 List all GGUF models
find /mnt/raid0/llm/models -name "*.gguf" -exec ls -lh {} \; 2>/dev/null | head -30

# 3.2 Check model sources in registry
grep -E "source:|url:|huggingface:" /mnt/raid0/llm/claude/orchestration/model_registry.yaml

# 3.3 Generate model hashes for verification
sha256sum /mnt/raid0/llm/models/*.gguf 2>/dev/null | tee /tmp/model_hashes.txt
```

**Model trust assessment:**

| Model | Source | Quantizer | Hash Verified |
|-------|--------|-----------|---------------|
| Qwen3-Coder-30B-A3B | | | [ ] |
| Qwen2.5-Coder-32B | | | [ ] |
| Qwen3-235B-A22B | | | [ ] |
| (add all production models) | | | |

### Phase 4: API Security Review

```bash
# 4.1 Check API routes for input validation
grep -rn "n_discard\|n_keep\|n_predict" /mnt/raid0/llm/claude/src/api/

# 4.2 Check for request size limits
grep -rn "max_tokens\|limit\|max_length" /mnt/raid0/llm/claude/src/api/

# 4.3 Review OpenAI-compatible endpoint
cat /mnt/raid0/llm/claude/src/api/routes/openai_compat.py 2>/dev/null | grep -E "def |async def |@"

# 4.4 Check for authentication/authorization
grep -rn "auth\|token\|api_key\|bearer" /mnt/raid0/llm/claude/src/api/
```

**Document findings:**
- [ ] Input validation for `n_discard`: Yes / No
- [ ] Request size limits: _______________
- [ ] Authentication required: Yes / No
- [ ] Rate limiting: Yes / No

### Phase 5: Python Bindings (CVE-2024-34359)

```bash
# 5.1 Check if llama-cpp-python is installed
pip show llama-cpp-python 2>/dev/null

# 5.2 Check version (vulnerable versions < 0.2.57)
python3 -c "import llama_cpp; print(llama_cpp.__version__)" 2>/dev/null

# 5.3 Search for Jinja2 template usage
grep -rn "Jinja\|ChatFormatter\|chat_template" /mnt/raid0/llm/claude/src/
```

**Document findings:**
- [ ] llama-cpp-python installed: Yes / No
- [ ] Version (if installed): _______________
- [ ] Vulnerable to CVE-2024-34359: Yes / No / N/A

### Phase 6: Memory Safety & Sandboxing

```bash
# 6.1 Check for ASLR
cat /proc/sys/kernel/randomize_va_space

# 6.2 Check binary hardening
readelf -l /mnt/raid0/llm/llama.cpp/build/bin/llama-cli | grep -E "GNU_RELRO|GNU_STACK"

# 6.3 Check if running in container/sandbox
cat /proc/1/cgroup 2>/dev/null | grep -E "docker|lxc|containerd" || echo "No containerization detected"
```

### Phase 7: File System Permissions

```bash
# 7.1 Check model directory permissions
ls -la /mnt/raid0/llm/models/ | head -10

# 7.2 Check for world-writable paths
find /mnt/raid0/llm -type d -perm -002 2>/dev/null

# 7.3 Who can write to model directory?
stat /mnt/raid0/llm/models/
```

---

## Remediation Actions

### Immediate (P0) - No rebuild required

- [ ] Bind all llama-server instances to 127.0.0.1 only (config change)
- [ ] Add firewall rules blocking external access to ports 8080-8085
- [ ] Verify all production GGUF models are from trusted sources
- [ ] Add input validation for `n_discard` in API layer (Python-side fix)

### Short-term (P1) - Requires careful patching

- [ ] **Identify specific security fix commits from upstream**
  ```bash
  # Find the actual fix commits for each CVE
  cd /mnt/raid0/llm/llama.cpp
  git fetch origin
  git log origin/master --oneline --grep="TALOS\|CVE\|overflow" --since="2024-07-01"
  ```

- [ ] **Cherry-pick security fixes onto production-consolidated**
  ```bash
  # Use llama.cpp-experimental for testing first!
  cd /mnt/raid0/llm/llama.cpp-experimental
  git checkout -b security-patch-test production-consolidated
  git cherry-pick <security-fix-commit-1>
  git cherry-pick <security-fix-commit-2>
  # ... test thoroughly before applying to production
  ```

- [ ] **Document cherry-picked security patches** in `/mnt/raid0/llm/claude/patches/`

- [ ] Update llama-cpp-python if installed (>= 0.2.57)

### Medium-term (P2)

- [ ] Consider periodic rebase of production-consolidated onto secure upstream tags
- [ ] Implement model signature verification pipeline
- [ ] Add monitoring/alerting for suspicious API patterns
- [ ] Document complete patch lineage for production-consolidated

---

## Security Patch Application Workflow

**DO NOT** run `git pull` or `git merge origin/master` on production-consolidated!

```bash
# 1. Work in experimental worktree
cd /mnt/raid0/llm/llama.cpp-experimental
git fetch origin

# 2. Create test branch from production-consolidated
git checkout -b security-fixes-$(date +%Y%m%d) production-consolidated

# 3. Identify and cherry-pick security fixes
git log origin/master --oneline --grep="overflow\|security" --since="2024-07-01"
git cherry-pick --no-commit <commit-hash>
# Review changes, then commit

# 4. Rebuild and test
cmake -B build && cmake --build build -j$(nproc)
# Run benchmark suite to verify optimizations still work
./scripts/benchmark/run_overnight_benchmark_suite.sh --suite thinking --quick

# 5. If all tests pass, apply to production
cd /mnt/raid0/llm/llama.cpp
git fetch /mnt/raid0/llm/llama.cpp-experimental security-fixes-$(date +%Y%m%d)
git merge --ff-only FETCH_HEAD  # Only if clean fast-forward
```

---

## References

- [Cisco Talos TALOS-2024-1912](https://talosintelligence.com/vulnerability_reports/TALOS-2024-1912)
- [Cisco Talos TALOS-2024-1913](https://talosintelligence.com/vulnerability_reports/TALOS-2024-1913)
- [Cisco Talos TALOS-2024-1914](https://talosintelligence.com/vulnerability_reports/TALOS-2024-1914)
- [Cisco Talos TALOS-2024-1915](https://talosintelligence.com/vulnerability_reports/TALOS-2024-1915)
- [Cisco Talos TALOS-2024-1916](https://talosintelligence.com/vulnerability_reports/TALOS-2024-1916)
- [GitHub llama.cpp Security](https://github.com/ggml-org/llama.cpp/security)
- [GHSA-8wwf-w4qm-gpqr](https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-8wwf-w4qm-gpqr)
- [GHSA-8947-pfff-2f3c](https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-8947-pfff-2f3c)
- [CVE-2024-34359](https://checkmarx.com/blog/llama-drama-critical-vulnerability-cve-2024-34359-threatening-your-software-supply-chain/)
- [LLAMA_CPP_WORKTREES.md](docs/reference/LLAMA_CPP_WORKTREES.md)

---

## Resume Commands

```bash
# Start audit
cd /mnt/raid0/llm/claude
cat handoffs/active/security_audit_orchestration_stack.md

# Quick version check
cd /mnt/raid0/llm/llama.cpp && git log --oneline -5

# Check what's in production-consolidated vs upstream
git log $(git merge-base HEAD origin/master)..HEAD --oneline  # Local patches
git log HEAD..origin/master --oneline | grep -i security      # Missing security fixes
```

---

## Completion Criteria

- [ ] All 7 phases documented with findings
- [ ] Risk assessment completed (Critical/High/Medium/Low)
- [ ] Security patches identified and cherry-pick plan created
- [ ] Remediation actions prioritized
- [ ] Findings added to `docs/reference/SECURITY_AUDIT.md`
- [ ] BLOCKED_TASKS.md updated if blockers found
- [ ] This handoff deleted after completion
