# Hotel AI Agent

The recording starting point for adding an AI concierge to Sanctuary Hotel,
a fictional luxury forest retreat.

**Status:** static website and chat widget only. The widget opens and closes,
but replies are disabled. No backend, agent, database or cloud deployment is
included in this starting version. The generated photography and fading hero
video are preserved.

## Start recording here

```bash
bash scripts/dev.sh
```

Open http://127.0.0.1:8773/. Python 3 is the only runtime requirement for the
starting website. Node is used for JavaScript syntax checks.

## Checks

```bash
python3 scripts/verify_website.py
node --check frontend/js/site.js
node --check frontend/js/chat.js
bash -n scripts/dev.sh
```

## Recording and build references

- [Recording guide](resources/recording-guide.md): ordered sections, short prompts,
  visible checks and stopping points.
- [Requirements](docs/Requirements.md) and [architecture](docs/Architecture.md).
- [Linear milestones and issues](https://linear.app/gradientwork/project/hotel-website-agent-4f0f8e301934/overview).
- [Demo conversations](demo.md), [hotel source pack](hotel/README.md) and guest cases in `evals/`.

## Layout

- `frontend/`: HTML, CSS, site/widget JavaScript and generated assets.
- `scripts/`: start and check the saved website.
- `docs/`: the planned product and architecture.
- `hotel/`: fictional policies and structured inventory.
- `evals/`: guest questions and expected behavior.
- `resources/`: the recording guide and short build prompts.

The original agent implementation is preserved on the private branch
`codex/agent-build-backup-20261006`, commit `09906ee`. It is an unfinished
reference, not the filming baseline. Do not merge it wholesale during recording.

For more on building real AI systems, join [AI Engineer](https://aiengineer.co).
