from pathlib import Path
import json

from duffel_offer_adapter import extract_offers
from itinerary_scoring import evaluate_offers
from traveler_profiles import PROFILES

HERE = Path(__file__).resolve().parent
payload = json.loads((HERE / "sample_duffel_offers.json").read_text(encoding="utf-8"))
offers = extract_offers(payload)
assert len(offers) == 4

results = {}
for profile in PROFILES:
    ranked = evaluate_offers(offers, profile_key=profile)
    assert len(ranked) == 4
    assert ranked["flightsmart_live_score"].between(0, 100).all()
    assert ranked["rank"].tolist() == [1, 2, 3, 4]
    assert ranked["operating_carrier_name"].notna().all()
    results[profile] = ranked.iloc[0]["offer_id"]

assert results["family"] == "off_demo_atl_dl_direct"
assert results["fewer_connections"] == "off_demo_atl_dl_direct"
print("Step 5 QA PASS")
print(results)
