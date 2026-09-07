# Host integration

The portable core is Markdown instructions plus local Python tools. It needs no particular model, cloud API, MCP server or external account. Actual discovery, automatic invocation and instruction-file loading remain host features.

## Codex

Use the host's current skill catalog and supported personal/project skill location. A package contains SKILL.md with name/description and optional agents/openai.yaml. The included metadata permits ordinary implicit selection for governance tasks, not every conversation. Resolve the actual applicable AGENTS.md before integration. Check official documentation or the installed host implementation when placement/inheritance is uncertain.

## Other skill-capable hosts

Install the skill folder using the host's supported method. If the host reads CLAUDE.md or another instruction file, pass that exact file to integrate after confirming it is loaded and the user authorized its scope. The script is a marked text-block writer; it does not verify host inheritance. Do not assume Codex-specific YAML changes another host's invocation behavior.

## Instruction-only hosts

Read SKILL.md and relevant references directly. Keep the policy in the task context if no persistent instruction entrypoint exists. Report that cross-task persistence is unavailable or unverified. Do not pretend the package installed a hook or enforcement layer.

## Portability boundary

Python 3.10+ and PyYAML 6 are required for scripts. The instructions can still guide an audit without Python. Use actual local path semantics; runtime state stores local absolute paths and must be regenerated/reconciled after moving machines. Test coverage on one OS is not proof of every host/OS integration. The supplied CI matrix exercises Python on Windows, Linux and macOS when run by a repository host.
