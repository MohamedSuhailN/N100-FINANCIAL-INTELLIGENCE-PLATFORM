from pathlib import Path

import pandas as pd

from src.etl.loader import clean_frame, load_excel_file, load_raw_data, run_pipeline


def test_load_excel_file_reads_csv(tmp_path):
    file = tmp_path / "sample.csv"
    pd.DataFrame({"ticker": [" tcs ", "infosys"], "year": ["2024", "FY2023"]}).to_csv(file, index=False)
    df = load_excel_file(file)
    assert list(df.columns) == ["ticker", "year"]
    assert len(df) == 2


def test_load_raw_data_handles_excel_and_csv(tmp_path):
    csv_file = tmp_path / "sample.csv"
    pd.DataFrame({"ticker": ["tcs"]}).to_csv(csv_file, index=False)
    data = load_raw_data(tmp_path)
    assert "sample" in data


def test_clean_frame_normalizes_fields():
    df = pd.DataFrame({"ticker": [" tcs ", "infosys"], "year": ["FY2023", "2022"]})
    cleaned = clean_frame(df)
    assert cleaned["ticker"].tolist() == ["TCS", "INFOSYS"]
    assert cleaned["year"].tolist() == [2023, 2022]


def test_run_pipeline_generates_summary(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    csv_file = raw_dir / "sample.csv"
    pd.DataFrame({"ticker": ["tcs"], "year": ["FY2023"]}).to_csv(csv_file, index=False)
    result = run_pipeline(raw_dir, tmp_path / "output")
    assert "frames_loaded" in result
    assert result["frames_loaded"] >= 1
