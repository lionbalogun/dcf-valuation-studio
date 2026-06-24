# DCF Valuation Studio

A Streamlit app for building DCF valuations on global and NGX (Nigerian
Exchange) tickers, with built-in analyst training guidance.

## Why Financial Modeling Prep (not Yahoo Finance)?

Yahoo Finance blocks automated requests from cloud server IPs (Streamlit
Cloud, AWS, Heroku, etc.) — so yfinance always fails in deployment.
FMP is a proper REST API that works reliably from any server.

## API Key Setup (free, 2 minutes)

1. Register at https://financialmodelingprep.com/register (free tier = 250 req/day)
2. Copy your API key from the dashboard

**On Streamlit Cloud:**
- Go to your app → Settings → Secrets
- Add this line:
  ```
  FMP_API_KEY = "your_key_here"
  ```
- Save and redeploy

**Running locally:**
- Create the file `.streamlit/secrets.toml` in the project folder
- Add:
  ```toml
  FMP_API_KEY = "your_key_here"
  ```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (share a link with analysts — no install needed)

1. Push this folder to a **public** GitHub repo
2. Go to https://share.streamlit.io → New app
3. Select your repo, set main file to `app.py`
4. Add your FMP_API_KEY in Settings → Secrets
5. Deploy → share the link

## NGX Tickers

The app appends `.LG` automatically for NGX. Try:
DANGCEM, MTNN, GTCO, ZENITHBANK, BUACEMENT, AIRTELAFRI, NESTLE, STANBIC

FMP's NGX coverage is better than Yahoo Finance but still partial for
smaller-cap names — manual input + training mode works well as a fallback.

## Files

- `app.py` — Streamlit UI
- `dcf_engine.py` — DCF calculation engine
- `data_fetch.py` — FMP API integration
- `dcf_training_guide.py` — analyst training knowledge base
- `requirements.txt` — dependencies

## Disclaimer

For educational/training use. Always cross-check DCF outputs against
comparable company analysis and recent transaction multiples.
