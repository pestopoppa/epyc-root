"""Tests for skill hub interop (B3)."""


from src.skill_hub_interop import (
    SkillBundle,
    SkillMetadata,
    export_skill_md,
    load_skills_from_directory,
    parse_skill_md,
    scan_skill,
)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_SAMPLE_SKILL = """\
---
name: Code Reviewer
description: Reviews code for quality and security issues
version: 2.1.0
author: epyc-team
tags: code, review, security
trust_level: trusted
---

## Instructions

Review the code for:
1. Security vulnerabilities
2. Performance issues
3. Style violations
"""


class TestParseSkillMd:
    def test_full_frontmatter(self):
        bundle = parse_skill_md(_SAMPLE_SKILL)
        assert bundle.metadata.name == "Code Reviewer"
        assert bundle.metadata.version == "2.1.0"
        assert bundle.metadata.author == "epyc-team"
        assert "code" in bundle.metadata.tags
        assert bundle.metadata.trust_level == "trusted"
        assert "Review the code" in bundle.instructions

    def test_no_frontmatter(self):
        bundle = parse_skill_md("Just plain instructions here")
        assert bundle.metadata.name == "unnamed"
        assert bundle.instructions == "Just plain instructions here"

    def test_minimal_frontmatter(self):
        text = "---\nname: Minimal\n---\n\nDo things."
        bundle = parse_skill_md(text)
        assert bundle.metadata.name == "Minimal"
        assert bundle.instructions == "Do things."

    def test_extra_fields_preserved(self):
        text = "---\nname: X\ncustom_field: hello\n---\n\nbody"
        bundle = parse_skill_md(text)
        assert bundle.metadata.extra["custom_field"] == "hello"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class TestExportSkillMd:
    def test_roundtrip(self):
        bundle = parse_skill_md(_SAMPLE_SKILL)
        exported = export_skill_md(bundle)
        re_parsed = parse_skill_md(exported)
        assert re_parsed.metadata.name == bundle.metadata.name
        assert re_parsed.metadata.version == bundle.metadata.version
        assert re_parsed.metadata.tags == bundle.metadata.tags
        assert "Review the code" in re_parsed.instructions

    def test_minimal_export(self):
        bundle = SkillBundle(
            metadata=SkillMetadata(name="test"),
            instructions="Do X.",
        )
        text = export_skill_md(bundle)
        assert "name: test" in text
        assert "Do X." in text


# ---------------------------------------------------------------------------
# Security scanning
# ---------------------------------------------------------------------------


class TestScanSkill:
    def test_safe_skill(self):
        bundle = parse_skill_md(_SAMPLE_SKILL)
        result = scan_skill(bundle)
        assert result.safe

    def test_eval_detected(self):
        bundle = SkillBundle(
            metadata=SkillMetadata(name="bad"),
            instructions="Run eval(user_input) to execute code",
        )
        result = scan_skill(bundle)
        assert not result.safe
        assert "eval_exec" in result.threats

    def test_subprocess_shell_detected(self):
        bundle = SkillBundle(
            metadata=SkillMetadata(name="bad"),
            instructions="Use subprocess.run(cmd, shell=True) for execution",
        )
        result = scan_skill(bundle)
        assert not result.safe
        assert "subprocess_shell" in result.threats

    def test_credential_access_detected(self):
        bundle = SkillBundle(
            metadata=SkillMetadata(name="bad"),
            instructions="Read the .ssh directory for keys",
        )
        result = scan_skill(bundle)
        assert not result.safe
        assert "credential_access" in result.threats

    def test_multiple_threats(self):
        bundle = SkillBundle(
            metadata=SkillMetadata(name="bad"),
            instructions="eval(x) and os.system('rm -rf /')",
        )
        result = scan_skill(bundle)
        assert not result.safe
        assert len(result.threats) >= 2


# ---------------------------------------------------------------------------
# Directory loading
# ---------------------------------------------------------------------------


class TestLoadSkills:
    def test_load_from_directory(self, tmp_path):
        # Create skill subdirectory
        skill_dir = tmp_path / "code-review"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(_SAMPLE_SKILL)

        bundles = load_skills_from_directory(tmp_path)
        assert len(bundles) == 1
        assert bundles[0].metadata.name == "Code Reviewer"

    def test_nonexistent_directory(self):
        bundles = load_skills_from_directory("/nonexistent/path")
        assert bundles == []
