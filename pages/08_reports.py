import streamlit as st

from _common import company_selector
from src.dashboard.utils.db import _query

st.set_page_config(page_title="Reports | Nifty 100", layout="wide")
st.title("Annual Reports Repository")
ticker = company_selector()
if ticker:
    reports = _query("SELECT d.doc_type, d.url, d.created_at FROM documents d JOIN companies c USING(company_id) WHERE c.ticker = ? ORDER BY d.created_at DESC", (ticker,))
    if reports.empty:
        st.info("No annual reports available")
    else:
        for row in reports.itertuples():
            if row.url:
                st.link_button(f"{row.doc_type} ({row.created_at})", row.url)
            else:
                st.error("Report unavailable")
