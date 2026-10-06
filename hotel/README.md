# Fictional hotel source pack

All facts and inventory here are invented for this tutorial. These files are the reviewed source content, not an implemented retrieval system.

- `policies/`: published guest information. Each file has a stable document ID and revision.
- `catalogue.json`: reviewed titles, summaries and keywords; file paths are importer-only.
- `villas.json`: public villa catalogue. Never contains guest details.
- `availability.json`: explicit nightly inventory for a fixed demonstration window.
- `../evals/guest-questions.json`: questions, expected facts, tools and failure behavior.

Build a repeatable importer into PostgreSQL. Expose `list_documents()` for published metadata and `read_document(document_id, revision)` for a complete selected document. Check availability with typed, deterministic SQL. Return versioned sources; no keyword/full-text or vector search is needed.

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

The agent lists the published catalogue, selects one or more IDs using summaries and keywords, and reads their complete bodies. `list_documents` returns ID, title, summary, keywords and revision; it does not return bodies or file paths. `read_document` returns body, title, ID, revision and a source link. Factual policy answers must use read bodies, never catalogue summaries alone.

The importer records reviewed catalogue metadata and Markdown bodies together. Changes need a successful re-import before the agent sees them. Publish each update atomically and retain cited versions; unknown IDs and unpublished content remain unavailable. The initial limits are 20 documents, 6,000 characters for the returned catalogue and 6,000 characters per document body. Reject oversize content instead of truncating it. A future customer wiki connector can supply this same import boundary, but is not built here.

See [demo.md](../demo.md) for recording conversations and expected facts. Published prices here are optional service charges; room pricing remains outside the demo.
