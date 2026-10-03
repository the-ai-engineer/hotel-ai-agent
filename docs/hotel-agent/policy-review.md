# Policy chat code review

Reviewed by Claude CLI on 3 October 2026, read-only with tools disabled.

The first pass found confirmed issues in HTTP rejection recovery, refresh recovery, generator cleanup and test database isolation. These were fixed and checked with nine PostgreSQL/ADK integration tests, three JavaScript tests and browser outage/rejection checks. Its SDK injection finding was disproved by the pinned ADK 2.11.0 source and an actual-client identity regression test.

Final follow-up verdict:

**Approve.** I found no remaining material issues in policy-chat for correctness, guest privacy or the streaming lifecycle at this scope.

What I checked:
- **Ownership:** every conversation and turn read or write goes through `owned()` with `owner_id`. Cross-guest access returns 404, and the test covers it.
- **Session tokens:** tokens are hashed at rest, and the cookie is `httponly`, `samesite=lax`, and `secure` outside local.
- **ADK isolation:** each request gets its own `InMemorySessionService`, deleted inside a shielded cleanup. The parallel no-leak test covers it.
- **Rendering:** model text is set with `textContent`, source URLs are regex-checked, and the policy template autoescapes.
- **Streaming:**
  - A disconnect re-raises `CancelledError`, closes both generators via `aclosing`, and the shielded `finish("interrupted")` runs.
  - A timeout surfaces as `TimeoutError`, so the guest gets the error event. The DB deadline guard makes a late commit a no-op, and `expire` marks the turn interrupted.
  - The unconditional `finally` finish is harmless after completion or failure because the update requires `state='running'`.
- **Concurrency:** admission takes a row lock on the conversation, and the partial unique index allows only one running turn. Pooled connections are never held across model calls.
- **Test isolation:** the `hotel_test` guard runs before migrations and again in the fixture. Explicit `DATABASE_URL` overrides `.env` for alembic.

Non-blocking notes, which can go in the follow-up issues:
1. **Stale conversation after 404** (`frontend/js/chat.js`, `send` catch): a 404, for example when another tab has replaced an expired session, shows "Please try again", but `conversation` is kept. Every later send then gets 404 until the guest clicks reset. Clearing `conversation` and the stored ID on 404 would let the next send reinitialize.
2. **Disconnect test only covers ASGI 2.3:** `test_disconnect_closes_run_and_marks_interrupted` pins `spec_version: "2.3"`, which uses Starlette's disconnect listener. If the deployed server reports 2.4, Starlette only notices a disconnect on the next `send`. A model call that has produced no output would then run until the deadline, though the result is still saved correctly. Check this under uvicorn when the reconnect/stop work is done.
3. **No data retention:** guest messages and answers in `turns`, plus `guest_sessions` rows, are never purged. The cookie expires after 24 hours, but the data stays. Track a retention or purge job alongside observability or the cloud release.


Follow-up scope: recovery and deployed-server disconnect behavior in issue #4; retention in issue #7. Live Vertex access and 100-user Cloud Run capacity remain unverified.
