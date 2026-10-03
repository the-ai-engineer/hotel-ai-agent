# Hotel AI Agent

A planned tutorial about adding an AI support widget to a fictional hotel website,
then deploying, testing, and operating it on Google Cloud.

**Status:** policy chat is implemented with Google ADK, Gemini on Vertex AI,
PostgreSQL and a fetch/SSE widget. Availability, deployment and capacity testing
are tracked in the [implementation issues](https://github.com/owainlewis/hotel-ai-agent/issues).
Cloud model access and production capacity are not yet verified.

## Run locally

Install Docker, uv, Python 3.12 and Node 22. Copy `.env.example` to `.env`, then:

```bash
docker compose -p hotel-ai-agent up -d postgres
uv sync --project backend --locked --python 3.12
(cd backend && uv run alembic upgrade head)
(cd backend && uv run python -m app.cli seed)
bash scripts/dev.sh
```

Open http://127.0.0.1:8773/. The seed is explicit fictional hotel data and refuses
production mode. The local database uses port 55439 to avoid other projects.

For real answers, set `GOOGLE_CLOUD_PROJECT` in `.env`, select an accessible
Gemini model, and use `gcloud auth application-default login`. Credentials stay
on the server. Without model access the widget reports an error and preserves
history; it never substitutes scripted answers.

The example selects `gemini-3.5-flash` on the global endpoint. Confirm access for
your project and recheck [Google's model lifecycle](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions) before recording or deploying.

## Check

```bash
bash scripts/check.sh
python3 scripts/verify_website.py
```

The compose initialization creates a separate `hotel_test` database. Tests refuse
remote URLs and never use the application `.env` database. If reusing a volume
created before this setup, create `hotel_test` explicitly with local psql.

Tests use a deterministic model inside the actual ADK tool loop and real local
PostgreSQL. They prove app behavior, not Vertex AI access or cloud capacity.

## Layout

- `frontend/`: saved hotel website, images, video and chat modules.
- `backend/app/`: FastAPI routes, agent adapter, read-only tools and persistence.
- `backend/migrations/`, `backend/seeds/`, `backend/tests/`: schema, fictional data and checks.
- `docs/hotel-agent/`: design and review; `resources/`: viewer guides.

## Start Here

- [Architecture diagram (PNG)](./docs/diagrams/architecture.png)
- [Implementation design for the remaining app](./docs/hotel-agent/design.md)
- [Earlier architecture proposal](./docs/architecture.md)

- [Scripted opening, architecture, and 30-minute outline](./LESSON.md)
- [Saved hotel website and preview instructions](./code/README.md)
- [Step-by-step CLI setup and build guide](./resources/setup-guide.md)
- [Implementation prompt](./resources/prompts.md)

## Go Deeper

For more on building real AI systems, join [AI Engineer](https://aiengineer.co).
