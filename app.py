from __future__ import annotations

import base64
import json
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from airport_catalog import airport_options
from duffel_client import create_offer_request
from duffel_offer_adapter import extract_offers, parse_offer
from airline_coverage import summarize_airline_coverage
from itinerary_scoring import evaluate_offers
from traveler_profiles import DEFAULT_PROFILE, PROFILES
from travel_calendar import travel_context, highest_level
from route_validation import origin_gateway_context, route_pair_context, validate_itinerary_facts
from smart_choices import build_choice_groups, diverse_options, preference_match

APP_DIR = Path(__file__).resolve().parent
DEMO_ONEWAY = APP_DIR / "sample_duffel_offers.json"
DEMO_ROUNDTRIP = APP_DIR / "sample_duffel_offers_roundtrip.json"
JAPAN_AIRPORTS = {
    "HND": "Tokyo Haneda (HND)", "NRT": "Tokyo Narita (NRT)", "KIX": "Osaka Kansai (KIX)",
    "NGO": "Nagoya Chubu (NGO)", "FUK": "Fukuoka (FUK)",
}
CABINS = {
    "economy": ("エコノミー", "Economy"), "premium_economy": ("プレミアムエコノミー", "Premium Economy"),
    "business": ("ビジネス", "Business"), "first": ("ファースト", "First"),
}
TRANS_PACIFIC_PREFS = {
    "ANY": ("指定なし", "Any transpacific airline"),
    "JP": ("日本系航空会社を希望", "Prefer a Japanese carrier"),
    "NH": ("ANAを希望", "Prefer ANA"),
    "JL": ("JALを希望", "Prefer Japan Airlines"),
    "ZG": ("ZIPAIRを希望", "Prefer ZIPAIR"),
}
PRIORITY_KEYS = ["family", "fewer_connections", "reliability", "lowest_price", "shortest_time"]

st.set_page_config(page_title="FlightSmart Japan", page_icon="✈️", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1320px; padding-top: 1.1rem; padding-bottom: 3rem;}
[data-testid="stMetric"] {background: rgba(127,127,127,.06); border-radius: 14px; padding: .65rem .8rem;}
[data-testid="stSidebar"] {min-width: 320px;}
.fs-hero {padding: 2.15rem 1.8rem; border: 1px solid #dfe7ef; border-radius: 22px; margin-bottom: 1.1rem; background-size: cover; background-position: center 54%; box-shadow:0 8px 28px rgba(20,54,90,.10); position:relative; overflow:hidden;}\n.fs-hero::before {content:""; position:absolute; inset:0; background:linear-gradient(90deg,rgba(255,255,255,.94) 0%,rgba(255,255,255,.82) 52%,rgba(255,255,255,.40) 100%);}\n.fs-hero > * {position:relative; z-index:1;}\n.fs-hero .fs-kicker {display:inline-block; background:rgba(255,255,255,.74); padding:.22rem .58rem; border-radius:999px;}\n.fs-hero .fs-sub {max-width:820px;}
.fs-kicker {font-size:.86rem; opacity:.75; letter-spacing:.04em; text-transform:uppercase;}
.fs-title {font-size:2.15rem; font-weight:800; margin:.15rem 0 .35rem 0; color:#102a43;}
.fs-sub {opacity:.82; line-height:1.55;}
.fs-story {padding:1.15rem 1.35rem; border-left:4px solid #2f80ed; border-radius:14px; background:#f8fbff; margin:-.25rem 0 1rem; line-height:1.75;}
.fs-story-title {font-size:1.05rem; font-weight:800; color:#102a43; margin-bottom:.35rem;}
.fs-story-en {font-size:.88rem; color:#64748b; margin-top:.65rem; line-height:1.6;}
@media (max-width: 700px) {
  .block-container {padding-left: .75rem; padding-right: .75rem;}
  .fs-title {font-size:1.55rem;}
  [data-testid="column"] {min-width: 100% !important;}
}

.fs-search {border:1px solid #dfe7ef; border-radius:20px; padding:1rem 1.15rem .35rem; background:white; box-shadow:0 8px 26px rgba(20,54,90,.06); margin:.8rem 0 1.2rem;}
.fs-section-title {font-size:1.35rem; font-weight:800; color:#102a43; margin:.35rem 0 .2rem;}
.fs-section-sub {color:#64748b; margin-bottom:.75rem;}
.fs-reco {border:2px solid #2f80ed; border-radius:20px; padding:1.15rem 1.25rem; background:#f7fbff; margin:.75rem 0 1rem;}
.fs-pill {display:inline-block; padding:.28rem .62rem; border-radius:999px; background:#eef6ff; color:#1769c2; font-size:.82rem; font-weight:700; margin-right:.35rem;}
.fs-ja {font-weight:750;} .fs-en {font-size:.82rem; color:#718096; margin-top:.08rem;}
[data-testid="stForm"] {border:0; padding:0;}
div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] button {border-radius:12px; min-height:3rem; font-weight:750;}
[data-testid="stDataFrame"] {border-radius:14px; overflow:hidden;}
</style>
""", unsafe_allow_html=True)


def tr(ja: str, en: str, lang: str) -> str:
    return ja if lang == "日本語" else en


def get_duffel_token() -> str | None:
    token = os.getenv("DUFFEL_ACCESS_TOKEN")
    if token: return token
    try: return st.secrets.get("DUFFEL_ACCESS_TOKEN")
    except Exception: return None


def money(currency, amount) -> str:
    if pd.isna(amount): return "—"
    try: return f"{currency or ''} {float(amount):,.0f}".strip()
    except Exception: return f"{currency or ''} {amount}".strip()


def duration_label(minutes, lang: str) -> str:
    if pd.isna(minutes): return "—"
    h, rem = divmod(int(minutes), 60)
    return f"{h}時間{rem}分" if lang == "日本語" else f"{h}h {rem}m"


def confidence_label(value: str, lang: str) -> str:
    mapping_ja={"VERY_HIGH":"非常に高い","HIGH":"高い","MEDIUM":"中程度","LOW":"低い","LIMITED":"限定的","UNAVAILABLE":"データなし"}
    return mapping_ja.get(str(value),str(value)) if lang=="日本語" else str(value).replace("_"," ").title()


def evidence_strength_label(score_value, lang: str, *, kind: str = "general", raw_value=None) -> str:
    """Convert existing evidence into an easy-to-read category without inventing a new numeric score."""
    if score_value is not None and not pd.isna(score_value):
        score = float(score_value)
        if score >= 80:
            return tr("🟢 良好", "🟢 Strong", lang)
        if score >= 60:
            return tr("🔵 参考になる", "🔵 Useful", lang)
        if score >= 40:
            return tr("🟡 中程度", "🟡 Moderate", lang)
        return tr("⚪ 限定的", "⚪ Limited", lang)

    # Descriptive BTS records are still useful even when they are not individually scored.
    if kind == "service" and raw_value is not None and not pd.isna(raw_value):
        months = int(raw_value)
        if months >= 5:
            return tr("✓ 継続実績あり", "✓ Consistent record", lang)
        if months >= 3:
            return tr("◯ 複数月の実績", "◯ Multi-month record", lang)
        return tr("△ 限定的な実績", "△ Limited record", lang)
    if kind == "passengers" and raw_value is not None and not pd.isna(raw_value):
        passengers = int(raw_value)
        if passengers >= 25000:
            return tr("✓ 十分な実績データ", "✓ Substantial record", lang)
        if passengers >= 10000:
            return tr("◯ 一定の実績データ", "◯ Meaningful record", lang)
        return tr("△ 参考データ", "△ Context only", lang)
    return tr("参考データ", "Context", lang)


def historical_evidence_table(row: pd.Series, lang: str) -> pd.DataFrame:
    """Build a traveler-facing BTS table that separates scored and descriptive evidence."""
    rows = []

    def add(ja_label: str, en_label: str, value: str, score_value=None, *, kind: str = "general", raw_value=None):
        rows.append({
            tr("BTSの過去データ", "BTS historical evidence", lang): tr(ja_label, en_label, lang),
            tr("確認できた実績", "Observed record", lang): value,
            tr("評価", "Evidence strength", lang): evidence_strength_label(score_value, lang, kind=kind, raw_value=raw_value),
        })

    months = row.get("historical_months_reported")
    if pd.notna(months) and months is not None:
        add("日米路線の継続運航", "U.S.–Japan service consistency",
            tr(f"{int(months)}か月分の運航実績", f"{int(months)} reported months of service", lang),
            row.get("historical_service_consistency_score"), kind="service", raw_value=months)

    passengers = row.get("historical_passengers")
    if pd.notna(passengers) and passengers is not None:
        add("日米路線の旅客実績", "U.S.–Japan passenger evidence",
            tr(f"過去データ旅客数 {int(passengers):,}人", f"{int(passengers):,} passengers in the historical data", lang),
            row.get("historical_passenger_evidence_score"), kind="passengers", raw_value=passengers)

    dep = row.get("historical_on_time_departure_pct")
    canc = row.get("historical_gateway_cancellation_pct")
    if pd.notna(dep) and dep is not None:
        val = tr(f"定時出発 {float(dep):.1f}%", f"{float(dep):.1f}% on-time departures", lang)
        if pd.notna(canc) and canc is not None:
            val += tr(f"・欠航 {float(canc):.1f}%", f" · {float(canc):.1f}% cancellations", lang)
        add("米国ゲートウェイ空港の実績", "U.S. gateway operating record", val, row.get("historical_gateway_score"))

    arr = row.get("historical_on_time_arrival_pct")
    ccanc = row.get("historical_carrier_cancellation_pct")
    if pd.notna(arr) and arr is not None:
        val = tr(f"航空会社の定時到着 {float(arr):.1f}%", f"Carrier on-time arrivals {float(arr):.1f}%", lang)
        if pd.notna(ccanc) and ccanc is not None:
            val += tr(f"・欠航 {float(ccanc):.1f}%", f" · {float(ccanc):.1f}% cancellations", lang)
        add("航空会社の定時運航実績", "Carrier on-time operating record", val, row.get("historical_carrier_score"))

    rank = row.get("historical_airport_rank_2025")
    ontime25 = row.get("historical_airport_ontime_pct_2025")
    if (pd.notna(rank) and rank is not None) or (pd.notna(ontime25) and ontime25 is not None):
        parts=[]
        if pd.notna(rank) and rank is not None:
            parts.append(tr(f"2025主要空港順位 #{int(rank)}", f"2025 major-airport rank #{int(rank)}", lang))
        if pd.notna(ontime25) and ontime25 is not None:
            parts.append(tr(f"定時到着 {float(ontime25):.1f}%", f"{float(ontime25):.1f}% on-time arrivals", lang))
        add("2025年空港パフォーマンス", "2025 airport performance context", " · ".join(parts), row.get("historical_airport_2025_score"))

    chronic = row.get("historical_chronic_risk_score")
    if pd.notna(chronic) and chronic is not None:
        add("慢性的な遅延シグナル", "Chronic-delay signal",
            tr("BTSの慢性的遅延記録をもとにした比較指標", "Comparison signal based on BTS chronic-delay records", lang), chronic)

    return pd.DataFrame(rows)


def show_historical_evidence(row: pd.Series, lang: str, expanded: bool = False) -> None:
    hist = row.get("historical_score")
    if pd.isna(hist) or hist is None:
        st.caption(tr("この候補には一致するBTS履歴実績がないため、履歴評価は表示しません。",
                      "No matched BTS historical evidence is available for this offer, so no historical rating is shown.", lang))
        return

    carrier = row.get("historical_carrier_name") or row.get("historical_carrier_code") or "—"
    gateway = row.get("international_gateway") or "?"
    dest = row.get("japan_arrival_airport") or row.get("destination") or "?"
    confidence = confidence_label(row.get("historical_data_confidence", "UNAVAILABLE"), lang)
    match_type = str(row.get("historical_match_type") or "")

    if match_type == "MARKET_MEDIAN_FALLBACK":
        st.markdown(tr(
            f"**BTS履歴評価：{float(hist):.1f}/100（市場参考値）** — {gateway}→{dest} の過去市場データを参照",
            f"**BTS historical rating: {float(hist):.1f}/100 (market context)** — based on past {gateway}→{dest} market data", lang))
        st.warning(tr(
            "この航空会社に一致するBTS航空会社別データがないため、同じ日米市場の中央値を参考情報として表示しています。航空会社固有の実績としては扱っていません。",
            "Carrier-specific BTS evidence was not matched. This uses the median for the same U.S.–Japan market as context and is not presented as that carrier's own record.", lang))
    else:
        st.markdown(tr(
            f"**BTS履歴評価：{float(hist):.1f}/100** — {carrier} / {gateway}→{dest} の過去運航実績を照合",
            f"**BTS historical rating: {float(hist):.1f}/100** — matched to past operating evidence for {carrier} / {gateway}→{dest}", lang))

    st.caption(tr(f"データ信頼度：{confidence}", f"Data confidence: {confidence}", lang))
    table = historical_evidence_table(row, lang)
    if not table.empty:
        st.dataframe(table, hide_index=True, use_container_width=True)

    reason = row.get("historical_reason_ja" if lang=="日本語" else "historical_reason_en")
    if isinstance(reason, str) and reason:
        st.markdown(tr("**この評価の主な根拠**", "**Why this rating**", lang))
        st.caption(reason)

    st.caption(tr(
        "※ 81.1などの履歴評価は、利用可能なBTS指標を組み合わせた比較用スコアです。個別に数値化する根拠が弱い項目は、無理に0〜100点へ変換せず『評価』として表示します。欠けている指標は減点用の0点として扱いません。",
        "Historical ratings such as 81.1 combine the BTS indicators that are actually available. Evidence that is not defensibly numeric is shown as a category instead of forcing it into a 0–100 score. Missing indicators are not treated as zero-point penalties.", lang))
    st.caption(tr("※ 過去の運航実績は将来の遅延を予測するものではなく、候補便を比較するための参考根拠です。",
                  "Historical operating records do not predict a future delay; they are supporting evidence for comparing current offers.", lang))

def priority_selector(lang: str) -> list[str]:
    label_key="label_ja" if lang=="日本語" else "label_en"
    selected=st.multiselect(
        tr("大切にしたいこと（複数選択可）","What matters to you? Choose more than one",lang),
        PRIORITY_KEYS,
        default=[],
        format_func=lambda k: PROFILES[k][label_key],
        max_selections=3,
        placeholder=tr("選択なし＝総合バランス","No selection = balanced overall",lang),
    )
    if selected:
        labels=" + ".join(PROFILES[k][label_key] for k in selected)
        st.caption(tr(f"選択した条件を組み合わせて評価します：{labels}",f"FlightSmart combines these priorities: {labels}",lang))
    else:
        st.caption(tr("選択しない場合は、運航実績・乗り継ぎ・時間・料金を総合的に評価します。","With no selections, FlightSmart uses a balanced overall comparison.",lang))
    return selected


def profile_selector(lang: str) -> str:
    # Backward-compatible helper used by older tests/components.
    keys=list(PROFILES); label_key="label_ja" if lang=="日本語" else "label_en"
    return st.selectbox(tr("今回の旅行で一番大切なことは？","What matters most for this trip?",lang),keys,index=keys.index(DEFAULT_PROFILE),format_func=lambda k:PROFILES[k][label_key])


def load_demo_payload(round_trip: bool) -> dict:
    with (DEMO_ROUNDTRIP if round_trip else DEMO_ONEWAY).open("r",encoding="utf-8") as f: return json.load(f)


def show_travel_context(d: date, lang: str, title: str) -> None:
    events=travel_context(d)
    if not events: return
    level=highest_level(events); icon="🔴" if level=="HIGH" else "🟠"
    labels=" / ".join(e["label_ja" if lang=="日本語" else "label_en"] for e in events)
    st.warning(f"{icon} **{title}:** {labels}")



def _fmt_clock(value: str | None) -> str:
    if not value:
        return "—"
    try:
        # Keep local clock represented in the Duffel timestamp; do not relabel timezone.
        return str(value).replace("T", " ")[:16]
    except Exception:
        return str(value)


def _segment_carrier_text(seg: dict, lang: str) -> tuple[str, str | None]:
    op_name = seg.get("operating_carrier_name") or seg.get("operating_carrier_code") or "—"
    op_code = seg.get("operating_carrier_code") or ""
    mk_name = seg.get("marketing_carrier_name") or seg.get("marketing_carrier_code")
    mk_code = seg.get("marketing_carrier_code") or ""
    flight = seg.get("flight_number")
    operating = f"{op_name}" + (f" ({op_code})" if op_code and op_code not in str(op_name) else "")
    if flight:
        display_code = mk_code or op_code
        operating += f" · {display_code}{flight}" if display_code else f" · {flight}"
    marketing = None
    if mk_name and (mk_code != op_code or str(mk_name).lower() != str(op_name).lower()):
        marketing = tr(f"販売: {mk_name}" + (f" ({mk_code})" if mk_code else ""),
                       f"Marketed by {mk_name}" + (f" ({mk_code})" if mk_code else ""), lang)
    return operating, marketing


def render_journey_segments(row: pd.Series, lang: str, direction: str) -> None:
    details = row.get(f"{direction}_segment_details") or []
    route_text = row.get(f"{direction}_route_path_text") or "—"
    stops = int(row.get(f"{direction}_stop_count") or 0)
    duration = duration_label(row.get(f"{direction}_duration_min"), lang)
    title = tr("往路", "Outbound", lang) if direction == "outbound" else tr("復路", "Return", lang)
    stop_text = tr("直行", "Nonstop", lang) if stops == 0 else tr(f"乗り継ぎ {stops}回", f"{stops} stop" + ("s" if stops != 1 else ""), lang)
    st.markdown(f"**{title}: {route_text}**  ·  **{stop_text}**  ·  {duration}")
    if not details:
        return
    for idx, seg in enumerate(details):
        op_text, marketing = _segment_carrier_text(seg, lang)
        is_tp = bool(seg.get("is_us_japan_segment"))
        prefix = "🇯🇵 **" + tr("日本行きの主区間", "Main Japan international segment", lang) + "** · " if is_tp else ""
        route = f"{seg.get('origin') or '?'} → {seg.get('destination') or '?'}"
        st.markdown(f"{prefix}**{route}** — {op_text}")
        meta=[]
        if marketing:
            meta.append(marketing)
        if seg.get("departing_at") and seg.get("arriving_at"):
            meta.append(f"{_fmt_clock(seg.get('departing_at'))} → {_fmt_clock(seg.get('arriving_at'))}")
        if seg.get("duration_min") is not None:
            meta.append(duration_label(seg.get("duration_min"), lang))
        if meta:
            st.caption(" · ".join(meta))
        lay = seg.get("layover_after_min")
        if lay is not None and idx < len(details)-1:
            conn_airport = seg.get("destination") or "?"
            st.caption(tr(f"↳ {conn_airport}で乗り継ぎ {duration_label(lay, lang)}",
                          f"↳ Connect at {conn_airport}: {duration_label(lay, lang)}", lang))


def render_route_reconstruction(row: pd.Series, lang: str) -> None:
    st.markdown(tr("#### 実際の旅程", "#### Actual itinerary", lang))
    render_journey_segments(row, lang, "outbound")
    if row.get("return_segment_details"):
        st.markdown("---")
        render_journey_segments(row, lang, "return")

def result_card(row: pd.Series, lang: str, is_top: bool=False) -> None:
    carrier=row.get("operating_carrier_name") or row.get("operating_carrier_code") or "—"; score=float(row["flightsmart_live_score"])
    rank_value=row.get("rank")
    is_ranked=bool(row.get("is_ranked_choice", True)) and pd.notna(rank_value)
    with st.container(border=True):
        if is_ranked:
            rank=int(rank_value)
            hist=row.get("historical_score")
            hist_txt="—" if pd.isna(hist) else f"{float(hist):.1f}/100"
            st.subheader(tr(
                f"{'🏆 ' if is_top else ''}BTS過去実績 #{rank}　{carrier} — {hist_txt}",
                f"{'🏆 ' if is_top else ''}BTS past-record rank #{rank}  {carrier} — {hist_txt}", lang))
            st.caption(tr(
                f"FlightSmart総合比較スコア：{score:.1f}/100（料金・時間・乗り継ぎを含む）",
                f"FlightSmart overall comparison score: {score:.1f}/100 (includes price, duration, and connections)", lang))
        else:
            st.subheader(f"⚠️ {carrier} — {tr('参考候補','Reference option',lang)}")
            st.warning(tr(
                "BTSの航空会社別履歴データが不足している、または信頼度が低いため、番号付きの過去実績ランキングには含めていません。料金・所要時間・乗り継ぎは参考として比較できます。",
                "Carrier-specific BTS history is unavailable or not reliable enough for a numbered past-record rank. Price, duration, and connections are still shown for reference.", lang))
        st.markdown(f"**{tr('運航航空会社','Operating carrier',lang)}:** {carrier}")
        out_intl=row.get("outbound_international_carrier")
        ret_intl=row.get("return_international_carrier")
        if out_intl or ret_intl:
            parts=[]
            if out_intl: parts.append(tr(f"往路の日米区間: {out_intl}", f"Outbound transpacific: {out_intl}", lang))
            if ret_intl: parts.append(tr(f"復路の日米区間: {ret_intl}", f"Return transpacific: {ret_intl}", lang))
            st.info("  ·  ".join(parts))
        marketing=row.get("marketing_carrier_name") or row.get("marketing_carrier_code")
        if marketing and str(marketing) != str(carrier):
            st.caption(f"{tr('販売航空会社','Marketing carrier',lang)}: {marketing}")
        render_route_reconstruction(row, lang)
        route_note=row.get("route_validation_warning_ja" if lang=="日本語" else "route_validation_warning_en")
        route_status=row.get("route_validation_status")
        if isinstance(route_note,str) and route_note:
            if route_status in {"LIVE_UNCONFIRMED_DIRECT","CONNECTION_WITH_UNCONFIRMED_US_JP_SEGMENT","ROUTE_UNDETERMINED"}:
                st.warning(route_note)
            else:
                st.caption(route_note)

        c1,c2,c3,c4=st.columns(4)
        c1.metric(tr("料金","Price",lang),money(row.get("total_currency"),row.get("total_amount")))
        c2.metric(tr("合計乗り継ぎ","Total connections",lang),int(row.get("stop_count",0)))
        c3.metric(tr("合計飛行旅程時間","Total itinerary duration",lang),duration_label(row.get("total_duration_min"),lang))
        c4.metric(tr("BTSデータ信頼度","BTS evidence confidence",lang),confidence_label(row.get("historical_data_confidence"),lang))
        if row.get("trip_type")=="round_trip":
            st.caption(tr(
                f"往路：乗り継ぎ{int(row.get('outbound_stop_count',0))}回・{duration_label(row.get('outbound_duration_min'),lang)} / 復路：乗り継ぎ{int(row.get('return_stop_count') or 0)}回・{duration_label(row.get('return_duration_min'),lang)}",
                f"Outbound: {int(row.get('outbound_stop_count',0))} connection(s), {duration_label(row.get('outbound_duration_min'),lang)} / Return: {int(row.get('return_stop_count') or 0)} connection(s), {duration_label(row.get('return_duration_min'),lang)}",lang))
        remaining=row.get("offer_minutes_remaining")
        if pd.notna(remaining) and remaining is not None:
            if int(remaining)<=5: st.error(tr(f"このオファーは約{int(remaining)}分で期限切れになります。",f"This offer expires in about {int(remaining)} minutes.",lang))
            else: st.caption(tr(f"ライブオファー有効時間：約{int(remaining)}分",f"Live offer validity: about {int(remaining)} minutes remaining",lang))
        raw_score=row.get("score_before_evidence_cap")
        cap=row.get("evidence_confidence_cap")
        if pd.notna(raw_score) and pd.notna(cap) and float(raw_score) > float(cap):
            st.caption(tr(
                f"履歴データの信頼度を反映し、総合スコアは{float(cap):.0f}点を上限にしています（ライブ条件のみの評価: {float(raw_score):.1f}）。",
                f"Evidence confidence limits this recommendation to {float(cap):.0f}/100 (live-itinerary-only result before the confidence cap: {float(raw_score):.1f}).", lang))
        if is_ranked:
            st.progress(max(0.0,min(1.0,score/100.0)),text=tr("FlightSmart 総合スコア","FlightSmart overall score",lang))
        else:
            st.progress(max(0.0,min(1.0,score/100.0)),text=tr("料金・時間・乗り継ぎの参考評価","Live price/time/connection reference score",lang))
        d1,d2,d3,d4=st.columns(4); hist=row.get("historical_score")
        d1.metric(tr("BTS履歴評価","BTS historical rating",lang),"—" if pd.isna(hist) else f"{float(hist):.1f}/100")
        d2.metric(tr("乗り継ぎやすさ","Connection",lang),f"{float(row['connection_score']):.1f}")
        d3.metric(tr("所要時間評価","Duration",lang),f"{float(row['duration_score']):.1f}")
        d4.metric(tr("料金評価","Price value",lang),f"{float(row['price_value_score']):.1f}")
        st.write(row["explanation_ja"] if lang=="日本語" else row["explanation_en"])
        hist_reason=row.get("historical_reason_ja" if lang=="日本語" else "historical_reason_en")
        if (isinstance(hist_reason,str) and hist_reason) or pd.notna(row.get("historical_score")):
            with st.expander(tr("BTSの過去実績：なぜこの評価？","BTS past evidence: why this rating?",lang)):
                show_historical_evidence(row, lang)



_hero_path = Path(__file__).parent / "assets" / "fuji_sakura_hero.png"
_hero_style = ""
if _hero_path.exists():
    _hero_b64 = base64.b64encode(_hero_path.read_bytes()).decode("ascii")
    _hero_style = f"background-image:url('data:image/png;base64,{_hero_b64}');"
st.markdown(f"""<div class="fs-hero" style="{_hero_style}"><div class="fs-kicker">Public beta · パブリックベータ</div><div class="fs-title">FlightSmart Japan 🇺🇸 ✈️ 🇯🇵</div><div class="fs-sub"><span class="fs-ja">日本行きのフライトを、安さだけでなく「選びやすさ」まで。</span><br><span class="fs-en">Compare U.S.–Japan flights by price, travel time, connections, and historical operating evidence.</span></div></div>""", unsafe_allow_html=True)

lang=st.segmented_control("Language / 言語",["日本語","English"],default="日本語") or "日本語"

st.markdown(f"""
<div class="fs-story">
  <div class="fs-story-title">{tr("このアプリを作った理由", "Why I made FlightSmart", lang)}</div>
  {tr(
      "私の家族は、アメリカから日本の家族に会いに行くため、数年ごとに家族で飛行機を予約します。子ども2人を連れての長距離移動で、欠航や大幅な遅延を経験したこともあり、どの便を選ぶかは私たちにとって大切な決断です。そこで、料金だけでなく、所要時間や乗り継ぎ、そして過去の運航実績も一緒に比較できたら、もっと納得して便を選べるのではないかと考え、FlightSmartを作りました。BTS（米国運輸統計局）の過去データを参考情報として組み合わせ、アメリカから日本を訪れる皆さまが、自分や家族に合ったフライトを選ぶための判断をサポートします。",
      "My family travels from the United States to Japan every few years to visit our family. Traveling long distance with two children has sometimes meant dealing with canceled or significantly delayed flights, so choosing the right flight is an important decision for us. I created FlightSmart to make that choice more informed by comparing not only price, but also travel time, connections, and historical operating performance. FlightSmart uses historical U.S. Bureau of Transportation Statistics (BTS) data as supporting context to help travelers choose an option that fits them and their families. Historical records do not predict or guarantee future flight performance.",
      lang
  )}
</div>
""", unsafe_allow_html=True)

# Step 25: single Mt. Fuji + cherry blossom hero replaces the Step 24 memory gallery.

AIRPORTS=airport_options()

# Main search bar: Japanese travel-site style, no permanent sidebar.
st.markdown('<div class="fs-search">', unsafe_allow_html=True)
trip=st.segmented_control(tr("旅程","Trip",lang),["round_trip","one_way"],default="round_trip",format_func=lambda x:tr("往復" if x=="round_trip" else "片道","Round trip" if x=="round_trip" else "One way",lang)) or "round_trip"
airport_keys=list(AIRPORTS); default_idx=airport_keys.index("ATL") if "ATL" in airport_keys else 0
r1,r2,r3,r4=st.columns([1.45,1.2,1.15,1.1])
with r1:
    origin=st.selectbox(tr("出発地","From",lang),airport_keys,index=default_idx,format_func=lambda k:AIRPORTS[k])
with r2:
    destination=st.selectbox(tr("目的地","To",lang),list(JAPAN_AIRPORTS),format_func=lambda k:JAPAN_AIRPORTS[k])
with r3:
    depart_date=st.date_input(tr("出発日","Depart",lang),value=date.today()+timedelta(days=45),min_value=date.today()+timedelta(days=1))
with r4:
    return_date=None
    if trip=="round_trip":
        return_date=st.date_input(tr("帰国日","Return",lang),value=depart_date+timedelta(days=14),min_value=depart_date+timedelta(days=1))
    else:
        st.text_input(tr("帰国日","Return",lang),value=tr("片道","One way",lang),disabled=True)

s1,s2,s3,s4,s5=st.columns([.9,1.05,1.15,1.55,1.0])
with s1:
    passenger_count=st.number_input(tr("旅行者","Travelers",lang),min_value=1,max_value=6,value=1,step=1)
with s2:
    cabin=st.selectbox(tr("座席クラス","Cabin",lang),list(CABINS),format_func=lambda k:CABINS[k][0 if lang=="日本語" else 1])
with s3:
    max_conn=st.selectbox(tr("乗り継ぎ","Connections",lang),[0,1,2],index=1,format_func=lambda n:tr("直行便のみ" if n==0 else f"最大{n}回", "Nonstop only" if n==0 else f"Up to {n}",lang))
with s4:
    airline_pref=st.selectbox(
        tr("太平洋横断便の希望航空会社","Preferred transpacific airline",lang),
        list(TRANS_PACIFIC_PREFS),
        format_func=lambda k:TRANS_PACIFIC_PREFS[k][0 if lang=="日本語" else 1],
    )
with s5:
    mode=st.selectbox(tr("検索データ","Search data",lang),["live","demo"],format_func=lambda x:tr("ライブ検索" if x=="live" else "デモ","Live search" if x=="live" else "Demo",lang))
st.caption(tr("※ 航空会社の希望は、主な米国↔日本区間に適用します。最初の米国内区間は別の航空会社になる場合があります。","Airline preference applies to the main U.S.–Japan segment. Your first U.S. feeder flight may be operated by another airline.",lang))

passenger_ages=[]
with st.expander(tr("旅行者の年齢を設定（お子様連れはこちら）","Passenger ages (including children)",lang),expanded=int(passenger_count)>1):
    st.caption(tr("正確な運賃検索のため年齢を使用します。18歳以上の旅行者が1名以上必要です。","Ages improve fare matching. At least one traveler must be 18+.",lang))
    age_cols=st.columns(min(int(passenger_count),3))
    for i in range(int(passenger_count)):
        with age_cols[i%len(age_cols)]:
            passenger_ages.append(int(st.number_input(tr(f"旅行者 {i+1}",f"Traveler {i+1}",lang),0,120,35 if i==0 else 10,1,key=f"age_{i}")))

p1,p2=st.columns([2.2,1])
with p1:
    priorities=priority_selector(lang)
with p2:
    search=st.button(tr("フライトを比較する","Compare flights",lang),type="primary",use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

st.caption(tr("FlightSmart Scoreは候補便を比較するための意思決定サポートです。将来の遅延予測や予約保証ではありません。","FlightSmart Score is decision support for comparing offers, not a future delay forecast or booking guarantee.",lang))
show_travel_context(depart_date,lang,tr("出発日の旅行情報","Departure-date travel context",lang))
if return_date: show_travel_context(return_date,lang,tr("帰国日の旅行情報","Return-date travel context",lang))
route_ctx=route_pair_context(origin,destination)
if not route_ctx["is_historical_nonstop_pair"]:
    st.info(tr(
        f"✈️ {origin}→{destination} は現在のFlightSmart BTS/T-100日米直行路線参照にはありません。**直行便とは表示せず**、検索結果の実際の区間を確認して、乗り継ぎ空港と日本行き区間を表示します。",
        f"✈️ {origin}→{destination} is not in FlightSmart's current BTS/T-100 U.S.–Japan nonstop-route reference. FlightSmart will **not label it as nonstop**; it will validate the returned segments and show the connection gateway and Japan-bound segment.",lang))

# Persist the most recent result so users can change tabs/sort without losing it.
if search:
    if not any(a>=18 for a in passenger_ages):
        st.error(tr("18歳以上の旅行者を1名以上含めてください。","Include at least one traveler age 18 or older.",lang)); st.stop()
    try:
        with st.spinner(tr("候補便を検索し、FlightSmartが比較しています…","Searching and comparing flight options…",lang)):
            if mode=="demo":
                payload=load_demo_payload(trip=="round_trip")
            else:
                token=get_duffel_token()
                if not token:
                    st.error(tr("Duffelトークンが設定されていません。","No Duffel token is configured.",lang)); st.stop()
                payload=create_offer_request(origin=origin,destination=destination,departure_date=depart_date.isoformat(),return_date=return_date.isoformat() if return_date else None,passenger_ages=passenger_ages,cabin_class=cabin,max_connections=int(max_conn),token=token)
            offers=extract_offers(payload)
            # Step 22: Duffel sandbox can return synthetic direct routes. Evaluate only
            # route-plausible offers; live unreferenced routes remain visible with a warning.
            rejected_routes=[]
            allowed_offers=[]
            for _offer in offers:
                _facts=parse_offer(_offer).to_dict()
                _route=validate_itinerary_facts(_facts)
                if _route.get("route_recommendation_allowed", True):
                    allowed_offers.append(_offer)
                else:
                    rejected_routes.append({**_facts, **_route})
            ranked=evaluate_offers(allowed_offers,profile_keys=priorities)
            coverage=summarize_airline_coverage(offers)
            coverage["rejected_route_count"]=len(rejected_routes)
            coverage["rejected_routes"]=rejected_routes[:20]
            st.session_state["fs_ranked"]=ranked
            st.session_state["fs_coverage"]=coverage
            st.session_state["fs_search_meta"]={"origin":origin,"destination":destination,"depart":depart_date,"return":return_date,"trip":trip,"profile":(priorities[0] if len(priorities)==1 else DEFAULT_PROFILE),"priorities":priorities,"airline_pref":airline_pref,"mode":mode,"ages":passenger_ages,"cabin":cabin,"max_conn":int(max_conn)}
    except Exception as exc:
        st.error(tr("検索または分析中にエラーが発生しました。","An error occurred while searching or scoring offers.",lang)); st.code(str(exc))

ranked=st.session_state.get("fs_ranked")
coverage=st.session_state.get("fs_coverage",{})
meta=st.session_state.get("fs_search_meta")

if isinstance(ranked,pd.DataFrame) and not ranked.empty:
    if coverage.get("is_test_mode"):
        st.warning(tr("🧪 Duffelテストモードの結果です。表示される航空会社・料金は実在庫を表しません。","🧪 Duffel test-mode results do not represent real airline inventory or fares.",lang))
    if coverage.get("rejected_route_count",0):
        st.warning(tr(
            f"🛫 テストモードで返されたうち {coverage.get('rejected_route_count')} 件は、BTS/T-100日米直行路線参照と矛盾する架空の直行ルートだったため、おすすめ候補から除外しました。",
            f"🛫 {coverage.get('rejected_route_count')} test-mode offer(s) claimed a nonstop U.S.-Japan route that conflicts with the BTS/T-100 route reference, so FlightSmart excluded them from recommendations.",lang))

    st.markdown('<div class="fs-section-title">あなたに合う選択肢 / Smart choices for you</div>',unsafe_allow_html=True)
    st.markdown('<div class="fs-section-sub">1位だけではなく、「家族向け」「移動が楽」「価格とのバランス」「日本系航空会社」など、違う理由で選べる候補を並べます。</div>' if lang=="日本語" else '<div class="fs-section-sub">Instead of one endless ranking, FlightSmart highlights different useful choices: family-friendly, easiest, best value, strong history, and Japanese-carrier options when returned.</div>',unsafe_allow_html=True)

    pref=meta.get("airline_pref","ANY") if meta else "ANY"
    choices=build_choice_groups(ranked,pref)
    if choices:
        cols=st.columns(min(3,len(choices)))
        for i,ch in enumerate(choices):
            row=ch["row"]
            with cols[i%len(cols)]:
                with st.container(border=True):
                    st.markdown("### "+(ch["label_ja"] if lang=="日本語" else ch["label_en"]))
                    st.markdown(f"**{row.get('outbound_route_path_text') or row.get('outbound_summary') or '—'}**")
                    carrier=row.get("outbound_international_carrier") or row.get("operating_carrier_name") or "—"
                    st.caption(tr(f"太平洋横断便: {carrier}",f"Transpacific: {carrier}",lang))
                    st.metric(tr("料金","Price",lang),money(row.get("total_currency"),row.get("total_amount")))
                    st.caption((ch["reason_ja"] if lang=="日本語" else ch["reason_en"]))
                    st.caption(tr(f"乗り継ぎ {int(row.get('outbound_stop_count',0) or 0)}回 · {duration_label(row.get('total_duration_min'),lang)}",f"{int(row.get('outbound_stop_count',0) or 0)} outbound connection(s) · {duration_label(row.get('total_duration_min'),lang)}",lang))

    cheapest=ranked.sort_values("total_amount",na_position="last").iloc[0]
    quickest=ranked.sort_values("total_duration_min",na_position="last").iloc[0]
    ranked_choices=ranked[ranked.get("is_ranked_choice", True) == True] if "is_ranked_choice" in ranked.columns else ranked
    best=ranked.sort_values("flightsmart_live_score",ascending=False,na_position="last").iloc[0]

    if pref != "ANY":
        matches=ranked[ranked.apply(lambda r: preference_match(r,pref),axis=1)]
        if matches.empty:
            st.warning(tr("選択した太平洋横断航空会社を含む旅程は、今回の検索では返されませんでした。他の候補は引き続き比較できます。","No itinerary matching your transpacific-airline preference was returned in this search. Other valid choices are still shown.",lang))
        else:
            st.success(tr(f"希望航空会社を含む候補：{len(matches)}件",f"Options matching your airline preference: {len(matches)}",lang))

    st.markdown('<div class="fs-reco">',unsafe_allow_html=True)
    st.markdown("### ⭐ "+tr("FlightSmartのおすすめ","FlightSmart recommendation",lang))
    best_hist = best.get("historical_score")
    best_rank = best.get("historical_evidence_rank")
    best_hist_text = "—" if pd.isna(best_hist) else f"{float(best_hist):.1f}/100"
    rank_text = "—" if pd.isna(best_rank) else f"#{int(best_rank)}"
    st.markdown(tr(
        f"**{best.get('operating_carrier_name') or '—'}**　{money(best.get('total_currency'),best.get('total_amount'))}　·　{duration_label(best.get('total_duration_min'),lang)}　·　**BTS過去実績 {rank_text} / {best_hist_text}**",
        f"**{best.get('operating_carrier_name') or '—'}**  {money(best.get('total_currency'),best.get('total_amount'))} · {duration_label(best.get('total_duration_min'),lang)} · **BTS past records {rank_text} / {best_hist_text}**", lang))
    st.write(best["explanation_ja"] if lang=="日本語" else best["explanation_en"])
    st.markdown('</div>',unsafe_allow_html=True)

    # Past-record ranking is intentionally separate and highly visible. Only offers
    # with airline/route-specific BTS matches appear here; market medians and missing
    # history are excluded from the numbered evidence ranking.
    st.markdown('<div class="fs-section-title">📊 BTS過去実績ランキング / BTS past-record ranking</div>', unsafe_allow_html=True)
    st.info(tr(
        "ランキング優先順：① 履歴データ信頼度（Very High → High → Medium） ② 航空会社・路線の一致精度 ③ BTS履歴評価。Low / Limited / Unavailable は番号付き順位を付けません。",
        "Ranking priority: (1) historical confidence (Very High → High → Medium), (2) airline/route match quality, then (3) BTS historical rating. Low / Limited / Unavailable evidence receives no numbered rank.", lang))
    st.caption(tr(
        "この順位は、各航空会社・日米ルートに一致するBTSの過去実績が確認できた候補だけを比較します。BTS履歴評価を中心に順位付けし、同程度の場合はデータ信頼度を優先します。航空会社固有の履歴がない候補は順位を付けません。",
        "This ranking includes only airline/route-specific BTS evidence with Medium, High, or Very High confidence. Historical confidence is the first ranking key, followed by match quality and the BTS historical rating. Low, Limited, or Unavailable evidence receives no numbered rank.", lang))
    evidence_ranked = ranked[ranked.get("is_ranked_choice", False) == True].copy() if "is_ranked_choice" in ranked.columns else ranked.iloc[0:0].copy()
    if not evidence_ranked.empty:
        ev_rows=[]
        for _, er in evidence_ranked.head(8).iterrows():
            ev_rows.append({
                tr("過去実績順位","Past-record rank",lang): f"#{int(er['historical_evidence_rank'])}" if pd.notna(er.get('historical_evidence_rank')) else "—",
                tr("航空会社","Airline",lang): er.get("operating_carrier_name") or er.get("operating_carrier_code") or "—",
                tr("日米区間","U.S.–Japan segment",lang): f"{er.get('international_gateway') or '?'}→{er.get('japan_arrival_airport') or er.get('destination') or '?'}",
                tr("BTS履歴評価","BTS historical rating",lang): "—" if pd.isna(er.get("historical_score")) else f"{float(er.get('historical_score')):.1f}/100",
                tr("データ信頼度","Evidence confidence",lang): confidence_label(er.get("historical_data_confidence"),lang),
                tr("確認月数","Months observed",lang): "—" if pd.isna(er.get("historical_months_reported")) else int(er.get("historical_months_reported")),
                tr("過去旅客数","Historical passengers",lang): "—" if pd.isna(er.get("historical_passengers")) else f"{int(er.get('historical_passengers')):,}",
            })
        st.dataframe(pd.DataFrame(ev_rows), hide_index=True, use_container_width=True)
    else:
        st.warning(tr(
            "今回の検索では、航空会社・ルートまで一致するBTS過去実績を確認できる候補がありません。料金や時間の候補は表示しますが、過去実績ランキングは作成しません。",
            "No returned offer has sufficiently reliable airline/route-specific BTS history (Medium confidence or better). Flight options can still be shown by price and schedule, but FlightSmart will not create a numbered past-record ranking for this search.", lang))

    # Flexible-date comparison is intentionally opt-in: it creates several live Duffel searches.
    if meta and meta.get("trip")=="round_trip":
        st.markdown('<div class="fs-section-title">📅 日程を少し変えると？ / Flexible dates</div>',unsafe_allow_html=True)
        st.caption(tr("出発日・帰国日を前後1日ずつ比較して、料金差を見つけます。ライブ検索では最大9通りを確認します。","Compare ±1 day around departure and return dates to reveal fare differences. Live mode checks up to 9 combinations.",lang))
        flex_btn=st.button(tr("前後1日の料金を比較","Compare ±1 day fares",lang),use_container_width=False)
        if flex_btn:
            if meta.get("mode")=="demo":
                st.info(tr("日付別料金はライブDuffel検索で利用できます。デモでは現在のサンプル料金のみ表示します。","Flexible-date fares require live Duffel search. Demo mode only contains the saved sample fare.",lang))
            else:
                token=get_duffel_token()
                rows=[]
                dep_dates=[meta["depart"]+timedelta(days=i) for i in (-1,0,1)]
                ret_dates=[meta["return"]+timedelta(days=i) for i in (-1,0,1)]
                prog=st.progress(0,text=tr("近い日程の料金を確認中…","Checking nearby-date fares…",lang))
                total=len(dep_dates)*len(ret_dates); done=0
                for rd in ret_dates:
                    for dd in dep_dates:
                        done+=1
                        if rd<=dd:
                            rows.append({"depart":dd,"return":rd,"price":None,"currency":""}); prog.progress(done/total); continue
                        try:
                            pp=create_offer_request(origin=meta["origin"],destination=meta["destination"],departure_date=dd.isoformat(),return_date=rd.isoformat(),passenger_ages=meta["ages"],cabin_class=meta["cabin"],max_connections=meta["max_conn"],token=token)
                            oo=extract_offers(pp); rr=evaluate_offers(oo,profile_keys=meta.get("priorities",[]))
                            if not rr.empty:
                                low=rr.sort_values("total_amount",na_position="last").iloc[0]
                                rows.append({"depart":dd,"return":rd,"price":float(low["total_amount"]),"currency":low.get("total_currency") or ""})
                            else: rows.append({"depart":dd,"return":rd,"price":None,"currency":""})
                        except Exception:
                            rows.append({"depart":dd,"return":rd,"price":None,"currency":""})
                        prog.progress(done/total)
                prog.empty(); st.session_state["fs_flex_rows"]=rows

        flex_rows=st.session_state.get("fs_flex_rows")
        if flex_rows:
            fdf=pd.DataFrame(flex_rows); valid=fdf.dropna(subset=["price"])
            if not valid.empty:
                minprice=float(valid["price"].min()); selected=valid[(valid["depart"]==meta["depart"])&(valid["return"]==meta["return"])]
                base=float(selected.iloc[0]["price"]) if not selected.empty else None
                currency=str(valid.iloc[0]["currency"] or "")
                grid=[]
                for rd in sorted(fdf["return"].unique()):
                    row={tr("帰国日","Return",lang):rd.strftime("%m/%d")}
                    for dd in sorted(fdf["depart"].unique()):
                        hit=fdf[(fdf["depart"]==dd)&(fdf["return"]==rd)]
                        if hit.empty or pd.isna(hit.iloc[0]["price"]): val="—"
                        else:
                            price=float(hit.iloc[0]["price"]); diff=(price-base) if base is not None else None
                            tag=" ⭐" if price==minprice else ""
                            val=f"{currency} {price:,.0f}{tag}" + ((f" ({diff:+,.0f})") if diff is not None and abs(diff)>=1 else "")
                        row[dd.strftime("%m/%d")]=val
                    grid.append(row)
                st.dataframe(pd.DataFrame(grid),hide_index=True,use_container_width=True)
                bestdate=valid.loc[valid["price"].idxmin()]
                if base is not None and minprice<base:
                    savings=base-minprice
                    st.success(tr(f"💡 {bestdate['depart'].strftime('%m/%d')}出発・{bestdate['return'].strftime('%m/%d')}帰国なら、検索された旅行者全員の表示運賃で約{currency} {savings:,.0f}安くなります。",f"💡 Depart {bestdate['depart'].strftime('%m/%d')} and return {bestdate['return'].strftime('%m/%d')} to save about {currency} {savings:,.0f} on the displayed total fare for the travelers in this search.",lang))

    st.markdown('<div class="fs-section-title">✈️ 候補便を比較 / Compare flight options</div>',unsafe_allow_html=True)
    view=st.segmented_control(tr("並び替え","Sort",lang),["recommended","cheapest","quickest"],default="recommended",format_func=lambda x:{"recommended":tr("⭐ おすすめ","⭐ Recommended",lang),"cheapest":tr("💴 最安値","💴 Cheapest",lang),"quickest":tr("⏱ 最短時間","⏱ Quickest",lang)}[x]) or "recommended"
    base_shown=ranked.sort_values("flightsmart_live_score",ascending=False,na_position="last") if view=="recommended" else ranked.sort_values("total_amount" if view=="cheapest" else "total_duration_min",na_position="last")
    shown=diverse_options(base_shown,limit=10)
    st.caption(tr("似た旅程を何件も続けて表示せず、経路や太平洋横断航空会社が異なる候補を優先して表示します。","FlightSmart prioritizes route and airline variety instead of filling the list with near-duplicate offers.",lang))
    for pos,(_,row) in enumerate(shown.iterrows()): result_card(row,lang,is_top=(pos==0 and view=="recommended"))

    with st.expander(tr("📊 おすすめの根拠：BTSの過去実績を見る","📊 Why recommended: see BTS historical evidence",lang),expanded=False):
        show_historical_evidence(best,lang)
    with st.expander(tr("検索で返された航空会社を確認","See airlines returned in this search",lang)):
        st.write(coverage.get("operating_counts",{}))
else:
    st.markdown('<div class="fs-section-title">FlightSmartでできること</div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    for col,icon,title,body in [(a,"💴","料金を比較","候補内の価格差をわかりやすく比較"),(b,"📅","日程を比較","前後1日で大きな料金差がないか確認"),(c,"📊","実績も確認","BTS/DOTの過去運航実績を比較の根拠に")]:
        with col:
            with st.container(border=True): st.markdown(f"### {icon} {title}"); st.caption(body)

st.divider()
with st.expander(tr("FlightSmartの比較方法・免責事項","How FlightSmart compares flights & disclaimer",lang)):
    st.markdown(tr("""**4つの視点:** ① BTS/DOTの履歴運航実績、② 乗り継ぎのしやすさ、③ 所要時間、④ 今回取得した候補内での料金。履歴データは将来の遅延を予測するものではありません。予約前に最終料金、手荷物、変更・払戻条件を必ず確認してください。""","""**Four dimensions:** (1) BTS/DOT historical operating evidence, (2) connection convenience, (3) itinerary duration, and (4) price relative to the returned offers. Historical data does not predict future delays. Verify final fare, baggage, and change/refund conditions before booking.""",lang))

st.subheader(tr("データソース・参照先","Data sources & references",lang))
s1,s2=st.columns(2)
with s1: st.link_button(tr("🇺🇸 BTS 航空データ公式ページ","🇺🇸 BTS official airline data",lang),"https://www.bts.gov/airline-data-downloads",use_container_width=True)
with s2: st.link_button(tr("✈️ Duffel API 公式ドキュメント","✈️ Duffel API official documentation",lang),"https://duffel.com/docs/api/offers",use_container_width=True)
st.caption(tr("BTS/DOTの履歴運航データ + Duffelの候補便・料金・旅程。","BTS/DOT historical operating evidence + Duffel flight offers, fares, and itineraries.",lang))
