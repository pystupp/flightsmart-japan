# FlightSmart Step 13 — Japanese-first Decision UI

## What changed
- Moved flight search from a permanent sidebar into a wide, Japanese travel-site-style search area.
- Japanese-first labels and simpler visual hierarchy, with English available through the language control.
- Added three immediate decision views: Cheapest, FlightSmart Recommended, and Quickest.
- Added sort controls for the ranked offer list.
- Added an opt-in flexible-date comparison for round trips. Live mode checks departure/return dates ±1 day (up to 9 Duffel searches) and displays the fare differences in a grid.
- Added a plain-language savings message when a nearby date combination is cheaper.
- Kept BTS historical evidence available as an explanation layer instead of making it dominate the first screen.
- Preserved passenger ages/children, cabin, connection limits, traveler profile, live/demo modes, airline coverage, BTS evidence, and official data-source links.

## Important note about flexible dates
Flexible-date comparison is intentionally opt-in because each date pair requires a Duffel offer request. The displayed fare is the lowest returned total offer amount for the travelers in that search. Live prices can change between requests.

## Run
```bash
streamlit run app.py
```
