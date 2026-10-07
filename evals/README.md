# Guest evaluation cases

`guest-questions.json` defines the broader behavior and injected-failure fixtures.
`demo-smoke.json` contains executable live cases for `backend/evaluate.py`, which
uses the same request-local ADK runner and hotel tools as the website.

```bash
uv run --directory backend python evaluate.py --output /tmp/hotel-evals.json
uv run --directory backend python evaluate.py --holdout --output /tmp/hotel-holdout.json
```

Use `--case model-disclosure`, `--case next-week-three-nights` or
`--case next-week-after-exact-search` for the production regressions. Run holdouts
after tuning the prompt. Model calls require local application credentials and
incur inference charges. Use an explicitly migrated and seeded local demo database;
the runner does not change hotel content or create reservations.

The regression checks reject model/provider identity and require clarification
before availability for ambiguous next-week dates. Availability attempts are recorded
per evaluation turn, including unsuccessful calls, so empty cards cannot hide a
premature lookup. `contains_any` groups accept equivalent clarification wording.
These are deterministic checks, not a complete semantic quality assessment. Review
saved answers as well, especially for unsupported date or availability claims.

- `question` and optional `prior_messages` define the guest input and context.
- `expected_tools` names relevant tools, not a rigid call sequence. A correct answer may need other allowed tools too.
- `expected_document_reads` requires successful reads of those document IDs before a grounded answer, except when `setup` deliberately makes a read fail.
- `source_ids` identifies valid policy sources. Check the returned revision against the body actually read; a source link alone is not proof of retrieval.
- `expected_action` covers clarification and unsupported requests.
- `setup` requires an isolated fixture or injected failure. Restore the baseline after each case; never change live hotel content to run an eval.

Evaluate document selection separately from factual answer quality. Catalogue summaries are not answer evidence. Test paraphrases, several relevant documents, missing reads, unpublished content and re-imported revisions. Direct tool/source-route contract tests must prove unknown IDs and unpublished versions are inaccessible, independently of the model's chosen calls.

Use real PostgreSQL for catalogue/import/source correctness and deterministic inventory checks. Live ADK/model runs assess selection and answers. Deterministic model doubles cannot establish real selection quality. Keep guest input, generated outputs and traces outside Git.
