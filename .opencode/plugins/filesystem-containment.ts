import type { Plugin } from "@opencode-ai/plugin"

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
 * PreToolUse hook calls; the repo's rule: never a fifth parser). Every bash
 * invocation is scanned before execution; a refuse verdict blocks the tool.
 *
 * The scanner reads EPYC_FS_ACK from ITS OWN process environment — the
 * opencode server's environment, which a bash-session `export` cannot reach —
 * so in this surface the env-ack is strictly operator-set. The operator
 * allowlist (scripts/hooks/filesystem_allowlist.yaml) approves CLASS B path
 * prefixes; CLASS A (mount/apt/systemctl/...) always needs the env ack.
 *
 * NOTE: the type import below is dev-time only (erased at runtime), so the
 * plugin loads with no dependencies and no network access. Config is loaded
 * at opencode start — RESTART opencode after changing plugin or permissions.
 */

const SCANNER = "/workspace/scripts/hooks/filesystem_containment_scan.py"

export const FilesystemContainment: Plugin = async ({ $, directory, client }) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash") return
      const command: unknown = output.args?.command
      if (typeof command !== "string" || command.trim() === "") return

      const args: string[] = [SCANNER, "--command", command]
      if (typeof directory === "string" && directory) args.push("--cwd", directory)

      let res: { exitCode: number; stdout: string; stderr: string }
      try {
        // Bun's shell passes array elements as individual argv entries, so the
        // command reaches the scanner untouched by shell quoting.
        res = await $`python3 ${args}`.nothrow().quiet()
      } catch {
        throw new Error(
          "[filesystem-containment] scanner could not be started — refusing (fail closed, INC-20260823)",
        )
      }

      if (res.exitCode === 0) return

      const detail = (res.stderr || "").trim() || (res.stdout || "").trim()
      const message = detail || `scanner refused the command (exit ${res.exitCode})`
      try {
        await client.app.log({
          body: {
            service: "filesystem-containment",
            level: "warn",
            message: `refused: ${message}`,
            extra: { tool: "bash" },
          },
        })
      } catch {
        // logging must never mask the refusal
      }
      throw new Error(
        `[filesystem-containment] ${message} — operator override: set ` +
          'EPYC_FS_ACK="operator: <who> <date>: <reason>" on the opencode process ' +
          "environment (CLASS A), or add the path to scripts/hooks/filesystem_allowlist.yaml (CLASS B)",
      )
    },
  }
}
