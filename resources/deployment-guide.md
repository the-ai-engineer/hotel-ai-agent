# Deploy the hotel demo

Live demo: https://hotel-agent-1004219842855.europe-west2.run.app/

## Release prompt

“Deploy the current hotel app to the existing hotel-agent Cloud Run service in europe-west2, project personal-infrastructure-505708. Build Linux amd64 from the root Dockerfile and push an immutable image to the existing cloud-run-source-deploy repository. Use Google Agents CLI with explicit Cloud Run target and prebuilt image. Preserve the hotel identity, Cloud SQL socket, secret version, Gemini model, HTTPS origin, Secure cookies and public-access setting. Keep zero minimum and two maximum instances. Run pending migrations as a one-off job. Do not reseed or replace existing reservations. Verify a public guest conversation, policy sources, villa pages and booking ownership. Record the image digest and results.”

## Deployment details

- One container serves the website, FastAPI and request-local ADK agent.
- PostgreSQL: hotel-postgres, database hotel. Cloud SQL socket is mounted on the service and release job.
- Runtime identity: hotel-agent. Database connection is Secret Manager hotel-database-url, version 1. Never paste the value into a prompt or command history.
- Model: gemini-3.8-flash on Vertex, global location.
- PUBLIC_ORIGIN matches the URL above; SECURE_COOKIE=true. Other hostnames need a deliberate origin change.
- Agents CLI deploys privately and does not add the Cloud SQL socket in this custom layout. Preserve or reapply those gcloud settings before releasing traffic. Its generic A2A and ADK test commands do not match our custom API.
- Public access uses the service-specific Invoker IAM setting after explicit approval. The project policy was not changed. See [Google's public access guide](https://docs.cloud.google.com/run/docs/authenticating/public).
- The release job hotel-db-setup overrides the container command with python -m app.db migrate. Seeding is explicit and currently uses fictional hotel data.

## Before recording

- Use the live URL above and start a new conversation. Cloud and local browser sessions are separate.
- Check `/api/health`, ask a policy question, and check availability for exact dates.
- Confirm reservations only on fictional demo data. Repeated takes occupy the chosen dates.
- Use demo.md for the recording sequence.

## Operating limits

The service scales from zero to two instances. Cloud SQL continues to incur charges when the website is idle. The configuration is for the demo; shared abuse budgets, retention and a 100-user capacity test are not completed.
