"""Parse Duffel-style offers into stable FlightSmart itinerary facts."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import re

JP_AIRPORTS = {"HND", "NRT", "KIX", "NGO", "FUK", "CTS", "OKA", "ITM"}


def _iata(place: Any) -> str | None:
    if isinstance(place, str): return place.upper()
    if isinstance(place, dict):
        code = place.get("iata_code") or place.get("iata")
        return str(code).upper() if code else None
    return None


def _country(place: Any) -> str | None:
    if isinstance(place, dict):
        value = place.get("iata_country_code") or place.get("country_code")
        return str(value).upper() if value else None
    return None


def _carrier(carrier: Any) -> tuple[str | None, str | None]:
    if not isinstance(carrier, dict): return None, None
    code = carrier.get("iata_code") or carrier.get("iata")
    return (str(code).upper() if code else None, str(carrier.get("name")) if carrier.get("name") else None)


def parse_iso_duration_minutes(value: str | None) -> int | None:
    if not value: return None
    m = re.fullmatch(r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?", value)
    if not m: return None
    return int(m.group("days") or 0)*1440 + int(m.group("hours") or 0)*60 + int(m.group("minutes") or 0) + round(int(m.group("seconds") or 0)/60)


def _parse_dt(value: str | None) -> datetime | None:
    if not value: return None
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None


def _slice_duration(sl: dict) -> int | None:
    duration = parse_iso_duration_minutes(sl.get("duration"))
    segs = sl.get("segments") or []
    if duration is None and segs:
        start, end = _parse_dt(segs[0].get("departing_at")), _parse_dt(segs[-1].get("arriving_at"))
        if start and end:
            try: duration = int((end-start).total_seconds()//60)
            except TypeError: pass
    return duration


def _connections(segs: list[dict]) -> list[int]:
    out=[]
    for a,b in zip(segs,segs[1:]):
        arr, dep = _parse_dt(a.get("arriving_at")), _parse_dt(b.get("departing_at"))
        if arr and dep:
            try: mins=int((dep-arr).total_seconds()//60)
            except TypeError: continue
            if mins >= 0: out.append(mins)
    return out


def _seg_summary(sl: dict) -> str:
    labels=[]
    for seg in sl.get("segments") or []:
        o,d=_iata(seg.get("origin")),_iata(seg.get("destination")); c,_=_carrier(seg.get("operating_carrier"))
        labels.append(f"{o or '?'}-{d or '?'} {c or ''}".strip())
    return " | ".join(labels)


@dataclass
class LiveItineraryFacts:
    offer_id: str | None
    expires_at: str | None
    offer_minutes_remaining: int | None
    total_amount: float | None
    total_currency: str | None
    origin: str | None
    destination: str | None
    trip_type: str
    slice_count: int
    segment_count: int
    stop_count: int
    outbound_stop_count: int
    return_stop_count: int | None
    total_duration_min: int | None
    outbound_duration_min: int | None
    return_duration_min: int | None
    international_gateway: str | None
    japan_arrival_airport: str | None
    operating_carrier_code: str | None
    operating_carrier_name: str | None
    marketing_carrier_code: str | None
    marketing_carrier_name: str | None
    international_departure_at: str | None
    international_arrival_at: str | None
    connection_minutes: list[int]
    segment_summary: str
    outbound_summary: str
    return_summary: str | None

    def to_dict(self): return asdict(self)


def parse_offer(offer: dict[str, Any]) -> LiveItineraryFacts:
    slices=offer.get("slices") or []
    outbound=None
    for sl in slices:
        if _iata(sl.get("destination")) in JP_AIRPORTS or _country(sl.get("destination"))=="JP": outbound=sl; break
    if outbound is None and slices: outbound=slices[0]
    outbound=outbound or {}
    outbound_index = slices.index(outbound) if outbound in slices else 0
    inbound = next((sl for i,sl in enumerate(slices) if i != outbound_index), None)

    out_segments=outbound.get("segments") or []
    all_segments=[seg for sl in slices for seg in (sl.get("segments") or [])]
    intl_seg=None
    for seg in out_segments:
        if _iata(seg.get("destination")) in JP_AIRPORTS or _country(seg.get("destination"))=="JP": intl_seg=seg; break
    if intl_seg is None and out_segments: intl_seg=out_segments[-1]
    intl_seg=intl_seg or {}
    op_code,op_name=_carrier(intl_seg.get("operating_carrier")); mk_code,mk_name=_carrier(intl_seg.get("marketing_carrier"))

    out_duration=_slice_duration(outbound)
    ret_duration=_slice_duration(inbound) if inbound else None
    durations=[x for x in [out_duration,ret_duration] if x is not None]
    total_duration=sum(durations) if durations else None
    layovers=[]
    for sl in slices: layovers.extend(_connections(sl.get("segments") or []))
    stop_counts=[max(0,len(sl.get("segments") or [])-1) for sl in slices]

    amount=offer.get("total_amount")
    try: amount_num=float(amount) if amount is not None else None
    except (TypeError,ValueError): amount_num=None

    expires=offer.get("expires_at")
    remaining=None
    exp_dt=_parse_dt(expires)
    if exp_dt:
        now=datetime.now(timezone.utc)
        if exp_dt.tzinfo is None: exp_dt=exp_dt.replace(tzinfo=timezone.utc)
        remaining=max(0,int((exp_dt-now).total_seconds()//60))

    out_summary=_seg_summary(outbound)
    ret_summary=_seg_summary(inbound) if inbound else None
    combined = f"OUT: {out_summary}" + (f" || RETURN: {ret_summary}" if ret_summary else "")
    return LiveItineraryFacts(
        offer_id=offer.get("id"), expires_at=expires, offer_minutes_remaining=remaining,
        total_amount=amount_num,total_currency=offer.get("total_currency"),
        origin=_iata(outbound.get("origin")) or (_iata(out_segments[0].get("origin")) if out_segments else None),
        destination=_iata(outbound.get("destination")) or (_iata(out_segments[-1].get("destination")) if out_segments else None),
        trip_type="round_trip" if len(slices)>=2 else "one_way", slice_count=len(slices), segment_count=len(all_segments),
        stop_count=sum(stop_counts), outbound_stop_count=stop_counts[outbound_index] if stop_counts else 0,
        return_stop_count=(stop_counts[1-outbound_index] if len(stop_counts)==2 else (sum(stop_counts)-stop_counts[outbound_index] if len(stop_counts)>1 else None)),
        total_duration_min=total_duration,outbound_duration_min=out_duration,return_duration_min=ret_duration,
        international_gateway=_iata(intl_seg.get("origin")),japan_arrival_airport=_iata(intl_seg.get("destination")),
        operating_carrier_code=op_code,operating_carrier_name=op_name,marketing_carrier_code=mk_code,marketing_carrier_name=mk_name,
        international_departure_at=intl_seg.get("departing_at"),international_arrival_at=intl_seg.get("arriving_at"),
        connection_minutes=layovers,segment_summary=combined,outbound_summary=out_summary,return_summary=ret_summary,
    )


def extract_offers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data=payload.get("data",payload)
    if isinstance(data,list): return data
    if isinstance(data,dict):
        if isinstance(data.get("offers"),list): return data["offers"]
        if isinstance(data.get("data"),list): return data["data"]
    if isinstance(payload.get("offers"),list): return payload["offers"]
    return []
