"""Local skill catalog and evidence checks; never executes a skill or installs tools."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tempfile

import yaml


IGNORED = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache"}


def path_key(path):
    return os.path.normcase(str(Path(path).resolve()))


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".write-", delete=False) as stream:
            temp = Path(stream.name)
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def metadata(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.S)
    if match is None:
        raise ValueError("Missing YAML frontmatter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict) or not all(isinstance(data.get(k), str) and data[k].strip() for k in ("name", "description")):
        raise ValueError("Frontmatter requires nonempty name and description")
    return data


def fingerprint(folder):
    folder = Path(folder).resolve()
    result = hashlib.sha256()
    count = 0
    files = []
    for directory, subdirs, names in os.walk(folder, followlinks=False):
        subdirs[:] = sorted(d for d in subdirs if d not in IGNORED)
        for name in subdirs:
            if (Path(directory) / name).is_symlink():
                raise ValueError("Linked resource directories require explicit review: " + str(Path(directory) / name))
        files.extend(Path(directory) / name for name in names)
    for path in sorted(files):
        rel = path.relative_to(folder)
        if path.is_symlink() and not path.resolve().is_relative_to(folder):
            raise ValueError("Resource symlink leaves skill folder: " + str(path))
        result.update(rel.as_posix().encode("utf-8") + b"\0")
        result.update(sha(path).encode("ascii") + b"\0")
        count += 1
    return result.hexdigest(), count


def load_sources(root):
    data = read_json(root / "sources.json")
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError("Unsupported sources schema")
    for entry in data["entries"]:
        if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("id", "path", "domain", "role")):
            raise ValueError("Every source requires nonempty id, path, domain and role")
    for field in ("local_roots", "plugin_bundles"):
        if not isinstance(data.get(field, []), list):
            raise ValueError("sources requires an array for " + field)
    return data


def entry_for(root, skill_id):
    matches = [x for x in load_sources(root)["entries"] if x["id"] == skill_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one registered entry for {skill_id}; found {len(matches)}")
    return matches[0]


def inspect_entry(entry):
    item = dict(entry)
    path = Path(entry["path"])
    item.update(installed=path.is_file(), structure_valid=False, review_state="invalid", tool_connection="not_checked", behavior_validation="not_inferred")
    if not path.is_absolute() or path.name != "SKILL.md":
        item["error"] = "Registered path must be absolute and end in SKILL.md"
        return item
    if not path.is_file():
        item["review_state"] = "missing"
        return item
    try:
        data = metadata(path)
        item.update(name=data["name"], description=data["description"], entrypoint_sha256=sha(path))
        item["fingerprint"], item["resource_files"] = fingerprint(path.parent)
        ui_path = path.parent / "agents/openai.yaml"
        ui = yaml.safe_load(ui_path.read_text(encoding="utf-8-sig")) if ui_path.exists() else {}
        ui = ui or {}
        if not isinstance(ui, dict):
            raise ValueError("openai.yaml must contain an object")
        item["implicit_policy"] = ui.get("policy", {}).get("allow_implicit_invocation", True)
        item["declared_tool_dependencies"] = ui.get("dependencies", {}).get("tools", [])
        item["structure_valid"] = True
        review = entry.get("review") or {}
        reviewed = review.get("fingerprint")
        item["review_state"] = "source_reviewed" if reviewed == item["fingerprint"] else ("changed_requires_review" if reviewed else "not_reviewed")
        if item["review_state"] == "source_reviewed":
            evidence = Path(review.get("evidence_path", ""))
            valid_review = all(isinstance(review.get(k), str) and review[k].strip() for k in ("reviewer", "timestamp", "scope", "evidence_sha256", "entrypoint_sha256"))
            if not valid_review or not evidence.is_absolute() or not evidence.is_file():
                item["review_state"] = "review_evidence_invalid"
            elif sha(evidence) != review["evidence_sha256"] or review["entrypoint_sha256"] != item["entrypoint_sha256"]:
                item["review_state"] = "review_evidence_changed"
    except (ValueError, OSError, yaml.YAMLError, AttributeError, TypeError) as exc:
        item["error"] = str(exc)
        item["review_state"] = "invalid"
    return item


def scan(root):
    sources = load_sources(root)
    entries = [inspect_entry(entry) for entry in sources["entries"]]
    issues = []
    ids = [entry["id"] for entry in entries]
    paths = [path_key(entry["path"]) for entry in entries]
    for label, values in (("id", ids), ("path", paths)):
        for duplicate in sorted({x for x in values if values.count(x) > 1}):
            issues.append({"kind": "duplicate_" + label, "value": duplicate})
    for entry in entries:
        if entry["domain"] == "unclassified":
            issues.append({"kind": "needs_classification", "id": entry["id"]})
        if not entry["structure_valid"]:
            issues.append({"kind": "missing_or_invalid", "id": entry["id"], "detail": entry.get("error", "source not found")})
        elif entry["review_state"] != "source_reviewed":
            issues.append({"kind": entry["review_state"], "id": entry["id"]})
        for companion in entry.get("companions", []):
            if companion not in ids:
                issues.append({"kind": "unknown_companion", "id": entry["id"], "companion": companion})
    discovered = set()
    for folder in sources.get("local_roots", []):
        root_path = Path(folder)
        if root_path.is_dir():
            candidates = [root_path / "SKILL.md"] if (root_path / "SKILL.md").is_file() else root_path.glob("*/SKILL.md")
            discovered.update(path_key(p) for p in candidates)
        else:
            issues.append({"kind": "source_root_missing", "path": str(root_path)})
    for path in sorted(discovered.difference(paths)):
        issues.append({"kind": "unregistered_local", "path": path})
    for bundle in sources.get("plugin_bundles", []):
        container = Path(bundle["container"])
        registered_version = bundle["observed_version"]
        for version in sorted(container.iterdir()) if container.exists() else []:
            if not version.is_dir() or version.name == registered_version:
                continue
            if any((version / "skills").glob("*/SKILL.md")) and version.name not in bundle.get("known_inactive_versions", []):
                issues.append({"kind": "plugin_version_candidate", "plugin": bundle["id"], "version": version.name,
                               "detail": "Verify current host catalog; no automatic version selection"})
        current = container / registered_version / "skills"
        if not current.is_dir() or not any(current.glob("*/SKILL.md")):
            issues.append({"kind": "observed_plugin_version_missing", "plugin": bundle["id"], "path": str(current)})
        for skill in sorted(current.glob("*/SKILL.md")):
            if path_key(skill) not in paths:
                issues.append({"kind": "unregistered_plugin_skill", "plugin": bundle["id"], "path": str(skill)})
    return {"schema_version": 1, "generated_at": now(), "entries": entries, "issues": issues,
            "limitations": ["Review hashes are version bindings, not comprehension or behavior proof.",
                            "Plugin cache presence is not active-host discovery.",
                            "Tools and external services are not executed by this checker."]}


def refresh(root):
    snapshot = scan(root)
    catalog = root / "registry.json"
    if catalog.exists():
        old = read_json(catalog)
        compare = lambda data: {k: v for k, v in data.items() if k != "generated_at"}
        if compare(old) != compare(snapshot):
            key = hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest()[:16]
            archive = root / "snapshots" / (key + ".json")
            if not archive.exists():
                write_json(archive, old)
    write_json(catalog, snapshot)
    return snapshot


def emit_read(root, skill_id, path, record_path):
    entry_for(root, skill_id)
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        raise ValueError("Read path must be an existing absolute file")
    content = path.read_text(encoding="utf-8-sig")
    print(content)
    if record_path:
        record_path = Path(record_path)
        if not record_path.is_absolute():
            raise ValueError("Record path must be absolute")
        record = read_json(record_path) if record_path.exists() else {
            "schema_version": 1, "selections": [], "reads": [], "executions": [], "verifications": [], "limitations": []}
        record["reads"].append({"id": skill_id, "path": str(path.resolve()), "sha256": sha(path),
                                "event": "content_emitted", "timestamp": now()})
        write_json(record_path, record)


def verify_record(root, record):
    errors = []
    if not isinstance(record, dict) or record.get("schema_version") != 1 or not record.get("selections"):
        return ["Record needs schema_version 1 and at least one selection"]
    for field in ("selections", "reads", "executions", "verifications", "limitations"):
        if not isinstance(record.get(field), list):
            errors.append("Record requires array: " + field)
    if errors:
        return errors
    nonblank = lambda value: isinstance(value, str) and bool(value.strip())
    for field in ("selections", "reads", "executions", "verifications"):
        if any(not isinstance(value, dict) for value in record[field]):
            errors.append("Record requires objects in: " + field)
    if errors:
        return errors
    for selection in record["selections"]:
        if not all(nonblank(selection.get(k)) for k in ("id", "stage", "reason")):
            errors.append("Selection needs nonblank id, stage and reason")
        if not isinstance(selection.get("required_paths"), list) or any(not nonblank(p) for p in selection.get("required_paths", []) or []):
            errors.append("Selection requires an array of applicable path strings")
        if type(selection.get("requires_execution")) is not bool:
            errors.append("Selection requires explicit boolean requires_execution")
    for read in record["reads"]:
        if not all(nonblank(read.get(k)) for k in ("id", "path", "sha256", "event", "timestamp")):
            errors.append("Read event missing nonblank id, path, sha256, event or timestamp")
        else:
            try:
                datetime.fromisoformat(read["timestamp"])
            except ValueError:
                errors.append("Read timestamp must be ISO 8601")
    for field in ("executions", "verifications"):
        for event in record[field]:
            if not all(nonblank(event.get(k)) for k in ("id", "stage", "status", "summary", "evidence_path")):
                errors.append("Malformed " + field + " event")
            elif event["status"] not in {"passed", "failed", "blocked", "not_applicable"}:
                errors.append("Unknown " + field + " status")
    if errors:
        return errors
    selections = record["selections"]
    selected_ids = {x["id"] for x in selections}
    for read in record.get("reads", []):
        if read.get("id") not in selected_ids:
            errors.append("Read event has unselected id: " + str(read.get("id")))
    for selection in selections:
        sid = selection["id"]
        stage = selection.get("stage")
        try:
            entry = entry_for(root, sid)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not stage or not selection.get("reason") or not isinstance(selection.get("required_paths"), list):
            errors.append(f"{sid}: missing stage, reason or applicable required_paths")
        required = [entry["path"]] + selection.get("required_paths", [])
        for filename in required:
            path = Path(filename)
            if not path.is_absolute() or not path.is_file():
                errors.append(f"{sid}: missing required absolute file {filename}")
                continue
            found = any(r.get("id") == sid and Path(r.get("path", "")).resolve() == path.resolve()
                        and r.get("sha256") == sha(path) and r.get("event") == "content_emitted"
                        for r in record.get("reads", []))
            if not found:
                errors.append(f"{sid}: no fresh read evidence for {filename}")
        if selection.get("requires_execution") is True:
            for field in ("executions", "verifications"):
                relevant = [x for x in record.get(field, []) if x.get("id") == sid and x.get("stage") == stage]
                if not relevant or relevant[-1].get("status") != "passed":
                    errors.append(f"{sid}/{stage}: no passed {field} evidence")
                    continue
                evidence = Path(relevant[-1].get("evidence_path", ""))
                if not evidence.is_absolute() or not evidence.is_file() or not relevant[-1].get("summary"):
                    errors.append(f"{sid}/{stage}: missing {field} evidence file or summary")
        elif selection.get("requires_execution") is not False:
            errors.append(f"{sid}: requires_execution must be explicit boolean")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Explicit private governance state directory")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("refresh")
    listing = sub.add_parser("list")
    listing.add_argument("--domain")
    show = sub.add_parser("show")
    show.add_argument("--id", required=True)
    for command in ("read", "read-file"):
        reader = sub.add_parser(command)
        reader.add_argument("--id", required=True)
        reader.add_argument("--record", type=Path)
        if command == "read-file":
            reader.add_argument("--file", type=Path, required=True)
    verify = sub.add_parser("verify-record")
    verify.add_argument("--record", type=Path, required=True)
    register = sub.add_parser("register")
    register.add_argument("--id", required=True)
    register.add_argument("--path", type=Path, required=True)
    register.add_argument("--domain", required=True)
    register.add_argument("--role", choices=["entry", "specialist", "project", "explicit-specialist", "internal", "system-unlisted"], required=True)
    register.add_argument("--origin", required=True)
    register.add_argument("--menu", choices=["observed", "not-listed", "unknown"], default="unknown")
    review = sub.add_parser("review")
    review.add_argument("--id", required=True)
    review.add_argument("--evidence", type=Path, required=True)
    review.add_argument("--reviewer", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command in {"check", "refresh"}:
        snapshot = refresh(root) if args.command == "refresh" else scan(root)
        print(json.dumps({"entries": len(snapshot["entries"]), "issues": snapshot["issues"],
                          "source_reviewed": sum(x["review_state"] == "source_reviewed" for x in snapshot["entries"])}, ensure_ascii=False, indent=2))
        return int(bool(snapshot["issues"]))
    if args.command == "list":
        entries = load_sources(root)["entries"]
        print(json.dumps([{k: entry.get(k) for k in ("id", "domain", "role", "menu_observation", "path")}
                          for entry in entries if not args.domain or entry["domain"] == args.domain], ensure_ascii=False, indent=2))
    elif args.command == "show":
        print(json.dumps(inspect_entry(entry_for(root, args.id)), ensure_ascii=False, indent=2))
    elif args.command in {"read", "read-file"}:
        path = args.file if args.command == "read-file" else Path(entry_for(root, args.id)["path"])
        emit_read(root, args.id, path, args.record)
    elif args.command == "verify-record":
        errors = verify_record(root, read_json(args.record))
        print(json.dumps({"record_consistent": not errors, "errors": errors, "behavior_or_comprehension_verified": False}, indent=2))
        return int(bool(errors))
    elif args.command == "register":
        sources = load_sources(root)
        if any(x["id"] == args.id or Path(x["path"]).resolve() == args.path.resolve() for x in sources["entries"]):
            raise ValueError("Identity/path already registered; reconcile existing entry instead")
        if not args.path.is_absolute() or args.path.name != "SKILL.md":
            raise ValueError("Provide an absolute SKILL.md path")
        metadata(args.path)
        sources["entries"].append({"id": args.id, "path": str(args.path), "domain": args.domain, "role": args.role,
                                   "origin": args.origin, "menu_observation": args.menu, "registered_at": now(), "review": None})
        write_json(root / "sources.json", sources)
        print("Registered, review still required: " + args.id)
    elif args.command == "review":
        if not args.evidence.is_absolute() or not args.evidence.is_file() or args.evidence.stat().st_size == 0:
            raise ValueError("Review evidence must be an existing nonempty absolute file")
        sources = load_sources(root)
        entry = entry_for(root, args.id)
        inspected = inspect_entry(entry)
        if not inspected["structure_valid"]:
            raise ValueError(inspected.get("error", "Invalid source"))
        entry["review"] = {"fingerprint": inspected["fingerprint"], "entrypoint_sha256": inspected["entrypoint_sha256"],
                           "reviewer": args.reviewer, "evidence_path": str(args.evidence), "evidence_sha256": sha(args.evidence),
                           "timestamp": now(), "scope": "source entrypoint/routing review; no execution implied"}
        sources["entries"] = [entry if x["id"] == args.id else x for x in sources["entries"]]
        write_json(root / "sources.json", sources)
        print("Recorded source review: " + args.id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        raise SystemExit(2)
