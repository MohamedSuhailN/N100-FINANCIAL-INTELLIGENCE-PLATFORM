def compute_free_cash_flow(operating_cash_flow: float, investing_cash_flow: float) -> float:
    return round((operating_cash_flow or 0) + (investing_cash_flow or 0), 2)

def compute_cfo_quality_score(cfo_pat_ratios: list[float]) -> str | None:
    valid_ratios = [r for r in cfo_pat_ratios if r is not None]
    if not valid_ratios:
        return None
    avg_ratio = sum(valid_ratios) / len(valid_ratios)
    if avg_ratio > 1.0:
        return "High Quality"
    elif 0.5 <= avg_ratio <= 1.0:
        return "Moderate"
    else:
        return "Accrual Risk"

def compute_capex_intensity(investing_cash_flow: float, sales: float) -> tuple[float | None, str | None]:
    if sales is None or sales <= 0:
        return None, None
    capex = abs(investing_cash_flow or 0)
    intensity = (capex / sales) * 100
    if intensity < 3.0:
        cat = "Asset Light"
    elif 3.0 <= intensity <= 8.0:
        cat = "Moderate"
    else:
        cat = "Capital Intensive"
    return round(intensity, 2), cat

def compute_fcf_conversion_rate(fcf: float, operating_profit: float) -> float | None:
    if operating_profit is None or operating_profit == 0:
        return None
    return round((fcf / operating_profit) * 100, 2)

def classify_capital_allocation(cfo: float, cfi: float, cff: float, cfo_pat_ratio: float = 1.0) -> str:
    s_cfo = "+" if (cfo or 0) >= 0 else "-"
    s_cfi = "+" if (cfi or 0) >= 0 else "-"
    s_cff = "+" if (cff or 0) >= 0 else "-"
    pattern = f"({s_cfo},{s_cfi},{s_cff})"

    if pattern == "(+,-,-)":
        return "Shareholder Returns" if cfo_pat_ratio > 1.2 else "Reinvestor"
    elif pattern == "(+,+,-)":
        return "Liquidating Assets"
    elif pattern == "(-,+,+)":
        return "Distress Signal"
    elif pattern == "(-,-,+)":
        return "Growth Funded by Debt"
    elif pattern == "(+,+,+)":
        return "Cash Accumulator"
    elif pattern == "(-,-,-)":
        return "Pre-Revenue"
    elif pattern == "(+,-,+)":
        return "Mixed"
    else:
        return "Asset Seller / Debt Payer"




# Backward-compatible names used by the ratio population pipeline.
free_cash_flow = compute_free_cash_flow


def cfo_quality_score(cfo_pat_ratios):
    """Return the legacy ``(average_ratio, label)`` result shape."""
    values = [value for value in cfo_pat_ratios if value is not None]
    average = sum(values) / len(values) if values else None
    return average, compute_cfo_quality_score(values)


capex_intensity = compute_capex_intensity
fcf_conversion_rate = compute_fcf_conversion_rate
capital_allocation_pattern = classify_capital_allocation


def build_cashflow_intelligence(db_path="db/nifty100.db", output_dir="output"):
    """Build the latest-year cash-flow intelligence mart and exports."""
    import sqlite3
    from pathlib import Path
    import pandas as pd

    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("""
            SELECT c.company_id, c.company_name, c.ticker,
                   COALESCE(s.sector_name, 'Unknown') AS sector,
                   r.year, r.free_cash_flow_cr, r.cash_from_operations_cr,
                   r.capex_cr, r.cfo_quality_score, r.capex_intensity_category,
                   r.capital_allocation_pattern, r.debt_to_equity,
                   r.total_debt_cr, p.sales, p.net_profit,
                   f.operating_cash_flow, f.investing_cash_flow, f.financing_cash_flow,
                   b.borrowings
            FROM financial_ratios r JOIN companies c USING(company_id)
            LEFT JOIN sectors s USING(sector_id)
            JOIN profitandloss p USING(company_id, year)
            JOIN cashflow f USING(company_id, year)
            JOIN balancesheet b USING(company_id, year)
        """, connection)
    frame = frame.sort_values(["company_id", "year"])
    frame["cfo_pat_ratio"] = frame.cash_from_operations_cr / frame.net_profit.replace(0, pd.NA)
    frame["cfo_quality_5yr_avg"] = frame.groupby("company_id").cfo_pat_ratio.transform(lambda x: x.tail(5).mean())
    frame["cfo_quality_label"] = frame.cfo_quality_5yr_avg.map(lambda x: "High Quality" if x > 1 else "Moderate" if x >= .5 else "Accrual Risk")
    frame["capex_intensity_pct"] = (frame.investing_cash_flow.abs() / frame.sales.replace(0, pd.NA) * 100).round(2)
    frame["capex_intensity_label"] = frame.capex_intensity_pct.map(lambda x: "Asset Light" if x < 3 else "Moderate" if x <= 8 else "Capital Intensive")
    frame["distress_signal"] = (frame.operating_cash_flow < 0) & (frame.financing_cash_flow > 0)
    previous_debt = frame.groupby("company_id").borrowings.shift(1)
    frame["deleveraging_flag"] = (frame.financing_cash_flow < 0) & frame.borrowings.lt(previous_debt)
    latest = frame.groupby("company_id", as_index=False).tail(1).copy()
    latest.to_excel(output / "cashflow_intelligence.xlsx", index=False)
    latest[latest.distress_signal].to_csv(output / "distress_alerts.csv", index=False)
    allocation_path = output / "capital_allocation.csv"
    if allocation_path.exists():
        allocation = pd.read_csv(allocation_path)
        allocation = allocation.rename(columns={"pattern_label": "capital_allocation_pattern"})
        latest = latest.drop(columns=["capital_allocation_pattern"], errors="ignore").merge(allocation[["company_id", "capital_allocation_pattern"]].drop_duplicates("company_id"), on="company_id", how="left")
    latest[["company_id", "capital_allocation_pattern"]].to_csv(output / "pattern_changes.csv", index=False)
    return latest
