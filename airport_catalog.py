"""Searchable U.S. airport catalog for FlightSmart.

The catalog is generated from BTS on-time-report airport codes/city names so the
core UI does not depend on OpenFlights reference data.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

CATALOG_FILE = Path(__file__).resolve().parent / "reference" / "us_airports_bts.csv"


def load_us_airports(path: str | Path = CATALOG_FILE) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    df["iata"] = df["iata"].str.upper()
    df["label"] = df["city_name"] + " (" + df["iata"] + ")"
    return df.sort_values(["city_name", "iata"]).reset_index(drop=True)


def airport_options(path: str | Path = CATALOG_FILE) -> dict[str, str]:
    df = load_us_airports(path)
    return dict(zip(df["iata"], df["label"]))
