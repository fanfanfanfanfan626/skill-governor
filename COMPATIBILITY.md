# Compatibility and evidence

| Environment or capability | Status | Evidence and limit |
| --- | --- | --- |
| Standalone package | Verified for v1.0.0 | The release ZIP contains the full nested Skill, requirements, references, scripts, metadata, and MIT license; a published checksum binds its bytes. |
| Python helpers | Tested contract | Unit tests cover temporary fixtures on the repository's configured Python 3.10 and 3.13 matrix. Actual remote job results must be checked per commit. |
| Codex Skill discovery | Package-compatible | The Skill follows the local directory and `SKILL.md` layout. Installation alone does not guarantee automatic routing every turn. |
| Other Agent Skills hosts | Instruction-compatible candidate | The host must verify discovery, relative resources, Python, permissions, and a persistent instruction entry point separately. |
| Read-only audit | Locally runnable | `audit_skills.py` reads only the selected roots and does not execute inspected skills. |
| Persistent governance | Host-dependent | Requires a verified host-readable rule entry point and explicit authorization for writes. It is advisory, not a security sandbox. |

File hashes prove version identity, not source comprehension, safe behavior, selection quality, or task outcomes. A credible compatibility report names the host/version, Skill release or commit, exposed roots, tools, permissions, commands actually run, and observed results.
