"""
Data fetching module — uses Financial Modeling Prep (FMP) API.

Why FMP instead of yfinance:
- yfinance scrapes Yahoo Finance HTML, which blocks cloud server IPs
  (Streamlit Cloud, Heroku, AWS, etc.) — so it always fails in deployment
- FMP is a proper REST API that works from any server, including Streamlit Cloud
- Free tier: 250 requests/day — plenty for analyst training use

Setup:
1. Get a FREE API key at https://financialmodelingprep.com/register
2. In Streamlit Cloud: Settings → Secrets → add:
      FMP_API_KEY = "your_key_here"
3. Locally: create a file called .streamlit/secrets.toml containing:
      FMP_API_KEY = "your_key_here"

NGX support:
- FMP covers major NGX tickers. Use the exchange suffix format e.g. "DANGCEM.LG"
- If a ticker isn't found on FMP, the app falls back to manual input.
"""

import requests
import streamlit as st

FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _get_api_key():
    """Pull API key from Streamlit secrets (works locally and on Cloud)."""
    try:
        return st.secrets["FMP_API_KEY"]
    except Exception:
        return None


def _fmp_get(endpoint, params=None, api_key=None):
    """Make a GET request to FMP and return JSON, or None on failure."""
    if not api_key:
        return None
    p = {"apikey": api_key}
    if params:
        p.update(params)
    try:
        r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=10)
        r.raise_for_status()
        data = r.json()
        # FMP returns {"Error Message": "..."} on bad key / unknown ticker
        if isinstance(data, dict) and "Error Message" in data:
            return None
        if isinstance(data, list) and len(data) == 0:
            return None
        return data
    except Exception:
        return None


def fetch_company_data(ticker, exchange="GLOBAL"):
    """
    Fetch fundamentals from Financial Modeling Prep.

    exchange: "GLOBAL" or "NGX"
    For NGX, appends ".LG" suffix automatically if not already present.

    Returns a dict of inputs ready for the DCF, or None if unavailable.
    """
    api_key = _get_api_key()
    if not api_key:
        return {"_error": "no_key"}   # special signal so app.py shows setup instructions

    symbol = ticker.strip().upper()
    if exchange == "NGX" and not symbol.endswith(".LG"):
        symbol = symbol + ".LG"

    # ── 1. Company profile (price, shares, beta, name, currency) ────────
    profile_data = _fmp_get(f"profile/{symbol}", api_key=api_key)
    if not profile_data:
        return None
    profile = profile_data[0]

    company_name  = profile.get("companyName", symbol)
    currency      = profile.get("currency", "NGN" if exchange == "NGX" else "USD")
    current_price = profile.get("price")
    beta          = float(profile.get("beta") or 1.0)
    beta          = max(0.3, min(beta, 3.0))
    shares_outstanding = profile.get("sharesOutstanding")    # raw units

    # ── 2. Income statement (most recent annual) ─────────────────────────
    income_data = _fmp_get(f"income-statement/{symbol}",
                           params={"limit": 1}, api_key=api_key)
    income = income_data[0] if income_data else {}

    revenue    = income.get("revenue")
    ebit       = income.get("operatingIncome") or income.get("ebitda")
    tax_exp    = income.get("incomeTaxExpense")
    pretax_inc = income.get("incomeBeforeTax")

    ebit_margin = (ebit / revenue) if (ebit and revenue) else 0.15
    if tax_exp and pretax_inc and pretax_inc != 0:
        tax_rate = max(0.01, min(abs(tax_exp / pretax_inc), 0.45))
    else:
        tax_rate = 0.30 if exchange == "NGX" else 0.25

    # ── 3. Cash flow statement ────────────────────────────────────────────
    cf_data = _fmp_get(f"cash-flow-statement/{symbol}",
                       params={"limit": 1}, api_key=api_key)
    cf = cf_data[0] if cf_data else {}

    dep   = cf.get("depreciationAndAmortization")
    capex = cf.get("capitalExpenditure")

    dep_pct   = abs(dep / revenue)   if (dep   and revenue) else 0.04
    capex_pct = abs(capex / revenue) if (capex and revenue) else 0.05
    nwc_pct   = 0.10

    # ── 4. Balance sheet ─────────────────────────────────────────────────
    bs_data = _fmp_get(f"balance-sheet-statement/{symbol}",
                       params={"limit": 1}, api_key=api_key)
    bs = bs_data[0] if bs_data else {}

    total_debt = bs.get("totalDebt") or 0
    cash       = bs.get("cashAndCashEquivalents") or bs.get("cashAndShortTermInvestments") or 0
    net_debt   = total_debt - cash

    # ── 5. WACC estimate (CAPM) ───────────────────────────────────────────
    if exchange == "NGX":
        risk_free      = 0.18   # Nigerian FGN 10-yr bond (~18-20% as of 2025/26)
        market_premium = 0.07
    else:
        risk_free      = 0.045  # US 10-yr Treasury
        market_premium = 0.05

    wacc = risk_free + beta * market_premium

    # ── 6. Unit conversion → millions ─────────────────────────────────────
    def to_m(v):
        return v / 1_000_000 if v else None

    return {
        "symbol":             symbol,
        "company_name":       company_name,
        "currency":           currency,
        "current_price":      current_price,
        "base_revenue":       to_m(revenue),
        "ebit_margin":        round(ebit_margin, 4),
        "tax_rate":           round(tax_rate, 4),
        "dep_pct":            round(dep_pct, 4),
        "capex_pct":          round(capex_pct, 4),
        "nwc_pct":            nwc_pct,
        "net_debt":           to_m(net_debt),
        "shares_outstanding": to_m(shares_outstanding),
        "wacc":               round(wacc, 4),
        "beta":               beta,
    }
