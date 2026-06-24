"""
DCF Analyst Training Module
-----------------------------
A knowledge base + interactive tutor explaining every manual input
in the DCF model: what it is, why it matters, and exactly where to
find it (10-K/annual report, NGX filings, company IR pages, etc.)

Used by dcf_model_live.py when a junior analyst needs guidance,
or run standalone as a training reference.
"""

# ---------------------------------------------------------------------
# KNOWLEDGE BASE
# ---------------------------------------------------------------------

INPUT_GUIDE = {

    "base_revenue": {
        "name": "Base Year Revenue",
        "what": "The company's total revenue (sales/turnover) for the most recent completed fiscal year. This is the starting point for all forecast projections.",
        "why": "Every other line item (EBIT, FCF, etc.) is projected as a percentage of revenue, or revenue itself is grown forward. An error here scales through the entire model.",
        "where_global": [
            "10-K (US companies) → Income Statement → 'Total Revenue' or 'Net Sales' (top line)",
            "Annual Report → Consolidated Statement of Profit or Loss → 'Revenue'",
            "Yahoo Finance: Statistics tab → 'Revenue (ttm)', or Financials tab → Income Statement",
        ],
        "where_ngx": [
            "NGX company filings page (ngxgroup.com) → select company → Financial Statements",
            "Annual Report (download PDF) → Statement of Profit or Loss and Other Comprehensive Income → 'Revenue' or 'Turnover' (usually first line)",
            "Company investor relations page (e.g. dangote.com/investors, mtnonline.com/investors)",
        ],
        "tips": "Use the GROUP/CONSOLIDATED figure, not parent-company-only, if the company has subsidiaries. Use the most recently completed FULL fiscal year (check year-end date — many NGX companies use Dec 31, but check).",
    },

    "ebit_margin": {
        "name": "EBIT Margin (Operating Margin)",
        "what": "Operating profit (EBIT = Earnings Before Interest and Tax) divided by revenue. Expressed as a decimal, e.g. 0.20 = 20%.",
        "why": "EBIT margin captures the core profitability of operations before financing and tax effects — it's the engine that drives projected cash flows. Small changes here have a large effect on valuation.",
        "where_global": [
            "10-K → Income Statement → 'Operating Income' ÷ 'Total Revenue'",
            "If 'Operating Income' isn't disclosed directly: EBIT ≈ Revenue − COGS − SG&A − D&A (check notes)",
        ],
        "where_ngx": [
            "Annual Report → Statement of Profit or Loss → look for 'Operating Profit' line",
            "If not shown directly: Operating Profit = Revenue − Cost of Sales − Operating Expenses (admin + selling/distribution expenses, BEFORE finance costs and tax)",
            "Double-check the notes to accounts — some NGX companies bury 'other income' or 'finance income' above the operating line; strip these out for a clean EBIT figure",
        ],
        "tips": "Use a 3-5 year average if margins are volatile (commodity businesses, FX-exposed companies — very relevant for NGX names with naira devaluation effects). One bad/good year can distort a single-year margin.",
    },

    "tax_rate": {
        "name": "Effective Tax Rate",
        "what": "The company's actual tax expense divided by pre-tax income (NOT the statutory/headline tax rate).",
        "why": "Converts EBIT to NOPAT (Net Operating Profit After Tax) — the cash that's actually available before reinvestment. Using the wrong rate over/understates cash flow.",
        "where_global": [
            "10-K → Income Statement → 'Income Tax Expense' ÷ 'Income Before Tax (Pretax Income)'",
            "Tax footnote often reconciles effective rate vs statutory rate — useful for sanity check",
        ],
        "where_ngx": [
            "Annual Report → Statement of Profit or Loss → 'Income Tax Expense' ÷ 'Profit Before Tax'",
            "Nigerian statutory Companies Income Tax rate is 30% (plus Education Tax, IT Levy for some sectors) — but many companies have a LOWER effective rate due to pioneer status, capital allowances, or tax holidays (common for Dangote Cement, BUA, etc.)",
        ],
        "tips": "If effective rate looks unusually low (<15%) or negative due to a one-off item (deferred tax credit, tax holiday expiry), consider normalizing toward the statutory rate (30% in Nigeria) for the terminal/long-run forecast, since tax holidays often expire.",
    },

    "dep_pct": {
        "name": "Depreciation & Amortization (% of Revenue)",
        "what": "D&A expense for the year, expressed as a percentage of revenue.",
        "why": "D&A is a non-cash expense already deducted in EBIT, so it's added BACK when calculating free cash flow (the company didn't actually pay this out in cash this year).",
        "where_global": [
            "10-K → Cash Flow Statement → Operating Activities → 'Depreciation and Amortization' (first adjustment to net income)",
            "Alternatively: Notes to Financial Statements → Property, Plant & Equipment note",
        ],
        "where_ngx": [
            "Annual Report → Statement of Cash Flows → Operating Activities section → 'Depreciation and Amortisation'",
            "Or: Notes → Property, Plant and Equipment → 'Depreciation charge for the year'",
        ],
        "tips": "Capital-intensive businesses (cement, telecoms, manufacturing — very common on NGX) often have D&A of 5-10% of revenue. Asset-light businesses (banks, consumer goods distributors) might be under 2%.",
    },

    "capex_pct": {
        "name": "Capital Expenditure (% of Revenue)",
        "what": "Cash spent on purchasing/upgrading fixed assets (property, plant, equipment), as a percentage of revenue.",
        "why": "CapEx is a real cash outflow needed to sustain/grow the business — it's subtracted from NOPAT+D&A to get free cash flow. Underestimating CapEx overstates the valuation.",
        "where_global": [
            "10-K → Cash Flow Statement → Investing Activities → 'Purchases of Property, Plant and Equipment' or 'Capital Expenditures'",
        ],
        "where_ngx": [
            "Annual Report → Statement of Cash Flows → Investing Activities → 'Purchase of Property, Plant and Equipment' (sometimes called 'Additions to PPE')",
            "Note: for high-growth NGX companies in expansion phase (e.g. new plant construction), CapEx can spike well above historical average — check Management Discussion for planned capex programs",
        ],
        "tips": "Compare CapEx to D&A: if CapEx consistently exceeds D&A, the company is in growth/expansion mode (common for NGX industrials). If CapEx ≈ D&A, the company is roughly maintaining its asset base ('maintenance capex').",
    },

    "nwc_pct": {
        "name": "Net Working Capital (% of Revenue)",
        "what": "Net working capital (current assets minus current liabilities, excluding cash and short-term debt) as a percentage of revenue. In this model it's used to estimate the INCREMENTAL cash tied up as the company grows.",
        "why": "As revenue grows, companies typically need more inventory, more receivables outstanding, etc. — this ties up cash that reduces free cash flow available to investors.",
        "where_global": [
            "10-K → Balance Sheet → (Total Current Assets − Cash) − (Total Current Liabilities − Short-term Debt), then divide by revenue",
            "Or use change in NWC directly from Cash Flow Statement → 'Changes in Working Capital' line items",
        ],
        "where_ngx": [
            "Annual Report → Statement of Financial Position → calculate: (Trade Receivables + Inventories + Prepayments) − (Trade Payables + Accruals)",
            "Then divide by Revenue from the Income Statement",
        ],
        "tips": "NGX companies with FX-denominated input costs (importers) often show working capital swings tied to naira volatility — consider using a multi-year average rather than a single year. If NWC is negative (common for retailers/telecoms that collect cash before paying suppliers), this can actually ADD to cash flow as the company grows — flag this rather than forcing a positive assumption.",
    },

    "net_debt": {
        "name": "Net Debt",
        "what": "Total interest-bearing debt (short-term + long-term borrowings) MINUS cash and cash equivalents.",
        "why": "Enterprise Value (what the DCF calculates) represents the value of the whole business available to ALL capital providers (debt + equity). To get to what EQUITY holders own, you subtract net debt — debt holders get paid first.",
        "where_global": [
            "10-K → Balance Sheet → 'Short-term Debt' + 'Long-term Debt' − 'Cash and Cash Equivalents' (and short-term investments if material)",
        ],
        "where_ngx": [
            "Annual Report → Statement of Financial Position → 'Borrowings' (current + non-current, sometimes split as 'Short-term loans' and 'Long-term loans') − 'Cash and Bank Balances'",
            "Watch for lease liabilities (IFRS 16) — decide consistently whether to treat these as debt",
        ],
        "tips": "If net debt is NEGATIVE (cash exceeds debt — a 'net cash' position), this ADDS to equity value rather than subtracting. Don't force it positive.",
    },

    "shares_outstanding": {
        "name": "Shares Outstanding",
        "what": "The total number of ordinary/common shares currently issued and held by shareholders.",
        "why": "The final step of a DCF divides total Equity Value by shares outstanding to get a per-share value — the number you compare to the market price.",
        "where_global": [
            "10-K cover page (shows shares outstanding as of a recent date)",
            "Yahoo Finance: Statistics tab → 'Shares Outstanding'",
        ],
        "where_ngx": [
            "Annual Report → Statement of Changes in Equity, or front cover/notes → 'Number of Ordinary Shares in Issue'",
            "NGX Fact Sheet for the stock (ngxgroup.com → company page) often lists shares outstanding directly",
        ],
        "tips": "Use shares IN ISSUE, not authorized share capital (these differ). If the company has treasury shares, decide whether to net them out — typically yes, since treasury shares don't receive dividends/value.",
    },

    "wacc": {
        "name": "WACC (Weighted Average Cost of Capital)",
        "what": "The blended required return for both debt and equity holders, used as the discount rate. Formula: WACC = (E/V × Cost of Equity) + (D/V × Cost of Debt × (1 − Tax Rate)), where E = equity value, D = debt value, V = E+D.",
        "why": "This is the discount rate — it converts future cash flows into today's money. Get this wrong and the whole valuation shifts dramatically (it's the single most sensitive input).",
        "where_global": [
            "Cost of Equity via CAPM: Risk-free rate (10-year US Treasury yield) + Beta × Equity Risk Premium (~4.5-5.5%)",
            "Beta: Yahoo Finance Statistics tab, or calculate via regression of stock returns vs market index",
            "Cost of Debt: company's interest expense ÷ total debt, or look at recent bond yields/credit rating",
        ],
        "where_ngx": [
            "Risk-free rate: Nigerian FGN Bond yield (10-year) — check CBN (cbn.gov.ng) or FMDQ (fmdq.com.ng) for current rates, typically 16-20% as of 2025/26",
            "Equity Risk Premium: add a country risk premium on top of a base global ERP (Damodaran's website publishes country risk premiums by country, including Nigeria)",
            "Beta: NGX stock betas vs the NGX All-Share Index — limited free sources; estimate conservatively (1.0-1.3 for most NGX large caps) if unavailable",
            "Cost of Debt: company's average borrowing rate from loan notes in the Annual Report, or Nigerian corporate bond yields",
        ],
        "tips": "For NGX companies, the WACC will be MUCH higher than US/global peers (often 18-25%+) due to higher risk-free rates and country risk — this is correct and reflects real Nigerian macro risk, not an error.",
    },

    "terminal_growth": {
        "name": "Terminal Growth Rate",
        "what": "The assumed perpetual growth rate of free cash flow AFTER the explicit forecast period (typically years 6+ forever).",
        "why": "Often 60-80% of total DCF value comes from the terminal value — this single number is hugely influential. It must be a rate the company (and economy) can sustain FOREVER.",
        "where_global": [
            "Should not exceed long-run nominal GDP growth of the country (~2-3% for US/developed markets)",
            "Cross-check against long-run inflation expectations",
        ],
        "where_ngx": [
            "Nigerian long-run nominal GDP growth ≈ real GDP growth (~3%) + long-run inflation expectations (~10-15% currently, though this should converge lower over decades)",
            "A reasonable long-run terminal growth for NGX names might be 8-12% in NAIRA terms — reflecting Nigeria's higher inflation environment — but NEVER above your WACC",
        ],
        "tips": "CRITICAL: terminal_growth must ALWAYS be less than WACC, or the formula breaks (produces negative/infinite values). If you're unsure, err on the conservative (lower) side — overly optimistic terminal growth is the most common DCF error.",
    },

    "growth_rates": {
        "name": "Revenue Growth Rate Forecast (Years 1-5)",
        "what": "Your projected annual revenue growth rate for each of the next several years (explicit forecast period).",
        "why": "Drives the entire revenue projection, which flows through to FCF for each forecast year.",
        "where_global": [
            "Historical growth: 10-K, 3-5 year revenue trend (calculate CAGR)",
            "Analyst consensus estimates: Yahoo Finance 'Analysis' tab shows revenue estimates for next 1-2 years",
            "Management guidance: earnings call transcripts, investor presentations",
        ],
        "where_ngx": [
            "Historical growth: calculate from 3-5 years of annual reports (note: NGX companies often show large naira-denominated growth that's partly inflation/FX-driven — try to separate volume growth from price/FX effects)",
            "Management guidance: NGX company investor presentations, earnings calls (often on company IR pages or NGX's X-Compliance portal)",
            "Industry/sector reports: NGX sector indices, CBN sector reports",
        ],
        "tips": "Start with recent historical growth, then taper toward a more sustainable long-run rate by year 5 (this is called 'fading' growth) — don't extrapolate a high growth year indefinitely.",
    },
}

# ---------------------------------------------------------------------
# TUTOR FUNCTIONS
# ---------------------------------------------------------------------

def explain(key, exchange="GLOBAL", verbose=True):
    """Print a full explanation for a given input key."""
    entry = INPUT_GUIDE.get(key)
    if not entry:
        print(f"No guide entry found for '{key}'.")
        return

    where_key = "where_ngx" if exchange == "NGX" else "where_global"

    print("\n" + "=" * 60)
    print(f"  {entry['name']}")
    print("=" * 60)
    print(f"\nWHAT IT IS:\n  {entry['what']}")
    print(f"\nWHY IT'S NEEDED:\n  {entry['why']}")
    print(f"\nWHERE TO FIND IT ({'NGX' if exchange == 'NGX' else 'Global / US'}):")
    for i, src in enumerate(entry[where_key], start=1):
        print(f"  {i}. {src}")
    if verbose and "tips" in entry:
        print(f"\nANALYST TIP:\n  {entry['tips']}")
    print()


def full_glossary(exchange="GLOBAL"):
    """Print explanations for every input, in logical model order."""
    order = ["base_revenue", "growth_rates", "ebit_margin", "tax_rate",
             "dep_pct", "capex_pct", "nwc_pct", "net_debt",
             "shares_outstanding", "wacc", "terminal_growth"]
    print("\n" + "#" * 60)
    print("#  DCF ANALYST TRAINING GUIDE")
    print(f"#  Exchange focus: {exchange}")
    print("#" * 60)
    for key in order:
        explain(key, exchange=exchange)


def interactive_tutor():
    """Run an interactive Q&A session: pick inputs to learn about."""
    print("DCF Analyst Training — Interactive Mode")
    print("Type the name of an input to learn about it, 'all' for the full")
    print("glossary, 'list' to see all topics, or 'quit' to exit.\n")

    exchange = input("Focus on GLOBAL or NGX sourcing guidance? [GLOBAL/NGX]: ").strip().upper()
    if exchange not in ("GLOBAL", "NGX"):
        exchange = "GLOBAL"

    while True:
        choice = input("\n> ").strip().lower()
        if choice in ("quit", "exit", "q"):
            print("Session ended.")
            break
        elif choice == "all":
            full_glossary(exchange=exchange)
        elif choice == "list":
            for k, v in INPUT_GUIDE.items():
                print(f"  {k:<22} - {v['name']}")
        elif choice in INPUT_GUIDE:
            explain(choice, exchange=exchange)
        else:
            # fuzzy match by name
            matches = [k for k in INPUT_GUIDE if choice in k or choice in INPUT_GUIDE[k]['name'].lower()]
            if matches:
                for m in matches:
                    explain(m, exchange=exchange)
            else:
                print(f"'{choice}' not recognized. Type 'list' to see available topics.")


# ---------------------------------------------------------------------
# INTEGRATION HOOK (used by dcf_model_live.py)
# ---------------------------------------------------------------------

def guided_input_prompt(key, exchange="GLOBAL", show_guide=True):
    """
    A drop-in replacement for a single input() call that shows the
    guide for an input BEFORE asking for it. Returns the raw string
    entered by the user.
    """
    if show_guide and key in INPUT_GUIDE:
        explain(key, exchange=exchange, verbose=True)
    entry = INPUT_GUIDE.get(key, {})
    label = entry.get("name", key)
    return input(f"Enter value for {label}: ").strip()


if __name__ == "__main__":
    interactive_tutor()
