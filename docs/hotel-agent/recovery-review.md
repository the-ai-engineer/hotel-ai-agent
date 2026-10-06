# Conversation recovery review

Status: implemented locally, awaiting Claude review. Not approved for the next slice.

The slice adds shared PostgreSQL admission limits, atomic counters, replay before budget checks, stable history pagination, bounded model retries before visible output, SSE heartbeats, disconnect cancellation and explicit browser recovery controls.

Verification on 4 October 2026:

- `bash scripts/check.sh`: 37 backend tests, 3 JavaScript tests, lint, formatting and website asset checks passed.
- Two real Uvicorn processes sharing the isolated local `hotel_test` database admitted one duplicate execution, exposed its saved result from the other process and completed eight independent guest requests without cross-guest access.
- Browser check with a test-only delayed model: Stop cancelled a request; recovery showed an interrupted attempt; explicit Try again completed a new attempt. Existing history and villa cards remained visible.
- Tests use synthetic models. Live Vertex AI access and 100-active-turn Cloud Run capacity remain unverified.

Claude Sonnet review was attempted twice. Both attempts returned: “Failed to authenticate: OAuth session expired and could not be refreshed”. Reauthenticate the Claude CLI before rerunning the review. No Claude approval is claimed.
