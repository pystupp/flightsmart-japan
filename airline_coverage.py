"""Airline-coverage diagnostics for FlightSmart live searches."""
from __future__ import annotations
from collections import Counter
from typing import Any
from duffel_offer_adapter import parse_offer

JAPAN_CARRIER_CODES = {"NH": "ANA", "JL": "Japan Airlines", "ZG": "ZIPAIR"}


def summarize_airline_coverage(offers: list[dict[str, Any]]) -> dict[str, Any]:
    facts = [parse_offer(o).to_dict() for o in offers]
    operating = Counter()
    marketing = Counter()
    owners = Counter()
    live_flags = []
    for f in facts:
        op = f.get("operating_carrier_name") or f.get("operating_carrier_code") or "Unknown"
        mk = f.get("marketing_carrier_name") or f.get("marketing_carrier_code") or "Unknown"
        owner = f.get("offer_owner_name") or f.get("offer_owner_code") or "Unknown"
        operating[op] += 1
        marketing[mk] += 1
        owners[owner] += 1
        if f.get("offer_live_mode") is not None:
            live_flags.append(bool(f.get("offer_live_mode")))

    present_codes = {str(f.get("operating_carrier_code") or "").upper() for f in facts}
    present_codes |= {str(f.get("marketing_carrier_code") or "").upper() for f in facts}
    japanese_status = {
        code: {"label": label, "present": code in present_codes}
        for code, label in JAPAN_CARRIER_CODES.items()
    }
    is_test_mode = bool(live_flags) and not any(live_flags)
    if not live_flags:
        # Duffel Airways is a strong test-mode signal even if live_mode is absent.
        is_test_mode = any(
            (f.get("offer_owner_code") == "ZZ") or
            (str(f.get("offer_owner_name") or "").lower() == "duffel airways") or
            (f.get("operating_carrier_code") == "ZZ")
            for f in facts
        )
    return {
        "offer_count": len(offers),
        "is_test_mode": is_test_mode,
        "operating_counts": dict(operating.most_common()),
        "marketing_counts": dict(marketing.most_common()),
        "owner_counts": dict(owners.most_common()),
        "japanese_status": japanese_status,
    }
