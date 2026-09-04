from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import BASE_DIR, DB_PATH


def _database_path() -> Path:
    preferred = BASE_DIR / "data" / "nifty100.db"
    return preferred if preferred.exists() else DB_PATH


def _query(sql: str, params: tuple = ()) -> pd.DataFrame:
    try:
        with sqlite3.connect(_database_path()) as connection:
            return pd.read_sql_query(sql, connection, params=params)
    except (sqlite3.Error, OSError, pd.errors.DatabaseError):
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    return _query("""
        SELECT c.company_id, c.ticker, c.company_name, c.sector_id,
               COALESCE(s.sector_name, 'Unknown') AS sector
        FROM companies c LEFT JOIN sectors s USING(sector_id)
        ORDER BY c.company_name
    """)


@st.cache_data(ttl=600)
def get_ratios(ticker: str, year: int | None = None) -> pd.DataFrame:
    clause = "AND r.year = ?" if year is not None else ""
    params = (ticker, year) if year is not None else (ticker,)
    return _query(f"""
        SELECT r.*, c.ticker, c.company_name, COALESCE(s.sector_name, 'Unknown') AS sector
        FROM financial_ratios r JOIN companies c USING(company_id)
        LEFT JOIN sectors s USING(sector_id)
        WHERE c.ticker = ? {clause} ORDER BY r.year
    """, params)


def _company_table(table: str, ticker: str) -> pd.DataFrame:
    return _query(f"""
        SELECT t.*, c.ticker, c.company_name
        FROM {table} t JOIN companies c USING(company_id)
        WHERE c.ticker = ? ORDER BY t.year
    """, (ticker,))


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    return _company_table("profitandloss", ticker)


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    return _company_table("balancesheet", ticker)


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    return _company_table("cashflow", ticker)


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    return _query("SELECT sector_id, sector_name FROM sectors ORDER BY sector_name")


@st.cache_data(ttl=600)
def get_peers(group_name: str) -> pd.DataFrame:
    return _query("""
        SELECT p.*, c.company_name, c.ticker
        FROM peer_percentiles p JOIN companies c USING(company_id)
        WHERE p.peer_group_name = ? ORDER BY c.company_name
    """, (group_name,))


@st.cache_data(ttl=600)
def get_valuation(ticker: str) -> pd.DataFrame:
    return _query("SELECT * FROM valuation_summary WHERE ticker = ?", (ticker,))