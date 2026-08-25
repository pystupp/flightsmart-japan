# FlightSmart Japan 🇺🇸✈️🇯🇵

FlightSmart Japan is a bilingual public-beta decision-support app for comparing U.S.–Japan flight options using live itinerary data and historical BTS/DOT operating evidence.

## What the beta compares

- Historical BTS/DOT operating evidence
- Connection convenience
- Itinerary duration
- Price relative to the offers returned in the current search
- Traveler priorities such as family travel, fewer connections, reliability, price, and duration

FlightSmart does **not** predict whether a future flight will be delayed and does not replace airline, booking-provider, immigration, or government guidance.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Start with **Demo data / デモデータ** to verify the app without a Duffel token.

## Optional live-search secrets

Create `.streamlit/secrets.toml` locally (never commit it):

```toml
DUFFEL_ACCESS_TOKEN = "your_duffel_token"
FLIGHTSMART_FEEDBACK_URL = "https://your-feedback-form-url"
```

A safe template is included as `.streamlit/secrets.toml.example`.

## Streamlit Community Cloud

1. Push the contents of this folder to a GitHub repository.
2. Connect GitHub to Streamlit Community Cloud.
3. Create an app and select `app.py` as the entrypoint.
4. In Advanced settings, choose Python 3.12.
5. Paste secrets into the Streamlit Secrets field instead of committing them.
6. Deploy and first test Demo mode before enabling live Duffel searches.

See `LAUNCH_CHECKLIST.md` and `FIRST_10_TESTERS.md` before sharing the beta.
