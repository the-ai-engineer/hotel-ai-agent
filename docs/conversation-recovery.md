# GRA-214: conversation recovery acceptance

Source: [GRA-214](https://linear.app/gradientwork/issue/GRA-214/keep-conversations-private-and-recover-interrupted-answers).
This records local acceptance evidence. Deployment, runtime database permissions,
public proxy attribution and 100-active-turn model capacity remain separate gates.

## Checks

```bash
uv sync --locked --directory backend
DATABASE_URL=postgresql://hotel:hotel@127.0.0.1:55439/hotel_policy uv run --directory backend pytest -q
uv run --directory backend ruff check app tests evaluate.py
npm ci --prefix frontend
npm test --prefix frontend
node frontend/tests/chat.test.cjs
python3 scripts/verify_website.py
git diff --check
```

PostgreSQL tests create isolated schemas and drop them after the run. Multiprocess
checks start two real Uvicorn processes using a deterministic producer, share only
the database and communicate over HTTP. No model credentials are required.

| Criterion | Local proof | Remaining scope |
| --- | --- | --- |
| R4: owned guest state | Foreign/expired cookies, foreign turn reads/Stop/replay, old-conversation denial and Origin rejection. | Deployed cookie/proxy configuration remains a release check. |
| R5: one active turn and no duplicate invocation | Running duplicate returns 202/status URL, competing UUID returns 409, completed UUID replays the result across processes. | No sticky sessions required. |
| R6: durable completion and accurate interruption | Final-write failure, late producer output, Stop/completion race, timeout, ASGI disconnect before/during stream, killed API process and committed history across restart. | A killed process is recovered at its stored deadline; token offsets are not resumed. |
| R7: isolated concurrent guests | 20 independent conversations across two API processes; database observation asserts a peak of 20 running turns. Each saved/replayed result has only its own question and history. Existing actual-ADK tests prove isolated working history/tool dispatch. | Deterministic concurrency is not a real-model or deployed capacity benchmark. |
| R8: widget recovery and retry | DOM regressions for refresh polling, cleared controllers, Stop and overload messages; real browser checks for saved refresh/restart history, active recovery in a second tab, Stop and immediate retry. | Existing availability, source rendering and booking tests continue to run. |
| R9: bounded admission and context | Shared budgets reject requests across processes before producers start; failed admitted attempts consume quota; local-midnight bucket, transactional rollback, expired-counter pruning, overflow rejection and released permits on cancellation/failure. Existing input/history/output caps remain. | Least-privilege runtime database roles and model-capacity-based throughput belong to deployment. |

The real browser checks use the same FastAPI/widget/PostgreSQL path with a
deterministic producer and disposable schema on port 8874. They prove recovery
behavior, not live Gemini answer quality. No agent prompt, model or tool changes
are part of GRA-214. Broad live-model evaluation remains GRA-215.
