# Sanctuary Hotel: requirements

Canonical product scope, refined 7 October 2026. [Architecture](Architecture.md) defines the implementation. [Linear](https://linear.app/gradientwork/project/hotel-website-agent-4f0f8e301934/overview) owns tasks and milestones.

## Problem and outcome

Visitors should find reliable answers and suitable accommodation without waiting for hotel staff. Staff should spend less time answering repeated questions. These are intended benefits to validate with a real hotel, not measured results of this demo.

Keep the existing Sanctuary Hotel website. Connect its disabled concierge preview to a real ADK agent. The demo uses fictional published policies, villas and occupancy in PostgreSQL. It checks availability but never creates a booking.

## Users and evidence

The primary user is an anonymous prospective guest browsing on desktop or mobile. Hotel staff benefit from fewer repeated enquiries, but have no staff-facing interface in this release. The demo operator installs, evaluates and operates the service.

The current repository contains the website and disabled widget, not a working concierge. The [hotel source pack](../hotel/README.md) supplies fictional policies and inventory; [guest evaluation cases](../evals/guest-questions.json) supply expected answers and failure behavior. The architecture describes planned behavior, not implementation evidence.

Assumption: guests benefit from self-service policy answers and date-based villa discovery. Validate this with a hotel and representative guests before claiming enquiry reduction or booking impact.

## Major user flows

| Flow | Trigger and main path | Alternatives and completion |
| --- | --- | --- |
| F1: Open the concierge | Guest opens the website widget, sees its scope and fictional-data notice, then enters a question. | Keyboard and mobile users can open, use and close it. Closing the widget does not erase completed conversation history. |
| F2: Find a policy answer | Guest asks whether breakfast is included. The concierge retrieves published evidence, answers and provides a source link. Guest opens the source to verify it. | Missing, unpublished or conflicting evidence cannot support a confident answer. Explain the uncertainty and whether staff confirmation is needed. |
| F3: Find a suitable villa | Guest supplies check-in, checkout and party size. The concierge checks the entire stay and shows matching villa cards with photos, capacity, searched dates and check time. | Clarify ambiguous dates or missing counts before lookup. Explain invalid dates, unsupported inventory dates and no matches distinctly. Never imply a reservation or invent prices. |
| F4: Continue a conversation | Guest asks a follow-up such as cancellation after a villa search. The concierge uses completed conversation context and retrieves fresh policy evidence. | Ask for clarification if the reference is unclear or older context is unavailable. Do not carry evidence or history between guests. |
| F5: Stop an answer | While a turn is running, guest selects Stop. The widget shows the confirmed final state and allows another question. | Partial output remains visibly incomplete. A committed result may win the race with Stop; otherwise show interruption. Never show a false completed answer. |
| F6: Recover after refresh or disconnect | Guest refreshes or reconnects in the same valid browser session. The widget loads completed answers, sources and cards and checks any active attempt. | Show running, completed, failed or interrupted status. Recover a committed result without another model invocation. An expired session offers a new conversation without exposing old history. |
| F7: Recover from failure or load limits | A dependency fails, a deadline expires or a request is rejected. Guest receives a safe explanation and an appropriate retry action. | Retrying an existing turn ID cannot duplicate work. A failed attempt needs an explicit new attempt. Explain when retry is appropriate and when information needs staff confirmation. |
| F8: Request booking or human help | Guest asks to book, pay or speak to staff. The concierge explains its supported scope and what still needs hotel confirmation. | No booking, payment or service request is created. With no approved contact destination, explain the limitation. Do not claim a staffed handoff or successful contact. |

A representative end-to-end journey is F1 → F2 → F3 → F4 → F6: a guest verifies breakfast, finds a villa for two on exact dates, checks cancellation terms and returns to the saved results.

## Functional requirements and acceptance

The existing R1–R11 identifiers remain stable. The evidence column defines the proof required before claiming acceptance; it does not claim that these checks already pass.

| ID | Requirement | Evidence |
| --- | --- | --- |
| R1 | Policy answers use published hotel evidence. Missing evidence is acknowledged. | Fixed questions, fact assertions and working source links; unpublished documents excluded. |
| R2 | Villa cards match capacity and availability for every night of the requested stay. | PostgreSQL tests for overlapping bookings, adjacent stays, closed/missing nights and cancelled bookings. |
| R3 | Ambiguous dates and missing guest counts prompt clarification before lookup. No invented prices or booking confirmation. | Evaluation cases and browser journey. |
| R4 | Anonymous guests can access only their own conversations. | Cookie, Origin, expiry and cross-session ownership tests on every read/write endpoint. |
| R5 | Each conversation permits one active turn. Retrying the same turn ID never starts another invocation. | Two API processes sharing PostgreSQL; duplicate and competing POST tests. |
| R6 | Completed answers survive restart. Stop, disconnect, timeout and failed persistence cannot turn partial output into a completed answer. | Cancellation, recovery, crash and final-write race checks. |
| R7 | Independent guest turns progress concurrently with isolated history and tool evidence. | At least 20 conversations across two processes locally; staged deployed capacity exercise below. |
| R8 | The widget supports loading, Stop, retry, refresh recovery, expired session, empty results and truthful staff-confirmation guidance. | Desktop/mobile browser checks, keyboard access, readable contrast, safe rendering and reduced motion. |
| R9 | Abuse limits and bounded model context apply before model calls. No credentials or private records reach the browser. | Shared-budget tests, runtime database permission tests and configured deployment checks. |
| R10 | Failures are traceable without logging guest text or secrets. Conversation data is deleted on schedule. | Injected lookup failure, linked trace/logs, delivered alert and retention cleanup. |
| R11 | A clean checkout can be installed, migrated, explicitly seeded, run, evaluated and deployed using documented prompts and commands. | Rehearsal with recorded versions and successful outputs. |

## Non-functional requirements

These requirements refine the quality constraints in R4–R11. Targets already agreed in the architecture are retained; unagreed service targets remain open decisions.

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| REQ-12 | Capacity: support 100 independent active turns at the agreed normal-load target, with at least 99% completing within 90 seconds during a five-minute sustained deployed exercise. | The staged exercise below passes, with no normal-load admission rejection, ownership leak, duplicate invocation or stuck lock. |
| REQ-13 | Responsiveness: website, health and turn-status requests remain responsive during chat load. An agent attempt has a 90-second application deadline; overload must not create an unbounded wait. | Concurrent non-chat requests and timeout/overload checks. Agree a numerical non-chat latency target before the capacity exercise. |
| REQ-14 | Reliability and integrity: committed answers and their evidence survive restart. Interrupted, expired or uncommitted output cannot become a completed answer. | Restart, cancellation, crash, reconnect and final-write race checks across two API processes. |
| REQ-15 | Security: every conversation and turn operation enforces session ownership; browser mutations validate Origin. Deployed session cookies are HttpOnly, Secure, host-only and SameSite=Lax, with a fixed 24-hour expiry. | Cross-session read/write denial, invalid Origin and cookie/expiry checks. IDs alone never grant access. |
| REQ-16 | Privacy: logs contain no guest messages, prompts, raw evidence, cookies or secrets. Delete sessions and associated conversation data 30 days after session creation through daily cleanup. | Log inspection, scheduled deletion checks and least-privilege access tests. Backup deletion commitments must be agreed before real guest use. |
| REQ-17 | Accessibility and compatibility: all widget actions work by keyboard; state changes and errors are accessible; text is readable, contrast is sufficient and reduced-motion preferences are respected. | Desktop/mobile browser checks, focus and screen-reader checks. Supported browser versions and a formal accessibility conformance target remain release decisions. |
| REQ-18 | Content safety: user/model text cannot execute markup or scripts. Cards and links use validated public hotel data and approved destinations. Private booking records and credentials never reach the browser. | Malicious-content rendering checks, URL validation and inspection of tool/API responses. |
| REQ-19 | Cost and abuse control: enforce shared admission limits before model invocation. Bound input to 2,000 characters, history to 20 completed turns and 16,000 characters, evidence to five 2,000-character passages, tool calls to eight, output to 2,048 tokens and final results to 64 KiB. | Boundary and shared-budget checks across processes; inspect configured deployment limits. Property-wide throughput and cloud spend limits require agreement. |
| REQ-20 | Observability: failures can be traced across a request, agent and tools without private text. Measure latency, failures, interruptions, rejections, model usage and dependency waits. | Inject a lookup failure, find correlated safe diagnostics and demonstrate a delivered alert; verify database/readiness failure detection. |
| REQ-21 | Operability and reproducibility: a clean checkout supports documented installation, explicit migration/seed, running, evaluation and deployment. Deployment preserves unrelated workloads and supports rollback-compatible migrations. | Recorded clean-checkout rehearsal and release/rollback checks. Never seed automatically on application startup. |

## Concurrent-user target

100 concurrent users means 100 independent agent turns in flight, not 100 visitors browsing the website. It is a target until measured with the real selected Gemini model.

Stage the deployed test at 10, 25, 50 and 100 active turns. Sustain the final stage for five minutes. Require at least 99% of admitted turns to complete within 90 seconds, no admission rejection at the agreed normal-load target, and zero ownership leaks, duplicate invocations or stuck locks. Surviving upstream quota/dependency errors count as failures. Record first-text/completion latency, model calls/tokens, database waits and resource settings. Verify the site, health and turn-status endpoints remain responsive during chat load. Agree the paid-test budget before running it.

## Delivery and video constraints

- Use Google ADK, Gemini, Agents CLI and gcloud. Record the actual prompts, commands and versions as work proceeds.
- Start the recording from the saved website and widget. Build the real agent, test it, deploy it and investigate a failure.
- Use concise prompts through a coding assistant, without a coding IDE walkthrough.
- Deploy into `personal-infrastructure-505708`; use hotel-prefixed resources and preserve unrelated workloads.
- Source stays in the private `the-ai-engineer/hotel-ai-agent` repository for the community.
- Label fictional inventory clearly. A real hotel needs an authoritative booking integration and operational sign-off.

## Out of scope

Booking or payment writes, prices, verified guest accounts, WhatsApp, multiple hotels, a staff inbox, a CMS, embeddings and background agent orchestration. No contact destination is configured in the source pack. Explain this honestly; add a normal contact link only when a destination is approved. There is no staffed live-chat handoff.

## Success measures

Validate answer usefulness, successful villa discovery and reduction in repeated staff enquiries with a real hotel. Establish baselines and agreed targets before presenting these as measured benefits. Passing demo acceptance checks does not establish commercial impact.

## Open decisions and release gates

| Decision | Current position | Effect |
| --- | --- | --- |
| Model, region and capacity | Verify the selected Gemini model and endpoint; architecture proposes application region `europe-west2`. | Blocks cloud capacity claims and release configuration, not document review. |
| Spend and alert ownership | Agree cloud spend limit, paid-test budget and alert recipient. | Blocks paid capacity testing and operational sign-off. |
| Public access and abuse policy | Keep the demo IAM-restricted until public abuse limits and forwarded-IP attribution are verified. | Blocks public release. |
| Responsiveness and compatibility | Agree non-chat latency target, supported browsers and accessibility conformance target. | Blocks complete performance/accessibility acceptance claims. |
| Production availability and recovery | No uptime objective, recovery-time target or recovery-point target is agreed. Set these with the operator before real guest use. | Blocks production service commitments; no invented SLA applies to the demo. |
| Real hotel authority and operations | Agree booking provider, policy owner, backup/deletion policy and operational responder. | Blocks real guest use. |
| Contact destination | No approved destination and no staffed live chat. | Keep F8 truthful; an approved destination is needed before adding a contact link. |
