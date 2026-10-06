# Recording the hotel agent build

Start with the website and disabled concierge preview. Record the screen during the real build; record explanations and the finished opening demo after the system works. Stop between sections and save a checked commit. Keep login, credentials and private account screens out of the footage.

## Website starting point

Run `bash scripts/dev.sh`. Show the homepage and open the widget: there are no agent responses yet. Explain the guest and hotel problem. Show `hotel/` and the fixed questions in `evals/`. Use [demo.md](../demo.md) as the on-screen question checklist.

## Requirements, architecture and plan

Show `docs/Requirements.md`, the diagram in `docs/Architecture.md`, and the Linear milestones. Policies need catalogue selection and complete document reads; availability needs deterministic inventory lookup. Chat uses asynchronous HTTP and SSE without a queue. PostgreSQL owns conversations across instances.

## Tool setup

Prompt: “Inspect existing tools. Use the official Google Agents CLI setup and installed skills, verify gcloud and local model credentials, and record exact commands and versions. Preserve this website. Do not provision resources yet.”

Show CLI help before choosing flags. Use the existing cloud project `personal-infrastructure-505708`. Verify a supported Gemini model rather than assuming a latest model name. Record successful commands as they are run.

## M1: Local guest journey

| Slice | Concise prompt | Visible checkpoint |
| --- | --- | --- |
| GRA-212: sourced policy answer | “Read the requirements and architecture. Use Agents CLI skills to add the smallest ADK policy agent with list_documents and read_document, local PostgreSQL, repeatable hotel seeds and sourced answers. Connect the existing widget through FastAPI and SSE. Preserve the design.” | Ask about breakfast, open the policy source, show catalogue selection, the document read and its versioned source. |
| GRA-213: villa availability | “Add read-only villa and availability tools using the source fixtures. Validate exact dates and capacity. Return validated cards, not generated HTML.” | Available stay, blocked stay, missing date clarification. |
| GRA-214: conversation state | “Implement owned guest sessions, saved turns, idempotency, bounded history and interrupted-turn recovery. Prove two guests cannot share history.” | Refresh, separate browser sessions, interruption and retry. |
| GRA-215: evaluations | “Turn the fixed guest cases into checks. Assert selected-document reads and tool facts deterministically; test paraphrases and cross-document answer grounding. Report failures before fixing and rerunning.” | Inspect an actual failure if one occurs, then show the checked dataset. |

Run one slice at a time. Inspect the diff and checks, request an independent review, commit and update its Linear issue. Do not narrate completion before the real model and browser journey pass.

## M2: Deployed hotel demo

GRA-216 prompt: “Prepare one Cloud Run image for the frontend and backend, Cloud SQL, scoped identities and secrets. Show resources and costs before provisioning. Deploy only after local checks; run explicit migrations and seeds, then verify the cloud guest journey.”

Show project, revision, source answer, villa card and history after refresh. Preserve unrelated infrastructure. Record actual deployment commands and settings.

## M3: Operational proof

GRA-217: trace a labelled lookup failure, verify guest fallback, remove the fault and test an alert. Demonstrate daily retention rather than retaining chats forever.

GRA-218: stage 10, 25, 50 and 100 active turns after agreeing the test spend. Show measured latency, failures and settings. Browsing users are not active model calls. Do not claim 100-turn capacity until measured.

## Finish the video

Record the family conversation in demo.md for the opening: suitable villa, early arrival, then vegan breakfast and the allergy boundary. Show tool calls, sources and saved history. Recap the guest journey, evaluations and operational checks. State remaining production work: booking provider, approved policies, public abuse controls and operational ownership.

## Fresh chat handoff

“Work in this repository on a normal branch, without a worktree. Read README.md, docs/Requirements.md, docs/Architecture.md, hotel/ and evals/. Inspect the linked Linear project. I am recording the build. Propose acceptance criteria and checks for GRA-212, then wait until I say recording is ready before coding. Use Google Agents CLI skills and log successful commands. Preserve the hotel design.”

## Preserved earlier work

The unfinished implementation is saved on `codex/agent-build-backup-20261006` at `09906ee`. Old documents are available there and in Git history. Use it as an explicit reference if needed; do not merge it wholesale or present reused code as a new live build.
