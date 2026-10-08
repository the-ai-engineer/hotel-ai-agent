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
  provisional output and duplicate submission rejection. Twelve tests pass, including
  actual ADK tool dispatch, cancelled ASGI cleanup and disconnect before streaming starts.
- The retained Node regression test proves one widget initialization during early submit.
- Independent agent review approved. Claude identified the cancellation cleanup defect;
  it was fixed with a bounded cancellation shield and a regression test.

## Remaining

Complete durable turn recovery and budget limits,
Agents CLI evaluations, Cloud Run deployment and operational proof remain in Linear.

## GRA-213: villa availability and widget

Added read-only PostgreSQL inventory tools, full-stay photo cards and a confirmed New conversation reset. Claude Opus refined the widget styling. Reset rotates the conversation UUID without deleting records; the next model invocation has empty history.

Verified commands:

```bash
uv run --directory backend python -m app.db migrate
uv run --directory backend python -m app.db seed
uv run --directory backend ruff check app tests
uv run --directory backend pytest -q
node frontend/tests/chat.test.cjs
python3 scripts/verify_website.py
```

Browser proof: confirmed reset and refresh show a fresh welcome screen; cancel preserves the chat. Reset is disabled during an answer. Live Vertex family question returns Garden Villa for 1–4 November 2026, four guests, with family policy evidence and an unfenced-pool warning.

Markdown replies use locally served, pinned marked and DOMPurify modules. Streaming renders token bursts every 100 ms and flushes the saved result immediately. DOM tests verify formatting, stripping executable markup and model links, final flush, and cancelled timers. `npm ci --prefix frontend` and `npm test --prefix frontend` run these test-only dependencies; the site needs no frontend build.

Final checks: 28 PostgreSQL/backend tests passed. Browser confirmed saved Markdown formatting, a live cancellation-policy follow-up, refreshed villa cards, correct Garden Villa navigation, reset cancellation/confirmation, and a mobile composer within viewport bounds. No browser console warnings/errors. Independent reviewer and Claude Opus approved the implementation; Claude also reviewed Markdown safety and streaming. The optional visual detector ran with regex fallback because its parser modules were unavailable, so browser inspection supplied the visual check.

## Villa detail pages

Added `/villas/forest-suite` and `/villas/garden-villa`, sharing one static detail template. Public villa facts come from `/api/villas/{id}` and the existing validated PostgreSQL catalogue. Cards and homepage actions open the detail pages; the same guest cookie preserves chat. Removed the requested widget footer. Added a connected recording sequence in demo.md.

Checks: backend route/facts/404 regression, ruff, frontend syntax, Markdown and initialization regressions, website dependencies and desktop/mobile browser navigation.

Verified 29 backend tests and frontend checks. Browser: both villa detail pages, homepage details action, preserved conversation and availability prompt passed. Claude and independent review approved; the showcase action retains its original arrow.

## Guest-confirmed demo bookings

Availability cards now open `/book` with the villa, dates and guests prefilled. Review is read-only; Confirm reservation creates an owned, idempotent fictional booking and rechecks availability under a villa lock. Reload recovers the confirmation. Chat and booking share one guest-session initialization.

Verified commands:

```bash
uv run --directory backend python -m app.db migrate
uv run --directory backend python -m app.db seed
npm test --prefix frontend
uv run --directory backend ruff check app tests
uv run --directory backend pytest -q
```

35 backend tests passed, including overlapping reservation concurrency, retry safety, ownership, request expiry and failure rollback. Frontend tests cover shared session initialization, booking review, failed confirmation retry and reload recovery. Claude review caught a clock fixture bypass; fixed by calling `property_today()`. Independent review caught a fresh-browser cookie race; fixed by a shared session promise. Final targeted review approved.

Live Vertex/browser proof: October availability, prefilled booking page, confirmed reference, owned booking lookup and explicit late-checkout note submission. Notes remain pending hotel review and never change the reservation. No payment, staff notification or Cloud Run deployment was performed.

## Demo prompt refinements and live smoke evaluation

Used the Agents CLI eval skill and `agents-cli eval run --help` to inspect the supported protocol. The hotel uses a custom HTTP/SSE adapter, not the standard ADK API server routes. This slice runs the same ADK Runner directly against local PostgreSQL and remote Vertex; it does not claim `agents-cli eval run` or managed grading passed.

Verified commands:

```bash
uv run --directory backend python evaluate.py --output /tmp/hotel-evals-release.json
uv run --directory backend python evaluate.py --holdout --output /tmp/hotel-evals-final-holdout.json
uv run --directory backend python evaluate.py --case blocked-alternative --output /tmp/hotel-evals-booking-fix-1.json
uv run --directory backend ruff check app tests evaluate.py
uv run --directory backend pytest -q
npm test --prefix frontend
python3 scripts/verify_website.py
```

Results: eight core scenarios and two held-back scenarios passed their deterministic smoke checks, covering 14 turns. Final core complete-answer times were 2.1–8.1 seconds; these are small local runs, not a load benchmark or first-token timings. Real Gemini Flash replies were reviewed alongside the checks. Source reads and selected phrases are not proof of universal grounding; no LLM judge score or token-usage metric was collected here. Managed CLI evaluation and broader release coverage remain in GRA-215.

Observed failures and fixes: weekend phrasing caused needless clarification, corrected with a computed Friday/Sunday default and explicit assumption; booking follow-up sometimes skipped fresh availability, corrected with an explicit same-stay recheck and date/card assertions. The failing multi-turn case passed twice after the fix, then passed in the full core suite. One source assertion was corrected because the arrival document alone contained all the facts. Reply inspection caught unsupported “plunge pool” wording, so the prompt now prohibits embellishing amenities. Nightly rates remain unavailable and must not be offered.

36 backend tests, frontend checks and desktop/mobile menu inspection passed. Open-menu header now uses dark ink on cream with clear space above navigation. Browser weekend search displays exact dates and a fresh Reserve card. Claude and independent reviews approved. Generated response files remain outside Git in `/tmp`.


## Concierge prompt Markdown extraction

Moved the existing concierge instruction unchanged to
`backend/prompts/concierge.md`. The agent loads UTF-8 relative to its module at
startup; restart the server after editing. Runtime property-date context is still
appended per invocation. The actual ADK test checks the complete file content is
passed to the model before the date context.

Verified commands:

```bash
uv run --locked --directory backend ruff check app tests evaluate.py
uv run --locked --directory backend pytest -q
```

Ruff passes and all 36 backend tests pass using real PostgreSQL and deterministic
model responses. Extraction was checked for exact equality with the previous
Python literal. No live-model evaluation or cloud deployment was needed.
Agents CLI 1.8.0 was inspected with `agents-cli info`; it does not recognize this
custom-layout project and its installed-skills query timed out.
