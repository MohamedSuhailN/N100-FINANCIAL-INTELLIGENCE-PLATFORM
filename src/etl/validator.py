import logging
import re
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DQ_RULES: dict[str, dict[str, str]] = {
    "DQ-01": {"severity": "CRITICAL", "description": "Primary key uniqueness"},
    "DQ-02": {"severity": "CRITICAL", "description": "Composite PK (company_id, year)"},
    "DQ-03": {"severity": "CRITICAL", "description": "Foreign key integrity"},
    "DQ-04": {"severity": "WARNING", "description": "Balance Sheet equation within 1%"},
    "DQ-05": {"severity": "WARNING", "description": "OPM cross-check"},
    "DQ-06": {"severity": "WARNING", "description": "Positive sales"},
    "DQ-07": {"severity": "WARNING", "description": "Net cash consistency"},
    "DQ-08": {"severity": "WARNING", "description": "Tax rate validation"},
    "DQ-09": {"severity": "WARNING", "description": "Dividend cap"},
    "DQ-10": {"severity": "WARNING", "description": "EPS sign consistency"},
    "DQ-11": {"severity": "WARNING", "description": "Duplicate ticker"},
    "DQ-12": {"severity": "WARNING", "description": "Missing year coverage"},
    "DQ-13": {"severity": "WARNING", "description": "URL validation"},
    "DQ-14": {"severity": "WARNING", "description": "Negative assets"},
    "DQ-15": {"severity": "WARNING", "description": "Invalid sector mapping"},
    "DQ-16": {"severity": "WARNING", "description": "Financial ratio completeness"},
}


def _append_failure(
    failures: list[dict[str, Any]],
    dataset_name: str,
    rule: str,
    severity: str,
    message: str,
    company: Any | None = None,
    year: Any | None = None,
    column: str | None = None,
    expected: Any | None = None,
    actual: Any | None = None,
) -> None:
    failures.append(
        {
            "dataset": dataset_name,
            "rule": rule,
            "severity": severity,
            "company": company,
            "year": year,
            "column": column,
            "expected": expected,
            "actual": actual,
            "message": message,
        }
    )


def validate_data(df: pd.DataFrame, dataset_name: str) -> list[dict[str, Any]]:
    """Apply the Sprint 1 data quality checks and return the recorded violations."""
    failures: list[dict[str, Any]] = []

    if df is None or df.empty:
        return failures

    if "company_id" in df.columns and df["company_id"].duplicated().any():
        dup_rows = df[df["company_id"].duplicated(keep=False)]
        _append_failure(
            failures,
            dataset_name,
            "DQ-01",
            DQ_RULES["DQ-01"]["severity"],
            "Duplicate company_id values found.",
            company=dup_rows["company_id"].iloc[0],
            column="company_id",
            expected="Unique company_id values",
            actual=str(dup_rows["company_id"].tolist()),
        )

    if {"company_id", "year"}.issubset(df.columns) and df.duplicated(subset=["company_id", "year"]).any():
        dup_rows = df[df.duplicated(subset=["company_id", "year"], keep=False)]
        _append_failure(
            failures,
            dataset_name,
            "DQ-02",
            DQ_RULES["DQ-02"]["severity"],
            "Duplicate (company_id, year) composite key entries found.",
            company=dup_rows["company_id"].iloc[0],
            year=dup_rows["year"].iloc[0],
            column="(company_id, year)",
            expected="Unique company and year pair",
            actual="Duplicate combination present",
        )

    if "sales" in df.columns:
        invalid_sales = df[df["sales"] < 0]
        if not invalid_sales.empty:
            _append_failure(
                failures,
                dataset_name,
                "DQ-06",
                DQ_RULES["DQ-06"]["severity"],
                f"{len(invalid_sales)} rows have negative sales values.",
                company=invalid_sales.iloc[0].get("company_id"),
                year=invalid_sales.iloc[0].get("year"),
                column="sales",
                expected="sales >= 0",
                actual=str(invalid_sales["sales"].tolist()),
            )

    if "ticker" in df.columns:
        dup_tickers = detect_duplicate_tickers(df)
        if dup_tickers:
            _append_failure(
                failures,
                dataset_name,
                "DQ-11",
                DQ_RULES["DQ-11"]["severity"],
                "Duplicate ticker values found.",
                company=None,
                column="ticker",
                expected="Unique ticker values",
                actual=str(dup_tickers),
            )

    if "url" in df.columns:
        invalid_urls = df[~df["url"].fillna("").astype(str).str.contains(r"^https?://", na=False)]
        if not invalid_urls.empty:
            _append_failure(
                failures,
                dataset_name,
                "DQ-13",
                DQ_RULES["DQ-13"]["severity"],
                "URL validation failed.",
                company=invalid_urls.iloc[0].get("company_id"),
                column="url",
                expected="Valid HTTP(S) URL",
                actual=str(invalid_urls["url"].tolist()),
            )

    if "total_assets" in df.columns:
        negative_assets = df[df["total_assets"] < 0]
        if not negative_assets.empty:
            _append_failure(
                failures,
                dataset_name,
                "DQ-14",
                DQ_RULES["DQ-14"]["severity"],
                "Negative asset values detected.",
                company=negative_assets.iloc[0].get("company_id"),
                column="total_assets",
                expected="total_assets >= 0",
                actual=str(negative_assets["total_assets"].tolist()),
            )

    return failures


def detect_duplicate_tickers(df: pd.DataFrame) -> list[str]:
    """Return ticker symbols that appear more than once."""
    if "ticker" not in df.columns:
        return []
    dup = df[df["ticker"].duplicated(keep=False)]["ticker"].dropna().astype(str)
    return sorted(set(dup.tolist()))


def validate_foreign_keys(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    child_key: str = "company_id",
    parent_key: str = "company_id",
) -> list[Any]:
    """Return IDs in the child dataset that are missing from the parent dataset."""
    if child_df.empty or parent_df.empty:
        return []
    parent_values = set(parent_df[parent_key].dropna().astype(int).tolist())
    child_values = child_df[child_key].dropna().astype(int)
    missing = sorted(set(child_values.tolist()) - parent_values)
    return missing


def log_failures(failures: list[dict[str, Any]], output_path: str = "output/validation_failures.csv") -> None:
    """Write validation failures to a CSV report."""
    logger.info("Writing validation report to %s", output_path)
    if failures:
        report_df = pd.DataFrame(failures)
    else:
        report_df = pd.DataFrame(columns=["dataset", "rule", "severity", "company", "year", "column", "expected", "actual", "message"])
    output = pd.DataFrame(report_df)
    output.to_csv(output_path, index=False)


def is_critical_failure_present(failures: list[dict[str, Any]]) -> bool:
    """Return True when any critical violation exists."""
    return any(failure.get("severity") == "CRITICAL" for failure in failures)
