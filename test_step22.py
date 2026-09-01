from pathlib import Path
import pandas as pd
from route_validation import load_nonstop_route_reference, route_pair_context, validate_itinerary_facts
from itinerary_scoring import evaluate_offers

ROOT=Path(__file__).resolve().parent
PAIRS=load_nonstop_route_reference()
AIRPORTS=pd.read_csv(ROOT/'reference'/'us_airports_bts.csv')
CODE_COL='iata_code' if 'iata_code' in AIRPORTS.columns else ('IATA' if 'IATA' in AIRPORTS.columns else AIRPORTS.columns[0])
CODES=set(AIRPORTS[CODE_COL].dropna().astype(str).str.upper())

def fake_facts(origin,dest='HND',live=False,path=None):
    path=path or [origin,dest]
    return {
        'origin':origin,'destination':dest,'outbound_route_path':path,'return_route_path':None,
        'offer_live_mode':live,'outbound_stop_count':max(0,len(path)-2),
    }

# AGS must never be claimed as a historical nonstop U.S.-Japan pair.
ctx=route_pair_context('AGS','HND')
assert not ctx['is_historical_nonstop_pair']
rv=validate_itinerary_facts(fake_facts('AGS','HND',False))
assert rv['route_validation_status']=='SANDBOX_UNSUPPORTED_DIRECT'
assert rv['route_recommendation_allowed'] is False

# A plausible feeder itinerary through ATL should be valid if ATL-HND is in the reference.
assert ('ATL','HND') in PAIRS
rv2=validate_itinerary_facts(fake_facts('AGS','HND',False,['AGS','ATL','HND']))
assert rv2['route_validation_status']=='CONNECTION_VIA_KNOWN_GATEWAY'
assert rv2['route_recommendation_allowed'] is True

# Exhaustive sanity check across the full BTS U.S. airport catalog for HND/NRT/KIX/NGO:
# a synthetic test-mode one-segment itinerary is allowed iff the pair is in reference.
checked=0
for origin in CODES:
    for dest in ('HND','NRT','KIX','NGO'):
        rv=validate_itinerary_facts(fake_facts(origin,dest,False))
        expected=(origin,dest) in PAIRS
        assert rv['route_recommendation_allowed'] is expected, (origin,dest,rv)
        checked+=1
print(f'Step 22 route QA PASS: {checked} direct-pair checks across {len(CODES)} U.S. airports; {len(PAIRS)} BTS/T-100 reference pairs.')
