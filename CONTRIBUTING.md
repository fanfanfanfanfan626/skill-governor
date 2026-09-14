# Contributing

Contributions should begin with a concrete skill-selection, review, installation, update, routing, or retirement failure.

## Before changing behavior

- Read [`skills/skill-governor/SKILL.md`](skills/skill-governor/SKILL.md) and the referenced contract that owns the behavior.
- Keep reusable package instructions separate from private inventories, paths, evidence, policies, and backups.
- Preserve the distinction between installed, discovered, reviewed, tool-ready, executed, verified, and accepted.
- Do not add silent deletion, background monitoring, network access, publishing, or universal allowlists.

## Validate

```bash
python -m pip install -r requirements.txt
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
python -X utf8 -m unittest discover -s tests -v
```

Pull Requests should describe the real failure, the smallest correction, positive and negative cases, compatibility implications, and any new permission or privacy boundary. Remove generated governance state, local paths, credentials, personal data, caches, and backups before committing.
