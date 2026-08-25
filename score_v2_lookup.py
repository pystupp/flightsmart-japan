from pathlib import Path
import pandas as pd

DEFAULT_FILE = Path(__file__).resolve().parent / 'score_v2' / 'flightsmart_app_routes_v2.csv'


def load_route_scores(path=DEFAULT_FILE):
    return pd.read_csv(path)


def recommend_historical_markets(destination='HND', origin=None, top_n=5, min_confidence='MEDIUM', path=DEFAULT_FILE):
    """Return historical U.S.→Japan market evidence ranked by FlightSmart Score v2.

    This is NOT a live flight search and does not predict a future delay. Live itineraries
    from Duffel should be matched to this evidence layer in the Streamlit integration step.
    """
    df = load_route_scores(path)
    order = {'LOW':0, 'MEDIUM':1, 'HIGH':2, 'VERY_HIGH':3}
    threshold = order[min_confidence]
    x = df[df['DEST'].eq(destination)].copy()
    if origin:
        x = x[x['ORIGIN'].eq(origin)]
    x = x[x['data_confidence'].map(order).fillna(-1) >= threshold]
    return x.sort_values(['flightsmart_score_v2','passengers'], ascending=False).head(top_n)


if __name__ == '__main__':
    print(recommend_historical_markets('HND', top_n=10).to_string(index=False))
