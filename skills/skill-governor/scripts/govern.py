"""Bootstrap a private skill catalog and integrate a reversible host instruction pointer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

import registry


START = "<!-- skill-governor:start -->"
END = "<!-- skill-governor:end -->"
VALUES = {"useful", "conditional", "redundant_candidate", "unsupported", "unassessed"}


def within(path, parent):
    return Path(path).resolve().is_relative_to(Path(parent).resolve())


def discover(specs):
    entries = []
    roots = []
    paths = set()
    ids = set()
    for spec in specs:
        namespace, separator, raw = spec.partition("=")
        if not separator or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", namespace):
            raise ValueError("Source must be namespace=path; namespace uses lowercase letters, digits, hyphens or underscores")
        root = Path(raw).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("Skill source directory does not exist: " + str(root))
        roots.append(str(root))
        files = [root / "SKILL.md"] if (root / "SKILL.md").is_file() else sorted(root.glob("*/SKILL.md"))
        for path in files:
            if not path.resolve().is_relative_to(root):
                raise ValueError("Discovered skill leaves the explicit source root: " + str(path))
            data = registry.metadata(path)
            sid = namespace + ":" + data["name"]
            key = registry.path_key(path)
            if sid in ids or key in paths:
                raise ValueError("Duplicate skill identity or source path: " + sid)
            ids.add(sid)
            paths.add(key)
            entries.append({"id": sid, "path": str(path.resolve()), "domain": "unclassified", "role": "specialist",
                            "origin": "User-supplied root " + namespace, "menu_observation": "unknown", "review": None,
                            "use_when": [], "avoid_when": [], "required_reads": [], "companions": [],
                            "value": "unassessed", "value_reason": "No task-level evidence reviewed", "value_evidence": []})
    return entries, roots


def plan(root):
    snapshot = registry.scan(root)
    lines = ["# Skill governance plan", "", "Status: draft. Source files and task evidence still determine adoption.", "",
             "This is a local environment report. Do not publish it with the Skill Governor source package.", "",
             "## Work sequence", "", "1. Read each relevant source entrypoint fully; distinguish required and conditional references.",
             "2. Classify actual roles, scope, use/avoid conditions and dependencies; assess value from evidence.",
             "3. Resolve overlaps with scoped routes and preserve project/tool gates.",
             "4. Write a tailored POLICY.md, then integrate the verified host entrypoint within authorization.",
             "5. Exercise positive, negative and boundary scenarios; record actual results and limitations.", "",
             "## Current entries", "", "| Skill | Domain | Value | Source state |", "|---|---|---|---|"]
    for item in snapshot["entries"]:
        values = [item["id"], item["domain"], item.get("value", "unassessed"), item["review_state"]]
        lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in values) + " |")
    lines += ["", "## Findings", ""]
    lines += ["- " + json.dumps(issue, ensure_ascii=False) for issue in snapshot["issues"]] or ["- No structural/drift issues found; behavior remains separately assessed."]
    lines += ["", "Do not infer skill quality, live connectivity, comprehension or task success from this plan.", ""]
    return "\n".join(lines)


def initialize(root, specs):
    entries, roots = discover(specs)
    if not entries:
        raise ValueError("No SKILL.md files found in the explicitly supplied roots")
    if root.exists() and any(root.iterdir()):
        raise ValueError("State directory must be absent or empty; use existing lifecycle commands to update it")
    for entry in entries:
        if within(root, Path(entry["path"]).parent):
            raise ValueError("State must be outside individual skill packages to avoid self-fingerprinting")
    root.mkdir(parents=True, exist_ok=True)
    registry.write_json(root / "sources.json", {"schema_version": 1, "entries": entries, "local_roots": roots, "plugin_bundles": []})
    (root / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    (root / "PLAN.md").write_text(plan(root), encoding="utf-8")
    return {"state": str(root), "entries": len(entries), "status": "draft_unreviewed", "host_modified": False}


def classify(root, sid, domain, use_when, avoid_when, value, reason):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", domain) or domain == "unclassified":
        raise ValueError("Choose a nonempty lowercase domain slug other than unclassified")
    if not use_when or any(not text.strip() for text in use_when + avoid_when) or not reason.strip() or value not in VALUES:
        raise ValueError("Use criteria and value reason must be nonblank and value must be supported")
    sources = registry.load_sources(root)
    entry = registry.entry_for(root, sid)
    entry.update(domain=domain, use_when=use_when, avoid_when=avoid_when, value=value, value_reason=reason)
    sources["entries"] = [entry if item["id"] == sid else item for item in sources["entries"]]
    registry.write_json(root / "sources.json", sources)
    return {"id": sid, "domain": domain, "assessment": value, "source_review_changed": False}


def block_bytes(root, newline):
    policy = root / "POLICY.md"
    if not policy.is_file() or not policy.read_text(encoding="utf-8-sig").strip():
        raise ValueError("Write the reviewed, tailored POLICY.md before integration")
    policy_text = str(policy).replace("\\", "/")
    if any(char in policy_text for char in ("\n", "\r", "`")):
        raise ValueError("Policy path cannot be represented safely in an instruction pointer")
    body = [START, "## Skill governance", "",
            "Before substantive work identify the project, stage and authorized outcome; honor explicitly requested skills, project rules and mandatory tool prerequisites.",
            "For skill-selection ambiguity or skill lifecycle work, read the tailored policy at `" + policy_text + "` and only the applicable domain rules.",
            "Read the complete selected SKILL.md and applicable prerequisites before use. Reuse complete unchanged context except when source rules require a fresh read. A summary or read flag is insufficient.",
            "Use the smallest sufficient workflow, possibly no skill. Do not broaden scope or invent tool availability; distinguish selected, read, executed and verified.",
            "After skill changes reconcile the private registry and affected checks. A refresh does not renew source review. Preserve existing authorization and invocation policy.", END]
    return newline.join(line.encode("utf-8") for line in body) + newline


def marker_span(raw):
    starts = list(re.finditer(re.escape(START.encode()), raw))
    ends = list(re.finditer(re.escape(END.encode()), raw))
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0].start() < starts[0].end():
        raise ValueError("Malformed or ambiguous Skill Governor markers; preserve file and resolve manually")
    begin, end = starts[0].start(), ends[0].end()
    if begin and raw[begin - 1:begin] != b"\n":
        raise ValueError("Managed block must start on its own line")
    if raw[end:end + 2] == b"\r\n":
        end += 2
    elif raw[end:end + 1] == b"\n":
        end += 1
    elif end != len(raw):
        raise ValueError("Managed block must end on its own line")
    return begin, end


def integration_paths(root, host):
    key = hashlib.sha256(registry.path_key(host).encode()).hexdigest()[:20]
    return root / "integrations" / (key + ".json"), root / "integrations" / (key + ".before")


def host_hash(host):
    return registry.sha(host) if host.is_file() else None


def atomic_host_write(host, content):
    host.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=host.parent, prefix=".skill-governor-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        if host.exists():
            os.chmod(temporary, host.stat().st_mode)
        os.replace(temporary, host)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def settled_record(record_path, host, dry_run):
    record = registry.read_json(record_path) if record_path.exists() else None
    if record is None:
        return record
    if not isinstance(record, dict):
        raise ValueError("Integration record must be an object")
    if "pending" not in record:
        validate_integration_record(record)
        return record
    if dry_run:
        raise ValueError("Pending integration transaction requires a non-dry retry or manual inspection")
    pending = record["pending"]
    required = {"before_sha256", "after_sha256", "before_record", "after_record"}
    if not isinstance(pending, dict) or not required.issubset(pending):
        raise ValueError("Malformed pending integration transaction")
    for key in ("before_sha256", "after_sha256"):
        if pending[key] is not None and not valid_hash(pending[key]):
            raise ValueError("Pending transaction has an invalid file hash")
    if pending["before_record"] is not None:
        validate_integration_record(pending["before_record"])
    validate_integration_record(pending["after_record"])
    actual = host_hash(host)
    if actual == pending["after_sha256"]:
        resolved = pending["after_record"]
    elif actual == pending["before_sha256"]:
        resolved = pending["before_record"]
    else:
        raise ValueError("Host changed during an interrupted transaction; inspect journal and host before recovery")
    if resolved is None:
        record_path.unlink()
    else:
        registry.write_json(record_path, resolved)
    return resolved


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_integration_record(record):
    if not isinstance(record, dict) or type(record.get("active")) is not bool:
        raise ValueError("Malformed integration ownership record")
    for key in ("host", "backup", "created_at"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError("Integration record needs " + key)
    for key in ("backup_sha256", "after_sha256", "block_sha256"):
        if not valid_hash(record.get(key)):
            raise ValueError("Integration record has an invalid " + key)
    if "host_existed" in record and type(record["host_existed"]) is not bool:
        raise ValueError("Integration host_existed must be boolean")
    if not isinstance(record.get("separator_hex", ""), str) or re.fullmatch(r"(?:0a|0d)*", record.get("separator_hex", "")) is None:
        raise ValueError("Integration separator must encode only line breaks")


def commit_host_change(record_path, host, content, previous, desired, remove=False):
    after_hash = None if remove else hashlib.sha256(content).hexdigest()
    registry.write_json(record_path, {"pending": {"before_sha256": host_hash(host), "after_sha256": after_hash,
                                                "before_record": previous, "after_record": desired}})
    if remove:
        host.unlink()
    else:
        atomic_host_write(host, content)
    registry.write_json(record_path, desired)


def integrate(root, host, dry_run=False):
    registry.load_sources(root)
    if host.is_symlink():
        raise ValueError("Resolve and explicitly select the real host instruction file instead of a symlink")
    host = host.resolve()
    if within(host, root):
        raise ValueError("Host instruction file must be outside private state")
    record_path, backup = integration_paths(root, host)
    prior = settled_record(record_path, host, dry_run)
    existed = host.exists()
    raw = host.read_bytes() if host.exists() else b""
    raw.decode("utf-8-sig")
    span = marker_span(raw)
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    block = block_bytes(root, newline)
    separator = b""
    if span:
        current = raw[span[0]:span[1]]
        if not prior or hashlib.sha256(current).hexdigest() != prior["block_sha256"]:
            raise ValueError("Existing managed block is unowned or changed; inspect before replacing")
        updated = raw[:span[0]] + block + raw[span[1]:]
    else:
        if prior and prior.get("active"):
            raise ValueError("Previously installed block is missing; reconcile before reinstalling")
        separator = b"" if not raw or raw.endswith(newline * 2) else (newline if raw.endswith(newline) else newline * 2)
        updated = raw + separator + block
    result = {"host_file": str(host), "changed": updated != raw, "dry_run": dry_run, "proposed_block": block.decode("utf-8")}
    if dry_run or updated == raw:
        return result
    record_path.parent.mkdir(parents=True, exist_ok=True)
    if prior is None or not prior.get("active"):
        backup.write_bytes(raw)
    host.parent.mkdir(parents=True, exist_ok=True)
    record = {"host": str(host), "backup": str(backup), "backup_sha256": registry.sha(backup),
              "after_sha256": hashlib.sha256(updated).hexdigest(), "block_sha256": hashlib.sha256(block).hexdigest(),
              "host_existed": prior.get("host_existed", True) if prior and prior.get("active") else existed,
              "separator_hex": prior.get("separator_hex", "") if span and prior else separator.hex(),
              "active": True, "created_at": registry.now()}
    commit_host_change(record_path, host, updated, prior, record)
    return result


def rollback(root, host, dry_run=False):
    if host.is_symlink():
        raise ValueError("Select the real host file explicitly")
    host = host.resolve()
    record_path, backup = integration_paths(root, host)
    record = settled_record(record_path, host, dry_run)
    if record is None:
        raise ValueError("No completed integration is recorded for this host")
    if not record.get("active"):
        return {"changed": False, "status": "already_rolled_back"}
    if not backup.is_file() or registry.sha(backup) != record["backup_sha256"]:
        raise ValueError("Rollback backup missing or changed")
    raw = host.read_bytes()
    span = marker_span(raw)
    if span is None or hashlib.sha256(raw[span[0]:span[1]]).hexdigest() != record["block_sha256"]:
        raise ValueError("Managed block changed or disappeared; refusing to overwrite newer edits")
    unchanged = hashlib.sha256(raw).hexdigest() == record["after_sha256"]
    if unchanged:
        updated = backup.read_bytes()
    else:
        prefix = raw[:span[0]]
        separator = bytes.fromhex(record.get("separator_hex", ""))
        original_prefix = backup.read_bytes() + separator
        if separator and original_prefix and prefix.endswith(original_prefix):
            prefix = prefix[:-len(separator)]
        updated = prefix + raw[span[1]:]
    if not dry_run:
        desired = dict(record, active=False, rolled_back_at=registry.now())
        commit_host_change(record_path, host, updated, record, desired,
                           remove=unchanged and not record.get("host_existed", True))
    return {"host_file": str(host), "changed": True, "dry_run": dry_run, "unrelated_edits_preserved": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--source", action="append", required=True, help="namespace=explicit_skill_root")
    sub.add_parser("plan")
    classify_parser = sub.add_parser("classify")
    classify_parser.add_argument("--id", required=True)
    classify_parser.add_argument("--domain", required=True)
    classify_parser.add_argument("--use-when", action="append", required=True)
    classify_parser.add_argument("--avoid-when", action="append", default=[])
    classify_parser.add_argument("--value", choices=sorted(VALUES), required=True)
    classify_parser.add_argument("--reason", required=True)
    for name in ("integrate", "rollback"):
        command = sub.add_parser(name)
        command.add_argument("--host-file", type=Path, required=True)
        command.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.state.expanduser().resolve()
    if args.command == "init":
        result = initialize(root, args.source)
    elif args.command == "plan":
        text = plan(root)
        (root / "PLAN.md").write_text(text, encoding="utf-8")
        result = {"plan": str(root / "PLAN.md"), "adoption": "not_inferred"}
    elif args.command == "classify":
        result = classify(root, args.id, args.domain, args.use_when, args.avoid_when, args.value, args.reason)
    elif args.command == "integrate":
        result = integrate(root, args.host_file.expanduser(), args.dry_run)
    else:
        result = rollback(root, args.host_file.expanduser(), args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, registry.yaml.YAMLError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        raise SystemExit(2)
