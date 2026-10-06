# Policy concierge build

Branch: `codex/hotel-policy-agent`. First slice: GRA-212.

## Prompt

“Connect the existing widget to one ADK policy agent. Use local PostgreSQL and
Vertex Gemini 3.8 Flash. List document metadata, read complete selected revisions
and display verified sources. Preserve the hotel design. Keep the code small.”

## Tooling

- Agents CLI 1.8.0. Inspected help and generated an official temporary reference.
- ADK 2.11.0, google-genai 2.28.0. Exact Python dependencies are in backend/uv.lock.
- Gemini `gemini-3.8-flash`, Vertex `global`, LOW thinking. Verified live access in
  `personal-infrastructure-505708`.
- Used Agents CLI workflow, scaffold and ADK coding skills. The CLI helps the
  coding assistant build code; it is not a runtime process or a hosted agent.

```bash
agents-cli --version
agents-cli scaffold create --help
agents-cli scaffold create hotel-policy-ref --output-dir /tmp --agent adk --prototype --deployment-target cloud_run --session-type in_memory --agent-guidance-filename AGENTS.md --region europe-west2 --skip-checks --auto-approve
uv sync --directory backend
uv run --directory backend python -m app.db migrate
uv run --directory backend python -m app.db seed
bash scripts/dev-agent.sh
uv run --directory backend ruff check app tests
uv run --directory backend pytest -q
python3 scripts/verify_website.py
node --check frontend/js/chat.js
```

The temporary scaffold was studied as a reference for this nonstandard layout.
Its sample tools and extra A2A/deployment dependencies were not copied. The hotel
uses its own same-origin HTTP/SSE adapter around the ADK Runner. CLI evaluation
and deployment integration are later slices; do not claim CLI run/eval passed here.

## Verified guest cases

- Live breakfast and terrace delivery question: dining-policy revision 2.
- Browser early-arrival question: stay-policy and services-policy revision 2.
- Live browser follow-up and refresh passed; history also survived an API restart.
- Live Stop followed by immediate retry passed after fixing cancellation cleanup.
- Mobile 390 × 844 bounds and keyboard Escape/focus restoration passed; no console errors.
- PostgreSQL tests cover immutable revisions, atomic import failure, withdrawal,
  complete bodies, catalogue limits, safe source reads, guest ownership, failed
  provisional output and duplicate submission rejection. Eleven tests pass, including
  actual ADK tool dispatch and cancelled ASGI disconnect cleanup.
- The retained Node regression test proves one widget initialization during early submit.
- Independent agent review approved. Claude identified the cancellation cleanup defect;
  it was fixed with a bounded cancellation shield and a regression test.

## Remaining

Villa availability/cards, complete durable turn recovery and budget limits,
Agents CLI evaluations, Cloud Run deployment and operational proof remain in Linear.
