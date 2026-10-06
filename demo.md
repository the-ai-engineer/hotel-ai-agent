# Hotel concierge demo

All hotel facts, charges and availability are fictional. These are target behaviors to film after implementation, not features already built. Prices below are IDR including tax; accommodation prices are not provided.

## Opening: one family conversation

1. **“Two adults and two children aged 7 and 10, three nights from 1 November 2026. Which villa would suit us?”**
   Check 1–4 November inventory, recommend Garden Villa, show its card, king bed and two single beds. Forest Suite has capacity two. Mention unfenced pools when discussing suitability; do not promise childproof accommodation.
2. **“Our flight lands at 8am. Can we come straight to the hotel?”**
   Explain the roughly 90-minute transfer estimate, IDR 450,000 car transfer for four passengers and advance request. Room check-in is 15:00; luggage, restaurant and shared pool/showers are available beforehand. Do not equate overnight availability with room readiness.
3. **“One child has a nut allergy and one adult is vegan. Can we have breakfast on our terrace?”**
   Retrieve dining evidence: vegan choices, rate-dependent inclusion, IDR 150,000 terrace delivery per villa per morning, previous-day request. Explain the kitchen handles nuts and staff must discuss allergies. Do not guarantee safety or claim staff were notified.

Capture: three tool types, cited policy passages, grounded villa card, follow-up context and honest approval boundaries. Refresh to demonstrate saved conversation once implemented.

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

## Optional later action

A late-checkout request could be a separate write-tool feature: verify the guest/booking, collect requested time, show a summary, ask confirmation, create an idempotent request and display “Pending hotel approval”. This is outside the current read-only scope. Do not film it as implemented or imply a reservation changed.

## Design explanation

Policy answers use `search_policies` over published PostgreSQL sections. The agent chooses search terms and may refine them; it does not need to guess a Markdown filename. `get_villa` supplies public facts; `check_availability` computes every night's availability. Service opening hours never prove service slots are available.
