# Skill Acquisition Policy

Use this policy only after confirming that the task lacks a reusable procedure. Keep acquisition subordinate to the user's actual task.

## Search order

1. Re-check the current host skill catalog, including system, personal, plugin, and repository-scoped skills.
2. Run `scripts/audit_skills.py` when local folders may contain an undisclosed, duplicated, or malformed candidate.
3. If the built-in `skill-installer` is available, read and follow it to list curated OpenAI skills.
4. Search a user-supplied repository or another source only when curated skills do not match.
5. If the gap is really an app, connector, account, or MCP capability, switch to the available plugin-management workflow. Respect any requirement that the user explicitly name or approve a plugin.

## Auto-install gate

Automatically install a skill only when every condition is true:

- The user has explicitly requested automatic skill acquisition or explicitly invoked this skill for that purpose.
- The missing capability is a reusable procedure, not facts, reasoning effort, data access, credentials, or an executable tool.
- One candidate uniquely matches the required deliverable and scope.
- The source is the curated `openai/skills` collection or another source the user explicitly supplied and trusted.
- Installation is local and reversible, does not overwrite an existing skill, and needs no new credential or elevated permission.

If any condition fails, present the best candidate and the precise unresolved issue instead of installing it.

## Install and verify

1. Use `skill-installer` rather than copying files by hand.
2. Install at most the smallest set that closes the verified gap.
3. Read the installed `SKILL.md`; inspect any script before executing it.
4. Confirm the name, description, source, dependencies, and trigger fit.
5. Run structural validation when the creator's validator is available.
6. Refresh the inventory and check for duplicate names or strong overlaps.
7. Use the new skill in the current turn only if the host exposes it. Otherwise report that it becomes available on the next turn or after restart and continue with safe general work.

## Failure and sprawl controls

- Make one acquisition attempt per distinct gap. Do not repeatedly install near-duplicates.
- Do not install a skill merely because the problem is unfamiliar or difficult.
- Do not generate a new persistent skill automatically after a single task.
- Never treat a successful download as proof that the skill is correct or that its dependent tools are connected.
- If installation fails, keep the original task moving with available capability and report the exact remaining limitation.
