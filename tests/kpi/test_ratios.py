import pytest
from src.analytics.ratios import (
    compute_net_profit_margin, compute_roe, compute_roce, 
    compute_debt_to_equity, compute_interest_coverage
)
from src.analytics.cagr import compute_cagr
from src.analytics.cashflow_kpis import compute_free_cash_flow, classify_capital_allocation

def test_profitability():
    assert compute_net_profit_margin(20, 100) == 20.0
    assert compute_net_profit_margin(20, 0) is None
    assert compute_roe(50, 100, 150) == 20.0

def test_leverage():
    de, flag = compute_debt_to_equity(0, 100, 100)
    assert de == 0.0 and flag is False
    icr, label, _ = compute_interest_coverage(100, 10, 0)
    assert icr is None and label == "Debt Free"

def test_cagr_flags():
    assert compute_cagr(100, 200, 5) == (14.87, "NORMAL")
    assert compute_cagr(-50, 100, 5) == (None, "TURNAROUND")
    assert compute_cagr(100, -20, 5) == (None, "DECLINE_TO_LOSS")

def test_cashflow():
    assert compute_free_cash_flow(200, -120) == 80.0
    assert classify_capital_allocation(100, -50, -20) == "Reinvestor"
