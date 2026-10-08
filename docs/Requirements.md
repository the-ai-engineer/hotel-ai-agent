# Sanctuary Hotel: requirements

Canonical product scope, 6 October 2026. [Architecture](Architecture.md) defines the implementation. [Linear](https://linear.app/gradientwork/project/hotel-website-agent-4f0f8e301934/overview) owns tasks and milestones.

## Problem and outcome

Visitors should find reliable answers and suitable accommodation without waiting for hotel staff. Staff should spend less time answering repeated questions. These are intended benefits to validate with a real hotel, not measured results of this demo.

Keep the existing Sanctuary Hotel website. Connect its disabled concierge preview to a real ADK agent. The demo uses fictional published policies, villas and occupancy in PostgreSQL. Published optional service charges may be explained; nightly room prices are not available. Guests can review and confirm fictional reservations on a dedicated booking page. The agent can look up session-owned reservations and prepare notes that the guest confirms for hotel review.

## Finished guest journey

- Ask whether breakfast is included. Read the answer and open its published source.
- Ask for a villa for two on exact dates. See matching villa cards with photos, capacity and searched dates.
- Ask a follow-up about cancellation. The agent keeps the conversation context and retrieves policy evidence.
- Refresh the page. Completed answers and cards remain available to the same browser session. A running turn is recovered from server status without another invocation; an interrupted attempt can be explicitly retried as a new turn.
- Stop an answer. Show its confirmed durable state; if completion won the race, retain the saved answer. Otherwise allow another question without treating partial output as complete.
- If information is missing or a dependency fails, get an honest explanation, retry option or explanation that staff confirmation is required.

## Acceptance criteria

| ID | Requirement | Evidence |
| --- | --- | --- |
| R1 | Policy answers read complete published documents selected from the catalogue. Summaries alone are not evidence; missing evidence is acknowledged. | Fixed questions and paraphrases, selected-document/read traces, fact assertions and versioned source links; unpublished documents excluded. |
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
| R12 | Demo booking confirmation is explicit, rejects overlaps, rechecks capacity and dates, and is idempotent. | PostgreSQL concurrency and API/browser confirmation tests. |
| R13 | Owned booking lookup and confirmed notes enforce guest ownership. Failed/reset/expired drafts cannot execute; notes remain pending review. | Cross-guest and note-state regressions. |

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

Real booking-provider or payment writes, accommodation pricing, verified guest accounts, WhatsApp, multiple hotels, a staff inbox, a CMS, embeddings and background agent orchestration. No contact destination is configured in the source pack. Explain this honestly; add a normal contact link only when a destination is approved. There is no staffed live-chat handoff.

## Decisions before release

Verify the selected Gemini model and capacity, deployment region, cloud spend limit and alert recipient. Keep the demo IAM-restricted until the public abuse policy and forwarded-IP attribution are verified. Before real guest use, agree the booking provider, policy owner, backup/deletion policy and operational responder.
