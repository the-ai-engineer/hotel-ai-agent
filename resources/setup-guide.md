# Set up the hotel agent with your coding assistant

Open this repository in Codex, Claude Code or another coding assistant with terminal access. Paste one prompt at a time. Review its result before continuing.

The website and policy chat are implemented. Cloud deployment and live capacity verification remain planned. The prompts below cover setup and subsequent build steps.

## Preview the website

```text
Read README.md and inspect the repository. Start the PostgreSQL service, install locked backend dependencies, apply migrations
and seed fictional policies explicitly. Start FastAPI on port 8773 if it is free. Reuse an existing server only if it
serves this website. Open the URL and verify the homepage and concierge widget.
Keep the design unchanged. Tell me whether model access is configured and how to stop the server.
Do not substitute mock answers if credentials are unavailable.
```

**Check:** the Sanctuary Hotel homepage loads and the widget works or explains that model access is missing.

## Install the local tools

```text
Inspect my operating system, processor and installed tools. Set up Python 3.12
(or a newer version supported by the project), uv, Node.js and Google Cloud CLI.
Use official installation instructions and reuse compatible installations.
Use WSL 2 for Agents CLI on Windows; native Windows is not officially supported.

Google Cloud CLI: https://docs.cloud.google.com/sdk/docs/install-sdk
Python: https://www.python.org/downloads/
uv: https://docs.astral.sh/uv/getting-started/installation/
Node.js: https://nodejs.org/en/download

Explain necessary PATH changes and verify each tool in a fresh shell. Report
the versions and any manual installer steps I need to complete. Do not create
cloud resources or change my active Google Cloud project yet.
```

**Check:** Python, uv, Node and gcloud report their versions. No cloud credentials are needed for the static preview.

## Install Agents CLI and skills

```text
Install Google Agents CLI and its skills for the coding assistant I'm using.
Read https://google.github.io/agents-cli/guide/getting-started/ and inspect the
current setup options first. Preview installation where supported and explain
whether the skills will be installed globally or for this project.

Use the official google-agents-cli package. Verify the agents-cli command works
and that this assistant can discover google-agents-cli-workflow and the other
installed skills. If a restart is required, tell me exactly what to reopen.
Do not scaffold over the existing website.
```

**Check:** the CLI runs and the assistant can find its installed skills. ADK is the application framework; Agents CLI helps the coding assistant build and operate it.

## Select a Google Cloud project

```text
For this recording, use the existing project personal-infrastructure-505708.
Verify its billing, enabled APIs and existing resources. Preserve unrelated
workloads and use hotel-prefixed resources. Check europe-west2 for the application
and verify the selected Gemini model endpoint separately.

Create or reuse a named gcloud configuration for this tutorial without changing
unrelated configurations. Do not create a new project for this recording.
Guide me through browser sign-in. Show the exact project and billing account
before changing billing or provisioning billable resources.

Verify the selected project and billing state. Help me configure a budget alert
and notification recipient using a budget I choose. Explain that a budget alert
does not stop spending. Separate projects help track client costs; they do not
automatically create separate billing accounts or invoices. This recording uses
a shared project, so it does not provide full per-client project isolation.
```

**Check:** the intended project is selected, billing is verified and the budget notification is configured.

## Authenticate the local agent

```text
Set up local Application Default Credentials for Gemini through Vertex AI in
the project we selected. CLI login and application credentials are separate.
Guide me through application-default login and set the ADC quota project.
Enable the required model API and check the narrow IAM permissions needed.

Configure GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION and
GOOGLE_GENAI_USE_VERTEXAI=TRUE for local development without committing secrets.
Verify a model ID supported by the project and location. With my agreement on
model usage costs, run one small authenticated request and report success or
the exact access problem. Never print tokens or credential file contents.

Use https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment
and https://google.github.io/agents-cli/guide/authentication/ as references.
Do not create service-account keys. Cloud Run will use its own service identity.
```

**Check:** a real model request succeeds. A CLI version check or a generated scaffold alone does not prove model access.

## Inspect an ADK starter

```text
Use the installed Agents CLI skills to create a minimal ADK starter in a new,
separate temporary directory. Check this installed version's help before choosing
flags. Target Cloud Run and keep the existing repository unchanged.

Install its dependencies, configure it to use our selected Vertex AI model and
start the local playground. Demonstrate one model response. Explain the agent
definition, runner, model configuration and session storage.

If the starter uses in-memory sessions, label that as temporary. Our hotel design
requires PostgreSQL persistence. If cloud checks are skipped during scaffolding,
do not report authentication or deployment as verified. Record the scratch
directory and exact commands that succeeded.
```

**Check:** the playground returns a real response. Keep the starter's credentials, caches and Git metadata outside the hotel repository.

## Build the first local slice

Paste the [implementation prompt](prompts.md). It asks the assistant to preserve the website, add PostgreSQL and prove one sourced policy answer.

**Check:** a guest asks a published policy question and receives a database-backed answer with a working source link.

## Complete the local hotel workflow

```text
Read docs/Architecture.md and inspect what is implemented. Continue the local
hotel workflow in small, checked steps, preserving the Sanctuary Hotel design.

Add get_villa and deterministic check_availability tools over fictional inventory
and occupancy. Validate dates, guest capacity, closed nights and checkout-exclusive
overlaps. Keep hotel tools read-only and never expose guest reservation records.

Connect the widget to FastAPI and ADK with SSE. Persist sessions and turns in
PostgreSQL. Enforce session ownership and the design's retry, duplicate-request
and disconnect rules. Render validated villa cards and policy source links.

Prove available and fully booked stays, missing dates, unavailable evidence,
tool failure, browser isolation and history recovery after an API restart.
Run a fixed evaluation dataset, inspect a failing case if one occurs and rerun
after fixing it. Keep credentials and guest content out of logs. Record exact
run and test commands that work. Do not deploy yet.
```

**Check:** the local guest journey and failure cases pass. Inventory correctness uses deterministic tests, not an LLM judge.

## Deploy the checked application

```text
Read docs/Architecture.md and inspect the completed local application and tests.
Prepare deployment only if the local checks pass. Package the static frontend
and FastAPI/ADK backend into one container for Cloud Run.

Prepare repeatable configuration for Artifact Registry, Cloud SQL for PostgreSQL,
Secret Manager and a scoped runtime service identity. Align application and
database regions. Set bounded connection pools, maximum instances, request
timeouts and application usage limits. Keep credentials server-side.

Show the target project, resources and cost implications before provisioning.
Once approved, deploy, run migrations as a release step and seed only fictional
hotel data. Verify the deployed website, SSE, source links, villa cards and
persistent conversations. Document revision rollback, database compatibility
and resource-specific cleanup. Do not claim deployment succeeded until the
cloud URL passes its smoke checks.
```

**Check:** the deployed guest journey works, with persistent state and a recorded revision.

## Observe failures and test alerts

```text
Add and verify Cloud Logging, Cloud Trace and Cloud Monitoring for the deployed
hotel application. Correlate request IDs, API/model/tool timings and errors
without logging guest messages or credentials.

Introduce a clearly labelled, demo-only availability lookup failure. Show the
guest fallback and failing trace span, remove the fault and verify recovery.
Configure an alert for repeated failures and test delivery to my chosen
notification channel. Record the test result, resource usage and who responds
to alerts. Do not leave the failure switch enabled.
```

**Check:** the failure is visible, recovery works and a test alert arrives.

## Troubleshoot or clean up

```text
Inspect the current state and the last failed step. Diagnose it before changing
anything. For model access, check project, billing, API enablement, ADC, IAM,
model ID and region separately. For missing commands, check the installed tool
and PATH. For lost history, check persistence rather than assuming Cloud Run
keeps process memory.

If I ask for cleanup, list only the resources and local processes created for
this tutorial. Show dependencies and any data that would be deleted before
removing them. Include Cloud SQL and stored artifacts; deleting Cloud Run alone
does not remove them. Keep unrelated projects and resources unchanged.
```

## Verification notes

These are prompts for a coding assistant, not a pre-tested installer. Cloud authentication, model calls and deployment must be verified in your own project as you work through them. Current repository status remains documented in [README.md](../README.md).

References checked on 27 September 2026:
[Agents CLI getting started](https://google.github.io/agents-cli/guide/getting-started/) ·
[Google Cloud CLI installation](https://docs.cloud.google.com/sdk/docs/install-sdk) ·
[Local ADC](https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).
