# FlightSmart Step 19 — Evidence-Aware Recommendation Confidence

This update keeps FlightSmart as a recommendation/decision-support app and improves how recommendation scores communicate uncertainty.

## Changes
- Adds an evidence-confidence ceiling to the overall recommendation score so an offer with unavailable BTS history cannot display a misleading 100/100 solely from price, duration, or connections.
- Confidence ceilings: Very High 100, High 97, Medium 94, Low 90, Limited 87, Unavailable 84.
- Missing BTS evidence is not treated as poor airline performance. The offer remains visible as a reference option and the UI explains when a confidence ceiling changed the displayed score.
- Shows the operating carrier on the transpacific segment separately for outbound and return trips, making mixed United/ANA, American/JAL, and similar codeshare itineraries easier to understand.
- Existing BTS past-record ranking remains evidence-first: only carrier/route-specific Medium-or-better evidence receives a numbered historical rank.

## QA
- Python compile: PASS
- Step 5 QA: PASS
- Step 6 QA: PASS
