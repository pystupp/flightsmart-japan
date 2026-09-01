from duffel_offer_adapter import parse_offer
from route_validation import origin_gateway_context
from smart_choices import build_choice_groups, diverse_options, preference_match
from itinerary_scoring import evaluate_offers


def carrier(code,name): return {"iata_code":code,"name":name}
def place(code,country): return {"iata_code":code,"iata_country_code":country}

offer={
 "id":"ags_atl_hnd_dl","total_amount":"1250","total_currency":"USD","live_mode":True,
 "owner":carrier("DL","Delta Air Lines"),
 "slices":[{
   "origin":place("AGS","US"),"destination":place("HND","JP"),"duration":"PT18H",
   "segments":[
     {"origin":place("AGS","US"),"destination":place("ATL","US"),"operating_carrier":carrier("DL","Delta Air Lines"),"marketing_carrier":carrier("DL","Delta Air Lines"),"departing_at":"2026-09-05T08:00:00-04:00","arriving_at":"2026-09-05T09:00:00-04:00"},
     {"origin":place("ATL","US"),"destination":place("HND","JP"),"operating_carrier":carrier("DL","Delta Air Lines"),"marketing_carrier":carrier("DL","Delta Air Lines"),"departing_at":"2026-09-05T11:00:00-04:00","arriving_at":"2026-09-06T14:00:00+09:00"},
   ]
 }]
}

f=parse_offer(offer).to_dict()
assert f["outbound_route_path_text"] == "AGS → ATL → HND", f
assert f["outbound_stop_count"] == 1
assert f["outbound_international_gateway"] == "ATL"
assert f["outbound_international_carrier_code"] == "DL"
assert origin_gateway_context("AGS","HND")["is_historical_us_japan_gateway"] is False

# ANA choice via a U.S. feeder: user preference applies to transpacific segment, not AGS.
ana={
 "id":"ags_iah_nrt_nh","total_amount":"1400","total_currency":"USD","live_mode":True,
 "owner":carrier("UA","United Airlines"),
 "slices":[{
   "origin":place("AGS","US"),"destination":place("NRT","JP"),"duration":"PT20H",
   "segments":[
     {"origin":place("AGS","US"),"destination":place("IAH","US"),"operating_carrier":carrier("UA","United Airlines"),"marketing_carrier":carrier("UA","United Airlines"),"departing_at":"2026-09-05T07:00:00-04:00","arriving_at":"2026-09-05T09:30:00-05:00"},
     {"origin":place("IAH","US"),"destination":place("NRT","JP"),"operating_carrier":carrier("NH","All Nippon Airways"),"marketing_carrier":carrier("UA","United Airlines"),"departing_at":"2026-09-05T11:00:00-05:00","arriving_at":"2026-09-06T15:00:00+09:00"},
   ]
 }]
}
ranked=evaluate_offers([offer,ana],profile_keys=["family","reliability"])
ana_row=ranked[ranked.offer_id=="ags_iah_nrt_nh"].iloc[0]
assert ana_row["outbound_route_path_text"] == "AGS → IAH → NRT"
assert ana_row["outbound_international_carrier_code"] == "NH"
assert preference_match(ana_row,"NH")
assert preference_match(ana_row,"JP")
choices=build_choice_groups(ranked,"NH")
assert any(c["key"]=="preferred" and c["row"]["offer_id"]=="ags_iah_nrt_nh" for c in choices)
diverse=diverse_options(ranked,10)
assert len(diverse)==2
print("STEP21_QA_PASS")
print(ranked[["offer_id","outbound_route_path_text","outbound_international_carrier_code","historical_data_confidence","flightsmart_live_score"]].to_string(index=False))
