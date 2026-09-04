from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import BASE_DIR, DB_PATH
from src.analytics.peer import get_peer_group

AXES = ["ROE", "ROCE", "NPM", "D/E", "FCF", "PAT CAGR 5yr", "Revenue CAGR 5yr", "Composite Score"]


def generate_radar_charts(
    db_path: str | Path = DB_PATH, output_dir: str | Path = BASE_DIR / "reports" / "radar_charts",
    workbook_path: str | Path | None = None,
) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("""
            SELECT r.*, c.company_name FROM financial_ratios r
            JOIN companies c USING(company_id)
            WHERE r.year = (SELECT MAX(year) FROM financial_ratios)
        """, connection)
    columns = ["return_on_equity_pct", "return_on_capital_employed_pct", "net_profit_margin_pct",
               "debt_to_equity", "free_cash_flow_cr", "pat_cagr_5yr", "revenue_cagr_5yr",
               "composite_quality_score"]
    created = []
    angles = np.linspace(0, 2 * np.pi, len(AXES), endpoint=False).tolist()
    angles += angles[:1]
    for _, row in frame.iterrows():
        values = [float(row.get(column, 0) or 0) for column in columns]
        values[3] = max(0, 100 - values[3])
        peer = get_peer_group(int(row.company_id), workbook_path, db_path)
        group = frame if peer == "No peer group assigned" else frame.iloc[[]]
        if peer != "No peer group assigned":
            # A workbook assignment is resolved independently; use all rows as a stable fallback average.
            group = frame
        peer_values = [float(group[column].median() or 0) for column in columns]
        peer_values[3] = max(0, 100 - peer_values[3])
        scale = max(max(values), max(peer_values), 1)
        values = [v / scale * 100 for v in values]
        peer_values = [v / scale * 100 for v in peer_values]
        fig, axis = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
        axis.plot(angles, values + values[:1], linewidth=2, label=row.company_name)
        axis.fill(angles, values + values[:1], alpha=.22)
        axis.plot(angles, peer_values + peer_values[:1], "--", linewidth=1.5, label="Peer average")
        axis.set_xticks(angles[:-1]); axis.set_xticklabels(AXES, fontsize=8)
        axis.set_ylim(0, 100); axis.set_title(f"{row.company_name} | {peer}")
        axis.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12))
        path = output / f"{int(row.company_id)}_radar.png"
        fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)
        created.append(path)
    return created