import { spawn } from "node:child_process"

import { Plugin } from "@opencode/plugin"

/**
 * Filesystem containment guard for opencode (INC-20260823).
 *
 * INC-20260823-filesystem-containment-gap: an agent ran
 *   sudo -n mkdir -p /mnt/bigdisk && sudo -n mount /dev/sdb1 /mnt/bigdisk
 * planned writes to /mnt/bigdisk/epyc-backup/, and `sudo apt-get install restic`
 * against the operator directive "do not touch anything outside /mnt/raid0/llm/".
 * The opencode surface had NO guard at all (no permissions, no plugins).
 *
 * This plugin is the opencode surface of the ONE shared scanner
 * (scripts/hooks/filesystem_containment_scan.py — the same file the Claude
 * PreToolUse hook calls; the repo's rule: never a fifth parser). Every shell
 * command is scanned before execution; every write/edit of a file path is
 * checked against the same containment roots + allowlist (--check-path);
 * a refuse verdict blocks the operation.
 *
 * Why no `permissions` block for edit/write: the opencode schema accepts
 * path-pattern deny maps for `edit`, but the scanner's allow-set
 * (/mnt/raid0/llm/**, /workspace/**, /tmp/**, ~/.claude/**, ~/.codex/** plus
 * the operator allowlist and EPYC_FS_ACK) cannot be expressed as deny
 * patterns without hand-copying the containment tables — the exact drift this
 * unification kills. The plugin runs the real check (realpath'd, allowlist-
 * aware, fail-closed); the generated shell permission block is defense-in-depth
 * only for the literal CLASS A verbs.
 *
 * The scanner reads EPYC_FS_ACK from ITS OWN process environment — the
 * opencode server's environment, which a shell-session `export` cannot reach —
 * so in this surface the env-ack is strictly operator-set. The operator
 * allowlist (scripts/hooks/filesystem_allowlist.yaml) approves CLASS B path
 * prefixes; CLASS A (mount/apt/systemctl/...) always needs the env ack.
 *
 * V2 note: OpenCode 2 calls the shell operation `shell` (not V1's `bash`), so
 * shell commands are intercepted at `ctx.shell.hook("create.before")`; file
 * writes/edits remain `ctx.tool.hook("execute.before")`. V1 plugin hooks are
 * intentionally not used because V2 does not run V1 plugin implementations.
 */

const SCANNER = "/workspace/scripts/hooks/filesystem_containment_scan.py"
const FILE_TOOLS = new Set(["write", "edit"])

type ScanResult = { exitCode: number; stdout: string; stderr: string }

function runScanner(args: string[]): Promise<ScanResult> {
  return new Promise((resolve, reject) => {
    const child = spawn("python3", args, { stdio: ["ignore", "pipe", "pipe"] })
    let stdout = ""
    let stderr = ""

    child.stdout?.on("data", (chunk) => {
      stdout += String(chunk)
    })
    child.stderr?.on("data", (chunk) => {
      stderr += String(chunk)
    })
    child.on("error", reject)
    child.on("close", (code) => resolve({ exitCode: code ?? 1, stdout, stderr }))
  })
}

function refusal(message: string): string {
  return (
    `[filesystem-containment] ${message} — operator override: set ` +
    'EPYC_FS_ACK="operator: <who> <date>: <reason>" on the opencode process ' +
    "environment (CLASS A), or add the path to scripts/hooks/filesystem_allowlist.yaml (CLASS B)"
  )
}

export default Plugin.define({
  id: "filesystem-containment",
  async setup(ctx) {
    const directory = ctx.location.directory

    await ctx.shell.hook("create.before", async (event) => {
      const command = event.command
      if (typeof command !== "string" || command.trim() === "") return

      const args = [SCANNER, "--command", command]
      const cwd = event.cwd || directory
      if (cwd) args.push("--cwd", cwd)

      let result: ScanResult
      try {
        result = await runScanner(args)
      } catch {
        throw new Error(
          "[filesystem-containment] scanner could not be started — refusing (fail closed, INC-20260823)",
        )
      }
      if (result.exitCode === 0) return

      const detail = (result.stderr || "").trim() || (result.stdout || "").trim()
      const message = detail || `scanner refused the command (exit ${result.exitCode})`
      console.warn(`[filesystem-containment] refused shell command: ${message}`)
      throw new Error(refusal(message))
    })

    await ctx.tool.hook("execute.before", async (event) => {
      if (!FILE_TOOLS.has(event.tool)) return

      const input = (event.input ?? {}) as Record<string, unknown>
      const filePath = input.path ?? input.filePath
      if (typeof filePath !== "string" || filePath.trim() === "") return

      const args = [SCANNER, "--check-path", filePath]
      if (directory) args.push("--cwd", directory)

      let result: ScanResult
      try {
        result = await runScanner(args)
      } catch {
        throw new Error(
          "[filesystem-containment] scanner could not be started — refusing (fail closed, INC-20260823)",
        )
      }
      if (result.exitCode === 0) return

      const detail = (result.stderr || "").trim() || (result.stdout || "").trim()
      const message = detail || `scanner refused the file path (exit ${result.exitCode})`
      console.warn(`[filesystem-containment] refused ${event.tool}: ${message}`)
      throw new Error(refusal(message))
    })
  },
})
