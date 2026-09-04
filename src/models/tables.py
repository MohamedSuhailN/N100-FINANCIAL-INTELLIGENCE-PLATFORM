from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Sector:
    sector_id: Optional[int] = None
    sector_name: str = ""


@dataclass
class Company:
    company_id: Optional[int] = None
    ticker: str = ""
    company_name: str = ""
    sector_id: Optional[int] = None


@dataclass
class ProfitAndLoss:
    id: Optional[int] = None
    company_id: int = 0
    year: int = 0
    sales: Optional[float] = None
    expenses: Optional[float] = None
    opm: Optional[float] = None
    net_profit: Optional[float] = None


@dataclass
class BalanceSheet:
    id: Optional[int] = None
    company_id: int = 0
    year: int = 0
    equity_capital: Optional[float] = None
    reserves: Optional[float] = None
    borrowings: Optional[float] = None
    total_assets: Optional[float] = None


@dataclass
class CashFlow:
    id: Optional[int] = None
    company_id: int = 0
    year: int = 0
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    net_cash_flow: Optional[float] = None


@dataclass
class FinancialRatio:
    id: Optional[int] = None
    company_id: int = 0
    year: int = 0
    pe_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
