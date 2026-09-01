"""Step 22 route-awareness helpers.

FlightSmart uses two different kinds of route truth:
1) Live/test provider segments describe what Duffel returned for a search.
2) BTS/T-100 U.S.-Japan market pairs provide a conservative historical reference
   for airports that have actually reported U.S.-Japan service.

Important: Duffel test mode can return synthetic routes. In test mode, a one-segment
U.S.-Japan itinerary that is not present in the BTS/T-100 reference is NOT treated
as a real nonstop flight and is excluded from recommendations.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd

ROUTE_FILE = Path(__file__).resolve().parent / "score_v2" / "flightsmart_app_routes_v2.csv"
JP_AIRPORTS = {"HND", "NRT", "KIX", "NGO", "FUK", "CTS", "OKA", "ITM"}


def load_nonstop_route_reference(path: str | Path = ROUTE_FILE) -> set[tuple[str, str]]:
    """Return historical U.S.->Japan airport pairs represented in FlightSmart BTS data."""
    df = pd.read_csv(path, usecols=["ORIGIN", "DEST"])
    df["ORIGIN"] = df["ORIGIN"].astype(str).str.upper()
    df["DEST"] = df["DEST"].astype(str).str.upper()
    return set(map(tuple, df[["ORIGIN", "DEST"]].dropna().drop_duplicates().itertuples(index=False, name=None)))


def load_gateway_reference(path: str | Path = ROUTE_FILE) -> set[str]:
    return {o for o, _ in load_nonstop_route_reference(path)}


def route_pair_context(origin: str, destination: str, path: str | Path = ROUTE_FILE) -> dict[str, Any]:
    pairs = load_nonstop_route_reference(path)
    origin = (origin or "").upper()
    destination = (destination or "").upper()
    return {
        "origin": origin,
        "destination": destination,
        "is_historical_nonstop_pair": (origin, destination) in pairs,
        "is_historical_us_japan_gateway": origin in {o for o, _ in pairs},
        "reference_route_count": len(pairs),
        "reference_gateway_count": len({o for o, _ in pairs}),
    }


def origin_gateway_context(origin: str, destination: str | None = None) -> dict:
    return route_pair_context(origin, destination or "")


def path_text(path: list[str] | tuple[str, ...] | None) -> str:
    return " → ".join([str(x) for x in (path or []) if x])


def _normalize_us_jp_pair(a: str | None, b: str | None) -> tuple[str, str] | None:
    a = (a or "").upper()
    b = (b or "").upper()
    if not a or not b:
        return None
    if b in JP_AIRPORTS and a not in JP_AIRPORTS:
        return (a, b)
    if a in JP_AIRPORTS and b not in JP_AIRPORTS:
        return (b, a)
    return None


def validate_itinerary_facts(facts: dict[str, Any], path: str | Path = ROUTE_FILE) -> dict[str, Any]:
    """Annotate parsed Duffel facts with route plausibility/reference information.

    This is deliberately conservative in Duffel TEST mode because sandbox routes can
    be synthetic. In LIVE mode, an unreferenced direct route is warned about but not
    discarded: a new live route may exist after the historical BTS reference period.
    """
    pairs = load_nonstop_route_reference(path)
    out_path = [str(x).upper() for x in (facts.get("outbound_route_path") or []) if x]
    ret_path = [str(x).upper() for x in (facts.get("return_route_path") or []) if x]
    live_mode = facts.get("offer_live_mode")

    origin = (facts.get("origin") or (out_path[0] if out_path else "")).upper()
    dest = (facts.get("destination") or (out_path[-1] if out_path else "")).upper()
    searched_pair = (origin, dest)
    searched_pair_known = searched_pair in pairs

    out_cross_pair = None
    for a, b in zip(out_path, out_path[1:]):
        p = _normalize_us_jp_pair(a, b)
        if p:
            out_cross_pair = p
            break

    if len(out_path) == 2 and dest in JP_AIRPORTS:
        if searched_pair_known:
            status = "KNOWN_NONSTOP"
            allowed = True
            warning_en = "This nonstop U.S.-Japan airport pair is present in FlightSmart's BTS/T-100 route reference."
            warning_ja = "この日米直行空港ペアはFlightSmartのBTS/T-100路線参照に含まれています。"
        elif live_mode is False:
            status = "SANDBOX_UNSUPPORTED_DIRECT"
            allowed = False
            warning_en = f"Duffel test mode returned {origin}→{dest} as nonstop, but this pair is not in FlightSmart's BTS/T-100 U.S.-Japan route reference. It is treated as a synthetic test route and excluded."
            warning_ja = f"Duffelテストモードでは{origin}→{dest}が直行便として返されましたが、FlightSmartのBTS/T-100日米路線参照にはありません。架空のテスト路線として除外します。"
        else:
            status = "LIVE_UNCONFIRMED_DIRECT"
            allowed = True
            warning_en = f"The live provider returned {origin}→{dest} nonstop, but this pair is not in the current historical BTS/T-100 reference. Verify the current airline schedule before booking."
            warning_ja = f"ライブ検索では{origin}→{dest}の直行便が返されましたが、現在のBTS/T-100履歴参照にはありません。予約前に航空会社の最新時刻表をご確認ください。"
    elif len(out_path) >= 3:
        if out_cross_pair and out_cross_pair in pairs:
            status = "CONNECTION_VIA_KNOWN_GATEWAY"
            allowed = True
            gateway = out_cross_pair[0]
            warning_en = f"Connection required from {origin}. The U.S.-Japan segment is validated through {gateway}."
            warning_ja = f"{origin}から日本へは乗り継ぎが必要です。日米区間は{gateway}発の路線として参照確認できます。"
        elif out_cross_pair:
            status = "CONNECTION_WITH_UNCONFIRMED_US_JP_SEGMENT"
            allowed = live_mode is not False
            warning_en = "The itinerary contains a U.S.-Japan segment not present in the current historical route reference."
            warning_ja = "旅程に、現在の履歴路線参照にない日米区間が含まれています。"
        else:
            # e.g. U.S. -> Canada/Europe/Asia hub -> Japan. BTS U.S.-Japan direct
            # pairs cannot validate the foreign-hub segment, but it can still be real.
            status = "CONNECTION_VIA_FOREIGN_HUB"
            allowed = True
            warning_en = "Connection itinerary returned through a non-U.S. hub; BTS U.S.-Japan direct-route reference does not validate the foreign-hub segment."
            warning_ja = "米国外のハブを経由する乗り継ぎ旅程です。BTSの日米直行路線参照では国外ハブ区間は検証対象外です。"
    else:
        status = "ROUTE_UNDETERMINED"
        allowed = live_mode is not False
        warning_en = "FlightSmart could not fully validate the returned route path."
        warning_ja = "返された経路をFlightSmartで十分に検証できませんでした。"

    return {
        "route_validation_status": status,
        "route_recommendation_allowed": bool(allowed),
        "route_reference_nonstop_pair": bool(searched_pair_known),
        "route_reference_us_japan_pair": "→".join(out_cross_pair) if out_cross_pair else None,
        "route_validation_warning_en": warning_en,
        "route_validation_warning_ja": warning_ja,
        "route_reference_route_count": len(pairs),
    }


def filter_offers_by_route_reference(offers: list[dict[str, Any]], parse_offer_func) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split raw offers into recommendation-safe and rejected synthetic routes."""
    allowed, rejected = [], []
    for offer in offers:
        facts = parse_offer_func(offer).to_dict()
        route = validate_itinerary_facts(facts)
        (allowed if route["route_recommendation_allowed"] else rejected).append(offer)
    return allowed, rejected
