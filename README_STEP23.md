# FlightSmart Step 23 — Flight Result Cards & Route Reconstruction

Step 23 makes the returned Duffel itinerary segments the source of truth for how a trip is shown to travelers.

## What changed

- Reconstructs each outbound and return path from actual segments, e.g. `AGS → DFW → NRT`.
- Shows stop count and journey duration separately for outbound and return.
- Shows every operating carrier by segment.
- Shows the marketing carrier when it differs from the operating carrier (codeshare clarity).
- Marks the main Japan international segment so users can see which airline actually operates the long-haul leg.
- Shows connection airport and layover duration between segments.
- Keeps Step 22 route guardrails: unsupported synthetic Duffel-test nonstop U.S.-Japan pairs are excluded.
- Keeps BTS historical evidence below the itinerary as comparison support rather than a future-performance guarantee.

## UX principle

A preferred airline is a preference for the relevant long-haul/Japan segment, not a claim that the airline serves the user's local origin airport. A regional-origin traveler should see the complete feeder + gateway + Japan path.

## QA

`test_step23.py` verifies an Augusta-style round trip with American feeder service and a JAL transpacific segment, including codeshare and layover reconstruction.
