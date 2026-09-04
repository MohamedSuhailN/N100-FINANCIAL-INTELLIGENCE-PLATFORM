import pytest
from src.etl.normaliser import normalize_ticker, normalize_year

def test_normalize_ticker():
    assert normalize_ticker("  tcs  ") == "TCS"
    assert normalize_ticker("infy") == "INFY"
    assert normalize_ticker("RELIANCE") == "RELIANCE"
    assert normalize_ticker(None) == ""

def test_normalize_year():
    assert normalize_year("2023") == 2023
    assert normalize_year(2023) == 2023
    assert normalize_year("FY2022") == 2022
    assert normalize_year(2021.0) == 2021
    assert normalize_year("Mar-2020") == 2020
    assert normalize_year(None) is None