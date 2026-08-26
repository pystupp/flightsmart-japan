# FlightSmart Step 12 — BTS Evidence Transparency + Source References

## What changed

Step 12 makes the historical part of the FlightSmart score visible to travelers instead of showing only one combined number.

For offers with a matched BTS U.S.–Japan historical record, the app can now display:

- Matched historical carrier and gateway-to-Japan market
- FlightSmart historical evidence score
- Months of reported U.S.–Japan service
- Historical passenger-volume evidence
- U.S. gateway on-time departure and cancellation context
- Carrier on-time arrival and cancellation context when comparable evidence is available
- 2025 major-airport performance context when available
- Chronic-delay signal
- Component evidence scores used by the historical model

Missing evidence remains visibly missing; it is not converted to a false zero or fabricated value.

## Traveler-facing wording

The evidence section explicitly states that historical operating records are supporting evidence for comparing current offers and do not predict whether a future flight will be delayed.

## Source transparency

A new Data sources & references section is displayed at the bottom of the Streamlit app with official links to:

- Bureau of Transportation Statistics airline data downloads:
  https://www.bts.gov/airline-data-downloads
- Duffel API offer documentation:
  https://duffel.com/docs/api/offers

## QA

Existing Step 5 and Step 6 regression tests pass. A Step 12 evidence check also confirmed that the detailed BTS component fields propagate from the historical route table into the live ranked-offer output.
