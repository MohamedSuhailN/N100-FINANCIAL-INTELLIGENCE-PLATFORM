import plotly.express as px
import streamlit as st

from _common import latest_frame, render_metric_tiles

st.set_page_config(page_title="Home | Nifty 100", layout="wide")
st.title("Nifty 100 Overview")
year = st.sidebar.selectbox("Year", list(range(2019, 2025)), index=5)
frame = latest_frame(year)
if frame.empty:
    st.warning("No data available for this year")
else:
    render_metric_tiles({"Average ROE": frame.return_on_equity_pct.mean(), "Median P/E": frame.pe_ratio.median() if "pe_ratio" in frame else None, "Median D/E": frame.debt_to_equity.median(), "Companies": frame.company_id.nunique(), "Median Revenue CAGR": frame.revenue_cagr_5yr.median(), "Debt-Free": (frame.debt_to_equity == 0).sum()})
    left, right = st.columns(2)
    with left:
        counts = frame.groupby("sector", dropna=False).company_id.nunique().reset_index(name="count")
        st.plotly_chart(px.pie(counts, names="sector", values="count", hole=.5, title="Companies by sector"), use_container_width=True)
    with right:
        st.subheader("Top 5 quality companies")
        st.dataframe(frame.nlargest(5, "composite_quality_score")[["company_name", "sector", "composite_quality_score"]], hide_index=True, use_container_width=True)
