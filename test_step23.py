from duffel_offer_adapter import parse_offer


def carrier(code, name):
    return {"iata_code": code, "name": name}


def place(code, country):
    return {"iata_code": code, "iata_country_code": country}


def seg(o,d,oc,on,mc,mn,dep,arr,dur,flight):
    return {
        "origin": place(o,"JP" if o in {"HND","NRT"} else "US"),
        "destination": place(d,"JP" if d in {"HND","NRT"} else "US"),
        "operating_carrier": carrier(oc,on),
        "marketing_carrier": carrier(mc,mn),
        "marketing_carrier_flight_number": flight,
        "departing_at": dep,
        "arriving_at": arr,
        "duration": dur,
    }

offer={
    "id":"route_card_ags_jal",
    "total_amount":"4200",
    "total_currency":"USD",
    "live_mode":True,
    "slices":[
        {
            "origin":place("AGS","US"),"destination":place("NRT","JP"),"duration":"PT18H",
            "segments":[
                seg("AGS","DFW","AA","American Airlines","AA","American Airlines","2026-10-03T07:00:00","2026-10-03T09:45:00","PT2H45M","1234"),
                seg("DFW","NRT","JL","Japan Airlines","JL","Japan Airlines","2026-10-03T11:45:00","2026-10-04T15:00:00","PT13H15M","11"),
            ]
        },
        {
            "origin":place("NRT","JP"),"destination":place("AGS","US"),"duration":"PT19H",
            "segments":[
                seg("NRT","DFW","JL","Japan Airlines","AA","American Airlines","2026-10-17T18:30:00","2026-10-17T16:00:00","PT11H30M","176"),
                seg("DFW","AGS","AA","American Airlines","AA","American Airlines","2026-10-17T18:00:00","2026-10-17T21:30:00","PT2H30M","5678"),
            ]
        }
    ]
}

f=parse_offer(offer).to_dict()
assert f["outbound_route_path_text"] == "AGS → DFW → NRT"
assert f["return_route_path_text"] == "NRT → DFW → AGS"
assert f["outbound_stop_count"] == 1 and f["return_stop_count"] == 1
assert len(f["outbound_segment_details"]) == 2
assert f["outbound_segment_details"][0]["operating_carrier_code"] == "AA"
assert f["outbound_segment_details"][0]["layover_after_min"] == 120
assert f["outbound_segment_details"][1]["operating_carrier_code"] == "JL"
assert f["outbound_segment_details"][1]["is_us_japan_segment"] is True
assert f["return_segment_details"][0]["operating_carrier_code"] == "JL"
assert f["return_segment_details"][0]["marketing_carrier_code"] == "AA"
print("STEP23_QA_PASS", f["outbound_route_path_text"], f["outbound_international_carrier"], f["return_route_path_text"])
