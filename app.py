"""
NGX & Global DCF Valuation Studio
-----------------------------------
Analyst feedback improvements:
  1. Scenario manager  — save/switch/compare up to 3 named scenarios
  2. Unit scale        — inputs in Thousands, Millions, or Billions
  3. Discount factors  — shown in the FCF output table
  4. Training mode     — inline guidance per input (existing, unchanged)

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import altair as alt
import copy

from dcf_engine import run_dcf, sensitivity_table
from data_fetch import fetch_company_data
from dcf_training_guide import INPUT_GUIDE


# ─────────────────────────────────────────────
# PAGE CONFIG & STYLE
# ─────────────────────────────────────────────

st.set_page_config(page_title="DCF Valuation Studio", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"]          { font-family: 'IBM Plex Sans', sans-serif; }
.main                                { background-color: #F7F3E8; }
h1, h2, h3                           { font-family: 'Source Serif 4', serif; color: #0F3D2E; }
h1                                   { font-weight: 700; letter-spacing: -0.01em; }

.app-header                          { border-bottom: 3px double #0F3D2E; padding-bottom: .75rem; margin-bottom: 1.25rem; }
.app-header .ticker                  { font-family: 'IBM Plex Mono', monospace; color: #C8932E; font-size: .95rem; letter-spacing: .08em; text-transform: uppercase; }
.ledger-line                         { border-top: 1px solid #D8CFB8; margin: 1rem 0; }

.metric-card                         { background: #fff; border: 1px solid #E2D9C3; border-left: 4px solid #0F3D2E; border-radius: 4px; padding: .9rem 1.1rem; margin-bottom: .5rem; }
.metric-card .label                  { font-family: 'IBM Plex Mono', monospace; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: #6E8B7A; }
.metric-card .value                  { font-family: 'Source Serif 4', serif; font-size: 1.6rem; font-weight: 600; color: #1C1B17; margin-top: .15rem; }
.upside-positive                     { color: #1F7A4D; font-weight: 600; }
.upside-negative                     { color: #B0492E; font-weight: 600; }

.scenario-pill                       { display:inline-block; background:#0F3D2E; color:#F7F3E8; font-family:'IBM Plex Mono',monospace; font-size:.72rem; padding:.18rem .6rem; border-radius:99px; margin-right:.35rem; }
.scenario-pill.active                { background:#C8932E; color:#1C1B17; }

.guide-box                           { background:#FFFEF9; border:1px solid #E2D9C3; border-radius:4px; padding:.75rem 1rem; font-size:.88rem; color:#3A3A33; }
.guide-box .guide-label              { font-family:'IBM Plex Mono',monospace; font-size:.7rem; text-transform:uppercase; letter-spacing:.1em; color:#C8932E; margin-bottom:.25rem; display:block; }

[data-testid="stSidebar"]            { background-color: #0F3D2E; }
[data-testid="stSidebar"] *          { color: #F7F3E8 !important; }
[data-testid="stSidebar"] hr        { border-color: #2A5A45; }

.stButton button                     { background-color:#C8932E; color:#1C1B17; border:none; font-weight:600; border-radius:4px; }
.stButton button:hover               { background-color:#B07F22; color:#fff; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTS & HELPERS
# ─────────────────────────────────────────────

CURRENCY_SYMBOL = {"USD": "$", "NGN": "₦", "GBP": "£", "EUR": "€"}

SCALE_OPTIONS   = {"Thousands": 1_000, "Millions": 1_000_000, "Billions": 1_000_000_000}
SCALE_LABELS    = {"Thousands": "K", "Millions": "M", "Billions": "B"}

DEFAULTS = dict(
    base_revenue=1_000.0, ebit_margin=0.20, tax_rate=0.25,
    dep_pct=0.04, capex_pct=0.05, nwc_pct=0.10,
    net_debt=500.0, shares_outstanding=100.0,
    wacc=0.09, terminal_growth=0.025,
    growth_rates=[0.10, 0.08, 0.06, 0.05, 0.04],
)

SCENARIO_COLORS = ["#0F3D2E", "#C8932E", "#6E8B7A"]


def fmt(value, currency):
    sym = CURRENCY_SYMBOL.get(currency, "")
    return f"{sym}{value:,.2f}"


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

def _blank_scenario(name):
    return {"name": name, "inputs": copy.deepcopy(DEFAULTS), "results": None, "meta": {}}

if "scenarios" not in st.session_state:
    st.session_state.scenarios    = [_blank_scenario("Base Case")]
    st.session_state.active_idx   = 0

if "fetched_data" not in st.session_state:
    st.session_state.fetched_data = None
if "meta" not in st.session_state:
    st.session_state.meta         = {"currency": "USD", "company_name": "Manual Model"}
if "unit_scale" not in st.session_state:
    st.session_state.unit_scale   = "Millions"


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 DCF Valuation Studio")
    st.markdown("---")

    # ── Unit scale ──────────────────────────
    st.markdown("### Display units")
    unit_scale = st.selectbox(
        "All monetary inputs are in:",
        options=list(SCALE_OPTIONS.keys()),
        index=list(SCALE_OPTIONS.keys()).index(st.session_state.unit_scale),
        help="Change this if your source data is in thousands or billions. "
             "All inputs and outputs will use the same unit.",
    )
    st.session_state.unit_scale = unit_scale
    scale_label = SCALE_LABELS[unit_scale]

    st.markdown("---")

    # ── Scenario manager ─────────────────────
    st.markdown("### Scenarios")
    scenarios    = st.session_state.scenarios
    active_idx   = st.session_state.active_idx

    scenario_names = [s["name"] for s in scenarios]
    chosen_name    = st.radio("Active scenario", scenario_names,
                              index=active_idx, key="scenario_radio")
    st.session_state.active_idx = scenario_names.index(chosen_name)
    active_idx = st.session_state.active_idx

    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        if st.button("＋ Add", use_container_width=True,
                     disabled=len(scenarios) >= 3):
            n = len(scenarios) + 1
            label = ["", "Bull Case", "Bear Case", "Alt Case"][n] if n <= 3 else f"Case {n}"
            scenarios.append(_blank_scenario(label))
            st.session_state.active_idx = len(scenarios) - 1
            st.rerun()
    with sc_col2:
        if st.button("🗑 Remove", use_container_width=True,
                     disabled=len(scenarios) <= 1):
            scenarios.pop(active_idx)
            st.session_state.active_idx = max(0, active_idx - 1)
            st.rerun()

    new_name = st.text_input("Rename scenario", value=scenarios[active_idx]["name"],
                              key="rename_input")
    if new_name != scenarios[active_idx]["name"]:
        scenarios[active_idx]["name"] = new_name

    st.markdown("---")

    # ── Data fetch ───────────────────────────
    st.markdown("### Data source")
    exchange = st.radio("Exchange", ["GLOBAL", "NGX"],
                        help="NGX tickers get '.LG' appended automatically.")
    ticker   = st.text_input("Ticker", placeholder="AAPL / DANGCEM / MTNN")

    fc1, fc2 = st.columns(2)
    with fc1:
        fetch_clicked = st.button("Fetch data", use_container_width=True)
    with fc2:
        clear_clicked = st.button("Use manual", use_container_width=True)

    st.markdown("---")
    training_mode = st.toggle("🎓 Training mode", value=False,
                               help="Show analyst guidance next to each input.")

    st.markdown("---")
    st.markdown("<small>Financial data via Financial Modeling Prep (FMP). "
                "Add FMP_API_KEY in Streamlit Secrets to enable live fetch.</small>",
                unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FETCH DATA
# ─────────────────────────────────────────────

if fetch_clicked:
    if not ticker.strip():
        st.sidebar.warning("Enter a ticker first.")
    else:
        with st.spinner(f"Fetching {ticker.upper()}…"):
            data = fetch_company_data(ticker.strip(), exchange=exchange)

        if isinstance(data, dict) and data.get("_error") == "no_key":
            st.sidebar.error(
                "**API key missing.**\n\n"
                "Get a free key at [financialmodelingprep.com/register]"
                "(https://financialmodelingprep.com/register), then add to\n"
                "Streamlit Cloud → Settings → Secrets:\n"
                "```\nFMP_API_KEY = \"your_key\"\n```"
            )
        elif data is None:
            sym = ticker.upper() + (".LG" if exchange == "NGX" else "")
            st.sidebar.warning(f"No data found for **{sym}**. Fill values manually.")
            st.session_state.fetched_data = None
            st.session_state.meta = {
                "currency": "NGN" if exchange == "NGX" else "USD",
                "company_name": ticker.upper(),
            }
        else:
            # Scale fetched monetary values to the chosen unit
            scale_factor = SCALE_OPTIONS[unit_scale]
            for key in ("base_revenue", "net_debt"):
                if data.get(key) is not None:
                    # FMP returns millions — convert to chosen scale
                    data[key] = data[key] * 1_000_000 / scale_factor
            # shares_outstanding stays as-is (millions) — treated separately
            st.session_state.fetched_data = data
            st.session_state.meta         = data
            st.sidebar.success(f"✅ {data['company_name']} ({data['symbol']})")

if clear_clicked:
    st.session_state.fetched_data = None
    st.session_state.meta         = {
        "currency": "NGN" if exchange == "NGX" else "USD",
        "company_name": ticker.upper() or "Manual Model",
    }

fetched  = st.session_state.fetched_data
meta     = st.session_state.meta
currency = meta.get("currency", "USD")


def get_default(key):
    if fetched and fetched.get(key) is not None:
        return fetched[key]
    return DEFAULTS.get(key)


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

company_name   = meta.get("company_name", "Manual Model")
ticker_display = meta.get("symbol", ticker.upper() if ticker else "—")
active_name    = scenarios[active_idx]["name"]

pills_html = "".join(
    f'<span class="scenario-pill{"  active" if i == active_idx else ""}">'
    f'{s["name"]}</span>'
    for i, s in enumerate(scenarios)
)

st.markdown(f"""
<div class="app-header">
  <div class="ticker">{ticker_display} · {exchange} · inputs in {unit_scale}</div>
  <h1>{company_name}</h1>
  <div>Discounted Cash Flow Valuation &nbsp;|&nbsp; {pills_html}</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# GUIDE HELPER
# ─────────────────────────────────────────────

def guide_for(key):
    if not training_mode:
        return
    entry = INPUT_GUIDE.get(key)
    if not entry:
        return
    where_key = "where_ngx" if exchange == "NGX" else "where_global"
    with st.expander(f"ℹ️ About: {entry['name']}", expanded=False):
        st.markdown(f"""
        <div class="guide-box">
        <span class="guide-label">What it is</span>{entry['what']}
        <br><br>
        <span class="guide-label">Why it's needed</span>{entry['why']}
        <br><br>
        <span class="guide-label">Where to find it ({'NGX' if exchange == 'NGX' else 'Global / US'})</span>
        {"<br>".join(f"&bull; {s}" for s in entry[where_key])}
        <br><br>
        <span class="guide-label">Analyst tip</span>{entry.get('tips', '')}
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ASSUMPTION INPUTS
# ─────────────────────────────────────────────

st.markdown("## Assumptions")
st.caption(
    f"All monetary inputs are in **{unit_scale}** ({scale_label}). "
    "Change the unit in the sidebar if your source figures are in thousands or billions."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Revenue & Growth")

    base_revenue = st.number_input(
        f"Base year revenue ({scale_label})",
        min_value=0.0,
        value=float(get_default("base_revenue") or DEFAULTS["base_revenue"]),
        step=10.0, format="%.2f",
    )
    guide_for("base_revenue")

    st.markdown("**5-Year Revenue Growth (%)**")
    growth_rates = []
    g_cols = st.columns(5)
    for i, gc in enumerate(g_cols):
        with gc:
            g = st.number_input(f"Y{i+1}", min_value=-50.0, max_value=100.0,
                                value=DEFAULTS["growth_rates"][i] * 100,
                                step=0.5, format="%.1f", key=f"gr_{i}")
            growth_rates.append(g / 100)
    guide_for("growth_rates")

with col2:
    st.markdown("#### Margins & Tax")

    ebit_margin = st.number_input(
        "EBIT margin (%)", min_value=-100.0, max_value=100.0,
        value=float(get_default("ebit_margin") or DEFAULTS["ebit_margin"]) * 100,
        step=0.5, format="%.2f",
    ) / 100
    guide_for("ebit_margin")

    tax_rate = st.number_input(
        "Effective tax rate (%)", min_value=0.0, max_value=60.0,
        value=float(get_default("tax_rate") or DEFAULTS["tax_rate"]) * 100,
        step=0.5, format="%.2f",
    ) / 100
    guide_for("tax_rate")

    dep_pct = st.number_input(
        "D&A (% of revenue)", min_value=0.0, max_value=50.0,
        value=float(get_default("dep_pct") or DEFAULTS["dep_pct"]) * 100,
        step=0.25, format="%.2f",
    ) / 100
    guide_for("dep_pct")

    capex_pct = st.number_input(
        "CapEx (% of revenue)", min_value=0.0, max_value=50.0,
        value=float(get_default("capex_pct") or DEFAULTS["capex_pct"]) * 100,
        step=0.25, format="%.2f",
    ) / 100
    guide_for("capex_pct")

    nwc_pct = st.number_input(
        "NWC (% of revenue)", min_value=-50.0, max_value=50.0,
        value=float(get_default("nwc_pct") or DEFAULTS["nwc_pct"]) * 100,
        step=0.5, format="%.2f",
    ) / 100
    guide_for("nwc_pct")

with col3:
    st.markdown("#### Capital Structure & Discounting")

    net_debt = st.number_input(
        f"Net debt ({scale_label})",
        value=float(get_default("net_debt") if get_default("net_debt") is not None else DEFAULTS["net_debt"]),
        step=10.0, format="%.2f",
        help="Total interest-bearing debt minus cash. Negative = net cash.",
    )
    guide_for("net_debt")

    shares_outstanding = st.number_input(
        "Shares outstanding (millions)",
        min_value=0.01,
        value=float(get_default("shares_outstanding") or DEFAULTS["shares_outstanding"]),
        step=1.0, format="%.2f",
        help="Always enter shares in millions regardless of the unit scale above.",
    )
    guide_for("shares_outstanding")

    wacc_default = get_default("wacc") or DEFAULTS["wacc"]
    wacc = st.number_input(
        "WACC (%)", min_value=0.1, max_value=60.0,
        value=float(wacc_default) * 100,
        step=0.25, format="%.2f",
    ) / 100
    guide_for("wacc")

    tg_default = 0.12 if exchange == "NGX" else DEFAULTS["terminal_growth"]
    terminal_growth = st.number_input(
        "Terminal growth rate (%)", min_value=0.0, max_value=30.0,
        value=float(tg_default) * 100,
        step=0.25, format="%.2f",
        help="Must be less than WACC.",
    ) / 100
    guide_for("terminal_growth")

    if terminal_growth >= wacc:
        st.error("Terminal growth must be less than WACC.")


# ─────────────────────────────────────────────
# SAVE INPUTS TO ACTIVE SCENARIO
# ─────────────────────────────────────────────

current_inputs = dict(
    base_revenue=base_revenue, growth_rates=growth_rates,
    ebit_margin=ebit_margin, tax_rate=tax_rate,
    dep_pct=dep_pct, capex_pct=capex_pct, nwc_pct=nwc_pct,
    wacc=wacc, terminal_growth=terminal_growth,
    net_debt=net_debt, shares_outstanding=shares_outstanding,
)
scenarios[active_idx]["inputs"] = current_inputs
scenarios[active_idx]["meta"]   = meta


# ─────────────────────────────────────────────
# RUN MODEL (all scenarios)
# ─────────────────────────────────────────────

st.markdown("<div class='ledger-line'></div>", unsafe_allow_html=True)

valid = terminal_growth < wacc

if not valid:
    st.warning("Fix the terminal growth / WACC relationship to see output.")
    st.stop()

# Run the active scenario
try:
    results = run_dcf(**current_inputs)
    scenarios[active_idx]["results"] = results
except Exception as e:
    st.error(f"Model error: {e}")
    st.stop()

# Run other scenarios silently (best-effort)
for i, sc in enumerate(scenarios):
    if i == active_idx:
        continue
    try:
        sc["results"] = run_dcf(**sc["inputs"])
    except Exception:
        sc["results"] = None


# ─────────────────────────────────────────────
# VALUATION OUTPUT
# ─────────────────────────────────────────────

st.markdown("## Valuation Output")
st.caption(f"Active scenario: **{active_name}** · Units: **{unit_scale}**")

current_price = meta.get("current_price")
price_per_share = results["price_per_share"]

n_metrics = 5 if current_price else 4
mcols = st.columns(n_metrics)

def metric_card(col, label, value_html):
    with col:
        st.markdown(f"""<div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{value_html}</div>
        </div>""", unsafe_allow_html=True)

metric_card(mcols[0], f"Enterprise Value ({scale_label})",
            fmt(results["enterprise_value"], currency))
metric_card(mcols[1], f"Equity Value ({scale_label})",
            fmt(results["equity_value"], currency))
metric_card(mcols[2], "Implied Price / Share",
            fmt(price_per_share, currency))

pv_fcf_sum = sum(results["pv_fcfs"])
tv_pct = results["pv_terminal_value"] / results["enterprise_value"] * 100
metric_card(mcols[3], "Terminal Value % of EV", f"{tv_pct:.1f}%")

if current_price:
    upside   = (price_per_share / current_price - 1) * 100
    css      = "upside-positive" if upside >= 0 else "upside-negative"
    sign     = "+" if upside >= 0 else ""
    metric_card(mcols[4],
                f"vs Market ({fmt(current_price, currency)})",
                f'<span class="{css}">{sign}{upside:.1f}%</span>')


# ─────────────────────────────────────────────
# FCF TABLE (with discount factors)
# ─────────────────────────────────────────────

st.markdown("### Free Cash Flow Projection")

n_years = len(results["fcfs"])
df = pd.DataFrame({
    "Year":            list(range(1, n_years + 1)),
    f"Revenue ({scale_label})": results["revenues"],
    f"FCF ({scale_label})":     results["fcfs"],
    "Discount Factor": results["discount_factors"],
    f"PV of FCF ({scale_label})": results["pv_fcfs"],
})

table_col, chart_col = st.columns([1, 1.3])

with table_col:
    st.dataframe(
        df.style.format({
            f"Revenue ({scale_label})":   "{:,.1f}",
            f"FCF ({scale_label})":       "{:,.1f}",
            "Discount Factor":            "{:.4f}",
            f"PV of FCF ({scale_label})": "{:,.1f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(f"""
    <div class="metric-card" style="margin-top:.5rem;">
      <div class="label">Terminal Value · undiscounted ({scale_label})</div>
      <div class="value" style="font-size:1.2rem;">{fmt(results['terminal_value'], currency)}</div>
    </div>
    <div class="metric-card">
      <div class="label">PV of Terminal Value ({scale_label})</div>
      <div class="value" style="font-size:1.2rem;">{fmt(results['pv_terminal_value'], currency)}</div>
    </div>
    <div class="metric-card">
      <div class="label">Discount Factor at Year {n_years}</div>
      <div class="value" style="font-size:1.2rem;">{results['discount_factors'][-1]:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with chart_col:
    chart_df = df.melt(
        id_vars="Year",
        value_vars=[f"FCF ({scale_label})", f"PV of FCF ({scale_label})"],
        var_name="Series", value_name="Value",
    )
    bar_chart = (
        alt.Chart(chart_df).mark_bar()
        .encode(
            x=alt.X("Year:O", title="Forecast Year"),
            y=alt.Y("Value:Q", title=f"Amount ({currency} {scale_label})"),
            color=alt.Color("Series:N",
                            scale=alt.Scale(
                                domain=[f"FCF ({scale_label})", f"PV of FCF ({scale_label})"],
                                range=["#6E8B7A", "#0F3D2E"]),
                            legend=alt.Legend(title=None, orient="top")),
            xOffset="Series:N",
            tooltip=["Year", "Series", alt.Tooltip("Value:Q", format=",.1f")],
        ).properties(height=280)
    )
    df_factor = df[["Year", "Discount Factor"]].copy()
    factor_line = (
        alt.Chart(df_factor).mark_line(color="#C8932E", strokeWidth=2, point=True)
        .encode(
            x=alt.X("Year:O"),
            y=alt.Y("Discount Factor:Q", axis=alt.Axis(title="Discount Factor", orient="right"),
                    scale=alt.Scale(domain=[0, 1])),
            tooltip=["Year", alt.Tooltip("Discount Factor:Q", format=".4f")],
        )
    )
    st.altair_chart(
        alt.layer(bar_chart, factor_line).resolve_scale(y="independent"),
        use_container_width=True,
    )

    ev_split = pd.DataFrame({
        "Component": ["PV Forecast FCFs", "PV Terminal Value"],
        "Value":     [sum(results["pv_fcfs"]), results["pv_terminal_value"]],
    })
    pie = (
        alt.Chart(ev_split).mark_arc(innerRadius=60)
        .encode(
            theta="Value:Q",
            color=alt.Color("Component:N",
                            scale=alt.Scale(range=["#C8932E", "#0F3D2E"]),
                            legend=alt.Legend(title=None, orient="bottom")),
            tooltip=["Component", alt.Tooltip("Value:Q", format=",.1f")],
        ).properties(height=200, title="Enterprise Value composition")
    )
    st.altair_chart(pie, use_container_width=True)


# ─────────────────────────────────────────────
# SCENARIO COMPARISON
# ─────────────────────────────────────────────

active_scenarios = [(i, sc) for i, sc in enumerate(scenarios) if sc["results"] is not None]

if len(active_scenarios) > 1:
    st.markdown("### Scenario Comparison")

    comp_rows = []
    for i, sc in active_scenarios:
        r = sc["results"]
        comp_rows.append({
            "Scenario":                sc["name"],
            "WACC":                    f"{sc['inputs']['wacc']:.2%}",
            "Terminal Growth":         f"{sc['inputs']['terminal_growth']:.2%}",
            f"EV ({scale_label})":     f"{r['enterprise_value']:,.1f}",
            f"Equity ({scale_label})": f"{r['equity_value']:,.1f}",
            "Price / Share":           f"{fmt(r['price_per_share'], currency)}",
            "TV % of EV":              f"{r['pv_terminal_value']/r['enterprise_value']*100:.1f}%",
        })
    st.dataframe(pd.DataFrame(comp_rows), hide_index=True, use_container_width=True)

    # Comparison bar chart
    comp_chart_data = pd.DataFrame([
        {"Scenario": sc["name"], "Metric": "Enterprise Value", "Value": sc["results"]["enterprise_value"]}
        for _, sc in active_scenarios
    ] + [
        {"Scenario": sc["name"], "Metric": "Equity Value", "Value": sc["results"]["equity_value"]}
        for _, sc in active_scenarios
    ])
    comp_chart = (
        alt.Chart(comp_chart_data).mark_bar()
        .encode(
            x=alt.X("Scenario:N", title=None),
            y=alt.Y("Value:Q", title=f"{currency} {scale_label}"),
            color=alt.Color("Scenario:N",
                            scale=alt.Scale(range=SCENARIO_COLORS[:len(active_scenarios)]),
                            legend=None),
            column=alt.Column("Metric:N", title=None),
            tooltip=["Scenario", "Metric", alt.Tooltip("Value:Q", format=",.1f")],
        ).properties(width=200, height=260)
    )
    st.altair_chart(comp_chart)


# ─────────────────────────────────────────────
# SENSITIVITY TABLE
# ─────────────────────────────────────────────

st.markdown("### Sensitivity: Price per Share")
st.caption("Rows = WACC · Columns = Terminal Growth Rate · Gold cell = current assumptions")

wacc_range   = sorted(set([round(wacc + d, 4) for d in (-0.02, -0.01, 0, 0.01, 0.02) if wacc+d > 0]))
growth_range = sorted(set([round(terminal_growth + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01) if terminal_growth+d >= 0]))

table    = sensitivity_table(current_inputs, wacc_range, growth_range)
sens_df  = pd.DataFrame(table).T
sens_df.index   = [f"{w:.2%}" for w in sens_df.index]
sens_df.columns = [f"{g:.2%}" for g in sens_df.columns]

base_row = f"{wacc:.2%}"
base_col = f"{terminal_growth:.2%}"

styled = sens_df.style.format("{:.2f}")
for r in sens_df.index:
    for c in sens_df.columns:
        if r == base_row and c == base_col:
            bg = "#C8932E"
        elif r == base_row or c == base_col:
            bg = "#F0E9D8"
        else:
            bg = ""
        if bg:
            styled = styled.set_properties(subset=pd.IndexSlice[r, c],
                                           **{"background-color": bg})

st.dataframe(styled, use_container_width=True)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown("<div class='ledger-line'></div>", unsafe_allow_html=True)
st.caption(
    "For educational/training use. DCF outputs are highly sensitive to input "
    "assumptions — always cross-check against comparable company multiples and "
    "recent transaction data."
)
