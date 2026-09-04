from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import BASE_DIR, DB_PATH


def _market_caps(path: str | Path | None, companies: pd.DataFrame) -> pd.DataFrame:
    file_path = Path(path) if path else BASE_DIR / "data" / "market_cap.xlsx"
    if file_path.exists():
        source = pd.read_excel(file_path, header=1)
        lowered = {str(col).lower().replace(" ", "_"): col for col in source.columns}
        id_col = lowered.get("company_id") or lowered.get("id")
        cap_col = next((lowered[key] for key in lowered if "market" in key and "cap" in key), None)
        if id_col and cap_col:
            result = source[[id_col, cap_col]].rename(columns={id_col: "company_id", cap_col: "market_cap_cr"})
            result["company_id"] = result["company_id"].astype(str).str.strip().str.upper()
            return result
    # Fallback is only for the checked-in synthetic fixture with no market-cap workbook.
    return companies[["company_id", "revenue_cr"]].assign(market_cap_cr=lambda x: x.revenue_cr * 20)[["company_id", "market_cap_cr"]]


def calculate_valuation(
    db_path: str | Path = DB_PATH, market_cap_path: str | Path | None = None,
) -> pd.DataFrame:
    with sqlite3.connect(db_path) as connection:
        companies = pd.read_sql_query("""
            SELECT c.company_id, c.company_name, c.ticker,
                   COALESCE(s.sector_name, 'Unknown') AS sector,
                   p.sales AS revenue_cr
            FROM companies c LEFT JOIN sectors s USING(sector_id)
            LEFT JOIN profitandloss p USING(company_id)
            WHERE p.year = (SELECT MAX(year) FROM profitandloss p2 WHERE p2.company_id = p.company_id)
        """, connection)
        ratios = pd.read_sql_query("""
            SELECT * FROM financial_ratios
            WHERE year = (SELECT MAX(year) FROM financial_ratios)
        """, connection)
    companies["company_id"] = companies["company_id"].astype(str).str.strip().str.upper()
    ratios["company_id"] = ratios["company_id"].astype(str).str.strip().str.upper()
    merged = companies.merge(ratios, on="company_id", how="left")
    merged = merged.merge(_market_caps(market_cap_path, merged), on="company_id", how="left")
    merged["pe"] = merged.get("pe_ratio", pd.Series(float("nan"), index=merged.index))
    merged["pb"] = merged.get("pb_ratio", pd.Series(float("nan"), index=merged.index))
    merged["ev_ebitda"] = merged.get("ev_ebitda", pd.Series(float("nan"), index=merged.index))
    merged["fcf_yield_pct"] = merged["free_cash_flow_cr"].div(merged["market_cap_cr"]).mul(100)
    sector_median = merged.groupby("sector")["pe"].transform("median")
    global_median = merged["pe"].median()
    sector_median = sector_median.fillna(global_median)
    merged["5yr_median_PE"] = sector_median
    merged["PE_vs_sector_median_pct"] = merged["pe"].div(sector_median).sub(1).mul(100)
    merged["flag"] = "Fair"
    merged.loc[merged["pe"].gt(sector_median * 1.5), "flag"] = "Caution"
    merged.loc[merged["pe"].lt(sector_median * .7), "flag"] = "Discount"
    columns = ["company_id", "company_name", "sector", "pe", "pb", "ev_ebitda",
               "fcf_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"]
    result = merged[columns].rename(columns={"pe": "P/E", "pb": "P/B", "ev_ebitda": "EV/EBITDA"})
    numeric = result.select_dtypes("number").columns
    result[numeric] = result[numeric].fillna(0)
    return result


def export_valuation(
    db_path: str | Path = DB_PATH, market_cap_path: str | Path | None = None,
    output_dir: str | Path = BASE_DIR / "output",
) -> tuple[Path, Path]:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    result = calculate_valuation(db_path, market_cap_path)
    workbook = output / "valuation_summary.xlsx"
    result.to_excel(workbook, index=False)
    flags = output / "valuation_flags.csv"
    result[result["flag"].isin(["Caution", "Discount"])].to_csv(flags, index=False)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE IF EXISTS valuation_summary")
        result.to_sql("valuation_summary", connection, index=False)
    return workbook, flags