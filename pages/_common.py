from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios


def safe(value) -> str:
    return "N/A" if pd.isna(value) else str(value)


def company_selector(label: str = "Company") -> str | None:
    companies = get_companies()
    if companies.empty:
        st.warning("No company data available")
        return None
    labels = {f"{row.ticker} | {row.company_name}": row.ticker for row in companies.itertuples()}
    selected = st.selectbox(label, list(labels))
    return labels[selected]


def latest_frame(year: int = 2024) -> pd.DataFrame:
    companies = get_companies()
    frames = [get_ratios(ticker, year) for ticker in companies.ticker] if not companies.empty else []
    ratios = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True) if frames else pd.DataFrame()
    return companies.merge(ratios, on=["company_id", "ticker", "company_name", "sector"], how="left")


def render_metric_tiles(values: dict[str, object]) -> None:
    cols = st.columns(len(values))
    for col, (label, value) in zip(cols, values.items()):
        col.metric(label, safe(value))
