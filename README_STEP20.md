# FlightSmart Step 20 — Japanese Carrier Validation

This update strengthens ANA/JAL/ZIPAIR visibility without giving Japanese airlines an artificial scoring bonus.

## Changes
- Tracks the operating carrier code and name on the actual U.S.–Japan transpacific segment separately for outbound and return trips.
- Japanese-airline coverage diagnostics now inspect both directions, so ANA/JAL are not hidden when they operate only one direction of a mixed-carrier itinerary.
- The airline-coverage panel now shows transpacific operating carriers rather than relying only on the single outbound carrier label.
- Clarifies that a missing ANA/JAL/ZIPAIR mark means the carrier was not returned in that particular search, not that the Duffel account lacks access.
- Keeps Step 19 evidence-confidence scoring unchanged. ANA/JAL/ZIPAIR receive no nationality bonus; ranking remains evidence-driven.

## QA
- Python compile
- Existing Step 5 and Step 6 regression tests
- New mixed United/ANA round-trip carrier detection test
