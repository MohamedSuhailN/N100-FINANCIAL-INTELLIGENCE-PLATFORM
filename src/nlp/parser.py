from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

from src.config import BASE_DIR, DB_PATH

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%", re.IGNORECASE)
TEXT_METRICS = ["compounded_sales_growth", "compounded_profit_growth", "stock_price_cagr", "roe"]


def parse_metric_text(value: object) -> tuple[int, float] | None:
    match = PATTERN.search(str(value)) if pd.notna(value) else None
    return (int(match.group(1)), float(match.group(2))) if match else None


def parse_analysis(
    workbook_path: str | Path | None = None,
    output_dir: str | Path = BASE_DIR / "output",
    db_path: str | Path = DB_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    path = Path(workbook_path) if workbook_path else BASE_DIR / "data" / "analysis.xlsx"
    parsed: list[dict] = []; failures: list[dict] = []
    if path.exists():
        source = pd.concat(pd.read_excel(path, sheet_name=None, header=1).values(), ignore_index=True)
        id_col = next((c for c in source.columns if str(c).lower() in {"company_id", "id"}), None)
        id_col = id_col or source.columns[0]
        source[id_col] = source[id_col].astype(str).str.strip().str.upper()
        for _, row in source.iterrows():
            for metric in TEXT_METRICS:
                column = next((c for c in source.columns if str(c).lower() == metric), None)
                if column is None: continue
                result = parse_metric_text(row[column])
                if result:
                    parsed.append({"company_id": row[id_col], "metric_type": metric, "period_years": result[0], "value_pct": result[1]})
                else:
                    failures.append({"company_id": row[id_col], "metric_type": metric, "raw_value": row[column]})
    parsed_frame = pd.DataFrame(parsed, columns=["company_id", "metric_type", "period_years", "value_pct"])
    failures_frame = pd.DataFrame(failures, columns=["company_id", "metric_type", "raw_value"])
    parsed_frame.to_csv(output / "analysis_parsed.csv", index=False)
    failures_frame.to_csv(output / "parse_failures.csv", index=False)
    validation = cross_validate_cagrs(parsed_frame, db_path)
    validation.to_csv(output / "cagr_cross_validation.csv", index=False)
    return parsed_frame, failures_frame


def cross_validate_cagrs(parsed: pd.DataFrame, db_path: str | Path = DB_PATH, tolerance_pct: float = 5) -> pd.DataFrame:
    if parsed.empty: return pd.DataFrame(columns=["company_id", "metric_type", "parsed_pct", "computed_pct", "divergence_pct", "manual_review"])
    with sqlite3.connect(db_path) as connection:
        ratios = pd.read_sql_query("SELECT company_id, pat_cagr_5yr, revenue_cagr_5yr FROM financial_ratios WHERE year = (SELECT MAX(year) FROM financial_ratios)", connection)
    mapping = {"compounded_sales_growth": "revenue_cagr_5yr", "compounded_profit_growth": "pat_cagr_5yr"}
    rows = []
    for _, row in parsed[parsed.metric_type.isin(mapping)].iterrows():
        computed = ratios.loc[ratios.company_id == row.company_id, mapping[row.metric_type]]
        value = computed.iloc[0] if not computed.empty else None
        divergence = abs(row.value_pct - value) if pd.notna(value) else None
        rows.append({"company_id": row.company_id, "metric_type": row.metric_type, "parsed_pct": row.value_pct, "computed_pct": value, "divergence_pct": divergence, "manual_review": bool(divergence is not None and divergence > tolerance_pct)})
    return pd.DataFrame(rows)