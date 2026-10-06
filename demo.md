# Hotel concierge demo

All hotel facts, charges and availability are fictional. Availability, policy answers, source links, villa detail pages and saved conversations are implemented locally. Guest-confirmed demo reservations and notes saved for hotel review are implemented. Booking changes, payments and staff notifications are not implemented. Prices below are IDR including tax; accommodation prices are not provided.

## Opening: one family conversation

1. **“Two adults and two children aged 7 and 10, three nights from 1 November 2026. Which villa would suit us?”**
   Check 1–4 November inventory, recommend Garden Villa, show its card, king bed and two single beds. Forest Suite has capacity two. Mention unfenced pools when discussing suitability; do not promise childproof accommodation.
2. **“Our flight lands at 8am. Can we come straight to the hotel?”**
   Explain the roughly 90-minute transfer estimate, IDR 450,000 car transfer for four passengers and advance request. Room check-in is 15:00; luggage, restaurant and shared pool/showers are available beforehand. Do not equate overnight availability with room readiness.
3. **“One child has a nut allergy and one adult is vegan. Can we have breakfast on our terrace?”**
   Retrieve dining evidence: vegan choices, rate-dependent inclusion, IDR 150,000 terrace delivery per villa per morning, previous-day request. Explain the kitchen handles nuts and staff must discuss allergies. Do not guarantee safety or claim staff were notified.

Capture: four tools (list documents, read documents, villa details and availability), cited policy passages, grounded villa card, follow-up context and honest approval boundaries. Refresh to demonstrate the saved conversation.

## More useful questions

| Question | Expected useful result |
| --- | --- |
| “What can we arrange for our anniversary?” | Flowers/cake IDR 600,000; terrace dinner for two IDR 1,800,000 excluding drinks; total IDR 2,400,000. Both require 48h notice and confirmation. |
| “Forest Suite is unavailable 3–5 November. What else works for two?” | Garden Villa fits those dates. Check alternatives only if the guest accepts different dates; never silently change the stay. |
| “Our flight leaves at 10pm. What can we do after checkout?” | Checkout 11:00; luggage until 22:00; shared pool/showers until 18:00. Late checkout until 14:00 costs IDR 500,000 if approved. Departure timing is an estimate. |
| “Flexible rate, arrival 1 November, cancelling 26 October. What would we pay?” | Free deadline was 25 October at 23:59 property time; one night's charge. No invented monetary fee or cancellation action. |
| “Can our seven-year-old join the activities?” | Walks accept children six and over with an adult, Tuesday/Thursday, IDR 200,000 each. Yoga/spa age 16+. Schedule is not confirmed participation. |
| “Can you move my checkout to 14:00?” | Explain charge, prior-day request deadline and staff approval. No booking change or claim a request was sent. |

## Short evaluation segment

Show the cases in `evals/guest-questions.json`. Check facts and availability deterministically; evaluate the answer for grounding and clarity. Include a family follow-up, unknown inventory, allergy boundary and failed lookup. Show an actual failing case if one occurs, fix it and rerun.

## Design explanation

Policy answers use `list_documents` to inspect titles, summaries and keywords, then `read_document` for complete published bodies with versioned sources. Show the selected document IDs and reads. Multi-part questions may need several documents; summaries alone cannot support an answer. `get_villa` supplies public facts and `check_availability` computes every night. No keyword/full-text or vector search is used in this version. Service opening hours never prove service slots are available.

## Reset between takes

Use **New conversation → Start new** before a fresh demo. **Keep this chat** cancels the reset. Refresh keeps the new conversation empty; closing the widget preserves it. This starts fresh context, it does not delete stored records.

## Strongest three-minute recording

Start a new conversation, then use this sequence:

1. **“We’re two adults. Is the Forest Suite available from 3 to 5 November 2026?”** Forest Suite is blocked. Garden Villa is an alternative for the same dates. Open its card to show a proper detail page and preserved chat.
2. **“We’d prefer the Forest Suite. What about 1 to 3 November instead?”** Fresh inventory check returns availability for the new full stay. Show the changed dates and Forest Suite card.
3. **“It’s our anniversary. Can we have flowers and a private dinner for two within IDR 2,500,000?”** Read experiences policy, combine IDR 600,000 flowers/cake and IDR 1,800,000 dinner: IDR 2,400,000 excluding drinks. Explain 48-hour notice and staff confirmation.
4. **“We arrive at 8am. Can we swim and leave our bags before our villa is ready?”** Read arrival and services evidence together. Explain the shared pool, luggage and showers without promising early room access.

The demo shows changing requirements, deterministic inventory, a visual recommendation, cross-page continuity and multiple policy reads. It should not imply any request or booking has been made.

## Other useful takes

- **Family:** “Two adults and two children, three nights from 1 November 2026. Which villa suits us?” Then ask about a nut allergy, vegan breakfast and terrace delivery. Show capacity, bedding and qualified dietary guidance.
- **Multilingual:** Ask an arrival question in Spanish. The current agent instructions support the guest’s language; verify the actual response before filming.
- **Unknown dates:** Ask about December 2027. Show a clear distinction between unrecorded inventory and sold-out accommodation.
- **Operational proof:** Refresh the villa page and continue the conversation. Stop a response and retry. Pair this with a short look at the tools and database records.

## Hotel request workflow

The agent looks up the current guest's booking and prepares a note. The guest reviews it and clicks **Send request**. PostgreSQL saves it as pending hotel review. No booking is changed, and no external message is sent. A staff inbox and notifications remain future scope.

## Full booking demo

1. “Can I book the Garden Villa for two guests, 10 to 11 October 2026?” Show availability and Reserve this villa. If this stay is already booked during rehearsal, choose another unblocked October date.
2. Open the booking page, review the exact dates/guests, then Confirm reservation. Show the generated reference. No payment or nightly price is claimed.
3. Click Ask about my booking. The concierge reads only the current guest's reservation.
4. “Please ask the hotel to review late checkout until 14:00.” It reads the policy, explains IDR 500,000 and approval/deadline conditions, then prepares a note. Review and click Send request. Show Pending hotel review, not approved checkout.
5. Refresh: the reservation stays confirmed, and the note status stays pending. Repeat the availability search: the reserved villa is excluded.

Today's property date is injected into the prompt. October 2026 through September 2027 are covered by sample inventory. Booking references alone cannot access other guests' records. The sample browser session lasts 24 hours. Real returning guests need authentication.

## Relative dates and booking follow-ups

- “Which villas are available for two guests next weekend?” The agent states its Friday-to-Sunday assumption and checks immediately. The upcoming Friday must be after today; on a Friday it uses the following Friday. Guests can correct the dates before booking.
- “Actually, 16 to 18 October instead.” It retains the guest count and checks the corrected dates.
- “Great, can I book it?” It refreshes availability for the agreed stay and shows a fresh Reserve card. The guest still confirms on the booking page.

For a stable recording, explicit dates are safest. Demo reservations change availability, so use a new unblocked stay for each booking take. Do not repeatedly book the same dates and expect the same result.

## Live smoke evaluations

```bash
uv run --directory backend python evaluate.py --output /tmp/hotel-evals.json
uv run --directory backend python evaluate.py --holdout --output /tmp/hotel-evals-holdout.json
```

`evals/demo-smoke.json` freezes the property date at 7 October 2026 for repeatable date assertions. The website still uses the real Bali date. The runner exercises the real ADK agent, Vertex and PostgreSQL without booking writes. It checks structured availability, dates, cards, source reads and selected phrases. Inspect the saved replies as well: these checks are smoke coverage, not a grounding score or proof every answer is correct. Booking ownership and confirmation are covered by backend tests and browser checks.

Useful failure to explain on camera: a booking follow-up initially referred to an old card without refreshing availability. Strengthening the date/card assertions caught it; the prompt now requires a fresh check. No IDE or extra queue is needed for this refinement.
