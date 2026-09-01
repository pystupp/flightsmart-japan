"""FlightSmart Step 4 traveler profiles and adaptive score weights."""
from __future__ import annotations

PROFILES = {
    "best_overall": {
        "label_en": "Best overall",
        "label_ja": "総合的におすすめ",
        "weights": {"historical": 0.55, "connection": 0.25, "duration": 0.10, "price_value": 0.10},
        "description_en": "Balances historical evidence, connection ease, duration and price.",
        "description_ja": "運航実績、乗り継ぎのしやすさ、所要時間、料金をバランスよく評価します。",
    },
    "family": {
        "label_en": "Traveling with children",
        "label_ja": "子供と一緒",
        "weights": {"historical": 0.40, "connection": 0.40, "duration": 0.12, "price_value": 0.08},
        "description_en": "Prioritizes fewer/easier connections and reliable historical evidence for family travel.",
        "description_ja": "お子様連れを想定し、乗り継ぎの少なさ・しやすさと運航実績を重視します。",
    },
    "elderly_family": {
        "label_en": "Traveling with elderly family",
        "label_ja": "高齢の家族と一緒",
        "weights": {"historical": 0.40, "connection": 0.45, "duration": 0.10, "price_value": 0.05},
        "description_en": "Strongly favors simpler connections and avoids making price the deciding factor.",
        "description_ja": "移動負担を減らすため、乗り継ぎのしやすさを最優先し、料金の比重を低くします。",
    },
    "fewer_connections": {
        "label_en": "Fewer connections",
        "label_ja": "乗り継ぎを少なく",
        "weights": {"historical": 0.35, "connection": 0.50, "duration": 0.10, "price_value": 0.05},
        "description_en": "Strongly favors nonstop and simpler itineraries.",
        "description_ja": "直行便や乗り継ぎの少ない旅程を強く優先します。",
    },
    "reliability": {
        "label_en": "Reliability priority",
        "label_ja": "運航実績を重視",
        "weights": {"historical": 0.70, "connection": 0.15, "duration": 0.10, "price_value": 0.05},
        "description_en": "Places the most weight on the available BTS historical evidence.",
        "description_ja": "利用可能なBTS履歴データを最も重視して評価します。",
    },
    "lowest_price": {
        "label_en": "Lowest price",
        "label_ja": "料金を重視",
        "weights": {"historical": 0.30, "connection": 0.15, "duration": 0.10, "price_value": 0.45},
        "description_en": "Gives price the largest weight while retaining basic reliability and connection context.",
        "description_ja": "料金を最も重視しつつ、運航実績と乗り継ぎ情報も最低限考慮します。",
    },
    "shortest_time": {
        "label_en": "Shortest travel time",
        "label_ja": "所要時間を重視",
        "weights": {"historical": 0.30, "connection": 0.15, "duration": 0.45, "price_value": 0.10},
        "description_en": "Prioritizes total travel time while keeping some reliability and price context.",
        "description_ja": "総所要時間を最も重視し、運航実績と料金も補助的に評価します。",
    },
}

DEFAULT_PROFILE = "best_overall"


def get_profile(profile_key: str | None) -> dict:
    key = profile_key if profile_key in PROFILES else DEFAULT_PROFILE
    return {"key": key, **PROFILES[key]}


def profile_options(language: str = "日本語") -> dict[str, str]:
    label_key = "label_ja" if language == "日本語" else "label_en"
    return {key: value[label_key] for key, value in PROFILES.items()}


def combine_profiles(profile_keys: list[str] | tuple[str, ...] | None) -> dict:
    """Combine multiple explicit traveler priorities by averaging their weights.

    No selection means the neutral best-overall profile. Selecting one or more
    specific priorities does not silently add the best-overall profile.
    """
    keys=[k for k in (profile_keys or []) if k in PROFILES and k != "best_overall"]
    if not keys:
        return get_profile(DEFAULT_PROFILE)
    dims=("historical","connection","duration","price_value")
    weights={d:sum(PROFILES[k]["weights"][d] for k in keys)/len(keys) for d in dims}
    total=sum(weights.values()) or 1.0
    weights={d:weights[d]/total for d in dims}
    return {
        "key":"+".join(keys),
        "label_en":" + ".join(PROFILES[k]["label_en"] for k in keys),
        "label_ja":" + ".join(PROFILES[k]["label_ja"] for k in keys),
        "weights":weights,
        "description_en":"Combined traveler priorities selected by the user.",
        "description_ja":"ユーザーが選択した複数の旅行優先事項を組み合わせて評価します。",
    }
