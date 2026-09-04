import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.analytics.clustering import run_clustering
from src.nlp.parser import parse_metric_text

client = TestClient(app)


@pytest.mark.parametrize("path", [
    "/api/v1/health", "/api/v1/companies", "/api/v1/sectors",
    "/api/v1/companies/N100001", "/api/v1/companies/N100001/pl",
    "/api/v1/companies/N100001/bs", "/api/v1/companies/N100001/cashflow",
    "/api/v1/companies/N100001/ratios", "/api/v1/screener",
    "/api/v1/market-cap/N100001", "/api/v1/portfolio/stats",
])
def test_endpoint_returns_success(path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("value,expected", [
    ("10 Years: 21.0%", (10, 21.0)), ("5 Year 12.5%", (5, 12.5)),
    ("3 Years: 7%", (3, 7.0)), ("1 Year 1.1%", (1, 1.1)),
    ("20 Years: 100.0%", (20, 100.0)), ("2 years: 0.5%", (2, .5)),
    ("8 Years 18%", (8, 18.0)), ("4 Years: 4.4%", (4, 4.4)),
    ("6 Year 6%", (6, 6.0)), ("12 YEARS: 30%", (12, 30.0)),
])
def test_parser_examples(value, expected):
    assert parse_metric_text(value) == expected


def test_invalid_company_is_404():
    assert client.get("/api/v1/companies/INVALID").status_code == 404


def test_invalid_sector_is_404():
    assert client.get("/api/v1/sectors/INVALID/companies").status_code == 404


def test_invalid_screener_parameter_is_400():
    assert client.get("/api/v1/screener?max_de=-1").status_code == 400


def test_cluster_file_has_full_universe():
    labels = run_clustering()
    assert len(labels) == 92 and labels.cluster_id.nunique() == 5


@pytest.mark.parametrize("path", [
    "/api/v1/companies/INVALID/pl", "/api/v1/companies/INVALID/bs",
    "/api/v1/companies/INVALID/cashflow", "/api/v1/companies/INVALID/ratios",
    "/api/v1/companies/INVALID/documents", "/api/v1/companies/INVALID/peers/compare",
])
def test_invalid_company_subresources_are_404(path):
    assert client.get(path).status_code == 404