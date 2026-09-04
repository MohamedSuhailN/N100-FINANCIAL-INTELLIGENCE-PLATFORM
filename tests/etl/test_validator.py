import pandas as pd
import pytest

from src.etl.validator import (
    DQ_RULES,
    detect_duplicate_tickers,
    validate_data,
    validate_foreign_keys,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "company_id": [1, 1, 2],
            "year": [2022, 2022, 2023],
            "sales": [100, 120, -10],
            "net_profit": [20, 30, 0],
            "equity": [50, 60, 20],
            "borrowings": [20, 15, 5],
            "total_assets": [100, 120, 30],
            "ticker": ["TCS", "TCS", "INFY"],
            "sector": ["IT", "IT", "IT"],
            "url": ["https://example.com", "https://example.com", "bad-url"],
        }
    )


def test_validate_data_returns_failures_for_duplicates_and_negative_sales(sample_df):
    failures = validate_data(sample_df, "sample")
    rules = {item["rule"] for item in failures}
    assert "DQ-01" in rules
    assert "DQ-02" in rules
    assert "DQ-06" in rules


def test_validate_foreign_keys_detects_missing_reference():
    child = pd.DataFrame({"company_id": [1, 2], "year": [2022, 2023]})
    parent = pd.DataFrame({"company_id": [1]})
    assert validate_foreign_keys(child, parent, "company_id") == [2]


def test_detect_duplicate_tickers():
    df = pd.DataFrame({"ticker": ["TCS", "TCS", "INFY"]})
    assert detect_duplicate_tickers(df) == ["TCS"]


def test_dq_rules_registry_exists():
    assert len(DQ_RULES) >= 16
    assert "DQ-01" in DQ_RULES
    assert "DQ-16" in DQ_RULES


@pytest.mark.parametrize(
    "rule, expected",
    [
        ("DQ-01", "CRITICAL"),
        ("DQ-02", "CRITICAL"),
        ("DQ-03", "CRITICAL"),
        ("DQ-04", "WARNING"),
        ("DQ-05", "WARNING"),
        ("DQ-06", "WARNING"),
        ("DQ-07", "WARNING"),
        ("DQ-08", "WARNING"),
        ("DQ-09", "WARNING"),
        ("DQ-10", "WARNING"),
        ("DQ-11", "WARNING"),
        ("DQ-12", "WARNING"),
        ("DQ-13", "WARNING"),
        ("DQ-14", "WARNING"),
        ("DQ-15", "WARNING"),
        ("DQ-16", "WARNING"),
    ],
)
def test_rule_severity_map(rule, expected):
    assert DQ_RULES[rule]["severity"] == expected
