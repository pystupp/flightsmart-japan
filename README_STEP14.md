# FlightSmart Step 14 — Evidence Clarity

This update improves the BTS evidence panel so travelers can understand what the historical rating actually means.

## What changed

- Replaced the often-empty **根拠スコア / Evidence score** column with **評価 / Evidence strength**.
- Descriptive evidence such as months of service and historical passenger volume is no longer forced into a 0–100 score.
- Added easy-to-read evidence labels such as **良好**, **参考になる**, **継続実績あり**, and **十分な実績データ**.
- Historical numeric subscores are still used internally when they exist, but the traveler-facing table emphasizes understandable evidence rather than unexplained numbers.
- Added a clear distinction between an exact carrier/route BTS match and **market-median context** when carrier-specific evidence is unavailable.
- Added **data confidence** near the BTS historical rating.
- Added an explanation that missing evidence is not treated as a zero-point penalty and that historical evidence does not predict future delays.
- Renamed the result-card metric from **履歴実績** to **BTS履歴評価** and displays `/100` explicitly.

## Design principle

FlightSmart should never invent a numeric score simply to fill an empty cell. A historical passenger count or number of months served can be useful evidence without pretending that the raw figure itself has an independently defensible 0–100 meaning.
