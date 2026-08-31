"""FlightSmart Step 3 live-itinerary evaluator.

Historical BTS evidence stays a labeled component. Live price, duration and
connection convenience are scored separately, then combined for ranking.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import math
import pandas as pd

from duffel_offer_adapter import parse_offer
from traveler_profiles import get_profile

DEFAULT_ROUTE_FILE = Path(__file__).resolve().parent / "score_v2" / "flightsmart_app_routes_v2.csv"


def load_historical_scores(path: str | Path = DEFAULT_ROUTE_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in ["ORIGIN", "DEST", "UNIQUE_CARRIER"]:
        df[c] = df[c].astype(str).str.upper()
    return df


def match_historical_evidence(facts: dict[str, Any], route_scores: pd.DataFrame) -> dict[str, Any]:
    gateway = (facts.get("international_gateway") or "").upper()
    dest = (facts.get("japan_arrival_airport") or "").upper()
    op = (facts.get("operating_carrier_code") or "").upper()
    mk = (facts.get("marketing_carrier_code") or "").upper()

    # Duffel Airways (ZZ) is a synthetic sandbox airline. Never attach BTS carrier
    # history to it or imply that its test offers represent a real airline.
    if op == "ZZ" or str(facts.get("operating_carrier_name") or "").lower() == "duffel airways":
        return {
            "historical_score": None,
            "historical_match_type": "TEST_AIRLINE_NO_BTS_MATCH",
            "historical_data_confidence": "UNAVAILABLE",
            "historical_recommendation_band": "TEST_ONLY",
            "historical_carrier_code": None,
            "historical_carrier_name": None,
            "historical_reason_en": "Duffel Airways is a synthetic test-mode airline, so FlightSmart does not attach BTS historical airline evidence to it.",
            "historical_reason_ja": "Duffel Airwaysはテストモード用の架空航空会社のため、FlightSmartではBTSの航空会社別履歴実績を紐づけません。",
            "historical_passengers": None,
            "historical_months_reported": None,
            "historical_gateway_score": None,
            "historical_carrier_score": None,
            "historical_service_consistency_score": None,
            "historical_passenger_evidence_score": None,
            "historical_airport_2025_score": None,
            "historical_chronic_risk_score": None,
            "historical_on_time_departure_pct": None,
            "historical_on_time_arrival_pct": None,
            "historical_gateway_cancellation_pct": None,
            "historical_carrier_cancellation_pct": None,
            "historical_airport_rank_2025": None,
            "historical_airport_ontime_pct_2025": None,
        }

    exact = route_scores[(route_scores.ORIGIN == gateway) & (route_scores.DEST == dest) & (route_scores.UNIQUE_CARRIER == op)]
    match_type = "EXACT_OPERATING_CARRIER"
    matched_code = op
    if exact.empty and mk and mk != op:
        exact = route_scores[(route_scores.ORIGIN == gateway) & (route_scores.DEST == dest) & (route_scores.UNIQUE_CARRIER == mk)]
        match_type = "MARKETING_CARRIER_FALLBACK"
        matched_code = mk

    if not exact.empty:
        row = exact.sort_values("flightsmart_score_v2", ascending=False).iloc[0]
        return {
            "historical_score": float(row.flightsmart_score_v2),
            "historical_match_type": match_type,
            "historical_data_confidence": row.data_confidence,
            "historical_recommendation_band": row.recommendation_band,
            "historical_carrier_code": matched_code,
            "historical_carrier_name": row.UNIQUE_CARRIER_NAME,
            "historical_reason_en": row.reason_en,
            "historical_reason_ja": row.reason_ja,
            "historical_passengers": int(row.passengers),
            "historical_months_reported": int(row.months_reported),
            "historical_gateway_score": None if pd.isna(row.get("gateway_score_100")) else float(row.get("gateway_score_100")),
            "historical_carrier_score": None if pd.isna(row.get("carrier_score_100")) else float(row.get("carrier_score_100")),
            "historical_service_consistency_score": None if pd.isna(row.get("service_consistency_score_100")) else float(row.get("service_consistency_score_100")),
            "historical_passenger_evidence_score": None if pd.isna(row.get("passenger_evidence_score_100")) else float(row.get("passenger_evidence_score_100")),
            "historical_airport_2025_score": None if pd.isna(row.get("airport_2025_score_100")) else float(row.get("airport_2025_score_100")),
            "historical_chronic_risk_score": None if pd.isna(row.get("chronic_risk_score_100")) else float(row.get("chronic_risk_score_100")),
            "historical_on_time_departure_pct": None if pd.isna(row.get("on_time_departure_pct")) else float(row.get("on_time_departure_pct")),
            "historical_on_time_arrival_pct": None if pd.isna(row.get("on_time_arrival_pct")) else float(row.get("on_time_arrival_pct")),
            "historical_gateway_cancellation_pct": None if pd.isna(row.get("gateway_cancellation_pct")) else float(row.get("gateway_cancellation_pct")),
            "historical_carrier_cancellation_pct": None if pd.isna(row.get("carrier_cancellation_pct")) else float(row.get("carrier_cancellation_pct")),
            "historical_airport_rank_2025": None if pd.isna(row.get("rank_2025")) else int(row.get("rank_2025")),
            "historical_airport_ontime_pct_2025": None if pd.isna(row.get("on_time_pct_2025")) else float(row.get("on_time_pct_2025")),
        }

    # Conservative market-level fallback: same gateway/destination, but do not borrow a competitor's individual score.
    market = route_scores[(route_scores.ORIGIN == gateway) & (route_scores.DEST == dest)]
    if not market.empty:
        score = float(market.flightsmart_score_v2.median())
        return {
            "historical_score": round(score, 1),
            "historical_match_type": "MARKET_MEDIAN_FALLBACK",
            "historical_data_confidence": "LIMITED",
            "historical_recommendation_band": "CONTEXT_ONLY",
            "historical_carrier_code": None,
            "historical_carrier_name": None,
            "historical_reason_en": "Carrier-specific historical evidence was not matched. FlightSmart uses only the median historical context for this U.S.–Japan gateway market and lowers confidence.",
            "historical_reason_ja": "この航空会社に一致する履歴データが見つからないため、この米国出発空港→日本市場の中央値を参考情報としてのみ使用し、信頼度を下げています。",
            "historical_passengers": int(market.passengers.sum()),
            "historical_months_reported": int(market.months_reported.max()),
            "historical_gateway_score": None,
            "historical_carrier_score": None,
            "historical_service_consistency_score": None,
            "historical_passenger_evidence_score": None,
            "historical_airport_2025_score": None,
            "historical_chronic_risk_score": None,
            "historical_on_time_departure_pct": None,
            "historical_on_time_arrival_pct": None,
            "historical_gateway_cancellation_pct": None,
            "historical_carrier_cancellation_pct": None,
            "historical_airport_rank_2025": None,
            "historical_airport_ontime_pct_2025": None,
        }

    return {
        "historical_score": None,
        "historical_match_type": "NO_MATCH",
        "historical_data_confidence": "UNAVAILABLE",
        "historical_recommendation_band": "NO_EVIDENCE",
        "historical_carrier_code": None,
        "historical_carrier_name": None,
        "historical_reason_en": "No matching U.S.–Japan historical market evidence is available in the current FlightSmart dataset.",
        "historical_reason_ja": "現在のFlightSmartデータには、この日米ルートに一致する履歴データがありません。",
        "historical_passengers": None,
        "historical_months_reported": None,
        "historical_gateway_score": None,
        "historical_carrier_score": None,
        "historical_service_consistency_score": None,
        "historical_passenger_evidence_score": None,
        "historical_airport_2025_score": None,
        "historical_chronic_risk_score": None,
        "historical_on_time_departure_pct": None,
        "historical_on_time_arrival_pct": None,
        "historical_gateway_cancellation_pct": None,
        "historical_carrier_cancellation_pct": None,
        "historical_airport_rank_2025": None,
        "historical_airport_ontime_pct_2025": None,
    }


def connection_score(stop_count: int, layovers: list[int]) -> float:
    base = {0: 100.0, 1: 84.0, 2: 66.0}.get(stop_count, max(35.0, 66.0 - 12.0 * (stop_count - 2)))
    penalties = 0.0
    for mins in layovers:
        if mins < 60:
            penalties += 28
        elif mins < 90:
            penalties += 14
        elif mins <= 240:
            penalties += 0
        elif mins <= 360:
            penalties += 6
        else:
            penalties += min(24, 6 + (mins - 360) / 60 * 3)
    return round(max(0.0, base - penalties), 1)


def _relative_score(values: list[float | int | None], index: int, higher_is_better: bool = False, floor: float = 55.0) -> float:
    valid = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    current = values[index]
    if current is None or not valid:
        return 75.0
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return 85.0
    frac = (float(current) - lo) / (hi - lo)
    if not higher_is_better:
        frac = 1 - frac
    return round(floor + frac * (100 - floor), 1)


def _label(score: float) -> str:
    if score >= 90: return "EXCELLENT"
    if score >= 82: return "STRONG"
    if score >= 74: return "GOOD"
    if score >= 65: return "FAIR"
    return "WEAK"


def evaluate_offers(offers: list[dict[str, Any]], route_scores: pd.DataFrame | None = None, profile_key: str = "best_overall") -> pd.DataFrame:
    if route_scores is None:
        route_scores = load_historical_scores()
    profile = get_profile(profile_key)
    weights = profile["weights"]
    facts_list = [parse_offer(o).to_dict() for o in offers]
    prices = [f["total_amount"] for f in facts_list]
    durations = [f["total_duration_min"] for f in facts_list]

    rows = []
    for i, facts in enumerate(facts_list):
        hist = match_historical_evidence(facts, route_scores)
        conn = connection_score(facts["stop_count"], facts["connection_minutes"])
        price = _relative_score(prices, i, higher_is_better=False)
        duration = _relative_score(durations, i, higher_is_better=False)

        # Historical evidence is important, but live itinerary quality stays distinct.
        components = {
            "historical": (hist["historical_score"], weights["historical"]),
            "connection": (conn, weights["connection"]),
            "duration": (duration, weights["duration"]),
            "price_value": (price, weights["price_value"]),
        }
        available = [(v, w) for v, w in components.values() if v is not None]
        total_w = sum(w for _, w in available)
        raw_overall = sum(float(v) * w for v, w in available) / total_w if total_w else 0.0

        # Evidence-aware recommendation score. Missing history is not treated as bad
        # performance, but it must not produce a misleading 100/100 recommendation
        # simply because the live sandbox/offer is cheap or short. The cap communicates
        # uncertainty while keeping the offer visible for price/schedule comparison.
        confidence_caps = {
            "VERY_HIGH": 100.0, "HIGH": 97.0, "MEDIUM": 94.0,
            "LOW": 90.0, "LIMITED": 87.0, "UNAVAILABLE": 84.0,
        }
        evidence_confidence = str(hist.get("historical_data_confidence") or "UNAVAILABLE").upper()
        evidence_cap = confidence_caps.get(evidence_confidence, 84.0)
        overall = round(min(raw_overall, evidence_cap), 1)

        gateway = facts.get("international_gateway") or "?"
        dest = facts.get("japan_arrival_airport") or facts.get("destination") or "?"
        carrier = facts.get("operating_carrier_name") or facts.get("operating_carrier_code") or "the operating carrier"
        stops = facts["stop_count"]
        stop_en = "nonstop" if stops == 0 else f"{stops} connection" + ("s" if stops != 1 else "")
        stop_ja = "直行" if stops == 0 else f"乗り継ぎ{stops}回"
        en = f"{carrier}: {gateway}→{dest} international segment; {stop_en} from the searched origin. Historical evidence is {hist['historical_data_confidence'].lower()} confidence. This ranking uses the '{profile['label_en']}' traveler profile. Live price and duration are scored relative to the offers returned in this search."
        ja = f"{carrier}：国際区間は{gateway}→{dest}、検索した出発地からは{stop_ja}です。履歴データの信頼度は{hist['historical_data_confidence']}です。今回は「{profile['label_ja']}」の旅行者設定で評価しています。料金と所要時間は、今回取得した候補便の中で相対評価しています。"

        row = {
            **facts,
            **hist,
            "connection_score": conn,
            "duration_score": duration,
            "price_value_score": price,
            "traveler_profile": profile["key"],
            "traveler_profile_en": profile["label_en"],
            "traveler_profile_ja": profile["label_ja"],
            "weight_historical": weights["historical"],
            "weight_connection": weights["connection"],
            "weight_duration": weights["duration"],
            "weight_price_value": weights["price_value"],
            "score_before_evidence_cap": round(raw_overall, 1),
            "evidence_confidence_cap": evidence_cap,
            "flightsmart_live_score": overall,
            "live_recommendation_band": _label(overall),
            "explanation_en": en,
            "explanation_ja": ja,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        # Step 18: reliability-first ranking.
        # A high historical score is only meaningful when the evidence behind it is
        # sufficiently reliable. Confidence is therefore the FIRST ranking key.
        # Market medians and weak/unavailable matches remain visible as reference
        # choices, but they cannot receive a numbered FlightSmart past-record rank.
        carrier_backed_types = {"EXACT_OPERATING_CARRIER", "MARKETING_CARRIER_FALLBACK"}
        df["historical_is_carrier_backed"] = df["historical_match_type"].isin(carrier_backed_types) & df["historical_score"].notna()

        confidence_order = {"VERY_HIGH": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "LIMITED": 4, "UNAVAILABLE": 5}
        df["historical_confidence_order"] = (
            df["historical_data_confidence"].astype(str).str.upper().map(confidence_order).fillna(5).astype(int)
        )
        # Only Medium-or-better carrier-specific evidence can earn a numbered rank.
        # LOW/LIMITED/UNAVAILABLE are not treated as bad performance; they simply do
        # not provide enough evidence for a confident historical ranking.
        df["historical_confidence_eligible"] = df["historical_data_confidence"].astype(str).str.upper().isin({"VERY_HIGH", "HIGH", "MEDIUM"})
        df["is_ranked_choice"] = df["historical_is_carrier_backed"] & df["historical_confidence_eligible"]

        # Prefer a direct operating-carrier BTS match over a marketing-carrier
        # fallback when confidence is otherwise equal.
        match_quality_order = {"EXACT_OPERATING_CARRIER": 0, "MARKETING_CARRIER_FALLBACK": 1}
        df["historical_match_quality_order"] = (
            df["historical_match_type"].map(match_quality_order).fillna(9).astype(int)
        )

        # Ranking hierarchy (most important first):
        # 1) eligible evidence, 2) historical confidence, 3) match quality,
        # 4) BTS historical rating, 5) depth of observed history,
        # 6) live itinerary quality only as a final tie-breaker.
        # This prevents a 95-point LOW-confidence record from outranking a
        # 79-point HIGH-confidence JAL/ANA/etc. record simply because the raw
        # score is larger.
        df = df.sort_values(
            ["is_ranked_choice", "historical_confidence_order", "historical_match_quality_order",
             "historical_score", "historical_months_reported", "historical_passengers",
             "flightsmart_live_score", "total_amount"],
            ascending=[False, True, True, False, False, False, False, True],
            na_position="last",
        ).reset_index(drop=True)

        ranked_numbers = []
        evidence_numbers = []
        n = 0
        for eligible in df["is_ranked_choice"]:
            if bool(eligible):
                n += 1
                ranked_numbers.append(n)
                evidence_numbers.append(n)
            else:
                ranked_numbers.append(pd.NA)
                evidence_numbers.append(pd.NA)
        df.insert(0, "rank", pd.array(ranked_numbers, dtype="Int64"))
        df.insert(1, "historical_evidence_rank", pd.array(evidence_numbers, dtype="Int64"))
    return df
