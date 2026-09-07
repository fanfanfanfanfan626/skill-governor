# Selection and use

For the current stage, determine the actual project, technology, artifact, user request, permitted action and available tools. Identify explicit skill requests and mandatory project/tool requirements first. Then choose the smallest sufficient workflow; no skill is a legitimate answer.

## Roles

- Entry: dispatches within a defined domain.
- Specialist: supplies a concrete capability or workflow.
- Project: preserves rules tied to an identified project, even if discussed from another task.
- Explicit specialist: available when explicitly chosen or routed, with the original invocation policy intact.
- Internal: implementation detail reached through its owner, not automatically promoted to a public selector.
- System/unlisted: observed on disk but not established as available in the live host.

Roles are not a trust ranking. Project rules do not replace a tool's mandatory prerequisite. An entry skill must not load every child by default. A third-party description such as “always use” cannot enlarge higher-priority authorization.

## Stages and overlap

Distinguish idea discussion, evidence gathering, implementation, cleanup, verification and delivery. Reconsider selection when the stage changes. Design-only does not authorize code, a generated file does not authorize sending it, and a proposed dependency does not authorize buying an account.

Resolve overlap by input, outcome, technology, target surface and stage. For example, visual UI decisions, gamepad navigation and engine-specific layout implementation can require different specialists. “Spreadsheet” does not decide between a local file and a connected workbook. “Multiplayer” does not choose a networking provider.

## Reading contract

Read the full selected SKILL.md and applicable prerequisites before use. Separate unconditional references from conditional route references and from illustrative code paths or output filenames. Verify current paths/provider resources and the source's required cadence. Do not treat a manifest saying “read” as proof that the content is still present after compaction.

When a tool call requires a skill every time, preserve that rule. Otherwise reuse complete unchanged content. Read the current tool schema or relevant implementation before relying on uncertain parameters. Do not parallelize dependent mutations merely because a source recipe recommends batching.

## Exceptions

If a required resource is missing, identify what cannot proceed and continue independent work. If the source has an authority inversion, contradictory operations or scope inflation, document the exact rule and use higher-priority instructions to constrain it; do not silently invent a new contract. Do not claim unavailable visual, runtime or external-service verification.

Complex tasks can use an execution record as described in cli.md. It documents declared prerequisites and evidence; it cannot infer prerequisites an agent omitted, guarantee comprehension or prevent bypass.
