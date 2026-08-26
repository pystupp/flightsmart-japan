# FlightSmart Step 17 — Past-Records-First Ranking

This revision makes FlightSmart's BTS historical evidence much more visible in the ranking itself.

## What changed

- Added a prominent **BTS Past-Record Ranking / BTS過去実績ランキング** section.
- Only offers with **airline/route-specific BTS matches** can receive a numbered past-record rank.
- Market-median fallback data remains visible only as context and does **not** receive a rank.
- Offers with no matched BTS history remain visible for price/time comparison but are unranked reference options.
- The numbered rank is now primarily driven by the **BTS historical rating**; evidence confidence is used next, then live itinerary quality only as a tie-breaker.
- Result cards now lead with **BTS past-record rank + BTS historical rating**. The live FlightSmart comparison score is secondary.
- The past-record table shows airline, U.S.–Japan segment, BTS rating, evidence confidence, months observed, and historical passenger count.

## Why

FlightSmart is intended to help travelers use historical operating records as decision support. A high live price/time score should not appear to be a strong evidence-backed recommendation when carrier-specific historical records are unavailable.
