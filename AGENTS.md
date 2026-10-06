# Hotel AI Agent

Build a customer-facing concierge for the fictional Sanctuary Hotel website.
Keep the code simple, organised and easy to explain during a recorded build.

## Start here

Read before proposing or implementing a change:

1. [README.md](README.md): local run commands and documented build state.
2. [Requirements](docs/Requirements.md): guest journeys, scope and acceptance criteria.
3. [Architecture](docs/Architecture.md): components, tools, state and operating constraints.
4. [Hotel source pack](hotel/README.md) and [guest cases](evals/guest-questions.json).
5. [Recording guide](resources/recording-guide.md): filming sequence and checkpoints.

Inspect the checkout before claiming a feature exists. The tag
`recording-start-20261006` is the static website and disabled widget baseline.
Earlier unfinished work is preserved on `codex/agent-build-backup-20261006`.
Do not merge that branch wholesale or present reused code as newly written.

## Linear owns the work

Project: [Hotel Website Agent](https://linear.app/gradientwork/project/hotel-website-agent-4f0f8e301934/issues).

Read the current milestones, issues, dependencies and acceptance criteria from
Linear. Do not duplicate task status or create another backlog in this repo.
If Linear is unavailable, say so and use only the confirmed scope in this chat.

Work through one high-level vertical slice at a time. Requirements and
architecture are long-lived documents. A feature spec belongs in its Linear
issue, or a linked document when needed; keep one authoritative copy.
Do not turn the project description into a detailed implementation log.

## Recorded build workflow

- Before coding, state the selected issue, intended result, acceptance criteria
  and checks. During filming, wait for Owain to say “recording ready”.
- Use Google Agents CLI and its installed skills for agent development,
  evaluation and deployment. Use gcloud for cloud configuration and inspection.
- Check installed CLI help before choosing commands. Verify model IDs and
  access instead of assuming an unverified latest model.
- Show concise prompts, important commands, relevant code and a working result.
  Do not rely on a coding IDE walkthrough.
- As work proceeds, capture successful commands, versions and verification in
  `resources/build-log.md`. Do not log secrets or private account details.
- Pause recording for sign-in and credential screens. Finish and check each
  slice before moving on. Leave later slices unimplemented until requested.

## Engineering and delivery

- Preserve the website design and generated imagery. Use normal `codex/`
  branches in this checkout, without worktrees.
- Keep frontend and backend code separate. Follow the architecture's one
  Cloud Run service, HTTP/SSE and PostgreSQL state model.
- Hotel tools are read-only. Availability is deterministic. Do not invent
  facts, prices, contact details or booking confirmations.
- Keep guest state isolated, history bounded and secrets server-side. Do not
  keep a database connection open while waiting for model output.
- Run checks appropriate to the slice, including real browser checks for
  widget changes. Distinguish deterministic tests from verified live model
  access and deployed behavior.
- Have Claude review implementation slices for correctness and simplicity.
  If Claude is unavailable, report it rather than claim its review occurred.
- Commit checked changes with Conventional Commit messages, push and open a
  pull request. Do not add agent co-authors. Merge only when authorised.
- Update the worked issue with the result, evidence and commit or PR link.
  Mark it complete only when its acceptance criteria pass.

## Cloud boundaries

Use project `personal-infrastructure-505708`. Use hotel-prefixed resources and
preserve unrelated workloads. Inspect current resources before changes.
Show billable resources and costs before provisioning; get approval before
new spending or destructive changes unless already explicitly authorised.
No production readiness or concurrent-user capacity claim without evidence.
