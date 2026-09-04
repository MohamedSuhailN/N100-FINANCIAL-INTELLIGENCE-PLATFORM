"""FastAPI REST service exposing the Nifty 100 analytics platform."""

from __future__ import annotations

import json
import sqlite3
import time
import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.config import BASE_DIR, DB_PATH
from src.screener.engine import ScreenerEngine

STARTED = time.time()
app = FastAPI(title="Nifty 100 Financial Intelligence API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
logger = logging.getLogger(__name__)


@app.middleware("http")
async def request_logging(request, call_next):
    """Log HTTP method, path, and request latency."""
    started = time.perf_counter()
    response = await call_next(request)
    logger.info("%s %s %.3fs", request.method, request.url.path, time.perf_counter() - started)
    return response


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(sql, connection, params=params)


def records(frame: pd.DataFrame) -> list[dict]:
    frame = frame.loc[:, ~frame.columns.duplicated()]
    return json.loads(frame.where(pd.notna(frame), None).to_json(orient="records"))


def company(ticker: str) -> pd.DataFrame:
    return query("""
        SELECT c.*, COALESCE(s.sector_name, 'Unknown') sector
        FROM companies c LEFT JOIN sectors s USING(sector_id) WHERE c.ticker = ?
    """, (ticker,))


api = APIRouter(prefix="/api/v1")


@api.get("/health")
def health():
    """Return service status and row counts for platform tables."""
    tables = ["companies", "sectors", "financial_ratios", "profitandloss", "balancesheet", "cashflow", "analysis", "documents", "prosandcons", "peer_percentiles"]
    counts = {}
    for table in tables:
        try: counts[table] = int(query(f"SELECT COUNT(*) count FROM {table}").iloc[0, 0])
        except (sqlite3.Error, IndexError): counts[table] = 0
    return {"status": "ok", "db_row_counts": counts, "uptime_seconds": round(time.time() - STARTED, 3), "version": app.version}


@api.get("/companies")
def companies(sector: str | None = None, market_cap_category: str | None = None, search: str | None = None):
    """List companies with optional sector and text filters."""
    frame = query("SELECT c.company_id, c.ticker, c.company_name, COALESCE(s.sector_name, 'Unknown') sector FROM companies c LEFT JOIN sectors s USING(sector_id)")
    if sector: frame = frame[frame.sector.str.casefold() == sector.casefold()]
    if search: frame = frame[frame.ticker.str.contains(search, case=False, na=False) | frame.company_name.str.contains(search, case=False, na=False)]
    return records(frame)


@api.get("/companies/{ticker}")
def company_profile(ticker: str):
    """Return company metadata and latest ratio record."""
    base = company(ticker)
    if base.empty: raise HTTPException(404, "Ticker not found")
    latest = query("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1", (int(base.company_id.iloc[0]),))
    result = records(base)[0]; result["latest_kpis"] = records(latest)[0] if not latest.empty else {}
    return result


def history(ticker: str, table: str, from_year: int | None, to_year: int | None):
    base = company(ticker)
    if base.empty: raise HTTPException(404, "Ticker not found")
    frame = query(f"SELECT t.* FROM {table} t WHERE company_id = ? ORDER BY year", (int(base.company_id.iloc[0]),))
    if from_year is not None: frame = frame[frame.year >= from_year]
    if to_year is not None: frame = frame[frame.year <= to_year]
    return records(frame)


@api.get("/companies/{ticker}/pl")
def pl(ticker: str, from_year: int | None = None, to_year: int | None = None): return history(ticker, "profitandloss", from_year, to_year)


@api.get("/companies/{ticker}/bs")
def bs(ticker: str, from_year: int | None = None, to_year: int | None = None): return history(ticker, "balancesheet", from_year, to_year)


@api.get("/companies/{ticker}/cashflow")
def cashflow(ticker: str, from_year: int | None = None, to_year: int | None = None): return history(ticker, "cashflow", from_year, to_year)


@api.get("/companies/{ticker}/ratios")
def ratios(ticker: str, from_year: int | None = None, to_year: int | None = None): return history(ticker, "financial_ratios", from_year, to_year)


@api.get("/companies/{ticker}/tearsheet")
def tearsheet(ticker: str):
    """Download a generated company tearsheet PDF."""
    path = BASE_DIR / "reports" / "tearsheets" / f"{ticker}_tearsheet.pdf"
    if not path.exists(): raise HTTPException(404, "Tearsheet not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@api.get("/screener")
def screener(min_roe: float | None = None, max_de: float | None = None, min_fcf: float | None = None, sector: str | None = None, min_rev_cagr_5yr: float | None = None, min_pat_cagr_5yr: float | None = None, max_pe: float | None = None):
    """Filter latest company KPIs, rejecting contradictory numeric ranges."""
    if max_de is not None and max_de < 0 or max_pe is not None and max_pe < 0: raise HTTPException(400, "Maximum values must be non-negative")
    frame = ScreenerEngine().load_data()
    if min_roe is not None: frame = frame[frame.return_on_equity_pct >= min_roe]
    if max_de is not None: frame = frame[(frame.debt_to_equity <= max_de) | frame.broad_sector.eq("Financials")]
    if min_fcf is not None: frame = frame[frame.free_cash_flow_cr >= min_fcf]
    if sector: frame = frame[frame.broad_sector.str.casefold() == sector.casefold()]
    if min_rev_cagr_5yr is not None: frame = frame[frame.revenue_cagr_5yr >= min_rev_cagr_5yr]
    if min_pat_cagr_5yr is not None: frame = frame[frame.pat_cagr_5yr >= min_pat_cagr_5yr]
    if max_pe is not None and "pe_ratio" in frame: frame = frame[frame.pe_ratio.fillna(0) <= max_pe]
    return records(frame)


@api.get("/sectors")
def sectors():
    """Return sector summary metrics."""
    frame = query("""SELECT COALESCE(s.sector_name, 'Unknown') sector, COUNT(DISTINCT c.company_id) company_count, AVG(r.return_on_equity_pct) median_roe, NULL AS median_pe, AVG(r.debt_to_equity) median_de FROM companies c LEFT JOIN sectors s USING(sector_id) JOIN financial_ratios r USING(company_id) WHERE r.year = (SELECT MAX(year) FROM financial_ratios) GROUP BY sector""")
    return records(frame)


@api.get("/sectors/{sector}/companies")
def sector_companies(sector: str):
    """Return companies and latest KPIs for one sector."""
    frame = query("""SELECT c.company_id, c.ticker, c.company_name, s.sector_name sector, r.* FROM companies c JOIN sectors s USING(sector_id) JOIN financial_ratios r USING(company_id) WHERE s.sector_name = ? AND r.year = (SELECT MAX(year) FROM financial_ratios)""", (sector,))
    if frame.empty: raise HTTPException(404, "Sector not found")
    return records(frame)


@api.get("/peers/{group_name}")
def peers(group_name: str):
    """Return peer percentile rows for a group."""
    frame = query("SELECT p.*, c.company_name, c.ticker FROM peer_percentiles p JOIN companies c USING(company_id) WHERE peer_group_name = ?", (group_name,))
    if frame.empty: raise HTTPException(404, "Peer group not found")
    return records(frame)


@api.get("/companies/{ticker}/peers/compare")
def peer_compare(ticker: str):
    """Return eight-axis percentile values and peer averages."""
    base = company(ticker)
    if base.empty: raise HTTPException(404, "Ticker not found")
    rows = query("SELECT * FROM peer_percentiles WHERE company_id = ?", (int(base.company_id.iloc[0]),))
    return {"ticker": ticker, "benchmark": records(rows), "peer_average": records(query("SELECT metric, AVG(percentile_rank) percentile_rank FROM peer_percentiles GROUP BY metric"))}


@api.get("/market-cap/{ticker}")
def market_cap(ticker: str):
    """Return available valuation history for a company."""
    base = company(ticker)
    if base.empty: raise HTTPException(404, "Ticker not found")
    return {"dataset_status": "SIMULATED", "data": records(query("SELECT r.year, NULL AS pe, NULL AS pb, r.free_cash_flow_cr FROM financial_ratios r WHERE company_id = ? ORDER BY year", (int(base.company_id.iloc[0]),)))}


@api.get("/portfolio/stats")
def portfolio_stats():
    """Return the portfolio percentile distribution table."""
    path = BASE_DIR / "output" / "portfolio_stats.csv"
    if not path.exists(): raise HTTPException(404, "Portfolio statistics not generated")
    return records(pd.read_csv(path))


@api.get("/companies/{ticker}/documents")
def documents(ticker: str):
    """Return annual report links and URL validity flags."""
    base = company(ticker)
    if base.empty: raise HTTPException(404, "Ticker not found")
    frame = query("SELECT doc_type, url, created_at FROM documents WHERE company_id = ?", (int(base.company_id.iloc[0]),))
    if frame.empty: return []
    frame["is_url_valid"] = frame.url.notna() & frame.url.str.startswith(("http://", "https://"), na=False)
    return records(frame)


app.include_router(api)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)