# AI installation contract

## Package identity

- Repository: `fanfanfanfanfan626/skill-governor`
- Skill name: `skill-governor`
- Installable directory: `skills/skill-governor`
- Entry point: `skills/skill-governor/SKILL.md`
- Source version: `v1.1.0`; verify the corresponding asset exists on Releases before reporting it as published.
- Runtime for optional helpers: Python 3.10+ and PyYAML 6

Do not search for a root-level `SKILL.md`; this repository intentionally keeps the installable package under `skills/skill-governor`. Do not install the repository root as though it were the skill folder.

## Installation procedure for an AI assistant

1. Inspect the target host's supported skill roots and check for an existing `skill-governor` installation.
2. Download the release archive or clone this repository.
3. Copy the complete `skills/skill-governor` source directory (or the `skill-governor` top-level directory from the release ZIP) into one verified skill root. Preserve all references, scripts, metadata and the included license.
4. Never copy generated governance state, local inventories, absolute paths, evidence records, backups or credentials into the skill package.
5. Reload the host through its documented mechanism and verify that the exact `skill-governor` entry is exposed.
6. Read the complete `SKILL.md` before use. Load only the reference files required for the selected governance mode.
7. Before any stateful setup, run the read-only audit appropriate to the distribution below. Both `audit_bundle.py` and `audit_skills.py` need only Python's standard library. Stateful helpers such as `govern.py` and `registry.py` also need PyYAML: install from the selected package's `requirements.txt` (`skills/skill-governor/requirements.txt` in a checkout; `skill-governor/requirements.txt` beside an extracted ZIP).
8. Report installation, host discovery, dependency readiness and successful execution as separate facts.

## Verification

### Source checkout

Run from the repository root. The test suite belongs to the repository, not the portable ZIP.

```sh
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
python -X utf8 -m unittest discover -s tests -v
```

You can also inspect a downloaded release ZIP without extracting it, using the checker from this trusted checkout. Substitute its actual download path below; `dist/` is not included in a fresh clone.

```sh
python skills/skill-governor/scripts/audit_bundle.py path/to/skill-governor-v1.1.0.zip
```

### Portable release ZIP only

Download `skill-governor-v1.1.0.zip` and its matching `skill-governor-v1.1.0.zip.sha256` asset from the same official release. Compare the SHA-256 before extraction (for example, `sha256sum -c skill-governor-v1.1.0.zip.sha256` in the download directory, or `Get-FileHash -Algorithm SHA256` in PowerShell and compare with the sidecar). The repository-root `SHA256SUMS` covers source files; it is not the portable ZIP checksum.

Extract into a new empty directory. From that directory, run:

```sh
python skill-governor/scripts/audit_bundle.py skill-governor
```

This checks the extracted bundle without installing it, uploading it or creating governance state. The ZIP contains no repository `tests/` directory: do not run checkout-only commands against it, and do not interpret absent tests as a corrupt download. Its complete `skill-governor/` folder is the installable unit.

A matching hash verifies bytes only. A passing bundle audit checks the documented structural rules, not arbitrary code safety, host compatibility, source comprehension or usefulness on a real task. Only run helper code from a source you have chosen to trust. Host discovery and a successful real invocation still need separate checks.

## Invocation

Explicit invocation:

> Use $skill-governor to audit my skill library and propose the smallest sufficient routing policy. Keep private paths and evidence local.

The skill may also be implicitly selected for genuine skill-governance work, but it should not be inserted into ordinary tasks that already have one obvious specialist.
