#!/usr/bin/env python3
"""Seed samples.jsonl for the multilingual ingest quality-gap test.

Sources:
- Flores-200 dev/devtest splits (CC-BY-SA-4.0) — covers most required language
  codes EXCEPT the Mandarin-minority/dialect stratum (Tibetan/Mongolian/Uyghur/
  Cantonese are partial; Cantonese (yue) is in NLLB but quality varies).
- intake_index.yaml entries with non-English source URLs — mined for foreign-
  language paper abstracts that the research-intake pipeline has actually seen.
- Manual additions hook for the strata Flores-200 cannot cover.

Output: JSONL file matching schema in README.md. Per-stratum target controlled
by --strata-target (default 10).

This script is offline-capable: --flores-cache reuses a previously-downloaded
Flores-200 archive. If the archive is absent and --no-download is passed, the
script reports the missing strata and exits without network access.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import yaml

FLORES_URL = "https://tinyurl.com/flores200dataset"  # canonical mirror
FLORES_FILENAME = "flores200_dataset.tar.gz"

# Map our stratum language codes to Flores-200 codes (BCP-47 → Flores ISO 639-3+script)
FLORES_CODES = {
    "zh": "zho_Hans",
    "en": "eng_Latn",
    "it": "ita_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "ru": "rus_Cyrl",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
}


def load_config(repo_root: Path) -> dict:
    """Load the test config to discover strata + targets."""
    cfg_path = repo_root / "config.yaml"
    with cfg_path.open() as f:
        return yaml.safe_load(f)


def download_flores(cache_dir: Path) -> None:
    """Fetch Flores-200 if not already cached. User-attended (network access)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive = cache_dir / FLORES_FILENAME
    if archive.exists():
        print(f"[curate] flores200 cached at {archive}", file=sys.stderr)
        return
    print(f"[curate] downloading flores200 to {archive} ...", file=sys.stderr)
    urllib.request.urlretrieve(FLORES_URL, archive)


def extract_flores(cache_dir: Path) -> Path:
    """Extract the archive (idempotent)."""
    import tarfile
    archive = cache_dir / FLORES_FILENAME
    out_dir = cache_dir / "flores200_dataset"
    if out_dir.exists():
        return out_dir
    with tarfile.open(archive) as tar:
        tar.extractall(cache_dir)
    return out_dir


def sample_flores_devtest(flores_root: Path, lang_code: str, n: int) -> list[str]:
    """Pull N sentences from Flores-200 devtest for a given language code."""
    path = flores_root / "devtest" / f"{lang_code}.devtest"
    if not path.exists():
        print(f"[curate] WARN: missing {path}", file=sys.stderr)
        return []
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return lines[:n]


def mine_intake_foreign_entries(intake_path: Path) -> list[dict]:
    """Scan intake_index.yaml for entries whose source URLs are non-English domains
    (heuristic). Returns a list of (url, title, source_type) tuples for manual review."""
    if not intake_path.exists():
        return []
    with intake_path.open() as f:
        entries = yaml.safe_load(f) or []
    foreign_domains = ["modelscope.cn", "aistudio.tencent.com", "wechat.com", "zhihu.com",
                       "bilibili.com", "weibo.com", ".jp/", ".kr/", ".cn/"]
    out = []
    for e in entries:
        url = e.get("url") or ""
        if any(d in url for d in foreign_domains):
            out.append({
                "intake_id": e.get("id"),
                "url": url,
                "title": e.get("title"),
                "source_type": e.get("source_type"),
            })
    return out


def make_sample(sid: str, stratum: str, lang: str, content: str,
                source_url: str = "flores200:devtest", source_type: str = "paper_abstract",
                notes: str = "") -> dict:
    return {
        "id": sid,
        "stratum": stratum,
        "language": lang,
        "source_url": source_url,
        "source_type": source_type,
        "char_count": len(content),
        "content": content,
        "notes": notes,
    }


def emit_manual_gap_report(strata_targets: dict[str, int],
                           collected: dict[str, list[dict]]) -> str:
    """Build a human-readable report of strata that need manual additions."""
    lines = ["# Manual Sample Curation Gaps", ""]
    for stratum, target in strata_targets.items():
        have = len(collected.get(stratum, []))
        if have >= target:
            lines.append(f"- [x] **{stratum}**: {have}/{target} ✓")
        else:
            lines.append(f"- [ ] **{stratum}**: {have}/{target} — need {target - have} more samples")
    lines.append("")
    lines.append("Flores-200 partially covers most strata. The Mandarin-minority/dialect stratum")
    lines.append("(bo, mn, ug, yue) and the mixed_script_structured stratum typically need manual")
    lines.append("additions from public corpora (CLUE, XTREME) or curated intake-pipeline samples.")
    lines.append("")
    lines.append("To add manual samples, append JSON lines to data/samples.jsonl matching the")
    lines.append("schema in README.md. Set source_url to the canonical source and notes to any")
    lines.append("provenance caveats (license, redistribution scope).")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path, help="Output samples.jsonl path")
    p.add_argument("--strata-target", type=int, default=10, help="Samples per stratum (default 10)")
    p.add_argument("--flores-cache", type=Path, default=Path("data/flores200"),
                   help="Directory to cache/extract Flores-200")
    p.add_argument("--no-download", action="store_true",
                   help="Do not attempt network access; use only cached data")
    p.add_argument("--intake-index", type=Path,
                   default=Path("../intake_index.yaml"),
                   help="Path to intake_index.yaml for mining foreign-language sources")
    p.add_argument("--gap-report", type=Path, default=Path("data/sample_curation_gaps.md"),
                   help="Output path for the manual-gap report")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent
    cfg = load_config(repo_root)
    strata_cfg = cfg["strata"]

    # Resolve relative paths against repo_root
    if not args.output.is_absolute():
        args.output = repo_root / args.output
    if not args.flores_cache.is_absolute():
        args.flores_cache = repo_root / args.flores_cache
    if not args.gap_report.is_absolute():
        args.gap_report = repo_root / args.gap_report
    intake_path = args.intake_index
    if not intake_path.is_absolute():
        intake_path = (repo_root / args.intake_index).resolve()

    # Step 1: Flores-200 fetch + extract (if cached or download allowed)
    flores_root = None
    if (args.flores_cache / "flores200_dataset").exists():
        flores_root = args.flores_cache / "flores200_dataset"
    elif (args.flores_cache / FLORES_FILENAME).exists():
        flores_root = extract_flores(args.flores_cache)
    elif not args.no_download:
        download_flores(args.flores_cache)
        flores_root = extract_flores(args.flores_cache)
    else:
        print("[curate] WARN: no Flores-200 cache and --no-download set; skipping Flores samples",
              file=sys.stderr)

    # Step 2: collect per-stratum samples from Flores-200
    collected: dict[str, list[dict]] = {s: [] for s in strata_cfg}
    if flores_root:
        for stratum, scfg in strata_cfg.items():
            target = args.strata_target
            per_lang = max(1, target // max(1, len(scfg["languages"])))
            for lang in scfg["languages"]:
                flores_code = FLORES_CODES.get(lang)
                if not flores_code:
                    continue  # No Flores mapping — manual-gap stratum
                lines = sample_flores_devtest(flores_root, flores_code, per_lang)
                for i, content in enumerate(lines):
                    sid = f"{stratum}-{lang}-{i:03d}"
                    collected[stratum].append(make_sample(
                        sid, stratum, lang, content,
                        source_url=f"flores200:devtest/{flores_code}",
                        notes="flores200 devtest sentence; CC-BY-SA-4.0",
                    ))

    # Step 3: mine intake_index for foreign-language sources (manual-review pointers)
    foreign_intake = mine_intake_foreign_entries(intake_path)

    # Step 4: write samples.jsonl
    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_written = 0
    with args.output.open("w", encoding="utf-8") as f:
        for stratum_samples in collected.values():
            for s in stratum_samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
                n_written += 1

    # Step 5: emit gap report + intake-mining pointers
    gap_report = emit_manual_gap_report({s: args.strata_target for s in strata_cfg}, collected)
    if foreign_intake:
        gap_report += "\n## Foreign-language intake entries (manual-curation candidates)\n\n"
        for entry in foreign_intake[:20]:
            gap_report += f"- {entry['intake_id']}: [{entry['title'][:80]}]({entry['url']})\n"
    args.gap_report.parent.mkdir(parents=True, exist_ok=True)
    args.gap_report.write_text(gap_report)

    print(f"[curate] wrote {n_written} samples to {args.output}")
    print(f"[curate] manual-gap report at {args.gap_report}")
    print(f"[curate] strata coverage:")
    for stratum, target in [(s, args.strata_target) for s in strata_cfg]:
        have = len(collected[stratum])
        status = "OK" if have >= target else f"NEED +{target - have}"
        print(f"  {stratum}: {have}/{target} [{status}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
