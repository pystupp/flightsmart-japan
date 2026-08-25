"""Duffel v2 flight search client for FlightSmart."""
from __future__ import annotations
import os
from datetime import date
import requests

BASE_URL = "https://api.duffel.com"


def create_offer_request(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    passenger_ages: list[int] | None = None,
    adults: int = 1,
    cabin_class: str = "economy",
    max_connections: int = 1,
    token: str | None = None,
    timeout_seconds: int = 35,
) -> dict:
    access_token = token or os.getenv("DUFFEL_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("DUFFEL_ACCESS_TOKEN is not configured")
    if cabin_class not in {"economy", "premium_economy", "business", "first"}:
        raise ValueError("Unsupported cabin class")
    if max_connections not in {0, 1, 2}:
        raise ValueError("max_connections must be 0, 1, or 2")

    try:
        outbound = date.fromisoformat(departure_date)
        inbound = date.fromisoformat(return_date) if return_date else None
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD") from exc
    if inbound and inbound <= outbound:
        raise ValueError("Return date must be after departure date")

    if passenger_ages is None:
        if adults < 1:
            raise ValueError("At least one adult passenger is required")
        passengers = [{"type": "adult"} for _ in range(adults)]
    else:
        ages = [int(a) for a in passenger_ages]
        if not ages or not any(a >= 18 for a in ages):
            raise ValueError("At least one passenger age 18+ is required")
        if any(a < 0 or a > 120 for a in ages):
            raise ValueError("Passenger ages must be between 0 and 120")
        # Duffel recommends age-based search passengers to reduce passenger-type mismatches.
        passengers = [{"age": a} for a in ages]

    slices = [{"origin": origin.strip().upper(), "destination": destination.strip().upper(), "departure_date": departure_date}]
    if return_date:
        slices.append({"origin": destination.strip().upper(), "destination": origin.strip().upper(), "departure_date": return_date})

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Duffel-Version": "v2",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
    }
    body = {"data": {"slices": slices, "passengers": passengers, "cabin_class": cabin_class, "max_connections": max_connections}}
    response = requests.post(
        f"{BASE_URL}/air/offer_requests",
        params={"return_offers": "true", "supplier_timeout": 20000, "view": "offers"},
        headers=headers,
        json=body,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response.json()
