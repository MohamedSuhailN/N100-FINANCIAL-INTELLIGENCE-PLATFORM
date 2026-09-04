def compute_cagr(start_val: float, end_val: float, periods: int) -> tuple[float | None, str]:
    if periods is None or periods <= 0 or start_val is None or end_val is None:
        return None, "INSUFFICIENT"
    if start_val == 0:
        return None, "ZERO_BASE"
    if start_val > 0 and end_val < 0:
        return None, "DECLINE_TO_LOSS"
    if start_val < 0 and end_val > 0:
        return None, "TURNAROUND"
    if start_val < 0 and end_val < 0:
        return None, "BOTH_NEGATIVE"

    try:
        cagr = ((end_val / start_val) ** (1.0 / periods) - 1.0) * 100.0
        return round(cagr, 2), "NORMAL"
    except Exception:
        return None, "ERROR"
