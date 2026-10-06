# Hotel AI Agent

Build the fictional Sanctuary Hotel concierge. Keep code simple and explainable.

## References

Before proposing or coding, read [README](README.md), [requirements](docs/Requirements.md),
[architecture](docs/Architecture.md), [hotel sources](hotel/README.md),
[guest cases](evals/guest-questions.json) and [recording guide](resources/recording-guide.md).
Inspect implementation before claiming features exist.

[Linear](https://linear.app/gradientwork/project/hotel-website-agent-4f0f8e301934/issues)
owns milestones, dependencies, acceptance criteria and status. Read it before work;
report unavailable access. Use confirmed chat scope if unavailable. No duplicate
backlog or detailed build log in the project description. Keep requirements and
architecture current; each feature spec lives in its issue or one linked document.

Baseline: `recording-start-20261006` has only the website and disabled widget.
Backup: `codex/agent-build-backup-20261006` is unfinished reference work.
Never merge it wholesale or present reused code as newly written.

## Build and record

- One vertical slice at a time. State issue, outcome, acceptance criteria and
  checks before coding. During filming, wait for “recording ready”. Finish and
  verify the slice; build later slices only when requested.
- Use Google Agents CLI and its installed skills for development, evaluation and deployment;
  gcloud for cloud configuration and inspection. Check CLI help, model IDs and access.
- Show short prompts, key commands, code and results without an IDE walkthrough.
  Log successful commands, versions and evidence in `resources/build-log.md`.
  Exclude secrets/private account details; pause recording for authentication.

## Engineering and delivery

- Preserve design and imagery. Use `codex/` branches here, no worktrees.
- Separate frontend/backend; follow one Cloud Run service, HTTP/SSE and PostgreSQL.
  Isolate guests, bound history, keep secrets server-side and release DB connections
  before awaiting models.
- Read-only hotel tools, deterministic availability; never invent facts, prices,
  contacts or booking confirmations.
- Verify each slice, including browser checks for widget changes. Distinguish
  deterministic tests, live model access and deployed proof. Have Claude review
  implementation quality/simplicity; report if unavailable.
- Conventional Commit, push, open PR; no agent co-authors. Merge only when authorised.
  Update the issue with results, evidence and commit/PR link. Complete only when
  acceptance criteria pass.

## Cloud

Project: `personal-infrastructure-505708`. Inspect resources first; use hotel-prefixed
names and preserve unrelated workloads. Show resources/costs before provisioning.
Require approval for new spending or destructive changes unless already explicitly
authorised. Claim production readiness or concurrency capacity only with evidence.
