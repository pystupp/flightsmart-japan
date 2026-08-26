from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from airport_catalog import airport_options
from duffel_client import create_offer_request
from duffel_offer_adapter import extract_offers
from airline_coverage import summarize_airline_coverage
from itinerary_scoring import evaluate_offers
from traveler_profiles import DEFAULT_PROFILE, PROFILES
from travel_calendar import travel_context, highest_level

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

st.set_page_config(page_title="FlightSmart Japan", page_icon="✈️", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 1.5rem; padding-bottom: 3rem;}
[data-testid="stMetric"] {background: rgba(127,127,127,.06); border-radius: 14px; padding: .65rem .8rem;}
[data-testid="stSidebar"] {min-width: 320px;}
.fs-hero {padding: 1.15rem 1.25rem; border: 1px solid rgba(127,127,127,.18); border-radius: 18px; margin-bottom: 1rem;}
.fs-kicker {font-size:.86rem; opacity:.75; letter-spacing:.04em; text-transform:uppercase;}
.fs-title {font-size:2rem; font-weight:750; margin:.15rem 0 .35rem 0;}
.fs-sub {opacity:.82; line-height:1.55;}
@media (max-width: 700px) {
  .block-container {padding-left: .75rem; padding-right: .75rem;}
  .fs-title {font-size:1.55rem;}
  [data-testid="column"] {min-width: 100% !important;}
}
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
    mapping_ja={"VERY_HIGH":"非常に高い","HIGH":"高い","MEDIUM":"中程度","LIMITED":"限定的","UNAVAILABLE":"データなし"}
    return mapping_ja.get(str(value),str(value)) if lang=="日本語" else str(value).replace("_"," ").title()


def profile_selector(lang: str) -> str:
    keys=list(PROFILES); label_key="label_ja" if lang=="日本語" else "label_en"; desc_key="description_ja" if lang=="日本語" else "description_en"
    selected=st.selectbox(tr("今回の旅行で一番大切なことは？","What matters most for this trip?",lang),keys,index=keys.index(DEFAULT_PROFILE),format_func=lambda k:PROFILES[k][label_key])
    st.caption(PROFILES[selected][desc_key]); return selected


def load_demo_payload(round_trip: bool) -> dict:
    with (DEMO_ROUNDTRIP if round_trip else DEMO_ONEWAY).open("r",encoding="utf-8") as f: return json.load(f)


def show_travel_context(d: date, lang: str, title: str) -> None:
    events=travel_context(d)
    if not events: return
    level=highest_level(events); icon="🔴" if level=="HIGH" else "🟠"
    labels=" / ".join(e["label_ja" if lang=="日本語" else "label_en"] for e in events)
    st.warning(f"{icon} **{title}:** {labels}")


def result_card(row: pd.Series, lang: str, is_top: bool=False) -> None:
    rank=int(row["rank"]); carrier=row.get("operating_carrier_name") or row.get("operating_carrier_code") or "—"; score=float(row["flightsmart_live_score"])
    with st.container(border=True):
        st.subheader(f"{'🏆 ' if is_top else ''}#{rank} {carrier} — {score:.1f}/100")
        st.markdown(f"**{tr('運航航空会社','Operating carrier',lang)}:** {carrier}")
        marketing=row.get("marketing_carrier_name") or row.get("marketing_carrier_code")
        if marketing and str(marketing) != str(carrier):
            st.caption(f"{tr('販売航空会社','Marketing carrier',lang)}: {marketing}")
        st.caption(row.get("segment_summary") or "—")
        c1,c2,c3,c4=st.columns(4)
        c1.metric(tr("料金","Price",lang),money(row.get("total_currency"),row.get("total_amount")))
        c2.metric(tr("合計乗り継ぎ","Total connections",lang),int(row.get("stop_count",0)))
        c3.metric(tr("合計飛行旅程時間","Total itinerary duration",lang),duration_label(row.get("total_duration_min"),lang))
        c4.metric(tr("履歴データ信頼度","Historical confidence",lang),confidence_label(row.get("historical_data_confidence"),lang))
        if row.get("trip_type")=="round_trip":
            st.caption(tr(
                f"往路：乗り継ぎ{int(row.get('outbound_stop_count',0))}回・{duration_label(row.get('outbound_duration_min'),lang)} / 復路：乗り継ぎ{int(row.get('return_stop_count') or 0)}回・{duration_label(row.get('return_duration_min'),lang)}",
                f"Outbound: {int(row.get('outbound_stop_count',0))} connection(s), {duration_label(row.get('outbound_duration_min'),lang)} / Return: {int(row.get('return_stop_count') or 0)} connection(s), {duration_label(row.get('return_duration_min'),lang)}",lang))
        remaining=row.get("offer_minutes_remaining")
        if pd.notna(remaining) and remaining is not None:
            if int(remaining)<=5: st.error(tr(f"このオファーは約{int(remaining)}分で期限切れになります。",f"This offer expires in about {int(remaining)} minutes.",lang))
            else: st.caption(tr(f"ライブオファー有効時間：約{int(remaining)}分",f"Live offer validity: about {int(remaining)} minutes remaining",lang))
        st.progress(max(0.0,min(1.0,score/100.0)),text=tr("FlightSmart 総合スコア","FlightSmart overall score",lang))
        d1,d2,d3,d4=st.columns(4); hist=row.get("historical_score")
        d1.metric(tr("履歴実績","Historical evidence",lang),"—" if pd.isna(hist) else f"{float(hist):.1f}")
        d2.metric(tr("乗り継ぎやすさ","Connection",lang),f"{float(row['connection_score']):.1f}")
        d3.metric(tr("所要時間評価","Duration",lang),f"{float(row['duration_score']):.1f}")
        d4.metric(tr("料金評価","Price value",lang),f"{float(row['price_value_score']):.1f}")
        st.write(row["explanation_ja"] if lang=="日本語" else row["explanation_en"])
        hist_reason=row.get("historical_reason_ja" if lang=="日本語" else "historical_reason_en")
        if isinstance(hist_reason,str) and hist_reason:
            with st.expander(tr("履歴データの根拠","Historical evidence details",lang)):
                st.write(hist_reason)
                st.caption(tr("履歴データは将来の遅延を予測するものではありません。","Historical evidence does not predict whether this future flight will be delayed.",lang))


st.markdown("""<div class="fs-hero"><div class="fs-kicker">Public beta · パブリックベータ</div><div class="fs-title">FlightSmart Japan 🇺🇸 ✈️ 🇯🇵</div><div class="fs-sub">アメリカから日本へのフライト選びを、料金だけでなく運航実績・乗り継ぎ・所要時間からサポート。<br>Smarter U.S.–Japan flight decisions beyond price alone.</div></div>""", unsafe_allow_html=True)
lang=st.segmented_control("Language / 言語",["日本語","English"],default="日本語") or "日本語"
AIRPORTS=airport_options()

with st.sidebar:
    st.header(tr("フライト検索","Flight search",lang))
    mode=st.radio(tr("検索モード","Search mode",lang),["live","demo"],format_func=lambda x:tr("Duffel ライブ検索" if x=="live" else "デモデータ","Duffel live search" if x=="live" else "Demo data",lang))
    trip=st.segmented_control(tr("旅程","Trip",lang),["round_trip","one_way"],default="round_trip",format_func=lambda x:tr("往復" if x=="round_trip" else "片道","Round trip" if x=="round_trip" else "One way",lang)) or "round_trip"
    airport_keys=list(AIRPORTS); default_idx=airport_keys.index("ATL") if "ATL" in airport_keys else 0
    origin=st.selectbox(tr("米国出発空港（都市名・コードで検索）","U.S. origin airport (search city or code)",lang),airport_keys,index=default_idx,format_func=lambda k:AIRPORTS[k])
    destination=st.selectbox(tr("日本の到着空港","Japan destination",lang),list(JAPAN_AIRPORTS),format_func=lambda k:JAPAN_AIRPORTS[k])
    depart_date=st.date_input(tr("出発日","Departure date",lang),value=date.today()+timedelta(days=45),min_value=date.today()+timedelta(days=1))
    return_date=None
    if trip=="round_trip":
        return_date=st.date_input(tr("帰国日","Return date",lang),value=depart_date+timedelta(days=14),min_value=depart_date+timedelta(days=1))

    passenger_count=st.number_input(tr("旅行者数","Travelers",lang),min_value=1,max_value=6,value=1,step=1)
    passenger_ages=[]
    with st.expander(tr("旅行者の年齢","Passenger ages",lang),expanded=int(passenger_count)>1):
        st.caption(tr("Duffel検索の運賃区分を正確にするため年齢を使用します。18歳以上の旅行者が1名以上必要です。","Ages are used for more accurate Duffel fare/passenger matching. At least one traveler must be 18+.",lang))
        for i in range(int(passenger_count)):
            default_age=35 if i==0 else 10
            age=st.number_input(tr(f"旅行者 {i+1} の年齢",f"Traveler {i+1} age",lang),min_value=0,max_value=120,value=default_age,step=1,key=f"age_{i}")
            passenger_ages.append(int(age))

    cabin=st.selectbox(tr("座席クラス","Cabin",lang),list(CABINS),format_func=lambda k:CABINS[k][0 if lang=="日本語" else 1])
    max_conn=st.selectbox(tr("片道ごとの最大乗り継ぎ回数","Maximum connections per direction",lang),[0,1,2],index=1)
    st.divider(); profile=profile_selector(lang)
    search=st.button(tr("おすすめ便を検索","Find recommended flights",lang),type="primary",use_container_width=True)

st.info(tr("FlightSmartのスコアは候補便を比較するための意思決定サポートです。航空会社の公式な遅延予測や予約保証ではありません。","FlightSmart scores are decision support for comparing offers. They are not airline-provided delay forecasts or booking guarantees.",lang))
with st.expander(tr("FlightSmartは何を比較するの？","What does FlightSmart compare?",lang)):
    st.markdown(tr("""**4つの視点で候補便を比較します。** ① BTS/DOTの履歴運航実績、② 乗り継ぎのしやすさ、③ 所要時間、④ 今回取得した候補内での料金。旅行スタイルを選ぶと重みが変わります。""","""**FlightSmart compares four dimensions:** (1) BTS/DOT historical operating evidence, (2) connection convenience, (3) itinerary duration, and (4) price relative to the offers returned in the current search. Your traveler profile changes the weights.""",lang))
show_travel_context(depart_date,lang,tr("出発日の旅行情報","Departure-date travel context",lang))
if return_date: show_travel_context(return_date,lang,tr("帰国日の旅行情報","Return-date travel context",lang))

if search:
    if not any(a>=18 for a in passenger_ages):
        st.error(tr("18歳以上の旅行者を1名以上含めてください。","Include at least one traveler age 18 or older.",lang)); st.stop()
    if mode=="demo" and (origin!="ATL" or destination!="HND"):
        st.warning(tr("デモデータはATL→HNDのサンプルです。入力条件ではなくサンプル旅程を表示します。","Demo data uses saved ATL→HND examples, so results below do not reflect the selected route.",lang))
    try:
        with st.spinner(tr("候補便を分析しています…","Analyzing flight options…",lang)):
            if mode=="demo":
                payload=load_demo_payload(trip=="round_trip")
                st.caption(tr("保存済みのデモ候補便を使用しています。","Using saved demo offers for this test.",lang))
            else:
                token=get_duffel_token()
                if not token:
                    st.error(tr("Duffelトークンが設定されていません。DUFFEL_ACCESS_TOKENを設定するか、デモモードを選んでください。","No Duffel token is configured. Set DUFFEL_ACCESS_TOKEN or use Demo mode.",lang)); st.stop()
                payload=create_offer_request(origin=origin,destination=destination,departure_date=depart_date.isoformat(),return_date=return_date.isoformat() if return_date else None,passenger_ages=passenger_ages,cabin_class=cabin,max_connections=int(max_conn),token=token)
            offers=extract_offers(payload)
            coverage=summarize_airline_coverage(offers)
            ranked=evaluate_offers(offers,profile_key=profile)
        if coverage.get("is_test_mode"):
            st.warning(tr(
                "🧪 現在のDuffel検索はテストモードです。Duffel Airwaysなどのサンドボックス結果は実際の航空会社在庫・料金を表しません。ANA/JALが表示されなくても、FlightSmartが除外しているという意味ではありません。実際の航空会社在庫を確認するにはDuffelのライブモードが必要です。",
                "🧪 This Duffel search is running in test mode. Sandbox results such as Duffel Airways do not represent real airline inventory or prices. If ANA/JAL are absent, that does not mean FlightSmart filtered them out. Duffel live mode is required to evaluate real airline availability.",lang))
        with st.expander(tr("ライブ検索の航空会社カバレッジ","Live-search airline coverage",lang),expanded=coverage.get("is_test_mode",False)):
            st.caption(tr(f"Duffelから返された候補：{coverage['offer_count']}件",f"Offers returned by Duffel: {coverage['offer_count']}",lang))
            op_counts=coverage.get("operating_counts",{})
            if op_counts:
                st.write(tr("運航航空会社別","By operating carrier",lang),op_counts)
            jp=coverage.get("japanese_status",{})
            status_bits=[]
            for code,info in jp.items():
                mark="✅" if info.get("present") else "—"
                status_bits.append(f"{mark} {info.get('label')} ({code})")
            st.write(tr("日本系航空会社の返却状況","Japanese-carrier return status",lang)+": "+" · ".join(status_bits))
            if not any(info.get("present") for info in jp.values()):
                st.info(tr("ANA/JAL/ZIPAIRは今回Duffelから返された候補に含まれていません。FlightSmartのランキング処理で削除されたわけではありません。","ANA/JAL/ZIPAIR were not present in the offers returned by Duffel for this search. They were not removed by FlightSmart ranking logic.",lang))
        if ranked.empty: st.warning(tr("条件に一致する候補便が見つかりませんでした。","No matching offers were returned.",lang))
        else:
            st.success(tr(f"{len(ranked)}件の候補便を分析しました。",f"Analyzed {len(ranked)} flight offers.",lang))
            top=ranked.iloc[0]
            st.header(tr("FlightSmart おすすめ","FlightSmart recommendation",lang))
            st.markdown(f"### 🏆 {top['operating_carrier_name']} — {float(top['flightsmart_live_score']):.1f}/100\n**{top['segment_summary']}**  ·  {money(top['total_currency'],top['total_amount'])}")
            st.caption(tr(f"旅行者設定：{top['traveler_profile_ja']}",f"Traveler profile: {top['traveler_profile_en']}",lang))
            st.markdown("#### " + tr("この便をおすすめする理由","Why this flight?",lang))
            st.write(top["explanation_ja"] if lang=="日本語" else top["explanation_en"])
            st.subheader(tr("候補便ランキング","Ranked flight options",lang))
            for idx,row in ranked.head(8).iterrows(): result_card(row,lang,is_top=(idx==0))
            with st.expander(tr("スコアの重みを見る","View score weights",lang)):
                st.write({tr("履歴実績","Historical evidence",lang):f"{float(top['weight_historical']):.0%}",tr("乗り継ぎ","Connection convenience",lang):f"{float(top['weight_connection']):.0%}",tr("所要時間","Duration",lang):f"{float(top['weight_duration']):.0%}",tr("料金","Price value",lang):f"{float(top['weight_price_value']):.0%}"})
    except Exception as exc:
        st.error(tr("検索または分析中にエラーが発生しました。","An error occurred while searching or scoring offers.",lang)); st.code(str(exc))

st.divider()
left,right=st.columns([2,1])
with left:
    with st.expander(tr("データ・スコア・免責事項","Data, scoring & disclaimer",lang)):
        st.markdown(tr("""- **履歴データ:** BTS/DOTの運航実績を意思決定の参考情報として使用します。
- **ライブ情報:** Duffelから返された候補便・料金・旅程を比較します。
- **繁忙期表示:** 旅行計画上の参考情報で、遅延や価格の予測ではありません。
- **FlightSmart Score:** 候補便を比較するための独自スコアで、航空会社や政府機関の公式評価ではありません。
- **予約前:** 最終料金、手荷物、変更・払戻条件、旅券・入国要件は予約画面と公式情報で必ず確認してください。""","""- **Historical data:** BTS/DOT operating history is used as decision-support evidence.
- **Live information:** Flight options, fares, and itineraries returned by Duffel are compared.
- **Travel-period notices:** Planning context only; they do not predict delays or prices.
- **FlightSmart Score:** A proprietary comparison score, not an official airline or government rating.
- **Before booking:** Verify final fare, baggage, change/refund rules, passport, and entry requirements with the booking provider and official sources.""",lang))
    with st.expander(tr("プライバシー（ベータ版）","Privacy (beta)",lang)):
        st.write(tr("FlightSmartは検索に必要な旅行条件を処理します。このベータ版はアカウントを作成せず、アプリ内で旅券番号や支払いカード情報を入力する設計ではありません。公開前には、利用するホスティング・分析・フィードバックサービスに合わせて正式なプライバシーポリシーを更新してください。","FlightSmart processes trip inputs needed to search and compare flights. This beta does not require an account and is not designed to collect passport numbers or payment-card details inside the app. Before a public launch, update the formal privacy policy to match the hosting, analytics, and feedback services you actually use.",lang))
with right:
    feedback_url=os.getenv("FLIGHTSMART_FEEDBACK_URL")
    try:
        feedback_url=feedback_url or st.secrets.get("FLIGHTSMART_FEEDBACK_URL")
    except Exception:
        pass
    st.markdown("**"+tr("ベータ版へのご意見","Beta feedback",lang)+"**")
    st.caption(tr("使いやすさやおすすめ結果について、ぜひ教えてください。","Tell us what felt useful, confusing, or surprising.",lang))
    if feedback_url:
        st.link_button(tr("フィードバックを送る","Send feedback",lang),feedback_url,use_container_width=True)
    else:
        st.caption(tr("管理者：FLIGHTSMART_FEEDBACK_URL を設定するとフィードバックボタンが有効になります。","Admin: set FLIGHTSMART_FEEDBACK_URL to enable the feedback button.",lang))
st.caption(tr("データ設計：BTS/DOTの履歴運航データ + Duffelのライブ候補便。","Data design: BTS/DOT historical operating evidence + Duffel live offers.",lang))
