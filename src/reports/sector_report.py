from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.config import BASE_DIR, DB_PATH


def _wrapped_table(frame: pd.DataFrame) -> Table:
    styles = getSampleStyleSheet(); values = [[Paragraph(str(c), styles["BodyText"]) for c in frame.columns]]
    values += [[Paragraph(str(value), styles["BodyText"]) for value in row] for row in frame.itertuples(index=False, name=None)]
    table = Table(values, repeatRows=1, colWidths=[1.1 * inch] * len(frame.columns))
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 6), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def generate_sector_reports(db_path: str | Path = DB_PATH, output_dir: str | Path = BASE_DIR / "reports" / "sector") -> list[Path]:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("""
            SELECT c.company_id, c.company_name, c.ticker, COALESCE(s.sector_name, 'Unknown') sector,
                   r.return_on_equity_pct AS ROE, r.return_on_capital_employed_pct AS ROCE,
                   r.net_profit_margin_pct AS NPM, r.debt_to_equity AS DE,
                   r.free_cash_flow_cr AS FCF, r.revenue_cagr_5yr AS Revenue_CAGR,
                   r.pat_cagr_5yr AS PAT_CAGR, r.composite_quality_score AS Quality
            FROM companies c LEFT JOIN sectors s USING(sector_id)
            JOIN financial_ratios r USING(company_id)
            WHERE r.year = (SELECT MAX(year) FROM financial_ratios)
        """, connection)
    paths = []
    groups = {sector: subset for sector, subset in frame.groupby("sector")}
    if len(groups) < 11:
        with sqlite3.connect(db_path) as connection:
            peer_groups = pd.read_sql_query("SELECT DISTINCT company_id, peer_group_name FROM peer_percentiles", connection)
        if not peer_groups.empty:
            groups = {}
            for name, assignments in peer_groups.groupby("peer_group_name"):
                groups[name] = frame[frame.company_id.isin(assignments.company_id)]
    for sector, subset in groups.items():
        path = output / f"{str(sector).replace('/', '_')}_report.pdf"
        document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
        summary = subset.select_dtypes("number").median().round(2).to_frame("Median").reset_index().rename(columns={"index": "Metric"})
        detail = subset.drop(columns=["sector"], errors="ignore").round(2)
        story = [Paragraph(f"{sector} Sector Report", getSampleStyleSheet()["Title"]), Paragraph(f"{len(subset)} companies | Latest available year", getSampleStyleSheet()["BodyText"]), Spacer(1, 10), Paragraph("Median KPIs", getSampleStyleSheet()["Heading2"]), _wrapped_table(summary), Spacer(1, 10), Paragraph("Company comparison", getSampleStyleSheet()["Heading2"]), _wrapped_table(detail)]
        document.build(story); paths.append(path)
    return paths


def generate_portfolio_summary(db_path: str | Path = DB_PATH, output_path: str | Path = BASE_DIR / "reports" / "portfolio" / "portfolio_summary.pdf") -> Path:
    output = Path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("""
            SELECT c.ticker, c.company_name, COALESCE(s.sector_name, 'Unknown') sector,
                   r.year, r.return_on_equity_pct AS ROE, r.return_on_capital_employed_pct AS ROCE,
                   r.net_profit_margin_pct AS NPM, r.debt_to_equity AS DE,
                   r.revenue_cagr_5yr AS Revenue_CAGR, r.free_cash_flow_cr AS FCF
            FROM companies c LEFT JOIN sectors s USING(sector_id)
            JOIN financial_ratios r USING(company_id)
            ORDER BY c.ticker, r.year
        """, connection)
    styles = getSampleStyleSheet(); story = []
    for (ticker, name, sector), history in frame.groupby(["ticker", "company_name", "sector"], sort=True):
        latest = history.iloc[-1]; previous = history.iloc[-2]
        rows = [["KPI", "Value", "Trend"]]
        for metric in ["ROE", "ROCE", "NPM", "DE", "Revenue_CAGR", "FCF"]:
            current, prior = latest[metric], previous[metric]
            trend = "Up" if current > prior else "Down" if current < prior else "Flat"
            rows.append([metric, "N/A" if pd.isna(current) else round(current, 2), trend])
        story += [Paragraph(f"{name} ({ticker})", styles["Title"]), Paragraph(f"Sector: {sector}", styles["Heading3"]), _wrapped_table(pd.DataFrame(rows[1:], columns=rows[0])), PageBreak()]
    document = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35); document.build(story[:-1]); return output