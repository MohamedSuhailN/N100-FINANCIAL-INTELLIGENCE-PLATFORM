from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR: Final[Path] = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
RAW_DIR: Final[Path] = Path(os.getenv("RAW_DIR", str(DATA_DIR / "raw")))
PROCESSED_DIR: Final[Path] = Path(os.getenv("PROCESSED_DIR", str(DATA_DIR / "processed")))
OUTPUT_DIR: Final[Path] = Path(os.getenv("OUTPUT_DIR", str(DATA_DIR / "output")))
DB_PATH: Final[Path] = Path(os.getenv("DB_PATH", str(DATA_DIR / "nifty100.db")))
SCHEMA_PATH: Final[Path] = Path(os.getenv("SCHEMA_PATH", str(BASE_DIR / "db" / "schema.sql")))
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")
