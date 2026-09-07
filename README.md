# Skill Governor

[中文说明](README.zh-CN.md) · [Install guide](AI_INSTALL.md) · [Documentation](https://fanfanfanfanfan626.github.io/skill-governor/) · MIT · Version 1.0.0

An open-source, local-first governance skill for AI agent skill libraries. It helps an assistant decide when a skill is useful, choose the smallest sufficient workflow, read required instructions, detect overlap and drift, and review additions or updates without creating skill sprawl.

Ask the assistant to use **`$skill-governor`**. It inspects the actual environment, drafts a scoped policy, and implements authorized local setup. Policies and inventories belong to each user's private state; this repository contains the reusable instructions and tools.

## What it does

- Inventories explicitly selected skill roots, with namespaces for equal names.
- Reviews actual scope, prerequisites, dependencies and overlapping workflows.
- Produces task/stage selection rules, including when no skill is needed.
- Requires the complete selected SKILL.md and applicable prerequisite documents.
- Governs adding, updating and retiring skills without silently deleting them.
- Separates source review, tool availability, execution evidence and usefulness.
- Detects source/reference drift and integrates a reversible host instruction pointer.
- Audits structural problems and likely routing overlap without modifying skills.

The AI performs source review and contextual judgment. Python helpers handle discovery, state, hashes and evidence consistency. A scan never claims to prove that a skill is useful, understood or safe.

## Who it is for

Skill Governor is most useful when an assistant has many skills, overlapping triggers, multiple installation roots, or copies that move between devices. It is intentionally unnecessary for a simple task with one obvious specialist.

It is Codex-first and also usable as an instruction package on other agent hosts that support compatible skill folders. Host discovery, persistent routing and tool permissions must be verified separately; copying the folder alone does not prove compatibility.

## Install

1. Download or clone this repository.
2. Copy `skills/skill-governor` into a skill directory supported by your host, preserving the whole folder. Check for an existing copy before replacing it.
3. Reload skills using your host's supported workflow and check that `skill-governor` appears.
4. If using the optional Python helpers, use Python 3.10+ and install that folder's `requirements.txt`. From this repository root:

```sh
python -m pip install -r requirements.txt
```

In Codex, use its skill installer with [`skills/skill-governor`](skills/skill-governor), or copy that whole folder to your verified personal skill root. See [AI_INSTALL.md](AI_INSTALL.md) for the exact package identity and verification steps. Installation alone does not create an always-on enforcement mechanism. Persistent routing requires a verified host-readable instruction entrypoint within the user's authorized scope.

## Use

Suggested requests:

> Use $skill-governor to audit my current skills. Keep the audit read-only and explain overlaps, required reading, missing capabilities and evidence limits.

> Use $skill-governor to set up skill governance for this project. Inspect existing rules, create a tailored plan and implement the authorized local setup with rollback instructions.

> Use $skill-governor to review this new skill before installation: determine when it adds value, when to avoid it and which existing workflows overlap.

> Use $skill-governor to reassess this updated skill and test the affected selection rules. Do not renew old reviews just because the inventory refreshed.

The assistant works in the user's language. With an existing governance policy it should reconcile that policy, not create a competing one. If the host has no verified persistent entrypoint, it supplies an explicit-use workflow and reports that limitation.

## Optional CLI

The following runnable example inventories this repository's own skill. State stays in a separate private directory.

```sh
python skills/skill-governor/scripts/govern.py --state .skill-governance init --source personal=skills
python skills/skill-governor/scripts/govern.py --state .skill-governance plan
python skills/skill-governor/scripts/registry.py --root .skill-governance check
```

Initial check findings are expected: entries are unclassified and unreviewed. Read [the complete CLI contract](skills/skill-governor/references/cli.md) before classification, review recording, host integration or rollback. Generated PLAN.md is a draft. The assistant must inspect sources and write an environment-specific POLICY.md before adoption.

For a read-only structural and routing audit without creating governance state:

```sh
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
```

## Boundaries

- No background daemon, scheduled scan, skill execution, network access or publishing in the helpers.
- No hardcoded personal paths, private project rules or universal skill whitelist.
- Host catalogs, permissions and mandatory tool prerequisites remain authoritative.
- Plain instruction integration is advisory; this package is not a security sandbox or a guaranteed every-turn dispatcher.
- Fingerprints and evidence records are consistency checks, not comprehension or outcome proof.
- Concurrent writers to one private state are unsupported; serialize mutations.
- A different host may need an explicit instruction-file adapter; compatibility is not established merely by copying the skill.

Keep generated inventories, absolute paths, audit evidence and integration backups private. Inspect the actual release file list and archive before publishing. See [host notes](skills/skill-governor/references/hosts.md) and [evaluation rules](skills/skill-governor/references/evaluation.md).

## Development

```sh
python -m pip install -r requirements.txt
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
python -X utf8 -m unittest discover -s tests -v
```

The current suite contains 63 unit tests. Tests use temporary local fixtures and do not change personal host configuration. CI is configured for Windows, Linux and macOS with Python 3.10 and 3.13; a configured matrix is not evidence that remote jobs have run. Report actual tested platforms and results for each release.

Contributions should include a concrete routing or lifecycle failure, a scoped correction and relevant positive/negative cases. Keep source instructions separate from generated private state. Do not add automated deletion, telemetry or external actions without an explicit design and user authorization model.

## License

[MIT](LICENSE). The installed skill folder includes its own copy of the license. Third-party skills inspected by Skill Governor retain their own licenses and policies.
