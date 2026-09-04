import plotly.express as px
import streamlit as st

from _common import latest_frame

st.set_page_config(page_title="Capital | Nifty 100", layout="wide")
st.title("Capital Allocation Map")
data = latest_frame()
if not data.empty and "capital_allocation_pattern" in data:
    counts = data.groupby("capital_allocation_pattern").size().reset_index(name="companies")
    st.plotly_chart(px.treemap(counts, path=["capital_allocation_pattern"], values="companies"), use_container_width=True)
    pattern = st.selectbox("Pattern", counts.capital_allocation_pattern)
    st.dataframe(data[data.capital_allocation_pattern == pattern][["company_name", "sector"]], hide_index=True)
else:
    st.info("Capital allocation data unavailable")
