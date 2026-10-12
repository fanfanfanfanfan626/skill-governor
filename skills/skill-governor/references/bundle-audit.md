# Read-only bundle preflight

Use `scripts/audit_bundle.py <skill-directory-or.zip>` for one distributable package. It emits JSON and never extracts, runs, installs or uploads the package. This is distinct from the installed-library inventory in `audit_skills.py`.

The [OpenAI Skills guide](https://developers.openai.com/api/docs/guides/tools-skills), checked 2026-10-12, specifies case-insensitive exactly-one SKILL.md, at most 500 files, 50 MB ZIP upload and 25 MB per uncompressed file. This implementation uses conservative decimal-byte thresholds. A ZIP needs one top-level Skill folder with its manifest directly inside.

Additional local safeguards reject unsafe paths, Unicode-normalized case collisions, Windows reserved/invalid names, duplicate entries, links/reparse points and encrypted files. The manifest read is capped at 1 MB and directory/ZIP entry inspection at 2,000 entries; these are local guards, not official API limits. Other member payloads are not decompressed or CRC-checked. Metadata checks reuse the intentionally limited frontmatter parser; this is not complete Agent Skills certification. A filesystem changed concurrently during inspection is outside the consistency guarantee; audit a stable copy.

Exit 0: no implemented structural finding. Exit 1: structural or inspection-limit finding. Exit 2: missing target or incomplete inspection. A pass does not establish safety, trustworthy instructions, actual routing, dependency readiness, host compatibility or account/API acceptance. Read the source before making it available to an agent. No registry migration or global setup is necessary.

Illustrative output fragment for two case-colliding manifests (not a real-user result):

```json
{"conforms":false,"issues":[{"code":"duplicate-or-case-colliding-path","path":"example/skill.md"},{"code":"exactly-one-manifest-required","path":""}]}
```

The full report also contains target path, limits and limitations. Keep private paths local or redact before opening an Issue.
