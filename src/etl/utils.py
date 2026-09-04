from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


def ensure_directories(*paths: str | Path) -> None:
    """Create directories if they do not exist."""
    for raw_path in paths:
        Path(raw_path).mkdir(parents=True, exist_ok=True)
        logger.info('Ensured directory exists: %s', raw_path)


def iter_excel_files(directory: str | Path) -> list[Path]:
    """Return Excel files contained in a directory."""
    base = Path(directory)
    if not base.exists():
        return []
    return sorted(
        path for path in base.iterdir()
        if path.is_file() and path.suffix.lower() in {'.xlsx', '.xls', '.csv'}
    )


def unique_values(sequence: Iterable[Any]) -> list[Any]:
    """Return unique values preserving order."""
    seen: set[Any] = set()
    result: list[Any] = []
    for item in sequence:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


from typing import Any
