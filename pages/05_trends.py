import plotly.express as px
import streamlit as st

from _common import company_selector
from src.dashboard.utils.db import get_ratios

st.set_page_config(page_title="Trends | Nifty 100", layout="wide")
st.title("10-Year Trend Analysis")
ticker = company_selector()
if ticker:
    data = get_ratios(ticker)
    metrics = [c for c in ["return_on_equity_pct", "return_on_capital_employed_pct", "net_profit_margin_pct", "debt_to_equity", "free_cash_flow_cr"] if c in data]
    selected = st.multiselect("Metrics", metrics, default=metrics[:2], max_selections=3)
    if selected:
        chart = px.line(data.tail(10), x="year", y=selected, markers=True, title="Selected metrics")
        st.plotly_chart(chart, use_container_width=True)
