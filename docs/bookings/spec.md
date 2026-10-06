# Demo reservations and hotel requests

Decision: agreed scope. Delivery: in progress.

## Outcome and scope

A complete local guest journey: current-date availability, a booking-page confirmation, owned reservation lookup and a confirmed note saved for hotel review. No payment, room pricing, real PMS connection, booking modification/cancellation or external notification.

## Behavior and design

- Every fresh agent invocation receives today's date in Asia/Makassar. Resolve clear relative dates, repeat exact stay dates and clarify ambiguity. The reviewed sample inventory covers 1 October 2026 through 30 September 2027, with explicit closed nights and seeded booking conflicts.
- Matching cards link to `/book` with villa, dates and total guests prefilled. The form checks availability before displaying the exact review summary. Only the guest's Confirm reservation click calls the same-origin authenticated POST endpoint. The model has no reservation-write tool.
- Confirmation rejects past dates, invalid stays and capacity mismatches, rechecks every night inside a transaction and serializes by request UUID then villa. Repeated matching confirmation returns the saved reference; changed details with the same UUID are rejected. Availability never holds a room.
- Booking references are random and access also requires the server-owned guest session. The concierge can look up a reference or the guest's latest reservation. Unknown and other-guest references produce the same not-found result. Reset preserves owned confirmed reservations; the guest cookie expires after 24 hours. Real returning-guest authentication is future scope.
- The agent may prepare one note per turn, after looking up the owned booking and reading relevant policy. The draft stays in memory until the answer-completion transaction saves it and links it to the completed turn. No completed turn means no executable draft.
- A new draft supersedes earlier unsent drafts in that conversation. The guest reviews the exact note and clicks Send request. Confirmation locks the guest session before the draft, checks ownership, current conversation, completed turn and ten-minute expiry, then saves Pending hotel review. Repeated send is idempotent. It does not approve a service, change the booking or send an external email.
- PostgreSQL stores owned reservations, party size, confirmation UUID and reference. Hotel requests carry booking, conversation, bounded plain-text note and draft/pending_review/superseded state. Conversation history reloads current request status. Seed import uses the same villa locks and preserves guest-created reservations.

## Acceptance and proof

| ID | Done when | Check |
|---|---|---|
| AC-1 | Current date reaches the actual ADK request; near-term dates work | ADK request assertion and PostgreSQL inventory test |
| AC-2 | Review does not create a reservation; guest confirmation does | API test and browser journey |
| AC-3 | Concurrent overlapping confirmations create one reservation; retry returns the same reference | Real PostgreSQL concurrency/idempotency tests |
| AC-4 | Another guest cannot read a reservation or confirm/add a note | Ownership tests |
| AC-5 | Confirmed notes persist as pending review and do not change bookings | API/database assertions |
| AC-6 | Reset, expired, superseded and failed-turn drafts cannot execute | Request regressions |
| AC-7 | Policy, Markdown, villa pages and reset stay intact | Existing checks and desktop/mobile browser |

## Open decisions

None for this fictional, session-owned demo. Returning-guest authentication, staff inbox and real PMS/payment integration remain outside scope.
