## What changed

Describe the concrete skill-governance failure this change addresses.

## Evidence and boundaries

- Which selection, setup, lifecycle, evaluation, host, or CLI contract changes?
- Which positive and negative cases demonstrate the correction?
- Does it change privacy, permissions, network behavior, deletion, persistence, or rollback?

## Validation

```bash
python -m pip install -r requirements.txt
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
python -X utf8 -m unittest discover -s tests -v
```

- [ ] I ran the relevant audit and tests.
- [ ] I removed private governance state, credentials, local paths, caches, and backups.
- [ ] I updated English and Chinese documentation when user-facing behavior changed.
