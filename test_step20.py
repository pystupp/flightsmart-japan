from duffel_offer_adapter import parse_offer
from airline_coverage import summarize_airline_coverage


def carrier(code, name):
    return {"iata_code": code, "name": name}


def airport(code, country):
    return {"iata_code": code, "iata_country_code": country}


def segment(o, oc, d, dc, code, name):
    c=carrier(code,name)
    return {"origin": airport(o,oc), "destination": airport(d,dc), "operating_carrier": c, "marketing_carrier": c}


offer={
    "id":"off_test", "total_amount":"5000", "total_currency":"USD", "live_mode":False,
    "owner": carrier("UA","United Airlines"),
    "slices":[
        {"origin":airport("CLT","US"),"destination":airport("NRT","JP"),"segments":[
            segment("CLT","US","IAH","US","UA","United Airlines"),
            segment("IAH","US","NRT","JP","UA","United Airlines")], "duration":"PT18H"},
        {"origin":airport("NRT","JP"),"destination":airport("CLT","US"),"segments":[
            segment("NRT","JP","ORD","US","NH","All Nippon Airways"),
            segment("ORD","US","CLT","US","UA","United Airlines")], "duration":"PT17H"}
    ]
}
f=parse_offer(offer).to_dict()
assert f["outbound_international_carrier_code"] == "UA"
assert f["return_international_carrier_code"] == "NH"
assert "All Nippon Airways" in f["return_international_carrier"]
c=summarize_airline_coverage([offer])
assert c["japanese_status"]["NH"]["present"] is True
assert c["japanese_status"]["JL"]["present"] is False
assert any("All Nippon Airways" in k for k in c["transpacific_counts"])
print("Step 20 Japanese-carrier validation — PASS")
