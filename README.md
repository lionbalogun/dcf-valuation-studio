# DCF Valuation Studio

A Streamlit app for building DCF valuations on global and NGX (Nigerian
Exchange) tickers, with built-in analyst training guidance.

## Features

- Live data fetch from Yahoo Finance (global tickers, plus NGX tickers
  via the `.LG` suffix — coverage is partial for NGX names)
- Manual override for every assumption
- Training mode: inline "what is this / why it matters / where to find
  it" guidance for each input, with separate sourcing notes for global
  vs NGX companies
- Free cash flow projection table and chart
- Enterprise value composition (forecast FCF vs terminal value)
- Sensitivity table: price per share across WACC and terminal growth

## Setup

```bash
pip install -r requirements.txt
```

## Run locally

```bash
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`.

## Share with others

### Option 1: Streamlit Community Cloud (free, recommended)
1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io and connect the repo
3. Set the main file to `app.py`
4. Share the resulting public URL

### Option 2: Run on your network
```bash
streamlit run app.py --server.address 0.0.0.0
```
Others on the same network can access it via your machine's IP, e.g.
`http://192.168.1.50:8501`

## File structure

- `app.py` — main Streamlit interface
- `dcf_engine.py` — pure DCF calculation functions
- `data_fetch.py` — Yahoo Finance / NGX data retrieval
- `dcf_training_guide.py` — analyst training knowledge base
- `requirements.txt` — dependencies

## Notes on NGX tickers

Yahoo Finance's coverage of the Nigerian Exchange is inconsistent.
Try tickers like `DANGCEM`, `MTNN`, `GTCO`, `ZENITHBANK`, `BUACEMENT`
(the app appends `.LG` automatically). If no data is found, the app
falls back to manual input — use the training mode to source figures
from annual reports and NGX filings.

## Disclaimer

For educational/illustrative use. DCF outputs are highly sensitive to
input assumptions — always cross-check against comparable company
analysis and recent transaction multiples.
