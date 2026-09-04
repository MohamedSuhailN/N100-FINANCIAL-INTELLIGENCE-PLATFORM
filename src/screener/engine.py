from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.config import BASE_DIR, DB_PATH

CONFIG_PATH = BASE_DIR / "config" / "screener_config.yaml"
SCORE_WEIGHTS = {
    "return_on_equity_pct": .15,
    "return_on_capital_employed_pct": .10,
    "net_profit_margin_pct": .10,
    "fcf_cagr_5yr": .15,
    "cfo_pat_ratio": .10,
    "fcf_positive": .05,
    "revenue_cagr_5yr": .10,
    "pat_cagr_5yr": .10,
    "debt_to_equity_score": .10,
    "interest_coverage_score": .05,
}


def _latest_frame(db_path: str | Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("""
            SELECT c.company_id, c.ticker, c.company_name,
                   s.sector_name AS broad_sector, r.*, p.sales AS revenue_cr,
                   CASE WHEN p.net_profit IS NULL OR p.net_profit = 0 THEN NULL
                        ELSE r.cash_from_operations_cr / p.net_profit END AS cfo_pat_ratio
            FROM financial_ratios r JOIN companies c USING(company_id)
            LEFT JOIN sectors s USING(sector_id)
            LEFT JOIN profitandloss p USING(company_id, year)
            WHERE r.year = (SELECT MAX(r2.year) FROM financial_ratios r2
                            WHERE r2.company_id = r.company_id)
        """, connection)
    frame = frame.loc[:, ~frame.columns.duplicated()]
    for column in ("pe_ratio", "pb_ratio", "dividend_yield_pct"):
        if column not in frame:
            frame[column] = math.nan
    return frame


def _number(value: Any) -> float:
    if isinstance(value, str) and value.strip().lower() == "debt free":
        return math.inf
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _winsor_scale(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    values = pd.to_numeric(series.map(_number), errors="coerce")
    if values.notna().sum() < 2 or values.max() == values.min():
        return pd.Series(50.0, index=series.index)
    low, high = values.quantile(.10), values.quantile(.90)
    score = (values.clip(low, high) - low) / (high - low) * 100
    return score if higher_is_better else 100 - score


def calculate_composite_quality_score(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    components: dict[str, pd.Series] = {}
    for metric, weight in SCORE_WEIGHTS.items():
        source = metric
        if metric == "fcf_positive":
            result[metric] = pd.to_numeric(result.get("free_cash_flow_cr", 0), errors="coerce").gt(0)
        elif metric == "debt_to_equity_score":
            source = "debt_to_equity"
        elif metric == "interest_coverage_score":
            source = "interest_coverage"
        elif metric == "fcf_cagr_5yr" and source not in result:
            result[source] = result.get("free_cash_flow_cr", pd.Series(index=result.index))
        if source not in result:
            result[source] = math.nan
        components[metric] = _winsor_scale(
            result[source], higher_is_better=metric != "debt_to_equity_score"
        ) * weight
    raw = pd.DataFrame(components, index=result.index).sum(axis=1, min_count=1)
    sector = result.get("broad_sector", pd.Series("Nifty 100", index=result.index))
    mean = raw.groupby(sector, dropna=False).transform("mean")
    std = raw.groupby(sector, dropna=False).transform("std").replace(0, 1).fillna(1)
    result["composite_quality_score"] = (50 + 15 * (raw - mean) / std).clip(0, 100).fillna(raw).round(2)
    return result


class ScreenerEngine:
    def __init__(self, db_path: str | Path = DB_PATH, config_path: str | Path = CONFIG_PATH):
        self.db_path = Path(db_path)
        self.config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))

    def load_data(self) -> pd.DataFrame:
        return calculate_composite_quality_score(_latest_frame(self.db_path))

    def filter_metrics(self, frame: pd.DataFrame, filters: dict[str, dict[str, Any]]) -> pd.DataFrame:
        result = frame.copy()
        for metric, rule in filters.items():
            column = self.config.get("metrics", {}).get(metric, {}).get("column", metric)
            if column not in result:
                continue
            values = result[column].map(_number)
            if rule.get("declining_yoy"):
                if "de_ratio_declining" in result:
                    result = result[result["de_ratio_declining"].fillna(True)]
                continue
            if rule.get("min") is not None:
                result = result[values >= rule["min"]]
            if rule.get("max") is not None:
                financial = result.get("broad_sector", pd.Series(False, index=result.index)).eq("Financials")
                if metric == "debt_to_equity":
                    result = result[financial | values.le(rule["max"])]
                else:
                    result = result[values <= rule["max"]]
            if rule.get("eq") is not None:
                result = result[values == rule["eq"]]
        return result

    def run_preset_screener(self, preset_name: str) -> pd.DataFrame:
        presets = self.config.get("presets", {})
        if preset_name not in presets:
            raise KeyError(f"Unknown preset: {preset_name}")
        result = self.filter_metrics(self.load_data(), presets[preset_name])
        return result.sort_values("composite_quality_score", ascending=False).reset_index(drop=True)


def run_preset_screener(preset_name: str, db_path: str | Path = DB_PATH) -> pd.DataFrame:
    return ScreenerEngine(db_path=db_path).run_preset_screener(preset_name)