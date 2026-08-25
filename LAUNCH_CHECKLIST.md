# FlightSmart Japan — Beta Launch Checklist

## Before GitHub

- [ ] Run `python test_step6.py`.
- [ ] Run `python -m py_compile app.py duffel_client.py duffel_offer_adapter.py itinerary_scoring.py traveler_profiles.py airport_catalog.py travel_calendar.py score_v2_lookup.py`.
- [ ] Run `streamlit run app.py` locally and test Japanese and English.
- [ ] Test one-way and round-trip Demo mode.
- [ ] Confirm `.streamlit/secrets.toml` is not included in Git.
- [ ] Confirm no Duffel token appears anywhere in the repository.

## GitHub

- [ ] Create a repository such as `flightsmart-japan-beta`.
- [ ] Upload the contents of `github_repo` so `app.py` is at repository root.
- [ ] Keep `.gitignore`, `.python-version`, `requirements.txt`, and `.streamlit/config.toml`.
- [ ] Make the first beta commit.

## Streamlit Community Cloud

- [ ] Connect the GitHub account.
- [ ] Create a new app from the FlightSmart repository.
- [ ] Entrypoint: `app.py`.
- [ ] Python: 3.12.
- [ ] Add `DUFFEL_ACCESS_TOKEN` in Streamlit Secrets only when ready for live searches.
- [ ] Add `FLIGHTSMART_FEEDBACK_URL` when the feedback form exists.
- [ ] Deploy.
- [ ] Test Demo mode on desktop.
- [ ] Test Demo mode on a phone.
- [ ] Test Japanese and English.
- [ ] Only then test live Duffel mode.

## Before inviting testers

- [ ] Add a feedback-form URL.
- [ ] Read `PRIVACY_BETA.md` and adapt it to the actual services you use.
- [ ] Read `BETA_TERMS.md` and adapt it before wider public release.
- [ ] Confirm the app does not collect passport numbers or payment-card data.
- [ ] Confirm live prices show their limited validity where available.
- [ ] Invite a small group first — target 10 testers, not a broad launch.

## Beta success checkpoint

After the first 10 testers, review:

- Did they understand what the FlightSmart Score means?
- Did they understand that historical evidence is not a future-delay prediction?
- Did the recommended option feel useful?
- Did family travelers value the connection-sensitive profiles?
- Was Japanese wording natural and clear?
- Did anyone try to book directly in the app when booking was not supported?
- What feature did testers ask for most often?
