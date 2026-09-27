# First implementation prompt

```text
Read docs/architecture.md and repository instructions. The design uses one Cloud
Run service with static frontend and a FastAPI/Google ADK backend, Gemini through
Vertex AI, SSE and PostgreSQL. Implement only the first working local slice.

Preserve the existing Sanctuary Hotel assets and behavior while moving the website
to frontend/. Add backend/ with a reproducible Python environment and a server
that serves those assets. Add local PostgreSQL, migrations and fictional published
hotel policy sections. Implement search_policies and versioned public policy pages.
Prove one ADK/Gemini question returns the correct fact and a working source link.

Use Agents CLI skills where supported, inspect generated code and pin dependencies.
Use parameterized lookups and server-side credentials. Do not introduce booking
writes, Calendar integration, WhatsApp, a queue or cloud provisioning in this task.

Define acceptance checks first. Supply credential-free tests plus a documented
live-model check. Document exact install, run, test and reset commands that you
have actually verified. Keep simulation distinct from live model output. Follow
the architecture's session, failure and source-access rules as the API develops.
```
