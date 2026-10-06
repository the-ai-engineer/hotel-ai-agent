# Fictional hotel source pack

All facts and inventory here are invented for this tutorial. These files are the reviewed source content, not an implemented retrieval system.

- `policies/`: published guest information. Each file has a stable document ID and revision.
- `villas.json`: public villa catalogue. Never contains guest details.
- `availability.json`: explicit nightly inventory for a fixed demonstration window.
- `../evals/guest-questions.json`: questions, expected facts, tools and failure behavior.

Build a repeatable importer into PostgreSQL. Search published policy sections with full-text search; check availability with typed, deterministic SQL. Return source IDs and passages for policy answers. No embeddings are needed initially.

Availability is only for 1–7 November 2026. Checkout is exclusive. Missing dates mean unknown/unavailable, never assumed open. A cancelled booking does not block inventory. Keep guest names and booking identifiers out of tool responses.

Before filming, agree this pack as the hotel brief. Change the facts and expected answers together if the brief changes. The agent may answer questions and check availability, but cannot confirm bookings, payments or service requests.

## Policy catalogue

| File | Topics |
| --- | --- |
| policies/stay.md | Arrival, transfers, early/late checkout, departure facilities, access. |
| policies/dining.md | Breakfast, terrace charges, vegan options, allergies, private dining. |
| policies/family.md | Capacity, bedding, cots, pool safety, children’s facilities. |
| policies/experiences.md | Regular activities, age restrictions, anniversary options. |
| policies/cancellation.md | Rate-specific deadlines, examples and charge basis. |
| policies/services.md | Wi-Fi, pools, spa and staff confirmation boundaries. |

## How retrieval will work

The agent chooses search terms and calls `search_policies`. The tool searches all published PostgreSQL sections and returns matching passages with document IDs, titles and revisions. It can search again with narrower terms. This is agent-driven retrieval over full-text search, not a vector-search requirement or unrestricted filesystem access.

The catalogue above is for reviewers, not a separate runtime index. The importer records document metadata and search-ready sections. Changes to Markdown require a successful re-import before the agent sees them; refresh existing IDs rather than leaving old published sections behind. Retain cited versions according to the architecture. A future customer wiki connector can supply the same import boundary, but is not built here.

See [demo.md](../demo.md) for recording conversations and expected facts. Published prices here are optional service charges; room pricing remains outside the demo.
