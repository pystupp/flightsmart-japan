# Changelog

## Step 8 — Beta Launch Preparation

- Reorganized the project as a GitHub-ready repository with `app.py` at root.
- Pinned Streamlit to 1.62.0 for reproducible Community Cloud deployment.
- Added Python 3.12 deployment marker.
- Removed generated `__pycache__` files.
- Added launch checklist, first-10-testers plan, beta privacy draft, beta limitations draft, and repository README.
- Preserved Demo and live Duffel modes, adaptive traveler profiles, round-trip support, BTS airport catalog, and bilingual UX from Step 7.

## Step 12 — BTS evidence transparency and source references
- Added traveler-facing BTS historical evidence tables behind matched FlightSmart scores.
- Added service months, historical passengers, gateway/carrier on-time context, airport context, and chronic-delay evidence where available.
- Added explicit explanation that historical evidence is not a future-delay prediction.
- Added official BTS and Duffel source/reference links to the app footer.

## Step 13 — Japanese-first decision UI
- Rebuilt the primary search experience as a horizontal travel-search interface.
- Added Cheapest / Recommended / Quickest decision cards and sorting.
- Added opt-in ±1 day flexible-date fare grid for round trips.
- Simplified first-screen explanations and moved BTS detail behind expandable evidence.

## Step 14 — BTS evidence clarity
- Replaced blank-heavy Evidence Score column with categorical Evidence Strength.
- Added descriptive labels for service continuity and passenger records.
- Added explicit market-context warning for carrier fallback matches.
- Added BTS data-confidence display and clearer score methodology language.
- Renamed traveler-facing historical metric to BTS Historical Rating.

## Step 15 — Founder Story / Why FlightSmart
- Added a Japanese-first “このアプリを作った理由 / Why I made FlightSmart” section at the top of the app.
- Explains the family travel experience that motivated FlightSmart, including traveling with two children and past cancellations/delays.
- Clarifies that BTS historical records are supporting decision evidence, not future-flight predictions or guarantees.

## Step 17 — Past-Records-First Ranking
- Added visible BTS past-record ranking table.
- Limited numbered rankings to airline/route-specific BTS matches.
- Market median and unavailable history are now unranked context/reference options.
- Made BTS historical rating the primary rank driver, with evidence confidence and live itinerary score used as secondary tie-breakers.
- Promoted BTS past-record rank and rating on each result card.
