# Hotel AI Agent

A planned tutorial about adding an AI support widget to a fictional hotel website,
then deploying, testing, and operating it on Google Cloud.

**Status:** runnable website prototype and draft lesson. Concierge replies and
requests are simulated. No working agent or cloud deployment is included yet.

## Run the website

```bash
git clone git@github.com:owainlewis/hotel-ai-agent.git
cd hotel-ai-agent
python3 -m http.server 8773 --bind 127.0.0.1 --directory code/website
```

Open http://127.0.0.1:8773/. The fictional property is Sanctuary Hotel,
Luxury Forest Retreat.

## Check

```bash
python3 code/verify_website.py
node --check code/website/app.js
```

## Start Here

- [Architecture diagram (PNG)](./docs/diagrams/architecture.png)
- [Proposed production architecture](./docs/architecture.md)

- [Scripted opening, architecture, and 30-minute outline](./LESSON.md)
- [Saved hotel website and preview instructions](./code/README.md)
- [Step-by-step CLI setup and build guide](./resources/setup-guide.md)
- [Implementation prompt](./resources/prompts.md)

## Go Deeper

For more on building real AI systems, join [AI Engineer](https://aiengineer.co).
