from pathlib import Path
import json
from airport_catalog import load_us_airports
from duffel_offer_adapter import extract_offers, parse_offer
from itinerary_scoring import evaluate_offers
from travel_calendar import travel_context
from datetime import date

BASE=Path(__file__).resolve().parent

a=load_us_airports(); assert len(a)>=300 and 'ATL' in set(a.iata) and 'AGS' in set(a.iata)
with (BASE/'sample_duffel_offers_roundtrip.json').open(encoding='utf-8') as f: payload=json.load(f)
offers=extract_offers(payload); assert len(offers)==4
facts=parse_offer(offers[0]); assert facts.trip_type=='round_trip' and facts.slice_count==2 and facts.return_duration_min is not None
ranked=evaluate_offers(offers,profile_key='family'); assert not ranked.empty and ranked.iloc[0].operating_carrier_code=='DL'
assert travel_context(date(2026,12,29))
assert travel_context(date(2026,5,3))
print('STEP6_QA_PASS')
print('airports',len(a),'offers',len(ranked),'family_winner',ranked.iloc[0].operating_carrier_name)
