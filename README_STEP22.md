# FlightSmart Step 22 — Real Route Guardrails

## Why this step exists
Duffel test mode can return synthetic one-segment routes such as AGS→HND. A one-segment sandbox response must not be presented to travelers as proof that a real nonstop service exists.

## New route-validation policy
FlightSmart now separates provider itinerary data from route plausibility:

- The returned segment path is still displayed as the provider result.
- A BTS/T-100 U.S.–Japan airport-pair reference is used to validate claimed nonstop routes.
- In **Duffel test mode**, a direct U.S.→Japan pair that is not in the BTS/T-100 reference is treated as a synthetic sandbox route and excluded from recommendations.
- A connection such as AGS→ATL→HND remains valid when the Japan-bound gateway pair ATL→HND is represented in the reference.
- In future **live mode**, a new direct route absent from historical BTS data is not automatically discarded. It is shown with a verification warning because live airline schedules can change after the historical reference period.
- Foreign-hub itineraries (for example U.S.→Canada→Japan) are allowed but labeled as outside the BTS U.S.–Japan direct-route validation scope.

## Reference coverage
`reference/us_japan_nonstop_reference.csv` contains the 34 U.S.→Japan airport pairs represented in the current FlightSmart BTS/T-100 processed data. The U.S. airport catalog contains 350 airports.

## UX changes
- Pre-search notice checks the exact origin→Japan destination pair, not only whether the origin has ever been a Japan gateway.
- Unsupported sandbox direct routes are removed from recommendation ranking.
- The user is told how many synthetic direct offers were removed.
- Recommendation explanations can only say “nonstop from the searched origin” when the pair is confirmed by the route reference.
- Connection itineraries identify the actual U.S.–Japan gateway.

## QA
Step 22 performs 1,400 direct-pair checks (350 U.S. airports × HND/NRT/KIX/NGO) and verifies that a test-mode direct itinerary is allowed if and only if its airport pair exists in the route reference.

Specific tests:
- AGS→HND direct test offer: rejected.
- AGS→ATL→HND: accepted; connection via ATL.
- Existing Step 5, Step 6, and Step 21 tests: pass.

## Source interpretation
BTS/T-100 is historical evidence and is not a guarantee of a current airline schedule. In live mode, FlightSmart will distinguish historical route verification from current live-provider availability rather than silently overriding a genuine new route.
