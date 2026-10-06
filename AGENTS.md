# Hotel AI Agent

Build the fictional Sanctuary Hotel concierge. Preserve the website design.

## Context

Read [README](README.md), [requirements](docs/Requirements.md),
[architecture](docs/Architecture.md), [hotel data](hotel/README.md),
[eval cases](evals/guest-questions.json) and [recording guide](resources/recording-guide.md).

[Linear](https://linear.app/gradientwork/project/hotel-website-agent-4f0f8e301934/issues)
owns tasks and status. Read the issue before coding; do not duplicate the backlog.

## Workflow

- Build one slice at a time. State acceptance criteria and checks first.
  During filming, wait for “recording ready”.
- Use Google Agents CLI and its skills; use gcloud for cloud configuration.
  Verify commands and model access. Log successful commands in `resources/build-log.md`.
- Show prompts, commands, code and results. Pause recording for credentials.
- Keep code simple. Verify changes; have Claude review implementation.
  Report unavailable tools or unverified results honestly.
- Use `codex/` branches, no worktrees. Commit, push and open a PR.
  Merge only when authorised; update Linear with evidence.

## Cloud

Use `personal-infrastructure-505708` and hotel-prefixed resources.
Preserve unrelated workloads and keep secrets out of code and logs.
Confirm new spending or destructive actions unless already authorised.
