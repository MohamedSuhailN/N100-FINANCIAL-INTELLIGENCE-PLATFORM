from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def write_audit_report(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    """Persist the ETL load audit rows to CSV."""
    report = pd.DataFrame(rows)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output, index=False)
    logger.info('Audit report written to %s', output)
