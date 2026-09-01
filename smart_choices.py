"""Step 21 traveler-friendly choice groups and diversity selection."""
from __future__ import annotations
import math
import pandas as pd

JP_CODES = {"NH", "JL", "ZG"}
JP_NAMES = ("all nippon", "ana", "japan airlines", "jal", "zipair")


def _num(v, default=0.0):
    try:
        if pd.isna(v): return default
        return float(v)
    except Exception:
        return default


def _confidence_cap(row):
    return _num(row.get("evidence_confidence_cap"), 84.0)


def _profile_score(row, weights):
    values = {
        "historical": row.get("historical_score"),
        "connection": row.get("connection_score"),
        "duration": row.get("duration_score"),
        "price_value": row.get("price_value_score"),
    }
    available=[]
    for k,w in weights.items():
        v=values.get(k)
        if v is not None and not pd.isna(v): available.append((float(v),float(w)))
    if not available: return 0.0
    tw=sum(w for _,w in available)
    raw=sum(v*w for v,w in available)/tw
    return round(min(raw,_confidence_cap(row)),1)


def family_score(row):
    return _profile_score(row,{"historical":.40,"connection":.40,"duration":.12,"price_value":.08})


def is_japanese_transpacific(row) -> bool:
    codes={str(row.get("outbound_international_carrier_code") or "").upper(),str(row.get("return_international_carrier_code") or "").upper(),str(row.get("operating_carrier_code") or "").upper()}
    if codes & JP_CODES: return True
    names=" ".join(str(row.get(k) or "").lower() for k in ["outbound_international_carrier_name","return_international_carrier_name","operating_carrier_name"])
    return any(x in names for x in JP_NAMES)


def preference_match(row, preference: str | None) -> bool:
    pref=(preference or "ANY").upper()
    if pref=="ANY": return True
    codes={str(row.get("outbound_international_carrier_code") or "").upper(),str(row.get("return_international_carrier_code") or "").upper(),str(row.get("operating_carrier_code") or "").upper()}
    if pref=="JP": return bool(codes & JP_CODES) or is_japanese_transpacific(row)
    return pref in codes


def _best(df, key, ascending=False):
    if df.empty: return None
    s=df.sort_values(key,ascending=ascending,na_position="last")
    return s.iloc[0] if not s.empty else None


def build_choice_groups(df: pd.DataFrame, preference: str = "ANY") -> list[dict]:
    """Return distinct, traveler-facing choices; same offer is not repeated unless necessary."""
    if df is None or df.empty: return []
    work=df.copy()
    work["_family_score"]=work.apply(family_score,axis=1)
    work["_pref_match"]=work.apply(lambda r: preference_match(r,preference),axis=1)
    used=set(); choices=[]

    def add(key,label_ja,label_en,row,reason_ja,reason_en):
        if row is None: return
        oid=str(row.get("offer_id") or row.name)
        if oid in used: return
        used.add(oid)
        choices.append({"key":key,"label_ja":label_ja,"label_en":label_en,"row":row,"reason_ja":reason_ja,"reason_en":reason_en})

    preferred=work[work["_pref_match"]] if preference and preference!="ANY" else work.iloc[0:0]
    if not preferred.empty:
        add("preferred","希望航空会社に合う便","Matches your airline preference",_best(preferred,"flightsmart_live_score"),
            "指定した太平洋横断便の航空会社を含む候補の中で、総合評価が高い便です。",
            "Highest overall-rated option among itineraries matching your transpacific-airline preference.")

    add("overall","総合バランス","Best overall balance",_best(work,"flightsmart_live_score"),
        "運航実績・乗り継ぎ・所要時間・料金のバランスが良い候補です。",
        "Balances historical evidence, connections, duration, and price.")
    add("family","家族旅行におすすめ","Best for families",_best(work,"_family_score"),
        "お子様連れを想定し、乗り継ぎの少なさ・しやすさと履歴実績を重視しています。",
        "Prioritizes simpler connections and historical evidence for family travel.")
    add("value","価格と便利さのバランス","Best value",_best(work.assign(_value=work["price_value_score"].fillna(0)*.55+work["connection_score"].fillna(0)*.25+work["duration_score"].fillna(0)*.20),"_value"),
        "安さだけでなく、乗り継ぎと所要時間も含めて価格に見合う候補です。",
        "Looks for value without ignoring connection burden or total duration.")
    add("easy","移動がいちばん楽","Easiest journey",_best(work.assign(_easy=work["connection_score"].fillna(0)*.75+work["duration_score"].fillna(0)*.25),"_easy"),
        "乗り継ぎ回数・乗り継ぎ時間を重視し、移動負担が少ない候補です。",
        "Favors fewer/easier connections and a manageable total journey time.")
    hist=work[work["historical_score"].notna()]
    if not hist.empty:
        add("history","BTS過去実績が強い","Strongest BTS evidence",_best(hist,"historical_score"),
            "今回の候補の中でBTSの過去実績評価が特に強い便です。",
            "Has particularly strong BTS historical evidence among the returned options.")
    jp=work[work.apply(is_japanese_transpacific,axis=1)]
    if not jp.empty:
        add("jp","日本系航空会社の候補","Best Japanese-carrier option",_best(jp,"flightsmart_live_score"),
            "ANA・JAL・ZIPAIRなど、日本系航空会社が太平洋横断区間を運航する候補です。",
            "Best-rated returned itinerary with a Japanese carrier operating a transpacific segment.")

    # If several categories point to the same itinerary, fill the remaining slots
    # with genuinely different returned options rather than showing only one or two cards.
    target=min(6,len(work))
    if len(choices)<target:
        for _,row in diverse_options(work.sort_values("flightsmart_live_score",ascending=False,na_position="last"),limit=target*2).iterrows():
            oid=str(row.get("offer_id") or row.name)
            if oid in used: continue
            add("alternative",f"別の選択肢 {len(choices)+1}",f"Alternative choice {len(choices)+1}",row,
                "上位候補と経路や航空会社が異なるため、比較しやすい別の選択肢として表示しています。",
                "Shown as a different route/carrier alternative so you can compare meaningful choices.")
            if len(choices)>=target: break
    return choices[:6]


def diverse_options(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Avoid showing many near-identical offers before giving the user variety."""
    if df is None or df.empty: return df
    chosen=[]; seen=set()
    for _,r in df.iterrows():
        key=(r.get("outbound_route_path_text") or r.get("outbound_summary"),
             r.get("return_route_path_text") or r.get("return_summary"),
             r.get("outbound_international_carrier_code") or r.get("operating_carrier_code"),
             r.get("return_international_carrier_code"))
        if key in seen: continue
        seen.add(key); chosen.append(r)
        if len(chosen)>=limit: break
    if not chosen: return df.head(limit)
    return pd.DataFrame(chosen).reset_index(drop=True)
