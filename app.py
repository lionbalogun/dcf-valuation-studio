"""
NGX & Global DCF Valuation Studio
-----------------------------------
A Streamlit app combining:
- DCF calculation engine
- Live data fetch (Yahoo Finance, with .LG suffix for NGX)
- Manual override inputs with inline analyst training guidance
- Sensitivity table + charts

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import altair as alt

from dcf_engine import run_dcf, sensitivity_table
from data_fetch import fetch_company_data
from dcf_training_guide import INPUT_GUIDE


# ---------------------------------------------------------------------
# PAGE CONFIG & STYLE
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="DCF Valuation Studio",
    page_icon="📊",
    layout="wide",
)

CUSTOM_CSS = """
<style>
/* ---- Design tokens ----
   Palette: deep ledger green (#0F3D2E), parchment (#F7F3E8),
   warm gold accent (#C8932E), ink (#1C1B17), muted sage (#6E8B7A)
   Type: 'Source Serif 4' for headers (ledger feel), 'IBM Plex Sans' for body/data
*/

@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

.main {
    background-color: #F7F3E8;
}

h1, h2, h3 {
    font-family: 'Source Serif 4', serif;
    color: #0F3D2E;
}

h1 {
    font-weight: 700;
    letter-spacing: -0.01em;
}

.app-header {
    border-bottom: 3px double #0F3D2E;
    padding-bottom: 0.75rem;
    margin-bottom: 1.25rem;
}

.app-header .ticker {
    font-family: 'IBM Plex Mono', monospace;
    color: #C8932E;
    font-size: 0.95rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.ledger-line {
    border-top: 1px solid #D8CFB8;
    margin: 1rem 0;
}

.metric-card {
    background-color: #FFFFFF;
    border: 1px solid #E2D9C3;
    border-left: 4px solid #0F3D2E;
    border-radius: 4px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.5rem;
}

.metric-card .label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6E8B7A;
}

.metric-card .value {
    font-family: 'Source Serif 4', serif;
    font-size: 1.6rem;
    font-weight: 600;
    color: #1C1B17;
    margin-top: 0.15rem;
}

.upside-positive {
    color: #1F7A4D;
    font-weight: 600;
}

.upside-negative {
    color: #B0492E;
    font-weight: 600;
}

.guide-box {
    background-color: #FFFEF9;
    border: 1px solid #E2D9C3;
    border-radius: 4px;
    padding: 0.75rem 1rem;
    font-size: 0.88rem;
    color: #3A3A33;
}

.guide-box .guide-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #C8932E;
    margin-bottom: 0.25rem;
    display: block;
}

[data-testid="stSidebar"] {
    background-color: #0F3D2E;
}

[data-testid="stSidebar"] * {
    color: #F7F3E8 !important;
}

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stSelectbox > div {
    color: #1C1B17 !important;
}

[data-testid="stSidebar"] hr {
    border-color: #2A5A45;
}

.stButton button {
    background-color: #C8932E;
    color: #1C1B17;
    border: none;
    font-weight: 600;
    border-radius: 4px;
}

.stButton button:hover {
    background-color: #B07F22;
    color: #FFFFFF;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# SESSION STATE DEFAULTS
# ---------------------------------------------------------------------

DEFAULTS = {
    "base_revenue": 1000.0,
    "ebit_margin": 0.20,
    "tax_rate": 0.25,
    "dep_pct": 0.04,
    "capex_pct": 0.05,
    "nwc_pct": 0.10,
    "net_debt": 500.0,
    "shares_outstanding": 100.0,
    "wacc": 0.09,
    "terminal_growth": 0.025,
    "growth_rates": [0.10, 0.08, 0.06, 0.05, 0.04],
}

CURRENCY_SYMBOL = {"USD": "$", "NGN": "₦", "GBP": "£", "EUR": "€"}


def fmt_currency(value, currency):
    symbol = CURRENCY_SYMBOL.get(currency, "")
    return f"{symbol}{value:,.2f}"


# ---------------------------------------------------------------------
# SIDEBAR — DATA SOURCE
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 📊 DCF Valuation Studio")
    st.markdown("---")

    st.markdown("### Data source")
    exchange = st.radio(
        "Exchange",
        options=["GLOBAL", "NGX"],
        help="NGX tickers will have '.LG' appended automatically for Yahoo Finance lookup.",
    )

    ticker = st.text_input(
        "Ticker symbol",
        placeholder="e.g. AAPL, MSFT  /  DANGCEM, MTNN, GTCO",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        fetch_clicked = st.button("Fetch data", use_container_width=True)
    with col_b:
        clear_clicked = st.button("Use manual", use_container_width=True)

    st.markdown("---")
    training_mode = st.toggle(
        "🎓 Training mode",
        value=False,
        help="Show analyst guidance (what it is, why it matters, where to find it) next to each input.",
    )

    st.markdown("---")
    st.markdown(
        "<small>Built for walkthroughs of DCF mechanics. "
        "Yahoo Finance NGX coverage is partial — manual input is often "
        "required for Nigerian tickers.</small>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# FETCH DATA
# ---------------------------------------------------------------------

if "fetched_data" not in st.session_state:
    st.session_state.fetched_data = None
if "meta" not in st.session_state:
    st.session_state.meta = {"currency": "USD", "company_name": "Manual Model"}

if fetch_clicked:
    if not ticker.strip():
        st.sidebar.warning("Enter a ticker symbol first.")
    else:
        with st.spinner(f"Fetching data for {ticker.upper()}..."):
            data = fetch_company_data(ticker.strip(), exchange=exchange)
        if data is None:
            st.sidebar.error(
                f"No data found for '{ticker.upper()}'"
                + (".LG" if exchange == "NGX" else "")
                + ". Falling back to manual input — adjust values in the form."
            )
            st.session_state.fetched_data = None
            st.session_state.meta = {
                "currency": "NGN" if exchange == "NGX" else "USD",
                "company_name": ticker.upper(),
            }
        else:
            st.session_state.fetched_data = data
            st.session_state.meta = data
            st.sidebar.success(f"Loaded {data['company_name']} ({data['symbol']})")

if clear_clicked:
    st.session_state.fetched_data = None
    st.session_state.meta = {"currency": "NGN" if exchange == "NGX" else "USD", "company_name": ticker.upper() or "Manual Model"}


fetched = st.session_state.fetched_data
meta = st.session_state.meta
currency = meta.get("currency", "USD")


def get_default(key, fallback_key=None):
    """Get a default value: fetched data first, else DEFAULTS."""
    if fetched and fetched.get(key) is not None:
        val = fetched[key]
        return val
    return DEFAULTS.get(fallback_key or key)


# ---------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------

company_name = meta.get("company_name", "Manual Model")
ticker_display = meta.get("symbol", ticker.upper() or "—")

st.markdown(
    f"""
    <div class="app-header">
        <div class="ticker">{ticker_display} · {exchange}</div>
        <h1>{company_name}</h1>
        <div>Discounted Cash Flow Valuation</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# HELPER: GUIDE EXPANDER
# ---------------------------------------------------------------------

def guide_for(key):
    """Render an expandable training guide box for a given input key."""
    if not training_mode:
        return
    entry = INPUT_GUIDE.get(key)
    if not entry:
        return
    where_key = "where_ngx" if exchange == "NGX" else "where_global"
    with st.expander(f"ℹ️ About: {entry['name']}", expanded=False):
        st.markdown(
            f"""
            <div class="guide-box">
            <span class="guide-label">What it is</span>
            {entry['what']}
            <br><br>
            <span class="guide-label">Why it's needed</span>
            {entry['why']}
            <br><br>
            <span class="guide-label">Where to find it ({'NGX' if exchange == 'NGX' else 'Global / US'})</span>
            {"<br>".join(f"&bull; {src}" for src in entry[where_key])}
            <br><br>
            <span class="guide-label">Analyst tip</span>
            {entry.get('tips', '')}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------
# INPUT FORM
# ---------------------------------------------------------------------

st.markdown("## Assumptions")
st.caption(
    "Values are pre-filled from Yahoo Finance where available. "
    "Review and adjust every figure before relying on the output."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Revenue & Growth")

    base_revenue = st.number_input(
        "Base year revenue (millions)",
        min_value=0.0,
        value=float(get_default("base_revenue") or DEFAULTS["base_revenue"]),
        step=10.0,
        format="%.2f",
    )
    guide_for("base_revenue")

    st.markdown("**5-Year Revenue Growth (%)**")
    growth_defaults = DEFAULTS["growth_rates"]
    growth_rates = []
    g_cols = st.columns(5)
    for i, gcol in enumerate(g_cols):
        with gcol:
            g = st.number_input(
                f"Y{i+1}",
                min_value=-50.0,
                max_value=100.0,
                value=growth_defaults[i] * 100,
                step=0.5,
                format="%.1f",
                key=f"growth_{i}",
            )
            growth_rates.append(g / 100)
    guide_for("growth_rates")

with col2:
    st.markdown("#### Margins & Tax")

    ebit_margin = st.number_input(
        "EBIT margin (%)",
        min_value=-100.0,
        max_value=100.0,
        value=float(get_default("ebit_margin") or DEFAULTS["ebit_margin"]) * 100,
        step=0.5,
        format="%.2f",
    ) / 100
    guide_for("ebit_margin")

    tax_rate = st.number_input(
        "Effective tax rate (%)",
        min_value=0.0,
        max_value=60.0,
        value=float(get_default("tax_rate") or DEFAULTS["tax_rate"]) * 100,
        step=0.5,
        format="%.2f",
    ) / 100
    guide_for("tax_rate")

    dep_pct = st.number_input(
        "Depreciation & amortization (% of revenue)",
        min_value=0.0,
        max_value=50.0,
        value=float(get_default("dep_pct") or DEFAULTS["dep_pct"]) * 100,
        step=0.25,
        format="%.2f",
    ) / 100
    guide_for("dep_pct")

    capex_pct = st.number_input(
        "CapEx (% of revenue)",
        min_value=0.0,
        max_value=50.0,
        value=float(get_default("capex_pct") or DEFAULTS["capex_pct"]) * 100,
        step=0.25,
        format="%.2f",
    ) / 100
    guide_for("capex_pct")

    nwc_pct = st.number_input(
        "Net working capital (% of revenue)",
        min_value=-50.0,
        max_value=50.0,
        value=float(get_default("nwc_pct") or DEFAULTS["nwc_pct"]) * 100,
        step=0.5,
        format="%.2f",
    ) / 100
    guide_for("nwc_pct")

with col3:
    st.markdown("#### Capital Structure & Discounting")

    net_debt = st.number_input(
        "Net debt (millions)",
        value=float(get_default("net_debt") if get_default("net_debt") is not None else DEFAULTS["net_debt"]),
        step=10.0,
        format="%.2f",
        help="Total debt minus cash. Negative = net cash position.",
    )
    guide_for("net_debt")

    shares_outstanding = st.number_input(
        "Shares outstanding (millions)",
        min_value=0.01,
        value=float(get_default("shares_outstanding") or DEFAULTS["shares_outstanding"]),
        step=1.0,
        format="%.2f",
    )
    guide_for("shares_outstanding")

    wacc_default = get_default("wacc") or DEFAULTS["wacc"]
    wacc = st.number_input(
        "WACC (%)",
        min_value=0.1,
        max_value=60.0,
        value=float(wacc_default) * 100,
        step=0.25,
        format="%.2f",
    ) / 100
    guide_for("wacc")

    tg_default = 0.12 if exchange == "NGX" else DEFAULTS["terminal_growth"]
    terminal_growth = st.number_input(
        "Terminal growth rate (%)",
        min_value=0.0,
        max_value=30.0,
        value=float(tg_default) * 100,
        step=0.25,
        format="%.2f",
        help="Must be lower than WACC.",
    ) / 100
    guide_for("terminal_growth")

    if terminal_growth >= wacc:
        st.error("Terminal growth must be less than WACC. Adjust one of the values above.")


# ---------------------------------------------------------------------
# RUN MODEL
# ---------------------------------------------------------------------

st.markdown("<div class='ledger-line'></div>", unsafe_allow_html=True)

valid = terminal_growth < wacc

if valid:
    inputs = dict(
        base_revenue=base_revenue,
        growth_rates=growth_rates,
        ebit_margin=ebit_margin,
        tax_rate=tax_rate,
        dep_pct=dep_pct,
        capex_pct=capex_pct,
        nwc_pct=nwc_pct,
        wacc=wacc,
        terminal_growth=terminal_growth,
        net_debt=net_debt,
        shares_outstanding=shares_outstanding,
    )

    results = run_dcf(**inputs)

    # --- Headline metrics ---
    st.markdown("## Valuation Output")

    current_price = meta.get("current_price")
    price_per_share = results["price_per_share"]

    metric_cols = st.columns(4 if current_price else 3)

    with metric_cols[0]:
        st.markdown(
            f"""<div class="metric-card">
            <div class="label">Enterprise Value</div>
            <div class="value">{fmt_currency(results['enterprise_value'], currency)}m</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with metric_cols[1]:
        st.markdown(
            f"""<div class="metric-card">
            <div class="label">Equity Value</div>
            <div class="value">{fmt_currency(results['equity_value'], currency)}m</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with metric_cols[2]:
        st.markdown(
            f"""<div class="metric-card">
            <div class="label">Implied Price / Share</div>
            <div class="value">{fmt_currency(price_per_share, currency)}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    if current_price:
        upside = (price_per_share / current_price - 1) * 100
        css_class = "upside-positive" if upside >= 0 else "upside-negative"
        sign = "+" if upside >= 0 else ""
        with metric_cols[3]:
            st.markdown(
                f"""<div class="metric-card">
                <div class="label">vs Market ({fmt_currency(current_price, currency)})</div>
                <div class="value"><span class="{css_class}">{sign}{upside:.1f}%</span></div>
                </div>""",
                unsafe_allow_html=True,
            )

    # --- Cash flow table & chart ---
    st.markdown("### Free Cash Flow Projection")

    df = pd.DataFrame({
        "Year": list(range(1, len(results["fcfs"]) + 1)),
        "Revenue": results["revenues"],
        "FCF": results["fcfs"],
        "PV of FCF": results["pv_fcfs"],
    })

    table_col, chart_col = st.columns([1, 1.3])

    with table_col:
        st.dataframe(
            df.style.format({"Revenue": "{:,.1f}", "FCF": "{:,.1f}", "PV of FCF": "{:,.1f}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown(
            f"""
            <div class="metric-card" style="margin-top: 0.5rem;">
            <div class="label">Terminal Value (undiscounted)</div>
            <div class="value" style="font-size:1.2rem;">{fmt_currency(results['terminal_value'], currency)}m</div>
            </div>
            <div class="metric-card">
            <div class="label">PV of Terminal Value</div>
            <div class="value" style="font-size:1.2rem;">{fmt_currency(results['pv_terminal_value'], currency)}m</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chart_col:
        chart_df = df.melt(id_vars="Year", value_vars=["FCF", "PV of FCF"], var_name="Series", value_name="Value")
        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X("Year:O", title="Forecast Year"),
                y=alt.Y("Value:Q", title=f"Amount ({currency}m)"),
                color=alt.Color(
                    "Series:N",
                    scale=alt.Scale(domain=["FCF", "PV of FCF"], range=["#6E8B7A", "#0F3D2E"]),
                    legend=alt.Legend(title=None, orient="top"),
                ),
                xOffset="Series:N",
                tooltip=["Year", "Series", alt.Tooltip("Value:Q", format=",.1f")],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

        ev_split_df = pd.DataFrame({
            "Component": ["PV of Forecast FCFs", "PV of Terminal Value"],
            "Value": [sum(results["pv_fcfs"]), results["pv_terminal_value"]],
        })
        pie = (
            alt.Chart(ev_split_df)
            .mark_arc(innerRadius=60)
            .encode(
                theta="Value:Q",
                color=alt.Color(
                    "Component:N",
                    scale=alt.Scale(range=["#C8932E", "#0F3D2E"]),
                    legend=alt.Legend(title=None, orient="bottom"),
                ),
                tooltip=["Component", alt.Tooltip("Value:Q", format=",.1f")],
            )
            .properties(height=220, title="Enterprise Value composition")
        )
        st.altair_chart(pie, use_container_width=True)

    # --- Sensitivity table ---
    st.markdown("### Sensitivity: Price per Share")
    st.caption("Rows = WACC, Columns = Terminal Growth Rate")

    wacc_range = [round(wacc + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    growth_range = [round(terminal_growth + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    wacc_range = [w for w in wacc_range if w > 0]
    growth_range = [g for g in growth_range if g >= 0]

    table = sensitivity_table(inputs, wacc_range, growth_range)

    sens_df = pd.DataFrame(table).T
    sens_df.index = [f"{w:.2%}" for w in sens_df.index]
    sens_df.columns = [f"{g:.2%}" for g in sens_df.columns]

    def highlight_base(val, row_label, col_label):
        is_base_row = row_label == f"{wacc:.2%}"
        is_base_col = col_label == f"{terminal_growth:.2%}"
        if is_base_row and is_base_col:
            return "background-color: #C8932E; color: #1C1B17; font-weight: 600;"
        elif is_base_row or is_base_col:
            return "background-color: #F0E9D8;"
        return ""

    styled = sens_df.style.format("{:.2f}")
    for r in sens_df.index:
        for c in sens_df.columns:
            styled = styled.set_properties(
                subset=pd.IndexSlice[r, c],
                **{"background-color": "#C8932E" if (r == f"{wacc:.2%}" and c == f"{terminal_growth:.2%}")
                   else ("#F0E9D8" if (r == f"{wacc:.2%}" or c == f"{terminal_growth:.2%}") else "")}
            )

    st.dataframe(styled, use_container_width=True)
    st.caption(f"Highlighted cell/row/column mark your selected WACC ({wacc:.2%}) and terminal growth ({terminal_growth:.2%}).")

else:
    st.warning("Fix the terminal growth / WACC relationship above to see valuation output.")


# ---------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------

st.markdown("<div class='ledger-line'></div>", unsafe_allow_html=True)
st.caption(
    "This tool is for educational/illustrative purposes. DCF outputs are highly "
    "sensitive to assumptions — always sanity-check against comparable company "
    "valuations and recent transaction multiples."
)
