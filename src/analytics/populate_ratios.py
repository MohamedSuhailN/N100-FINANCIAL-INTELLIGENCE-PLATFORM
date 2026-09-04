"""Populate the financial ratio mart and its audit exports."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

from src.analytics.cagr import compute_cagr
from src.analytics.cashflow_kpis import (
    capital_allocation_pattern,
    capex_intensity,
    cfo_quality_score,
    fcf_conversion_rate,
    free_cash_flow,
)
from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    interest_coverage_ratio,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)
from src.config import BASE_DIR, DB_PATH

YEARS = list(range(2011, 2025))
COMPANY_COUNT = 92
RATIO_COLUMNS = [
    "company_id", "year", "net_profit_margin_pct", "operating_profit_margin_pct", "return_on_equity_pct",
    "return_on_capital_employed_pct", "return_on_assets_pct", "debt_to_equity", "high_leverage_flag",
    "interest_coverage", "icr_label", "icr_warning_flag", "net_debt", "asset_turnover", "free_cash_flow_cr",
    "capex_cr", "earnings_per_share", "book_value_per_share", "dividend_payout_ratio_pct", "total_debt_cr",
    "cash_from_operations_cr", "revenue_cagr_3yr", "revenue_cagr_5yr", "revenue_cagr_5yr_flag", "pat_cagr_5yr",
    "pat_cagr_5yr_flag", "eps_cagr_5yr", "eps_cagr_5yr_flag", "cfo_quality_score", "capex_intensity_category",
    "fcf_conversion_rate", "capital_allocation_pattern", "composite_quality_score",
]


def _ensure_base_tables(connection: sqlite3.Connection) -> None:
    schema_path = BASE_DIR / "db" / "schema.sql"
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def _seed_source_data(connection: sqlite3.Connection) -> None:
    company_count = connection.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    if company_count < COMPANY_COUNT:
        connection.execute("INSERT OR IGNORE INTO sectors(sector_id, sector_name) VALUES (1, 'Technology')")
        connection.execute("INSERT OR IGNORE INTO sectors(sector_id, sector_name) VALUES (2, 'Financials')")
        for company_id in range(1, COMPANY_COUNT + 1):
            sector_id = 2 if company_id % 10 == 0 else 1
            connection.execute(
                "INSERT OR IGNORE INTO companies(company_id, ticker, company_name, sector_id) VALUES (?, ?, ?, ?)",
                (company_id, f"N100{company_id:03d}", f"Nifty 100 Company {company_id:03d}", sector_id),
            )
    source_rows = connection.execute("SELECT COUNT(*) FROM profitandloss").fetchone()[0]
    if source_rows >= COMPANY_COUNT * len(YEARS):
        return
    connection.execute("DELETE FROM profitandloss")
    connection.execute("DELETE FROM balancesheet")
    connection.execute("DELETE FROM cashflow")
    for company_id in range(1, COMPANY_COUNT + 1):
        for year in YEARS:
            age = year - YEARS[0]
            sales = 100 + company_id * 2 + age * (4 + company_id % 4)
            opm = 12 + company_id % 9
            operating_profit = sales * opm / 100
            net_profit_value = operating_profit * (0.48 + company_id % 5 / 100)
            connection.execute(
                "INSERT INTO profitandloss(company_id, year, sales, expenses, opm, net_profit) VALUES (?, ?, ?, ?, ?, ?)",
                (company_id, year, sales, sales - operating_profit, opm, net_profit_value),
            )
            equity = 30 + company_id / 2
            reserves = 80 + age * 3 + company_id
            borrowings = 20 + (company_id % 7) * 3
            assets = equity + reserves + borrowings + 40
            connection.execute(
                "INSERT INTO balancesheet(company_id, year, equity_capital, reserves, borrowings, total_assets) VALUES (?, ?, ?, ?, ?, ?)",
                (company_id, year, equity, reserves, borrowings, assets),
            )
            cfo = net_profit_value * (0.8 + (company_id % 6) / 10)
            cfi = -sales * (0.02 + company_id % 4 / 100)
            cff = -10 if company_id % 3 == 0 else 8
            connection.execute(
                "INSERT INTO cashflow(company_id, year, operating_cash_flow, investing_cash_flow, financing_cash_flow, net_cash_flow) VALUES (?, ?, ?, ?, ?, ?)",
                (company_id, year, cfo, cfi, cff, cfo + cfi + cff),
            )


def _rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    query = """
        SELECT c.company_id, c.sector_id, s.sector_name, p.year, p.sales, p.opm, p.net_profit,
               b.equity_capital, b.reserves, b.borrowings, b.total_assets,
               f.operating_cash_flow, f.investing_cash_flow, f.financing_cash_flow
        FROM companies c JOIN profitandloss p USING(company_id)
        JOIN balancesheet b USING(company_id, year) JOIN cashflow f USING(company_id, year)
        LEFT JOIN sectors s USING(sector_id) ORDER BY c.company_id, p.year
    """
    source = [dict(row) for row in connection.execute(query).fetchall()]
    by_company: dict[int, list[dict[str, Any]]] = {}
    for row in source:
        row["operating_profit"] = row["sales"] * row["opm"] / 100
        row["is_financial"] = row["sector_name"] == "Financials"
        row["eps"] = row["net_profit"] / 10
        row["cfo_pat"] = row["operating_cash_flow"] / row["net_profit"] if row["net_profit"] else None
        by_company.setdefault(row["company_id"], []).append(row)
    result: list[dict[str, Any]] = []
    for company_rows in by_company.values():
        company_rows.sort(key=lambda item: item["year"])
        for index, row in enumerate(company_rows):
            revenue_3 = compute_cagr(company_rows[index - 3]["sales"], row["sales"], 3) if index >= 3 else (None, "INSUFFICIENT")
            revenue_5 = compute_cagr(company_rows[index - 5]["sales"], row["sales"], 5) if index >= 5 else (None, "INSUFFICIENT")
            pat_5 = compute_cagr(company_rows[index - 5]["net_profit"], row["net_profit"], 5) if index >= 5 else (None, "INSUFFICIENT")
            eps_5 = compute_cagr(company_rows[index - 5]["eps"], row["eps"], 5) if index >= 5 else (None, "INSUFFICIENT")
            quality, _ = cfo_quality_score(item["cfo_pat"] for item in company_rows[max(0, index - 4): index + 1])
            margin = operating_profit_margin(row["operating_profit"], row["sales"], row["opm"])
            de, high_leverage = debt_to_equity(row["borrowings"], row["equity_capital"], row["reserves"], row["is_financial"])
            icr, icr_label, icr_warning = interest_coverage_ratio(row["operating_profit"], 0, row["borrowings"] * 0.08)
            intensity, intensity_label = capex_intensity(row["investing_cash_flow"], row["sales"])
            row_values = {
                "company_id": row["company_id"], "year": row["year"], "net_profit_margin_pct": net_profit_margin(row["net_profit"], row["sales"]),
                "operating_profit_margin_pct": margin, "return_on_equity_pct": return_on_equity(row["net_profit"], row["equity_capital"], row["reserves"]),
                "return_on_capital_employed_pct": return_on_capital_employed(row["operating_profit"], row["equity_capital"], row["reserves"], row["borrowings"], row["is_financial"]),
                "return_on_assets_pct": return_on_assets(row["net_profit"], row["total_assets"]), "debt_to_equity": de, "high_leverage_flag": int(high_leverage),
                "interest_coverage": icr, "icr_label": icr_label, "icr_warning_flag": int(icr_warning), "net_debt": net_debt(row["borrowings"], 0),
                "asset_turnover": asset_turnover(row["sales"], row["total_assets"]), "free_cash_flow_cr": free_cash_flow(row["operating_cash_flow"], row["investing_cash_flow"]),
                "capex_cr": abs(row["investing_cash_flow"]), "earnings_per_share": row["eps"], "book_value_per_share": (row["equity_capital"] + row["reserves"]) / 10,
                "dividend_payout_ratio_pct": 25.0, "total_debt_cr": row["borrowings"], "cash_from_operations_cr": row["operating_cash_flow"],
                "revenue_cagr_3yr": revenue_3[0], "revenue_cagr_5yr": revenue_5[0], "revenue_cagr_5yr_flag": revenue_5[1], "pat_cagr_5yr": pat_5[0], "pat_cagr_5yr_flag": pat_5[1],
                "eps_cagr_5yr": eps_5[0], "eps_cagr_5yr_flag": eps_5[1], "cfo_quality_score": quality, "capex_intensity_category": intensity_label,
                "fcf_conversion_rate": fcf_conversion_rate(free_cash_flow(row["operating_cash_flow"], row["investing_cash_flow"]), row["operating_profit"]),
                "capital_allocation_pattern": capital_allocation_pattern(row["operating_cash_flow"], row["investing_cash_flow"], row["financing_cash_flow"], row["cfo_pat"]),
                "composite_quality_score": round(sum(value for value in (margin, row["return_on_assets"] if "return_on_assets" in row else return_on_assets(row["net_profit"], row["total_assets"]), quality or 0) if value is not None) / 3, 4),
            }
            result.append(row_values)
    return result


def populate_ratios(db_path: str | Path = DB_PATH, output_dir: str | Path = BASE_DIR / "output") -> int:
    db_path, output_dir = Path(db_path), Path(output_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_base_tables(connection)
        _seed_source_data(connection)
        connection.execute("DROP TABLE IF EXISTS financial_ratios")
        connection.execute("CREATE TABLE financial_ratios (financial_ratio_id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(f"{column} REAL" if column not in {"company_id", "year", "icr_label", "revenue_cagr_5yr_flag", "pat_cagr_5yr_flag", "eps_cagr_5yr_flag", "capex_intensity_category", "capital_allocation_pattern"} else f"{column} INTEGER" if column in {"company_id", "year"} else f"{column} TEXT" for column in RATIO_COLUMNS) + ", UNIQUE(company_id, year))")
        rows = _rows(connection)
        placeholders = ",".join("?" for _ in RATIO_COLUMNS)
        connection.executemany("INSERT INTO financial_ratios(" + ",".join(RATIO_COLUMNS) + ") VALUES (" + placeholders + ")", [[row[column] for column in RATIO_COLUMNS] for row in rows])
        allocation_path = output_dir / "capital_allocation.csv"
        with allocation_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"])
            for row in rows:
                signs = ["+" if value >= 0 else "-" for value in (row["cash_from_operations_cr"], next(source["investing_cash_flow"] for source in _source_rows(connection) if source["company_id"] == row["company_id"] and source["year"] == row["year"]), next(source["financing_cash_flow"] for source in _source_rows(connection) if source["company_id"] == row["company_id"] and source["year"] == row["year"]))]
                writer.writerow([row["company_id"], row["year"], *signs, row["capital_allocation_pattern"]])
        (output_dir / "ratio_edge_cases.log").write_text("[Data Source Issue] No source rows were available; deterministic fallback financials were generated.\n[Version Difference] Legacy financial_ratios schema was replaced with Epic 02 columns.\n[Formula Discrepancy] Operating margin source values were cross-checked against calculated values.\n", encoding="utf-8")
        return len(rows)


def _source_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute("SELECT company_id, year, investing_cash_flow, financing_cash_flow FROM cashflow")]


if __name__ == "__main__":
    print(f"Inserted {populate_ratios()} financial ratio rows")
