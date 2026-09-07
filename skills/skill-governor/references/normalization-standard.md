# Skill Normalization Standard

Apply this standard to the exact skill the user placed in scope. Preserve its domain behavior unless the user requested a redesign.

## Inspect before editing

1. Resolve the target folder and read its complete `SKILL.md`.
2. List `agents/`, `scripts/`, `references/`, and `assets/`; read only resources needed to understand or validate the workflow.
3. Identify the skill's one primary job, expected inputs and outputs, positive triggers, negative triggers, tool dependencies, and destructive or external actions.
4. Run `scripts/audit_skills.py --root TARGET_PARENT --format markdown` or perform an equivalent manual audit.
5. Record nearby overlaps and duplicate names. Do not modify neighboring skills without explicit scope.

## Normalize `SKILL.md`

- Use a lowercase, hyphenated name under 64 characters and match the folder name.
- Keep YAML frontmatter to `name` and `description` unless the active host specification explicitly requires another supported field.
- Front-load the description with the primary job and concrete trigger terms. Include when to use it and a concise exclusion when a nearby skill could be confused with it.
- Write the body in imperative language and keep essential procedures in `SKILL.md`.
- Keep the body under 500 lines. Move detailed schemas, variants, examples, or policies into directly linked one-level `references/` files.
- Avoid duplicating the same rule in the body and references.
- Keep only files that support runtime use. Remove generated placeholders; do not add README, changelog, or installation-guide clutter.
- Use scripts only for deterministic, repeated, or error-prone operations. Test every new or changed script on representative input.

## Normalize UI metadata

If `agents/openai.yaml` is supported, make it agree with `SKILL.md`:

- Quote string values.
- Provide `interface.display_name`, a 25–64 character `interface.short_description`, and a one-sentence `interface.default_prompt` that explicitly mentions `$skill-name`.
- Set `policy.allow_implicit_invocation: false` only when accidental triggering is risky or explicit use is essential.
- Declare only real MCP dependencies. Do not declare ordinary shell programs, scripts, or hypothetical tools as MCP dependencies.

## Resolve overlaps

Prefer boundaries over merging:

- Separate by artifact or app when implementation environments differ.
- Separate by lifecycle stage when research, design, implementation, testing, and review have different outputs.
- Keep project-specific rules inside repository scope when they should not affect unrelated work.
- Rename, disable, merge, or delete a skill only when the user explicitly authorizes that action.
- When two skills remain valid, make each description name the other's exclusion boundary.

## Validate behavior

1. Run the creator's `quick_validate.py` against the skill folder when available.
2. Run every changed script with representative input and inspect its output.
3. Test at least:
   - two prompts that should trigger the skill,
   - two prompts that should not trigger it,
   - one ambiguous prompt that should resolve to the intended neighbor or ask a material question.
4. Confirm the skill does not claim unavailable tools, permissions, credentials, or automatic installation behavior.
5. Re-run the inventory audit and report remaining duplicates, overlaps, and validation limitations.
