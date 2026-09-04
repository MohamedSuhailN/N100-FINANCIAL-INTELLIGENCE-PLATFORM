def compute_net_profit_margin(net_profit: float, sales: float) -> float | None:
    if sales is None or sales == 0:
        return None
    return round((net_profit / sales) * 100, 2)

def compute_operating_profit_margin(operating_profit: float, sales: float) -> float | None:
    if sales is None or sales == 0:
        return None
    return round((operating_profit / sales) * 100, 2)

def compute_roe(net_profit: float, equity_capital: float, reserves: float) -> float | None:
    total_equity = (equity_capital or 0) + (reserves or 0)
    if total_equity <= 0 or net_profit is None:
        return None
    return round((net_profit / total_equity) * 100, 2)

def compute_roce(ebit: float, equity_capital: float, reserves: float, borrowings: float, is_financial: bool = False) -> float | None:
    capital_employed = (equity_capital or 0) + (reserves or 0) + (borrowings or 0)
    if capital_employed <= 0 or ebit is None:
        return None
    roce = (ebit / capital_employed) * 100
    return round(roce, 2)

def compute_roa(net_profit: float, total_assets: float) -> float | None:
    if total_assets is None or total_assets <= 0 or net_profit is None:
        return None
    return round((net_profit / total_assets) * 100, 2)

def compute_debt_to_equity(borrowings: float, equity_capital: float, reserves: float, is_financial: bool = False) -> tuple[float | None, bool]:
    total_equity = (equity_capital or 0) + (reserves or 0)
    if total_equity <= 0:
        return None, False
    if borrowings is None or borrowings == 0:
        return 0.0, False
    de = round(borrowings / total_equity, 2)
    high_leverage = (de > 5.0) and (not is_financial)
    return de, high_leverage

def compute_interest_coverage(operating_profit: float, other_income: float, interest: float) -> tuple[float | None, str | None, bool]:
    if interest is None or interest == 0:
        return None, "Debt Free", False
    earnings = (operating_profit or 0) + (other_income or 0)
    icr = round(earnings / interest, 2)
    warning = icr < 1.5
    return icr, None, warning

def compute_net_debt(borrowings: float, investments: float) -> float:
    return round((borrowings or 0) - (investments or 0), 2)

def compute_asset_turnover(sales: float, total_assets: float) -> float | None:
    if total_assets is None or total_assets <= 0 or sales is None:
        return None
    return round(sales / total_assets, 2)


# Backward-compatible names used by the ratio population pipeline.
net_profit_margin = compute_net_profit_margin


def operating_profit_margin(operating_profit, sales, source_margin=None):
    """Compute OPM while accepting the legacy source-margin argument."""
    return compute_operating_profit_margin(operating_profit, sales)


return_on_equity = compute_roe
return_on_capital_employed = compute_roce
return_on_assets = compute_roa
debt_to_equity = compute_debt_to_equity
interest_coverage_ratio = compute_interest_coverage
net_debt = compute_net_debt
asset_turnover = compute_asset_turnover
