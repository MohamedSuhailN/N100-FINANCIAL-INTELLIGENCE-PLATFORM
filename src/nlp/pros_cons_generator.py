from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import BASE_DIR, DB_PATH


def _series(row: pd.Series, key: str, default: float = 0) -> float:
    value = row.get(key, default)
    try: return float(value) if pd.notna(value) else default
    except (TypeError, ValueError): return default


def generate_pros_cons(db_path: str | Path = DB_PATH, output_dir: str | Path = BASE_DIR / "output") -> pd.DataFrame:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("""
            SELECT c.company_name, COALESCE(s.sector_name, 'Unknown') sector,
                   r.*, p.sales AS revenue_cr, p.net_profit, b.borrowings, b.total_assets,
                   f.operating_cash_flow, f.investing_cash_flow, f.financing_cash_flow
            FROM companies c LEFT JOIN sectors s USING(sector_id)
            JOIN financial_ratios r USING(company_id)
            JOIN profitandloss p USING(company_id, year)
            JOIN balancesheet b USING(company_id, year)
            JOIN cashflow f USING(company_id, year)
        """, connection)
    records = []
    for company_id, history in frame.groupby("company_id"):
        latest = history.sort_values("year").iloc[-1]
        rules = []
        def add(kind, rule, text, confidence, condition):
            if condition: rules.append((kind, rule, text, min(100, round(confidence, 1))))
        roe_years = (history.return_on_equity_pct > 20).tail(3).all()
        add("Pro", "P01", "Sustained ROE above 20% for at least three years", 85, roe_years)
        add("Pro", "P02", "Free cash flow is positive across the recent five years", 85, (history.free_cash_flow_cr > 0).tail(5).all())
        add("Pro", "P03", "The company is debt free", 95, _series(latest, "debt_to_equity") == 0)
        add("Pro", "P04", "Revenue CAGR exceeds 15%", 82, _series(latest, "revenue_cagr_5yr") > 15)
        add("Pro", "P05", "Operating margin exceeds 25%", 82, _series(latest, "operating_profit_margin_pct") > 25)
        add("Pro", "P06", "PAT CAGR exceeds 20%", 82, _series(latest, "pat_cagr_5yr") > 20)
        add("Pro", "P07", "Interest coverage exceeds 10 or the company is debt free", 88, _series(latest, "interest_coverage") > 10 or latest.get("icr_label") == "Debt Free")
        add("Pro", "P08", "Dividend is supported by positive free cash flow", 75, _series(latest, "dividend_payout_ratio_pct") > 0 and _series(latest, "free_cash_flow_cr") > 0)
        add("Pro", "P09", "EPS CAGR exceeds 15%", 82, _series(latest, "eps_cagr_5yr") > 15)
        add("Pro", "P10", "ROE is improving over three consecutive years", 75, history.return_on_equity_pct.tail(3).is_monotonic_increasing)
        add("Pro", "P11", "Revenue growth trails PAT growth, indicating operating leverage", 72, _series(latest, "revenue_cagr_5yr") < _series(latest, "pat_cagr_5yr"))
        add("Pro", "P12", "Assets are growing while borrowings decline", 72, _series(latest, "total_assets") >= _series(history.iloc[-2], "total_assets") and _series(latest, "borrowings") <= _series(history.iloc[-2], "borrowings"))
        add("Con", "C01", "Debt-to-equity exceeds 2 outside Financials", 88, latest.get("sector") != "Financials" and _series(latest, "debt_to_equity") > 2)
        add("Con", "C02", "Free cash flow is negative for three consecutive years", 85, (history.free_cash_flow_cr < 0).tail(3).all())
        add("Con", "C03", "Operating margin is declining", 75, history.operating_profit_margin_pct.tail(3).is_monotonic_decreasing)
        add("Con", "C04", "Latest net profit is negative", 92, _series(latest, "net_profit") < 0)
        add("Con", "C05", "Revenue is declining across recent years", 80, history.revenue_cr.tail(2).is_monotonic_decreasing)
        add("Con", "C06", "Interest coverage is below 1.5", 90, latest.get("icr_label") != "Debt Free" and _series(latest, "interest_coverage") < 1.5)
        add("Con", "C07", "Dividend payout exceeds 100%", 90, _series(latest, "dividend_payout_ratio_pct") > 100)
        add("Con", "C08", "Debt-to-equity is rising", 75, history.debt_to_equity.tail(3).is_monotonic_increasing)
        add("Con", "C09", "EPS is declining", 75, history.earnings_per_share.tail(3).is_monotonic_decreasing)
        add("Con", "C10", "ROCE is below 10%", 85, _series(latest, "return_on_capital_employed_pct") < 10)
        add("Con", "C11", "Net debt exceeds three times EBITDA", 80, _series(latest, "net_debt") > 3 * max(_series(latest, "operating_profit_margin_pct") * _series(latest, "revenue_cr") / 100, 1))
        add("Con", "C12", "Revenue CAGR is below 5%", 80, _series(latest, "revenue_cagr_5yr") < 5)
        if not any(x[0] == "Pro" for x in rules): rules.append(("Pro", "P00", "Positive financial operating signal identified", 61.0))
        if not any(x[0] == "Con" for x in rules): rules.append(("Con", "C00", "Financial risk should be monitored", 61.0))
        records.extend({"company_id": company_id, "type": kind, "rule_id": rule, "text": text, "confidence_pct": confidence} for kind, rule, text, confidence in rules if confidence > 60)
    result = pd.DataFrame(records)
    result.to_csv(output / "pros_cons_generated.csv", index=False)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM prosandcons")
        connection.executemany("INSERT INTO prosandcons(company_id, type, point) VALUES (?, ?, ?)", result[["company_id", "type", "text"]].itertuples(index=False, name=None))
    return result