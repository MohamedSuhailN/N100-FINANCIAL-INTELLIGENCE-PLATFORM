import plotly.graph_objects as go
import streamlit as st

from _common import company_selector, render_metric_tiles
from src.dashboard.utils.db import get_companies, get_pl, get_ratios

st.set_page_config(page_title="Profile | Nifty 100", layout="wide")
st.title("Company Deep-Dive")
ticker = company_selector()
if ticker:
    company = get_companies().query("ticker == @ticker").iloc[0]
    ratios, pl = get_ratios(ticker), get_pl(ticker)
    if ratios.empty:
        st.error("Ticker not found — please try another")
    else:
        latest = ratios.iloc[-1]
        st.subheader(company.company_name)
        st.caption(f"NSE: {ticker} | Sector: {company.sector}")
        render_metric_tiles({"ROE": latest.get("return_on_equity_pct"), "ROCE": latest.get("return_on_capital_employed_pct"), "NPM": latest.get("net_profit_margin_pct"), "D/E": latest.get("debt_to_equity"), "Revenue CAGR": latest.get("revenue_cagr_5yr"), "FCF": latest.get("free_cash_flow_cr")})
        if not pl.empty:
            fig = go.Figure([go.Bar(x=pl.year, y=pl.sales, name="Revenue"), go.Bar(x=pl.year, y=pl.net_profit, name="Net Profit")])
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("Pros & Cons")
        st.info("Pros and cons are unavailable for this company.")
