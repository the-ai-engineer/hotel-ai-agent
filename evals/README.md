# Guest evaluation cases

These fixtures define expected behavior; no evaluation runner is implemented yet.

- `question` and optional `prior_messages` define the guest input and context.
- `expected_tools` names relevant tools, not a rigid call sequence. A correct answer may need other allowed tools too.
- `expected_document_reads` requires successful reads of those document IDs before a grounded answer, except when `setup` deliberately makes a read fail.
- `source_ids` identifies valid policy sources. Check the returned revision against the body actually read; a source link alone is not proof of retrieval.
- `expected_action` covers clarification and unsupported requests.
- `setup` requires an isolated fixture or injected failure. Restore the baseline after each case; never change live hotel content to run an eval.

Evaluate document selection separately from factual answer quality. Catalogue summaries are not answer evidence. Test paraphrases, several relevant documents, missing reads, unpublished content and re-imported revisions. Direct tool/source-route contract tests must prove unknown IDs and unpublished versions are inaccessible, independently of the model's chosen calls.

Use real PostgreSQL for catalogue/import/source correctness and deterministic inventory checks. Live ADK/model runs assess selection and answers. Deterministic model doubles cannot establish real selection quality. Keep guest input, generated outputs and traces outside Git.
