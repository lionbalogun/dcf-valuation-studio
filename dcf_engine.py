"""
Core DCF calculation engine — pure functions, no I/O.
Used by app.py (Streamlit) and can be reused by CLI tools.
"""


def project_fcf(base_revenue, growth_rates, ebit_margin, tax_rate,
                 dep_pct, capex_pct, nwc_pct):
    """Project Free Cash Flow for each forecast year."""
    revenues, fcfs = [], []
    revenue = base_revenue

    for g in growth_rates:
        revenue = revenue * (1 + g)
        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax_rate)
        dep = revenue * dep_pct
        capex = revenue * capex_pct
        delta_nwc = revenue * nwc_pct * g
        fcf = nopat + dep - capex - delta_nwc
        revenues.append(revenue)
        fcfs.append(fcf)

    return revenues, fcfs


def discount_cash_flows(fcfs, wacc):
    """
    Discount each FCF back to present value.
    Returns (pv_fcfs, discount_factors).
    discount_factor[t] = 1 / (1 + wacc)^t
    """
    pv_fcfs, discount_factors = [], []
    for t, fcf in enumerate(fcfs, start=1):
        df = 1 / ((1 + wacc) ** t)
        discount_factors.append(df)
        pv_fcfs.append(fcf * df)
    return pv_fcfs, discount_factors


def run_dcf(base_revenue, growth_rates, ebit_margin, tax_rate,
             dep_pct, capex_pct, nwc_pct, wacc, terminal_growth,
             net_debt, shares_outstanding, **kwargs):
    """Run a full DCF and return a dict of all intermediate and final results."""

    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth rate.")

    revenues, fcfs = project_fcf(base_revenue, growth_rates, ebit_margin,
                                  tax_rate, dep_pct, capex_pct, nwc_pct)

    pv_fcfs, discount_factors = discount_cash_flows(fcfs, wacc)
    n = len(fcfs)

    tv    = fcfs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_tv = tv / ((1 + wacc) ** n)

    enterprise_value  = sum(pv_fcfs) + pv_tv
    equity_value      = enterprise_value - net_debt
    price_per_share   = equity_value / shares_outstanding

    return {
        "revenues":          revenues,
        "fcfs":              fcfs,
        "discount_factors":  discount_factors,
        "pv_fcfs":           pv_fcfs,
        "terminal_value":    tv,
        "pv_terminal_value": pv_tv,
        "enterprise_value":  enterprise_value,
        "equity_value":      equity_value,
        "price_per_share":   price_per_share,
    }


def sensitivity_table(base_inputs, wacc_range, growth_range):
    """Build a 2D sensitivity table: price per share vs WACC and terminal growth."""
    table = {}
    for wacc in wacc_range:
        row = {}
        for g in growth_range:
            inputs = dict(base_inputs)
            inputs["wacc"] = wacc
            inputs["terminal_growth"] = g
            try:
                result = run_dcf(**inputs)
                row[g] = round(result["price_per_share"], 2)
            except (ValueError, ZeroDivisionError):
                row[g] = None
        table[wacc] = row
    return table
