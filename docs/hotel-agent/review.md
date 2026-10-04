# Claude design review

3 October 2026. Independent Claude Code review, supplied complete repository context and proposal with tools disabled. Review is of the design, not runtime proof.

**Approve.**

I found no remaining material defects. All three prior gaps are closed:

- **Turns ordering.** `created_at` is set by the database clock under the conversation lock. Ordering and cursors use `(created_at, client_turn_id)` with a matching index, so client UUID randomness no longer decides chronology. Postgres `now()` is the transaction start time, so a transaction that waits on the lock could in theory get an earlier timestamp than the turn ahead of it. INV-2 makes this unreachable: the waiting admission would see the running turn and return 409, and the next turn can only be admitted after the previous one reaches a terminal state.
- **DSQ capacity and retry basis.** The capacity basis is now recorded as measured DSQ throughput or allocated Provisioned Throughput. There is one jittered retry of a single model request, only before response content, within the deadline. Loops and tools are never replayed, SDK retries are disabled and retries count toward usage. Admission 429s are kept separate from upstream errors in the acceptance criteria. `PROPERTY_TURNS_PER_MINUTE` is now derived from this basis.
- **Simulated IP contradiction.** Load comes either from distributed real sources or from a single source with the demo-only override. The override is rejected in production, and results must record whether IP limiting was actually exercised. Forwarded headers are never forged. Pre-release access is IAM-private with identity tokens, separate guest cookies and the allowed Origin. This is now consistent with the abuse-limit gate in §8 and §12.

Lifecycle, idempotency, lock order, connection budget (10 instances × 5 connections × 2 revisions ≤ 120), deadlines and cancellation are internally consistent. Runtime proofs are correctly framed as gates rather than claims.

**Optional nits (non-blocking):**
1. Use `clock_timestamp()` instead of `now()` for `created_at` so ordering holds without relying on the INV-2 argument above.
2. Add `DEMO_IP_LIMIT_OVERRIDE` to the §6 configuration list. State that it also covers the per-IP session-creation limit (10/IP/minute), since the test needs 100+ sessions from one source.
3. §4 acceptance has a typo: "surviving the bounded retry count in the error budget" should read "…retry **counts** in the error budget".


The three optional clarifications were incorporated after this verdict. Prior findings were resolved in the design: request-local agent/tool isolation; disconnect/recovery rules; current-policy uniqueness; villa lookup identity; idempotency order; bounded cancellation cleanup; schema compatibility; history ordering; capacity basis and private load-test attribution.
