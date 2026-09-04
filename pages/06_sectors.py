import plotly.express as px
import streamlit as st

from _common import latest_frame

st.set_page_config(page_title="Sectors | Nifty 100", layout="wide")
st.title("Sector Analytics")
data = latest_frame()
if not data.empty:
    sector = st.selectbox("Sector", sorted(data.sector.dropna().unique()))
    subset = data[data.sector == sector]
    st.plotly_chart(px.scatter(subset, x="revenue_cr", y="return_on_equity_pct", size="revenue_cr", color="company_name", hover_name="company_name", title=f"{sector} companies"), use_container_width=True)
    medians = subset.select_dtypes("number").median().reset_index(name="value").rename(columns={"index": "metric"})
    st.plotly_chart(px.bar(medians, x="metric", y="value", title="Sector median KPIs"), use_container_width=True)
