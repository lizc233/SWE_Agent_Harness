# Security

## Security model

SWE Agent Harness treats user prompts, model output, repository content, tool names, and tool arguments as untrusted input.

The current controls are:

- workspace-relative path resolution;
- explicit tool registration;
- `observe`, `write`, `execute`, and `destructive` risk classes;
- `allow`, `deny`, and `ask` decisions;
- read-only, ask, and auto-edit operating modes;
- exact-match atomic editing with concurrent-change detection;
- command argument arrays executed with `shell=False`;
- command timeout and output limits;
- step, tool-call, wall-clock, and context budgets;
- traces that omit raw tool arguments.

## Important limitations

This project is not an operating-system sandbox.

An approved executable can access resources available to the current operating-system user. `cwd` limits where the command starts, not what the process can access. Command timeout terminates the direct process, but complete descendant-process cleanup is not guaranteed on every platform.

Do not use `auto-edit` on an untrusted repository without reviewing its contents. Commands always require approval in the current implementation, including in auto-edit mode.

## Reporting

Do not publish API keys, private repository contents, or exploit details in a public issue. Remove secrets from traces before sharing them. Report security problems privately to the repository maintainer.

