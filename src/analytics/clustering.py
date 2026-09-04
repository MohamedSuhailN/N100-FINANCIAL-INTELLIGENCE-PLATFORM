"""Portfolio clustering, profiling, correlation, and outlier analytics."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.config import BASE_DIR, DB_PATH

FEATURES = [
    "return_on_equity_pct", "debt_to_equity", "revenue_cagr_5yr",
    "fcf_cagr_5yr", "operating_profit_margin_pct",
]
ARCHETYPES = [
    "High-Quality Compounders", "Defensive Dividend Payers", "Value Cyclicals",
    "Distressed/Turnaround", "Emerging Growth",
]


def _latest_data(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("""
            SELECT c.company_id, c.company_name, COALESCE(s.sector_name, 'Unknown') AS broad_sector,
                   r.*, p.sales AS revenue_cr
            FROM companies c LEFT JOIN sectors s USING(sector_id)
            JOIN financial_ratios r USING(company_id)
            LEFT JOIN profitandloss p USING(company_id, year)
            WHERE r.year = (SELECT MAX(year) FROM financial_ratios)
        """, connection)
        if "fcf_cagr_5yr" not in frame:
            frame["fcf_cagr_5yr"] = frame["free_cash_flow_cr"]
        return frame


def _prepare_features(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame[FEATURES].copy()
    for column in FEATURES:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
        prepared[column] = prepared[column].fillna(
            frame.assign(_value=prepared[column]).groupby("broad_sector")["_value"].transform("median")
        )
        prepared[column] = prepared[column].fillna(prepared[column].median()).fillna(0)
    return prepared


def run_clustering(
    db_path: str | Path = DB_PATH,
    output_dir: str | Path = BASE_DIR / "output",
    reports_dir: str | Path = BASE_DIR / "reports",
    n_clusters: int = 5,
) -> pd.DataFrame:
    """Run KMeans and export labels, elbow, correlations, outliers, and statistics."""
    output = Path(output_dir); reports = Path(reports_dir)
    output.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)
    frame = _latest_data(db_path)
    features = _prepare_features(frame)
    scaled = StandardScaler().fit_transform(features)
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit(scaled)
    centers = model.cluster_centers_
    distances = ((scaled - centers[model.labels_]) ** 2).sum(axis=1) ** .5
    # Names follow deterministic cluster quality ordering, while IDs remain KMeans labels.
    quality = features.assign(cluster=model.labels_).groupby("cluster")["return_on_equity_pct"].mean().sort_values(ascending=False)
    names = {cluster: ARCHETYPES[index % len(ARCHETYPES)] for index, cluster in enumerate(quality.index)}
    labels = frame[["company_id"]].copy()
    labels["cluster_id"] = model.labels_
    labels["cluster_name"] = labels.cluster_id.map(names)
    labels["distance_from_centroid"] = distances.round(6)
    labels.to_csv(output / "cluster_labels.csv", index=False)

    inertias = []
    ks = range(2, 11)
    for k in ks:
        inertias.append(KMeans(n_clusters=k, random_state=42, n_init=10).fit(scaled).inertia_)
    figure, axis = plt.subplots(figsize=(7, 4)); axis.plot(list(ks), inertias, marker="o"); axis.set(xlabel="k", ylabel="Inertia", title="KMeans elbow plot"); figure.tight_layout(); figure.savefig(reports / "elbow_plot.png", dpi=150); plt.close(figure)

    core = ["return_on_equity_pct", "return_on_capital_employed_pct", "net_profit_margin_pct", "debt_to_equity", "free_cash_flow_cr", "pat_cagr_5yr", "revenue_cagr_5yr", "eps_cagr_5yr", "interest_coverage", "asset_turnover"]
    correlation = frame[core].apply(pd.to_numeric, errors="coerce").corr()
    figure, axis = plt.subplots(figsize=(10, 8)); sns.heatmap(correlation, cmap="coolwarm", center=0, ax=axis); figure.tight_layout(); figure.savefig(reports / "correlation_heatmap.png", dpi=150); plt.close(figure)

    stats = frame.select_dtypes("number").agg([lambda x: x.quantile(.1), lambda x: x.quantile(.25), "median", lambda x: x.quantile(.75), lambda x: x.quantile(.9), "mean", "std"]).T
    stats.index.name = "metric"; stats.columns = ["P10", "P25", "P50", "P75", "P90", "Mean", "Std"]; stats.to_csv(output / "portfolio_stats.csv")
    numeric = frame[core].apply(pd.to_numeric, errors="coerce")
    zscores = numeric.groupby(frame.broad_sector).transform(lambda values: (values - values.mean()) / values.std(ddof=0).replace(0, 1) if hasattr(values.std(ddof=0), "replace") else (values - values.mean()) / (values.std(ddof=0) or 1))
    outliers = frame[["company_id", "company_name", "broad_sector"]].copy()
    for column in core:
        outliers[f"{column}_z"] = zscores[column]
        outliers[f"{column}_outlier"] = zscores[column].abs() > 3
    outliers.to_csv(output / "outlier_report.csv", index=False)
    return labels