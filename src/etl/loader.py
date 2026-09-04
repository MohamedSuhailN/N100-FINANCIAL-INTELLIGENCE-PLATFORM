from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.etl.normaliser import normalize_ticker, normalize_year
from src.etl.validator import is_critical_failure_present, log_failures, validate_data

logger = logging.getLogger(__name__)


def load_excel_file(file_path: str | Path) -> pd.DataFrame:
    """Read an Excel or CSV file and return the contents as a DataFrame."""
    path = Path(file_path)
    logger.info("Loading file: %s", path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, header=1)
    return pd.read_csv(path)


def load_raw_data(raw_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load all supported files from the raw input directory."""
    raw_path = Path(raw_dir)
    frames: dict[str, pd.DataFrame] = {}

    if not raw_path.exists():
        logger.warning("Raw directory %s does not exist.", raw_path)
        return frames

    for file in sorted(raw_path.iterdir()):
        if not file.is_file() or file.suffix.lower() not in {".xlsx", ".xls", ".csv"}:
            continue

        try:
            if file.suffix.lower() in {".xlsx", ".xls"}:
                excel = pd.ExcelFile(file)
                for sheet_name in excel.sheet_names:
                    frame = excel.parse(sheet_name, header=1)
                    key = f"{file.stem.lower()}_{sheet_name.lower()}"
                    frames[key] = frame
            else:
                frames[file.stem.lower()] = pd.read_csv(file)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.exception("Could not read %s: %s", file, exc)

    return frames


def clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize common financial DataFrame fields before validation."""
    if frame is None or frame.empty:
        return frame

    cleaned = frame.copy()
    if "ticker" in cleaned.columns:
        cleaned["ticker"] = cleaned["ticker"].map(lambda value: normalize_ticker(value))
    if "year" in cleaned.columns:
        cleaned["year"] = cleaned["year"].map(lambda value: normalize_year(value))
    if "company_name" in cleaned.columns:
        cleaned["company_name"] = cleaned["company_name"].fillna("").astype(str).str.strip()
    if "company_id" in cleaned.columns:
        cleaned["company_id"] = cleaned["company_id"].astype(str).str.strip().str.upper()
    return cleaned


def run_pipeline(raw_dir: str | Path = "data/raw", output_dir: str | Path = "data/output") -> dict[str, Any]:
    """Execute the ETL load cycle and return a summary dictionary."""
    raw_path = Path(raw_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    frames = load_raw_data(raw_path)
    audit_rows: list[dict[str, Any]] = []
    all_failures: list[dict[str, Any]] = []

    for name, frame in frames.items():
        cleaned = clean_frame(frame)
        failures = validate_data(cleaned, name)
        all_failures.extend(failures)
        audit_rows.append(
            {
                "table_name": name,
                "rows_processed": len(cleaned),
                "status": "SUCCESS" if not is_critical_failure_present(failures) else "FAILED",
            }
        )

    log_failures(all_failures, str(output_path / "validation_failures.csv"))
    return {
        "frames_loaded": len(frames),
        "audit_rows": audit_rows,
        "failure_count": len(all_failures),
        "critical_failures": sum(1 for item in all_failures if item.get("severity") == "CRITICAL"),
    }


if __name__ == "__main__":
    run_pipeline()