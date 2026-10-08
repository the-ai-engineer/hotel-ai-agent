# Hotel AI Agent

The recording starting point for adding an AI concierge to Sanctuary Hotel,
a fictional luxury forest retreat.

**Status:** the existing website is connected to a local ADK policy concierge using
Gemini 3.8 Flash on Vertex AI. Policies and completed conversations live in
PostgreSQL. Read-only villa availability returns photo cards. Guests can start a
new conversation without carrying old context forward. Villa cards open dedicated
Forest Suite and Garden Villa pages with the same saved conversation. Reserve buttons
open a review-and-confirm booking page. The concierge can look up owned demo
reservations and prepare notes for explicit guest confirmation. Stronger turn recovery, production limits and
cloud deployment are later Linear slices. This branch is a local development demo.

## Run the agent locally

Prompt: “Check uv, Docker, gcloud and application credentials. Set up the local
PostgreSQL database, apply migrations, import hotel policies and run the existing
website with its real ADK concierge. Keep credentials outside Git.”

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project personal-infrastructure-505708
docker compose up -d postgres
cp backend/.env.example backend/.env
uv sync --directory backend
uv run --directory backend python -m app.db migrate
uv run --directory backend python -m app.db seed
bash scripts/dev-agent.sh
```

Open http://127.0.0.1:8773/. Ask “Is breakfast included?” then “Can it be brought
to our terrace?” Open a source link and refresh: completed answers are saved.
Model requests go to your Google Cloud project and incur inference charges.
The app uses application credentials, which are separate from gcloud's CLI login.

If port 55439 already serves an older hotel database, preserve its data. Create
an isolated database named `hotel_policy` there, or set another local port in
Compose and `backend/.env`. Do not replace another application's volume.

## Concierge prompt

Edit [backend/prompts/concierge.md](backend/prompts/concierge.md) to update the
concierge instructions, then restart the server. The agent loads the UTF-8 file
relative to its own location and appends the current property date at runtime.

## Website-only recording start

The `recording-start-20261006` tag preserves the disabled-widget starting point.
Use `bash scripts/dev.sh` there for the static website. Record build sections
from checked commits, using [the recording guide](resources/recording-guide.md).

## Checks

```bash
python3 scripts/verify_website.py
node --check frontend/js/site.js
node --check frontend/js/chat.js
node frontend/tests/chat.test.cjs
npm ci --prefix frontend
npm test --prefix frontend
bash -n scripts/dev.sh scripts/dev-agent.sh
uv run --directory backend ruff check app tests
uv run --directory backend pytest -q
```

## Recording and build references

- [Recording guide](resources/recording-guide.md): ordered sections, short prompts,
  visible checks and stopping points.
- [Requirements](docs/Requirements.md) and [architecture](docs/Architecture.md).
- [Linear milestones and issues](https://linear.app/gradientwork/project/hotel-website-agent-4f0f8e301934/overview).
- [Demo conversations](demo.md), [hotel source pack](hotel/README.md) and guest cases in `evals/`.

## Layout

- `frontend/`: HTML, CSS, site/widget JavaScript and generated assets.
- `backend/`: API, isolated ADK invocations, document tools, migrations and tests.
- `scripts/`: start and check the website and agent.
- `docs/`: the planned product and architecture.
- `hotel/`: fictional policies and structured inventory.
- `evals/`: guest questions and expected behavior.
- `resources/`: the recording guide and short build prompts.

The original agent implementation is preserved on the private branch
`codex/agent-build-backup-20261006`, commit `09906ee`. It is an unfinished
reference, not the filming baseline. Do not merge it wholesale during recording.

For more on building real AI systems, join [AI Engineer](https://aiengineer.co).
