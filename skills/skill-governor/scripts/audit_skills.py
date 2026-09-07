#!/usr/bin/env python3
"""Inventory local Codex skills and flag structural or routing risks.

Uses only the Python standard library. It never modifies a skill.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]+", re.IGNORECASE)
CJK_RE = re.compile(r"[\u3400-\u9fff]+")
STOP_WORDS = {
    "and", "are", "for", "from", "into", "the", "this", "that", "use",
    "uses", "using", "when", "with", "skill", "skills", "codex", "user",
    "task", "tasks", "work", "create", "edit", "manage", "file", "files",
    "should", "can", "will", "needs", "need", "any", "all", "only",
}


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        if value[0] == '"':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    issues: list[str] = []
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, ["missing-yaml-frontmatter"]
    end = normalized.find("\n---", 4)
    if end < 0:
        return {}, ["unclosed-yaml-frontmatter"]

    lines = normalized[4:end].splitlines()
    data: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = KEY_RE.match(line)
        if not match:
            index += 1
            continue
        key, raw = match.group(1), (match.group(2) or "").strip()
        if raw in {">", ">-", "|", "|-"}:
            block: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index][0].isspace()):
                block.append(lines[index].strip())
                index += 1
            data[key] = " ".join(part for part in block if part)
            continue
        data[key] = unquote(raw)
        index += 1
    return data, issues


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            resolved = path.expanduser().absolute()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def default_roots() -> list[Path]:
    candidates: list[Path] = []
    current = Path.cwd().resolve()
    for folder in (current, *current.parents):
        candidates.append(folder / ".agents" / "skills")
    user_root = Path.home()
    candidates.append(user_root / ".agents" / "skills")
    configured = os.environ.get("CODEX_HOME")
    if configured:
        candidates.append(Path(configured) / "skills")
    candidates.append(user_root / ".codex" / "skills")
    return [path for path in unique_paths(candidates) if path.exists()]


def skill_files(roots: Iterable[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file() and root.name == "SKILL.md":
            found.append(root)
        elif root.is_dir():
            found.extend(root.rglob("SKILL.md"))
    return unique_paths(found)


def routing_tokens(value: str) -> set[str]:
    lowered = value.lower()
    tokens = {
        token.strip("-")
        for token in WORD_RE.findall(lowered)
        if len(token.strip("-")) > 2 and token.strip("-") not in STOP_WORDS
    }
    for run in CJK_RE.findall(value):
        if len(run) == 1:
            tokens.add(run)
        else:
            tokens.update(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def inspect_skill(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        return {
            "name": path.parent.name,
            "path": str(path),
            "description": "",
            "issues": [f"read-error:{exc}"],
            "body_lines": 0,
        }

    metadata, issues = parse_frontmatter(text)
    name = metadata.get("name", "").strip()
    description = metadata.get("description", "").strip()
    if not name:
        issues.append("missing-name")
    elif not NAME_RE.fullmatch(name) or len(name) > 64:
        issues.append("invalid-name")
    if name and path.parent.name != name:
        issues.append("folder-name-mismatch")
    if not description:
        issues.append("missing-description")
    else:
        if len(description) < 50:
            issues.append("description-may-be-too-vague")
        trigger_terms = (
            "use when", "use for", "do not use", "trigger", "when ",
            "用于", "使用场景", "不用于", "不要用于", "当", "适用",
        )
        if not any(term in description.lower() for term in trigger_terms):
            issues.append("description-may-lack-trigger-boundary")
    if "todo" in description.lower():
        issues.append("contains-todo")

    body = text
    normalized = text.replace("\r\n", "\n")
    if normalized.startswith("---\n"):
        end = normalized.find("\n---", 4)
        if end >= 0:
            body = normalized[end + 4 :]
    body_lines = len(body.splitlines())
    if body_lines > 500:
        issues.append("body-over-500-lines")
    if not (path.parent / "agents" / "openai.yaml").exists():
        issues.append("missing-optional-agents-metadata")

    return {
        "name": name or path.parent.name,
        "path": str(path),
        "description": description,
        "issues": sorted(set(issues)),
        "body_lines": body_lines,
    }


def build_report(roots: list[Path], threshold: float) -> dict[str, Any]:
    skills = [inspect_skill(path) for path in skill_files(roots)]
    skills.sort(key=lambda item: (item["name"].lower(), os.path.normcase(item["path"])))

    by_name: dict[str, list[str]] = defaultdict(list)
    for skill in skills:
        by_name[skill["name"]].append(skill["path"])
    duplicates = [
        {"name": name, "paths": paths}
        for name, paths in sorted(by_name.items())
        if len(paths) > 1
    ]

    token_sets = [routing_tokens(f"{item['name']} {item['description']}") for item in skills]
    overlaps: list[dict[str, Any]] = []
    for left in range(len(skills)):
        for right in range(left + 1, len(skills)):
            first, second = token_sets[left], token_sets[right]
            union = first | second
            if not union:
                continue
            shared = first & second
            score = len(shared) / len(union)
            if score >= threshold:
                overlaps.append(
                    {
                        "score": round(score, 3),
                        "first": skills[left]["name"],
                        "second": skills[right]["name"],
                        "first_path": skills[left]["path"],
                        "second_path": skills[right]["path"],
                        "shared_terms": sorted(shared)[:12],
                    }
                )
    overlaps.sort(key=lambda item: (-item["score"], item["first"], item["second"]))
    issue_count = sum(bool(skill["issues"]) for skill in skills)
    return {
        "roots": [str(path) for path in roots],
        "summary": {
            "skills": len(skills),
            "skills_with_issues": issue_count,
            "duplicate_names": len(duplicates),
            "possible_overlaps": len(overlaps),
            "overlap_threshold": threshold,
        },
        "duplicates": duplicates,
        "possible_overlaps": overlaps,
        "skills": skills,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Skill Audit",
        "",
        f"- Skills: {summary['skills']}",
        f"- Skills with issues: {summary['skills_with_issues']}",
        f"- Duplicate names: {summary['duplicate_names']}",
        f"- Possible overlaps: {summary['possible_overlaps']} (threshold {summary['overlap_threshold']})",
        "",
        "## Roots",
        "",
    ]
    lines.extend(f"- `{root}`" for root in report["roots"])

    lines.extend(["", "## Duplicate names", ""])
    if report["duplicates"]:
        for duplicate in report["duplicates"]:
            lines.append(f"- **{duplicate['name']}**")
            lines.extend(f"  - `{path}`" for path in duplicate["paths"])
    else:
        lines.append("None.")

    lines.extend(["", "## Possible overlaps", ""])
    if report["possible_overlaps"]:
        for item in report["possible_overlaps"]:
            shared = ", ".join(item["shared_terms"]) or "n/a"
            lines.append(
                f"- **{item['first']}** ↔ **{item['second']}**: "
                f"{item['score']:.3f}; shared: {shared}"
            )
    else:
        lines.append("None at this threshold.")

    lines.extend(["", "## Skills", ""])
    if not report["skills"]:
        lines.append("No skills found.")
    for skill in report["skills"]:
        issues = ", ".join(skill["issues"]) if skill["issues"] else "none"
        lines.extend(
            [
                f"### {skill['name']}",
                "",
                f"- Path: `{skill['path']}`",
                f"- Body lines: {skill['body_lines']}",
                f"- Issues: {issues}",
                f"- Description: {skill['description'] or '(missing)'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        help="Skill root or SKILL.md path. Repeat to add roots. Defaults to repo and user roots.",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.42,
        help="Jaccard threshold for possible description overlap (default: 0.42).",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit 1 when structural issues or duplicate names are found.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0.0 <= args.threshold <= 1.0:
        print("error: --threshold must be between 0 and 1", file=sys.stderr)
        return 2
    roots = unique_paths(args.root) if args.root else default_roots()
    roots = [path for path in roots if path.exists()]
    report = build_report(roots, args.threshold)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(markdown(report), end="")
    if args.fail_on_issues and (
        report["summary"]["skills_with_issues"] or report["summary"]["duplicate_names"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
