# Build and Deploy AI Agents on Google Cloud

Repository companion to the [working Google Doc](https://docs.google.com/document/d/1iew1Q6D1TstNOhaNfR92Rjt5rQtfq4UBF7rP0c0UIB0/edit). Edit the sponsor script in that Doc.

Sponsor review draft. Target: 30 minutes. A practical walkthrough for developers
and freelancers who know basic Python and want to deploy an agent-backed web app.
The website is built; agent, database and cloud demonstrations are planned.

**Outcome:** a Sanctuary Hotel website with an assistant that answers published
policy questions, finds villas available for specified dates, and remembers the
conversation. Viewers see the local build, cloud deployment, evaluation and a
production failure investigation.

**Scope:** one fictional hotel, Gemini through Vertex AI, Google ADK, FastAPI,
Cloud Run, Cloud SQL for PostgreSQL, Secret Manager, Cloud Logging, Cloud Trace
and Cloud Monitoring. SSE streams answers. No booking writes or background queue.
Gemini is the recording path; Claude is not a second implementation in this video.

Architecture: [design](docs/architecture.md) · [video diagram](docs/diagrams/architecture.svg).
Setup: [CLI walkthrough](resources/setup-guide.md).

## 1. Hook and finished result · 00:00–00:45

**On screen:** hotel homepage, a guest asking for a villa, matching cards and a
policy answer. Record this opening after the real backend works.

Today I'll show you how to build and deploy AI agents on Google Cloud. About twelve
months ago, I started freelancing as an AI engineer, and getting client applications
running reliably became a big part of the work.

In this video, we're adding an AI concierge to a hotel website. It will answer
guest questions and check which villas are available. Then we'll deploy it, test
its answers, and investigate what happens when a tool fails.

I'll share the code and setup guide so
you can build along. Let's get into it.

## 2. Sponsor note and personal context · 00:45–01:45

**On screen:** presenter, then the project console.

This video is sponsored by Google Cloud. When I first started freelancing 12
months ago I needed to find one platform to run all my client projects on. In
particular I needed access to AI models, reliable infrastructure, and easy per
client billing. That’s why I settled on Google Cloud because it gave me everything
I needed in one platform and it’s where I run all my business and personal projects.

**Recording note:** personal account supplied by Owain. In the setup walkthrough,
explain per-client project organization and cost tracking; separate projects do
not automatically create separate billing accounts or client invoices.

## 3. Use case and business problem · 01:45–03:15

**On screen:** the Upwork listing, Chatlyn's hotel chatbot page, then Sanctuary.

Imagine a hotel client comes to you with a familiar problem. Their team spends a
lot of time answering the same questions. What time is check-in? Is breakfast
included? Which villa would work for two people next month?

They want guests to get useful answers quickly, including when the team is busy,
and they want staff to spend less time handling repetitive enquiries.

I found a related project on Upwork with an advertised budget of four thousand
seven hundred and fifty dollars. That project was for a WhatsApp holiday concierge,
with a knowledge base and a live activity calendar. We're adapting the general
idea to a hotel website, with villa availability instead of the calendar.

There are also businesses such as Chatlyn selling hotel chatbots. So this is a
recognizable category of software. Our goal is to understand how to build and
operate a focused version of it.

Our hotel is fictional. The assistant can read policies, explain the villas and
check our sample inventory. It cannot take a payment or make a reservation. For a
real hotel, that availability tool would connect to its existing booking system.

**Evidence and claim boundaries:**

- [Upwork: Holiday Concierge Chat Bot](https://www.upwork.com/freelance-jobs/apply/Holiday-Concierge-Chat-Bot_~022092567151788852206/).
  Checked 27 September 2026. Advertised fixed budget, not proof of a paid contract,
  typical market rate, or a project Owain won.
- [Chatlyn hotel chatbot](https://chatlyn.com/en/features/hotel-chatbot/).
  A commercial reference, not an affiliation or evidence of our results.
- Faster answers and less repetitive work are intended benefits. Do not claim
  proven staffing reductions, conversion gains or round-the-clock human support.

## 4. Design the system · 03:15–06:00

**On screen:** reveal the [architecture diagram](docs/diagrams/architecture.svg)
in stages: browser and API, then agent/model/database, then operations.

The browser has our hotel website and a chat widget. When a guest asks a question,
the widget sends it to our Python API. The API runs an agent built with Google's
Agent Development Kit, or ADK. Gemini decides which of our tools it needs, and
those tools return information from the database.

We'll use three tools: search the hotel policies, get villa details, and check
availability for a date range. The availability calculation is ordinary database
logic. The model helps interpret the question and explain the result.

Our Python API and the static website will run together in one Cloud Run service.
We'll keep the frontend and backend in separate folders, but they don't need
separate deployments. Cloud SQL runs PostgreSQL for us, and Secret Manager holds
the application secrets.

The response comes back using Server-Sent Events. That means the server can send
updates over the same HTTP response while the guest waits. We don't need a queue
for this conversation. The request is still active while the agent works.

Conversation state lives in Postgres, so it doesn't depend on whichever Cloud Run
instance handled the previous question. We also need to check who owns each
conversation, limit how much work a turn can do, and handle a browser disconnect.

**Show one worked example:** exact dates → `check_availability` → deterministic
villa results → fixed UI cards → follow-up breakfast question → policy source.
Explain checkout-exclusive dates with one back-to-back stay. No arbitrary SQL,
model-generated HTML, booking mutations or exposure of guest reservation records.

## 5. Break the work into checked steps · 06:00–06:45

**On screen:** a short build checklist beside the repository.

Before I ask a coding assistant to build this, I want a clear sequence. First we
need the project and local environment. Then we'll connect the website to one
working agent turn, add the database tools, and test the guest journey. After
that we'll deploy the same application and add the checks we need to operate it.

Agents CLI gives the coding assistant tools and skills for the ADK workflow. We
will still inspect the generated code and verify each step before moving on.

**Visible completion checks:** sourced policy answer; correct available villas;
conversation survives restart; cloud deployment works; failed tool is observable.

## 6. Set up Google Cloud and the CLIs · 06:45–09:15

**On screen:** terminal and project console. Follow the [setup guide](resources/setup-guide.md).

- Check Python, uv and Node; install/check gcloud.
- Sign in, create a dedicated project, select it explicitly and link billing.
- Explain project ID, region and billing budget. A budget alert is not a hard cap.
- Configure local Application Default Credentials separately from CLI login.
- Enable the model API and verify access to the selected Gemini model/region.
- Install Agents CLI and its coding-assistant skills, inspect the generated starter.

**Spoken transition:**

The credentials on my laptop are for development. When we deploy, the application
will use its own service identity. We aren't putting my personal credentials or
a model API key into the website.

**Proof:** correct project printed; CLI versions visible; a minimal authenticated
model call works before continuing. Hide account identifiers and credentials in
screen captures. Do not spend the recording watching downloads or provisioning.

## 7. Build the frontend · 09:15–11:00

**On screen:** preserved website, frontend folder and widget components.

- Start from the Sanctuary Hotel design and generated photography.
- Explain the chat input, progressive answer, source link and villa card.
- Add loading, retry, unavailable and session-expired states.
- Keep the UI responsible for presentation; the backend owns data and credentials.

**Spoken transition:**

The website gives us something a hotel could actually put in front of guests.
But at this point the replies are still mocked. Next we'll replace those with
answers from our agent and real database lookups.

**Proof:** desktop and mobile layout; readable chat; reduced-motion behavior;
no secret in browser assets. Keep visual styling edits short in the final cut.

## 8. Build the ADK agent with Gemini · 11:00–15:00

**On screen:** agent definition, one tool implementation, tool trace, API route.

- Define a focused concierge instruction and the three typed tool contracts.
- Explain how ADK runs the model/tool loop using a single policy question.
- Use Gemini through Vertex AI with a configurable model ID.
- Wrap the runner in FastAPI with guest sessions and bounded SSE events.
- Show that source links and villa cards come from validated server data.

**Spoken explanation:**

The agent doesn't need all the hotel's data in its prompt. It can ask a tool for
the information it needs. That also gives us a place to control what it can see
and what it can do. In our case, the hotel tools only read data.

If the guest asks for next week, the assistant asks for exact dates. If a lookup
fails, it says it couldn't check. It should never fill that gap by inventing an
available room.

**Proof:** agent calls the expected tool, passes validated arguments and returns
a sourced answer. No cloud-runtime claims based only on the local playground.

## 9. Run locally with Postgres and test quality · 15:00–20:00

**On screen:** local database, website chat and a small evaluation results table.

- Start Postgres, run migrations, seed published policies, villas and occupancy.
- Connect the widget to the real backend; label inventory as fictional demo data.
- Show a successful availability search, a fully booked stay and an ambiguous date.
- Reload after restarting the API and recover completed conversation history.
- Try a second browser session to prove conversation isolation.
- Run a fixed dataset: policy facts, missing evidence, conflicting occupancy,
  closed nights, prompt injection and failed lookup.
- Review one answer manually; compare with an optional LLM judge. Deterministic
  tests decide inventory correctness. A model judge is not the booking authority.
- Fix one observed failing case and rerun the same dataset. Record actual findings;
  do not manufacture a model failure for the narrative.

**Spoken transition:**

A helpful answer and a working API are different things to test. We need to know
that the application works, and that the answers match the hotel's information.
These examples give us a repeatable check when we change the prompt or model.

**Proof:** test results, evaluation verdicts, latency and token usage; duplicate
requests do not run the same turn twice. Keep terminal details in the written guide.

## 10. Deploy to Google Cloud · 20:00–25:00

**On screen:** deployment configuration, Cloud Run, Cloud SQL and deployed site.

- Build one container with frontend assets and the Python backend.
- Provision Cloud SQL, runtime identity and Secret Manager entries using reviewed,
  repeatable configuration. Keep the database and application region aligned.
- Run migrations as a release step and seed the fictional demo inventory.
- Deploy Cloud Run; explain service identity, request timeout, instance/concurrency
  limits, database connection budget and application admission limits.
- Test SSE on the real URL, source pages, villa cards and persistent history.
- Show the deployed revision and explain how an image rollback works alongside
  backward-compatible database changes.

**Spoken explanation:**

Cloud Run can add instances as requests increase, but we still need to respect
our database connections and model quota. We'll start with conservative limits,
measure the application, and adjust them from evidence.

**Proof:** cloud smoke test and persistence across restart/revision. Record actual
model, region and configuration. Do not promise thousands of simultaneous model
calls without a corresponding load test. Include resource teardown in the guide.

## 11. Observe the agent and add alerts · 25:00–29:00

**On screen:** one request traced through API, model and lookup; monitoring chart.

- Explain logs as records of events, metrics as counts/timings, traces as the path
  through a request. Instrument locally earlier; here show the deployed exports.
- Inspect response time, failures, tool durations and model usage without exposing
  guest message content in logs.
- Enable a clearly labelled demo fault in the availability tool, restricted to the
  demo environment. Show the honest guest fallback and locate the failing span.
- Remove the fault and repeat the request.
- Configure an alert for repeated failed turns, a notification channel and a
  tested delivery path. Distinguish controlled alert testing from real incidents.
- Explain billing alerts plus application turn budgets, dependency limits and
  cleanup. Show measured usage; do not invent an average operating cost.

**Spoken explanation:**

A guest shouldn't need to tell us every time something breaks. This trace shows
where the request failed, and the alert tells us when failures are happening
often enough to investigate. That's part of delivering the application to a
client, along with deciding who responds when an alert arrives.

## 12. Wrap up · 29:00–30:00

**On screen:** repeat the finished guest journey, then the repository.

We now have a hotel website with an agent that can answer policy questions and
check villa availability. We've connected it to a database, deployed it to Google
Cloud, and added tests and operational visibility.

The availability data in this example is fictional. For a real hotel, the next
step would be connecting the same tool to its booking provider and validating the
answers with the hotel's team.

The code, architecture diagram and setup guide are linked below. Try adding a
new hotel policy, write a question that should retrieve it, and check the answer
and its source. That's a useful first change to make before adapting the project
for your own client.

Thanks to Google Cloud for sponsoring the video. I'll see you in the next one.

## Recording and review notes

This is a 30-minute edited walkthrough, not a claim that the full implementation
can be built in 30 minutes. Show meaningful code and decisions; cut installation
waits and provide reproducible commands in the repository. Record the completed
demo before recording the opening. Final outro statements depend on actual checks
passing. Do not claim that planned functionality already exists.

The agreed runtime is Cloud Run. Calling Gemini through Vertex AI does not mean
this agent is deployed to a separate managed agent runtime. Confirm final product
naming and required sponsor links with the sponsor review before recording.

## Appendix: services and tools shown

| Service / tool | Role in the system | What viewers will see |
| --- | --- | --- |
| Cloud Run | Application and agent runtime | Container deployment, revision, limits and streamed chat. |
| Cloud SQL for PostgreSQL | Durable application data | Policies, villas, demo occupancy and persistent conversations. |
| Vertex AI + Gemini | Model access | Authenticated model call, tool selection and model configuration. |
| Secret Manager | Runtime secrets | Secret reference in deployment; no credentials in the frontend. |
| IAM + service accounts | Runtime permissions | Dedicated service identity with scoped model and database access. |
| Cloud Logging | Operational events | Correlated request IDs and safe error records. |
| Cloud Trace | Request investigation | API, model and tool spans for a failed availability lookup. |
| Cloud Monitoring | Metrics and alerts | Latency/error chart, alert policy and notification test. |
| Cloud Billing | Project cost visibility | Project billing, budget alert and distinction from a hard spend cap. |
| Artifact Registry | Container image storage | Image tag/digest used by a Cloud Run revision. |
| Google ADK (framework) | Agent implementation | Agent instructions, typed tools, runner and session integration. |
| Agents CLI (developer tool) | Build workflow support | Installed coding-assistant skills, starter inspection and evaluation workflow. |
| gcloud (developer tool) | Cloud configuration | Project setup, local credentials and deployment commands. |
