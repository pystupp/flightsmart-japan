# FlightSmart Step 11 — Japanese Airline Coverage Diagnostics

## Key finding
The existing BTS T-100 International Market data already has strong Japanese-carrier coverage. The current Score v2 table contains JAL, ANA and ZIPAIR route/carrier records.

The more important issue discovered from the public-beta screenshot is Duffel **test mode**: Duffel Airways is Duffel's synthetic sandbox airline. Test-mode offers and prices are not representative of real airline inventory.

## Changes in this patch
- Detects Duffel test mode from `offer.live_mode` and Duffel Airways (`ZZ`).
- Shows a prominent bilingual sandbox warning.
- Adds a live-search airline coverage diagnostic showing operating-carrier counts.
- Shows whether ANA (NH), JAL (JL), and ZIPAIR (ZG) were actually returned by Duffel.
- Explicitly states that absent Japanese airlines were not filtered out by FlightSmart.
- Displays marketing carrier when it differs from operating carrier.
- Prevents synthetic Duffel Airways from receiving borrowed BTS historical airline evidence.

## What this proves
FlightSmart's `evaluate_offers()` evaluates every offer extracted from Duffel and does not contain an ANA/JAL exclusion filter. In live mode, Japanese carriers can be scored when Duffel returns them and the historical route/carrier record matches.

## Next production decision
To assess real ANA/JAL availability, activate Duffel live mode and use a live token. Keep the test token for integration QA only.
