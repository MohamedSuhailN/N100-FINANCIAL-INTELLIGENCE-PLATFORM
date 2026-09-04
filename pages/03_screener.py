import streamlit as st

from src.screener.engine import ScreenerEngine

st.set_page_config(page_title="Screener | Nifty 100", layout="wide")
st.title("Custom Financial Screener")
engine = ScreenerEngine(); data = engine.load_data()
with st.sidebar:
    st.header("Filters")
    minimum_roe = st.slider("Min ROE", -50.0, 100.0, 0.0)
    maximum_de = st.slider("Max D/E", 0.0, 10.0, 10.0)
    minimum_fcf = st.number_input("Min FCF", value=-1e9)
    minimum_revenue_cagr = st.slider("Min Revenue CAGR", -100.0, 100.0, -100.0)
    minimum_pat_cagr = st.slider("Min PAT CAGR", -100.0, 100.0, -100.0)
    minimum_opm = st.slider("Min OPM", -100.0, 100.0, -100.0)
    maximum_pe = st.number_input("Max P/E", value=1e9)
    maximum_pb = st.number_input("Max P/B", value=1e9)
    minimum_dividend = st.number_input("Min Div Yield", value=-1e9)
    minimum_icr = st.number_input("Min ICR", value=-1e9)
    preset = st.selectbox("Preset", ["Custom"] + list(engine.config["presets"]))
if preset != "Custom":
    result = engine.run_preset_screener(preset)
else:
    result = data[(data.return_on_equity_pct >= minimum_roe) & (data.debt_to_equity <= maximum_de) & (data.free_cash_flow_cr >= minimum_fcf) & (data.revenue_cagr_5yr >= minimum_revenue_cagr) & (data.pat_cagr_5yr >= minimum_pat_cagr) & (data.operating_profit_margin_pct >= minimum_opm) & (data.pe_ratio.fillna(0) <= maximum_pe) & (data.pb_ratio.fillna(0) <= maximum_pb) & (data.interest_coverage.fillna(0) >= minimum_icr)]
st.subheader(f"{len(result)} companies match your filters")
display = [c for c in ["company_id", "company_name", "broad_sector", "composite_quality_score", "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr", "revenue_cagr_5yr", "pat_cagr_5yr"] if c in result]
st.dataframe(result[display], hide_index=True, use_container_width=True)
st.download_button("Download CSV", result.to_csv(index=False), "screener_results.csv", "text/csv")
