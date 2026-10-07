# Sanctuary Hotel requirements

Sanctuary Hotel is a fictional hotel website with an AI concierge. The concierge helps guests understand hotel policies, find suitable villas, and review fictional reservations. This document defines the intended product and the conditions that demonstrate it works. [Architecture](Architecture.md) describes how the system meets these requirements.

## Purpose and users

Guests need reliable answers while planning a stay. They should be able to ask in everyday language, check the evidence behind an answer, and find accommodation that fits their dates and party size.

The hotel needs consistent answers to routine questions without giving the concierge authority to make unsupported promises. Policies, inventory, and permissions determine what the system can say and do.

The intended benefits are faster guest decisions and fewer repeated questions for staff. These are hypotheses to validate with a real hotel, not measured results of this demonstration.

| User | Need |
| --- | --- |
| Prospective guest | Understand policies and find a villa for a specific stay. |
| Guest with a demo reservation | Review their own reservation and prepare a request for hotel review. |
| Hotel content owner | Publish accurate policies and inventory without exposing private or unpublished information. |
| System operator | Identify failures, control usage, and delete conversation data on schedule. |

## Scope

Preserve the existing website design and connect its concierge widget to the agent. The system supports sourced policy answers, villa details, full-stay availability, saved conversations, explicit demo booking confirmation, and guest-confirmed hotel notes.

All hotel facts and inventory are fictional. A demo reservation records a choice within this system; it does not book a real room or take payment. A submitted note remains pending hotel review; it does not approve a service, change a reservation, or notify external staff.

The system does not provide nightly room prices, real booking-provider writes, payments, verified guest accounts, WhatsApp, multiple properties, a staff inbox, a CMS, wiki synchronization, embeddings, background agent orchestration, or a staffed live-chat handoff. Published optional service charges may be explained. No contact destination is configured, so the concierge must explain when staff confirmation is needed without inventing a contact link.

## Guest journey

1. A guest asks whether breakfast is included. The concierge reads the relevant published policy, answers with its conditions, and links to that version of the source.
2. The guest gives arrival and departure dates and the total number of guests. The system returns villas that fit the party and are available for every night.
3. The guest opens a villa page, reviews the stay, and explicitly confirms a fictional reservation on the booking page.
4. The guest asks about late checkout. The concierge reads the policy and looks up only that guest's reservation before preparing a note.
5. The guest reviews the note and selects **Send request**. The system records it as pending hotel review.
6. After a page refresh, completed conversation results remain available to the same browser session. Interrupted work has a clear recovery state.

At every step, missing information prompts clarification. Missing evidence or a failed dependency produces an honest explanation and an appropriate retry or staff-confirmation option.

## Product requirements

The IDs below are stable references for implementation and verification.

### Answers and accommodation

| ID | Required behavior | Acceptance evidence |
| --- | --- | --- |
| R1 | Policy answers use complete published documents selected from the catalogue. Summaries guide selection but do not support factual answers. Answers link to the document revision read. Missing or unpublished evidence cannot produce an invented answer. | Fixed questions, paraphrases, and cross-document cases show the selected reads, supported facts, and versioned sources. Unpublished documents are inaccessible. |
| R2 | Villa results satisfy capacity and availability for every night of the requested stay. Checkout is exclusive. Cancelled bookings do not block a stay; closed or missing nights cannot be treated as available. | Inventory checks cover overlapping bookings, adjacent stays, closed nights, missing nights, and cancelled bookings. |
| R3 | The concierge clarifies ambiguous dates and missing guest counts before an availability lookup. It does not invent prices or claim to have confirmed a booking. | Evaluation cases and a browser journey show clarification before lookup and truthful booking guidance. |

### Conversations and guest access

| ID | Required behavior | Acceptance evidence |
| --- | --- | --- |
| R4 | Anonymous guests can access only their own conversations and related records. Knowing a record ID is insufficient to gain access. | Every read and write endpoint is checked for session ownership, cookie handling, allowed Origin, and expiry. |
| R5 | A conversation has at most one active turn. Repeating a turn ID does not start another model invocation. | Duplicate and competing requests across two API processes sharing the database prove both rules. |
| R6 | Completed answers survive an application restart. Stop, disconnect, timeout, crash, or failed persistence cannot promote partial output into a completed answer. | Cancellation, crash recovery, and final-write race checks distinguish completed results from interrupted attempts. |
| R7 | Independent guest turns progress concurrently. Each turn uses only its own conversation history and tool evidence. | At least 20 conversations run across two local processes, followed by the deployed capacity exercise below. |
| R8 | The widget provides clear loading, Stop, retry, refresh recovery, expired-session, and empty-result states. Starting a new conversation clears the active context and is rejected while a turn is active; closing the widget does not reset it. | Desktop and mobile checks cover these states, keyboard access, readable contrast, reduced motion, and safe rendering. |

### Safety and operation

| ID | Required behavior | Acceptance evidence |
| --- | --- | --- |
| R9 | Shared abuse limits and bounded context apply before model calls. Credentials and other guests' records never reach the browser or model. | Shared-budget tests, context-boundary checks, database permission checks, and deployment configuration inspection. |
| R10 | Operators can trace failures without logging guest text or secrets. Sessions and their conversations are deleted 30 days after session creation. Authentication expires after 24 hours and does not itself delete records. | An injected lookup failure produces a safe guest response, linked diagnostics, and a delivered alert. Retention checks verify scheduled deletion. |
| R11 | A clean checkout can be installed, migrated, explicitly seeded, run, evaluated, and deployed using documented commands. | A reproducible rehearsal records the versions, configuration, and successful results. |

### Demo reservations and hotel requests

| ID | Required behavior | Acceptance evidence |
| --- | --- | --- |
| R12 | Only explicit confirmation on the booking page creates a demo reservation. Confirmation rechecks dates, capacity, and full-stay availability, rejects overlapping reservations, and is idempotent. | Database concurrency checks and API/browser tests prove confirmation, conflict handling, and safe retries. |
| R13 | Booking lookup and hotel notes enforce guest ownership. A note requires explicit guest submission and remains pending review. Failed, superseded, expired, or reset-conversation drafts cannot be submitted. | Cross-guest checks and draft-state regressions prove that invalid drafts have no effect. |

## Performance and availability

The release target is **100 independent agent turns in flight**. Browsing visitors do not count as active turns. This target remains unproven until measured with the selected Gemini model in the deployed system.

Run staged exercises at 10, 25, 50, and 100 active turns. Sustain the final stage for five minutes. Acceptance requires:

- At least 99% of admitted turns complete within 90 seconds. Upstream quota and dependency errors count as failures.
- No admission rejection at the agreed normal-load target.
- Zero ownership leaks, duplicate model invocations, or stuck conversation locks.
- The website, health checks, and turn-status endpoints remain responsive during chat load.

Record time to first text, completion latency, model calls and tokens, database waits, and resource settings. Agree the paid-test budget before running the exercise. A numerical responsiveness threshold for non-chat endpoints remains an open release decision.

## Constraints and evidence

Use Google ADK and Gemini for the concierge. Deploy in the existing Google Cloud project `personal-infrastructure-505708` with hotel-prefixed resources, preserving unrelated workloads. These are project constraints; development and recording instructions belong in the [recording guide](../resources/recording-guide.md).

The [hotel source pack](../hotel/README.md) defines the fictional facts and inventory. The [guest evaluation cases](../evals/guest-questions.json) provide concrete answer and tool expectations. Change reviewed facts and their expected answers together. A real hotel deployment requires authoritative inventory, approved policies, and operational sign-off.

## Open decisions

| Decision | Required resolution | Effect |
| --- | --- | --- |
| Model and capacity | Verify the selected Gemini model, endpoint, quotas, and measured throughput. | Blocks claims about supported load. |
| Public access | Approve abuse limits and verify forwarded-IP attribution. Keep the demo IAM-restricted until these checks pass. | Blocks public exposure. |
| Operating budget | Agree cloud spending limits and the capacity-test budget. | Blocks paid provisioning or load testing without authorization. |
| Monitoring ownership | Choose the alert recipient and operational responder. | Blocks operational acceptance. |
| Deployment region | Verify service availability for the proposed region. | Blocks final deployment configuration. |
| Non-chat responsiveness | Set a measurable latency threshold for site, health, and status requests under chat load. | Blocks complete performance acceptance. |
| Real hotel operation | Agree the booking provider, policy owner, and backup/deletion policy. | Blocks use with real inventory or guest data. |
