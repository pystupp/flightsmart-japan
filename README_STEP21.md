# FlightSmart Step 21 — Smart Japan Flight Choices

Step 21 makes FlightSmart more understandable for travelers starting at regional U.S. airports and reduces the risk of implying that a preferred airline flies nonstop from the searched origin.

## What changed

- **Actual route paths from returned segments** — results show paths such as `AGS → ATL → HND`, not a misleading `AGS → HND` airline label.
- **Connection-aware messaging** — when the outbound journey has a connection, FlightSmart says where the Japan-bound transpacific segment begins.
- **Regional-airport heads-up** — if the selected origin is not in the current BTS U.S.–Japan gateway reference, the app explains that a connection is likely and that actual returned segments will be validated.
- **Preferred transpacific airline** — ANA/JAL/ZIPAIR preferences apply to the main U.S.–Japan segment, not necessarily the first U.S. feeder flight.
- **Multiple traveler priorities** — users can combine up to three priorities (family, fewer connections, reliability, price, shortest time). The scoring weights are averaged transparently.
- **Smart choice groups** — FlightSmart can surface distinct choices such as best overall balance, family-friendly, easiest journey, best value, strongest BTS evidence, and Japanese-carrier option.
- **Result diversity** — near-identical route/carrier combinations are deduplicated before the main comparison list so users see meaningful variety sooner.
- **No invented routes** — route truth comes from Duffel-returned segments. The BTS gateway reference is contextual only.

## Important methodology note

The pre-search BTS gateway reference is historical context, not a current airline schedule database. Actual itinerary routing and operating-carrier information displayed after a search comes from the returned Duffel offer segments. FlightSmart does not construct a route that was not returned by the flight provider.

## QA

- Existing Step 5 regression: PASS
- Existing Step 6 regression: PASS
- New Step 21 regional-airport route test: PASS
- `AGS → ATL → HND` correctly recognized as one connection
- `AGS → IAH → NRT` with ANA on the transpacific segment correctly recognizes ANA preference without implying ANA operates from AGS
- Multi-priority scoring: PASS
- Diverse-results selector: PASS
