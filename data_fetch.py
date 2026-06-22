"""
Data fetching module — pulls company fundamentals from Yahoo Finance.
Supports global tickers directly, and NGX (Nigerian Exchange) tickers
via the ".LG" suffix convention.

Note: Yahoo's NGX coverage is partial. If data is missing, this module
returns None and the caller (app.py) should fall back to manual input.
"""

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


def fetch_company_data(ticker, exchange="GLOBAL"):
    """
    Fetch fundamentals needed for the DCF from Yahoo Finance.

    exchange: "GLOBAL" or "NGX"
    For NGX, appends ".LG" suffix automatically if not already present.

    Returns a dict of inputs, or None if data couldn't be retrieved.
    """
    if not YF_AVAILABLE:
        return None

    symbol = ticker.upper()
    if exchange == "NGX" and not symbol.endswith(".LG"):
        symbol = symbol + ".LG"

    try:
        tk = yf.Ticker(symbol)
        info = tk.info
        financials = tk.financials
        balance_sheet = tk.balance_sheet
        cashflow = tk.cashflow

        if not info or ("regularMarketPrice" not in info and "currentPrice" not in info):
            return None

        # --- Revenue (most recent annual) ---
        revenue = None
        if not financials.empty and "Total Revenue" in financials.index:
            revenue = financials.loc["Total Revenue"].iloc[0]

        # --- EBIT margin ---
        ebit_margin = None
        if not financials.empty:
            if "Operating Income" in financials.index and revenue:
                ebit = financials.loc["Operating Income"].iloc[0]
                ebit_margin = ebit / revenue

        # --- Tax rate (effective) ---
        tax_rate = 0.25  # default fallback
        if not financials.empty and "Tax Provision" in financials.index and "Pretax Income" in financials.index:
            tax = financials.loc["Tax Provision"].iloc[0]
            pretax = financials.loc["Pretax Income"].iloc[0]
            if pretax and pretax != 0:
                tax_rate = max(0, min(tax / pretax, 0.45))

        # --- Depreciation, CapEx ---
        dep_pct = 0.04
        capex_pct = 0.05
        if not cashflow.empty and revenue:
            if "Depreciation And Amortization" in cashflow.index:
                dep = cashflow.loc["Depreciation And Amortization"].iloc[0]
                dep_pct = abs(dep) / revenue
            if "Capital Expenditure" in cashflow.index:
                capex = cashflow.loc["Capital Expenditure"].iloc[0]
                capex_pct = abs(capex) / revenue

        nwc_pct = 0.10  # generic placeholder

        # --- Net debt ---
        net_debt = 0
        if not balance_sheet.empty:
            total_debt = 0
            cash = 0
            if "Total Debt" in balance_sheet.index:
                total_debt = balance_sheet.loc["Total Debt"].iloc[0]
            if "Cash And Cash Equivalents" in balance_sheet.index:
                cash = balance_sheet.loc["Cash And Cash Equivalents"].iloc[0]
            net_debt = total_debt - cash

        # --- Shares outstanding & current price ---
        shares_outstanding = info.get("sharesOutstanding")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")

        # Convert shares to millions for consistency with revenue in millions
        if shares_outstanding:
            shares_outstanding = shares_outstanding / 1_000_000
        if revenue:
            revenue = revenue / 1_000_000
        if net_debt:
            net_debt = net_debt / 1_000_000

        # --- WACC estimate (simple CAPM-based default) ---
        beta = info.get("beta", 1.0) or 1.0

        if exchange == "NGX":
            risk_free = 0.18
            market_premium = 0.07
        else:
            risk_free = 0.045
            market_premium = 0.05

        wacc = risk_free + beta * market_premium

        return {
            "symbol": symbol,
            "company_name": info.get("longName", symbol),
            "currency": info.get("currency", "USD"),
            "current_price": current_price,
            "base_revenue": revenue,
            "ebit_margin": ebit_margin if ebit_margin else 0.15,
            "tax_rate": tax_rate,
            "dep_pct": dep_pct,
            "capex_pct": capex_pct,
            "nwc_pct": nwc_pct,
            "net_debt": net_debt,
            "shares_outstanding": shares_outstanding,
            "wacc": round(wacc, 4),
            "beta": beta,
        }

    except Exception:
        return None
