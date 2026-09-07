# AI installation contract

## Package identity

- Repository: `fanfanfanfanfan626/skill-governor`
- Skill name: `skill-governor`
- Installable directory: `skills/skill-governor`
- Entry point: `skills/skill-governor/SKILL.md`
- Current release: `v1.0.0`
- Runtime for optional helpers: Python 3.10+ and PyYAML 6

Do not search for a root-level `SKILL.md`; this repository intentionally keeps the installable package under `skills/skill-governor`. Do not install the repository root as though it were the skill folder.

## Installation procedure for an AI assistant

1. Inspect the target host's supported skill roots and check for an existing `skill-governor` installation.
2. Download the release archive or clone this repository.
3. Copy the complete `skills/skill-governor` directory into one verified skill root. Preserve all references, scripts, metadata and the included license.
4. Never copy generated governance state, local inventories, absolute paths, evidence records, backups or credentials into the skill package.
5. Reload the host through its documented mechanism and verify that the exact `skill-governor` entry is exposed.
6. Read the complete `SKILL.md` before use. Load only the reference files required for the selected governance mode.
7. If optional helpers are needed, install `skills/skill-governor/requirements.txt` and run the read-only audit before any stateful setup.
8. Report installation, host discovery, dependency readiness and successful execution as separate facts.

## Verification

```sh
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
python -X utf8 -m unittest discover -s tests -v
```

The release page publishes a SHA-256 checksum for the portable ZIP. A matching hash verifies bytes only; it does not prove host compatibility, source comprehension or usefulness on a real task.

## Invocation

Explicit invocation:

> Use $skill-governor to audit my skill library and propose the smallest sufficient routing policy. Keep private paths and evidence local.

The skill may also be implicitly selected for genuine skill-governance work, but it should not be inserted into ordinary tasks that already have one obvious specialist.
