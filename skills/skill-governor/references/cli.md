# Local tools and state contract

Python 3.10 or newer and PyYAML 6 are required. Install the adjacent skill `requirements.txt` using your environment's approved dependency workflow. Run commands from the repository root; for an installed standalone skill use its actual script path. All state paths are explicit. Mutating commands must run serially against a state directory; concurrent writers are unsupported. Scripts never execute a reviewed skill or connect to its services.

## Bootstrap and plan

```sh
python skills/skill-governor/scripts/govern.py --state .skill-governance init --source personal=skills
python skills/skill-governor/scripts/govern.py --state .skill-governance plan
python skills/skill-governor/scripts/registry.py --root .skill-governance check
```

This complete example inventories this repository's `skills` directory. Replace the source with the host-confirmed skill directory for a real setup; pass additional `--source namespace=path` arguments for distinct roots. A root is one skill folder or a direct container of skill folders, not a recursive search. The initializer requires an absent or empty state directory, outside all discovered skill packages. It writes a draft, never an adopted policy. Equal names in distinct namespaces remain distinct entries.

The initial `check` normally exits 1: unclassified and unreviewed entries are expected findings. For check and refresh, exit 0 means no implemented structural/drift checks found issues; both exit 1 when issues exist. Exit 2 means invalid input or an operational error. `plan`, `init`, `classify`, `register`, `review`, `integrate` and `rollback` exit 0 on successful operation, without implying a clean audit. `check` is read-only; `refresh` writes `registry.json` and archives a changed prior snapshot without renewing reviews, even when it exits 1. An empty source library is rejected before initialization writes; use a minimal instruction-only policy until actual skills exist.

## Classify and record a completed review

```sh
python skills/skill-governor/scripts/govern.py --state .skill-governance classify --id personal:skill-governor --domain governance --use-when "Set up or audit skill governance" --avoid-when "An ordinary task has an unambiguous specialist" --value conditional --reason "Useful for library management; task outcomes still need evaluation"
python skills/skill-governor/scripts/registry.py --root .skill-governance read --id personal:skill-governor
python skills/skill-governor/scripts/registry.py --root .skill-governance show --id personal:skill-governor
```

`classify` changes annotations, not review state. An agent must fully review the entrypoint and applicable references, write a real evidence report, then run `review` with `--id`, `--evidence` (existing nonempty absolute file) and `--reviewer`. The command records the caller's review assertion with source/evidence hashes; it does not perform the review. A changed or missing report invalidates its binding.

`list` prints registered IDs, domains, roles, menu observations and paths; optional `--domain` filters that list. `show --id` inspects one registered source and its current review binding. Neither changes state.

`register` requires `--id`, `--path` (absolute SKILL.md), `--domain`, `--role`, `--origin`; optional `--menu` is observed, not-listed or unknown. Registration neither installs nor approves the skill. Roles are entry, specialist, project, explicit-specialist, internal and system-unlisted. Source provenance must describe what was actually inspected. Use the host-supported installer separately when installation is requested.

## Tailored state

`sources.json` uses schema_version 1 and arrays `entries`, `local_roots`, `plugin_bundles`. Each entry requires nonempty `id`, absolute `path`, `domain`, `role`. Useful reviewed annotations are `use_when`, `avoid_when`, `companions` (registered IDs), `required_reads` (path/condition objects), `value`, `value_reason`, `value_evidence`. Preserve annotations when reconciling updates. Domains are user-chosen slugs; unclassified requires review. Values are useful, conditional, redundant_candidate, unsupported and unassessed. The checker does not assess whether prose annotations are correct or complete.

For a host with versioned plugin caches, optional bundle objects have `id`, absolute `container`, `observed_version` and `known_inactive_versions`. This adapter expects `container/version/skills/name/SKILL.md`. Use it only for a verified matching layout. New cached versions are candidates, never automatically treated as active. Non-file/runtime skills remain documented limitations outside the filesystem checker.

Fingerprinting hashes package-relative names and bytes, excluding .git, __pycache__, node_modules, .venv and .pytest_cache. These exclusions are not reviewed dependencies. Symlinked resource directories and file links leaving the package require explicit handling; do not treat a rejected package as reviewed. Resource hashes bind a version, not the quality or safety of the contents. Use explicit real source paths when links are involved.

## Host pointer and rollback

After writing and reviewing the environment-specific `POLICY.md`, the following commands demonstrate a **repository-scoped** host entrypoint. Use them only after verifying this host reads AGENTS.md and the user's scope includes that file.

```sh
python skills/skill-governor/scripts/govern.py --state .skill-governance integrate --host-file AGENTS.md --dry-run
python skills/skill-governor/scripts/govern.py --state .skill-governance integrate --host-file AGENTS.md
python skills/skill-governor/scripts/govern.py --state .skill-governance rollback --host-file AGENTS.md --dry-run
python skills/skill-governor/scripts/govern.py --state .skill-governance rollback --host-file AGENTS.md
```

Dry runs do not write files. Integration requires UTF-8 host text, preserves its original bytes and newline convention, and refuses changed/unowned/malformed managed blocks. The tool does not verify that the host loads the file or that POLICY.md is semantically reviewed. Never select arbitrary personal instruction files by guessing.

Rollback restores original content if the complete installed file is unchanged, including removing an unchanged host file created by integration. Otherwise it removes only the unchanged owned block, preserving subsequent outside edits. An inserted separator is removed only when the original preceding content is still identifiable; ambiguous surrounding whitespace is preserved. Changed owned blocks or damaged backups require inspection, not forced overwrite. Keep private state and backups until rollback is no longer needed. Serialize integration and rollback operations.

A write-ahead journal records the before/after file hashes before an atomic host replacement. If interrupted, a non-dry retry of integration or rollback reconciles the journal when the host still matches a recorded state. A dry run never performs recovery. If the host changed to neither recorded state, inspect the journal and host manually; do not discard the journal or overwrite newer content. This protects ordinary operation failures, not arbitrary power-loss durability, concurrent writers, or hostile filesystem changes.

## Optional task evidence

For substantial workflows, `read --record` or `read-file --file --record` emits full file content and appends its hash with event `content_emitted`. File and record arguments must be absolute. Output truncation requires further reading: an emitted-content record does not prove the agent saw the complete text.

A record has schema_version 1 and arrays selections, reads, executions, verifications, limitations. Each selection contains id, stage, reason, required_paths (all applicable absolute prerequisite paths) and an explicit boolean requires_execution. Read events contain id, path, sha256, event and ISO timestamp. Execution/verification events contain id, stage, status, summary and evidence_path; status is passed, failed, blocked or not_applicable.

`verify-record --record` checks selected entrypoint and declared prerequisites against current hashes. A stage with requires_execution true also needs passed execution and verification events with existing evidence files. It does not infer omitted prerequisites, establish comprehension, validate evidence truth, or certify task success. Result `record_consistent` is deliberately narrower. Simple conversation and no-skill tasks need no record file.
