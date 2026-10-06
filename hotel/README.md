# Fictional hotel source pack

All facts and inventory here are invented for this tutorial. These files are the reviewed source content, not an implemented retrieval system.

- `policies/`: published guest information. Each file has a stable document ID and revision.
- `villas.json`: public villa catalogue. Never contains guest details.
- `availability.json`: explicit nightly inventory for a fixed demonstration window.
- `../evals/guest-questions.json`: questions, expected facts, tools and failure behavior.

Build a repeatable importer into PostgreSQL. Search published policy sections with full-text search; check availability with typed, deterministic SQL. Return source IDs and passages for policy answers. No embeddings are needed initially.

Availability is only for 1–7 November 2026. Checkout is exclusive. Missing dates mean unknown/unavailable, never assumed open. A cancelled booking does not block inventory. Keep guest names and booking identifiers out of tool responses.

Before filming, agree this pack as the hotel brief. Change the facts and expected answers together if the brief changes. The agent may answer questions and check availability, but cannot confirm bookings, payments or service requests.
