import plotly.graph_objects as go
import streamlit as st

from src.analytics.peer import PEER_METRICS, load_peer_groups
from src.dashboard.utils.db import get_peers

st.set_page_config(page_title="Peers | Nifty 100", layout="wide")
st.title("Peer Comparison")
groups = load_peer_groups()["peer_group_name"].unique().tolist()
group = st.selectbox("Peer group", groups)
peers = get_peers(group)
if peers.empty:
    st.info("No peer data available")
else:
    company = st.selectbox("Company", peers.company_name.unique())
    selected = peers[peers.company_name == company].set_index("metric")["percentile_rank"]
    average = peers.groupby("metric").percentile_rank.mean()
    labels = list(PEER_METRICS)
    fig = go.Figure()
    for name, values, dash in [(company, selected, "solid"), ("Peer average", average, "dash")]:
        points = [float(values.get(label, 0)) * 100 for label in labels]
        fig.add_trace(go.Scatterpolar(r=points + points[:1], theta=labels + labels[:1], fill="toself" if name == company else None, name=name, line={"dash": dash}))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(peers[peers.company_name == company], hide_index=True, use_container_width=True)
