# FlightSmart Step 18 — Confidence-First Ranking

Step 18 makes historical confidence the primary key for the numbered BTS past-record ranking.

## Ranking rules

1. Only carrier/route-specific BTS matches with **Medium, High, or Very High** confidence can receive a numbered rank.
2. **Low, Limited, and Unavailable** evidence stays visible only as a reference option and cannot be #1, #2, etc.
3. Among eligible offers, rank priority is:
   - historical confidence (Very High > High > Medium)
   - direct operating-carrier match over marketing-carrier fallback
   - BTS historical rating
   - months observed and historical passenger depth
   - live price/time/connection score only as a final tie-breaker
4. The ranking does not give a nationality bonus to Japanese airlines. If JAL/ANA rank above another airline, it is because their matched historical evidence is more reliable/stronger for the searched U.S.–Japan segment.

This keeps "missing evidence" separate from "bad performance" while preventing poorly backed choices from appearing at the top.
