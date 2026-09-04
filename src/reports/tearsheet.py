from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.config import BASE_DIR, DB_PATH


def _chart(history: pd.DataFrame, kind: str) -> io.BytesIO:
    figure, axis = plt.subplots(figsize=(8.5, 2.7), dpi=150)
    if kind == "income":
        axis.bar(history.year - .2, history.sales, width=.4, label="Revenue", color="#17365D")
        axis.bar(history.year + .2, history.net_profit, width=.4, label="Net Profit", color="#4F81BD")
        axis.set_ylabel("Crore")
    elif kind == "returns":
        axis.plot(history.year, history.return_on_equity_pct, marker="o", label="ROE", color="#17365D")
        axis.plot(history.year, history.return_on_capital_employed_pct, marker="o", label="ROCE", color="#70AD47")
        axis.set_ylabel("Percent")
    else:
        axis.bar(history.year, history.borrowings, label="Borrowings", color="#A5A5A5")
        axis.plot(history.year, history.operating_cash_flow, marker="o", label="CFO", color="#70AD47")
        axis.plot(history.year, history.free_cash_flow_cr, marker="o", label="FCF", color="#ED7D31")
        axis.set_ylabel("Crore")
    axis.set_title(kind.title()); axis.grid(axis="y", alpha=.2); axis.legend(fontsize=7)
    figure.tight_layout(); buffer = io.BytesIO(); figure.savefig(buffer, format="png"); plt.close(figure); buffer.seek(0)
    return buffer


def _table(rows: list[list[object]], widths=None) -> Table:
    wrapped = [[Paragraph(str(cell), getSampleStyleSheet()["BodyText"]) for cell in row] for row in rows]
    table = Table(wrapped, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#D9E2F3")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 7), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FC")])]))
    return table


def generate_tearsheets(db_path: str | Path = DB_PATH, output_dir: str | Path = BASE_DIR / "reports" / "tearsheets", output_root: str | Path = BASE_DIR / "output") -> tuple[list[Path], pd.DataFrame]:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True); root = Path(output_root); root.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        data = pd.read_sql_query("""
            SELECT c.company_id, c.ticker, c.company_name, COALESCE(s.sector_name, 'Unknown') sector,
                   p.year, p.sales, p.net_profit, b.borrowings, b.total_assets,
                   f.operating_cash_flow, f.investing_cash_flow, f.financing_cash_flow,
                   r.free_cash_flow_cr, r.return_on_equity_pct, r.return_on_capital_employed_pct,
                   r.net_profit_margin_pct, r.debt_to_equity, r.revenue_cagr_5yr,
                   r.capital_allocation_pattern
            FROM companies c LEFT JOIN sectors s USING(sector_id)
            JOIN profitandloss p USING(company_id) JOIN balancesheet b USING(company_id, year)
            JOIN cashflow f USING(company_id, year) JOIN financial_ratios r USING(company_id, year)
            ORDER BY c.ticker, p.year
        """, connection)
    skipped = []; created = []
    for (company_id, ticker, name, sector), history in data.groupby(["company_id", "ticker", "company_name", "sector"]):
        if len(history) < 3:
            skipped.append({"ticker": ticker, "reason": "fewer than 3 years of history"}); continue
        latest = history.iloc[-1]
        path = output / f"{ticker}_tearsheet.pdf"
        document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=30, leftMargin=30, topMargin=25, bottomMargin=25)
        story = [Table([[Paragraph(f"{name} ({ticker})", getSampleStyleSheet()["Title"]), Paragraph(f"Sector: {sector}<br/>Company ID: {company_id}", getSampleStyleSheet()["BodyText"])]], colWidths=[4.2 * inch, 3 * inch], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#17365D")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (0, 0), (-1, -1), 0, colors.white)])), Spacer(1, 8)]
        kpis = [["ROE", "ROCE", "NPM"], [f"{latest.return_on_equity_pct:.2f}%", f"{latest.return_on_capital_employed_pct:.2f}%", f"{latest.net_profit_margin_pct:.2f}%"], ["D/E", "Revenue CAGR", "Latest FCF"], [f"{latest.debt_to_equity:.2f}", f"{latest.revenue_cagr_5yr if pd.notna(latest.revenue_cagr_5yr) else 'N/A'}%", f"{latest.free_cash_flow_cr:.2f}"]]
        story += [_table(kpis, [2.4 * inch] * 3), Spacer(1, 8), Image(_chart(history.tail(10), "income"), width=7.1 * inch, height=2.25 * inch), Image(_chart(history.tail(10), "returns"), width=7.1 * inch, height=2.25 * inch), PageBreak()]
        story += [Paragraph("Balance Sheet and Cash Flow", getSampleStyleSheet()["Heading2"]), Image(_chart(history.tail(10), "cash"), width=7.1 * inch, height=2.25 * inch), Spacer(1, 6)]
        bullets = [["Pros", "Cons"], ["Positive financial operating signal", "Financial risks should be monitored"]]
        story += [_table(bullets, [3.5 * inch, 3.5 * inch]), Spacer(1, 8), Paragraph(f"Capital Allocation: {latest.capital_allocation_pattern or 'N/A'}", getSampleStyleSheet()["Heading3"])]
        document.build(story); created.append(path)
    pd.DataFrame(skipped, columns=["ticker", "reason"]).to_csv(root / "skipped_tearsheets.csv", index=False)
    return created, pd.DataFrame(skipped)


generate_company_tearsheets = generate_tearsheets