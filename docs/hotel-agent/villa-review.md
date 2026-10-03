# Villa availability code review

Claude Sonnet reviewed the slice read-only on 3 October 2026. The findings were fixed with invocation-order evidence guards, specific input errors, integral numeric argument handling, read-only snapshot transactions, visible check timestamps and nonduplicated card metadata. Verification: 24 PostgreSQL/ADK tests, three JavaScript tests, Ruff, assets and browser card checks.

**Approve**, with one non-blocking note.

I reviewed the diff only and did not re-run the suite, so the 24 PostgreSQL/ADK and 3 JS test results are as you reported them. All seven earlier findings hold up:

- **Stale-call guard:** the `latest_availability_call` sequence plus clearing `availability` up front means an older completion can't overwrite a newer failure. The parallel regression covers this.
- **Error classification:** pydantic's `ValidationError` is not an `InvalidStay`, so malformed DB rows fall through to `unavailable`, and only guest input produces `invalid_input`.
- **Guest type handling:** integral floats are normalized in the tool only, and `type(guests) is not int` still rejects bools and non-integral values.
- **Transactions:** `SET TRANSACTION ...` is the first statement in the transaction, which `REPEATABLE READ` requires. The setting is transaction-local, so it can't leak into the pool, and the pool-reset test covers that.
- **Booking overlap:** the booking overlap predicate and the checkout-exclusive night count are correct.
- **Response shape:** `AvailabilitySummary` serialization drops `villas` and the villa DTO has no `id`, which the ADK test asserts.

**Non-blocking note:** `Concierge.run` now awaits `hotel.catalogue(self.db)` before building the agent. A fault in the villas table, or the `>20` villa `ValueError`, would therefore break policy-only chats too, even though those never need villas. Consider catching the error there and falling back to an empty catalogue, so the villa tools degrade on their own the way `get_villa` and `check_availability` already do. It's fine to ship without this.

Two minor observations, neither blocking:

- **Missing `more_available` hint:** the UI never surfaces `more_available`, so a guest sees at most 6 villas with no indication there are more.
- **Seed deletes bookings:** `seed` deletes bookings for the demo villa IDs on any database it is pointed at. The comment says re-seeding is explicit, so this is acceptable for a demo.

Live Vertex and cloud capacity remain unverified, as you noted.
