from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.config import BASE_DIR, DB_PATH, OUTPUT_DIR, RAW_DIR
from src.analytics.populate_ratios import populate_ratios
from src.etl.audit import write_audit_report
from src.etl.loader import run_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
console = Console()


def _print_summary(results: dict) -> None:
    """Render a Rich summary table for ETL results."""
    table = Table(title='ETL Load Summary')
    table.add_column('Table')
    table.add_column('Rows')
    table.add_column('Status')
    for row in results.get('audit_rows', []):
        table.add_row(str(row.get('table_name', 'n/a')), str(row.get('rows_processed', 0)), str(row.get('status', 'UNKNOWN')))
    console.print(table)


def load_command() -> None:
    """Run the full load process."""
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    results = run_pipeline(RAW_DIR, output_dir)
    if results.get('audit_rows'):
        write_audit_report(results['audit_rows'], output_dir / 'load_audit.csv')
    _print_summary(results)
    console.print(f'[green]Database Created:[/] {DB_PATH}')


def report_command() -> None:
    """Print output report locations."""
    console.print(f'[cyan]Load audit:[/] {OUTPUT_DIR / "load_audit.csv"}')
    console.print(f'[cyan]Validation failures:[/] {OUTPUT_DIR / "validation_failures.csv"}')


def dashboard_command() -> None:
    """Placeholder dashboard command."""
    console.print('[yellow]Dashboard generation is not yet implemented for Sprint 1.[/]')


def api_command() -> None:
    """Placeholder API command."""
    console.print('[yellow]API service is not yet implemented for Sprint 1.[/]')


def ratios_command() -> None:
    """Populate the financial ratio mart and export its audit files."""
    row_count = populate_ratios(DB_PATH, BASE_DIR / 'output')
    console.print(f'[green]Financial ratio rows populated:[/] {row_count}')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Nifty 100 Data Foundation')
    parser.add_argument('command', choices=['load', 'report', 'dashboard', 'api', 'ratios'])
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == 'load':
        load_command()
    elif args.command == 'report':
        report_command()
    elif args.command == 'dashboard':
        dashboard_command()
    elif args.command == 'api':
        api_command()
    elif args.command == 'ratios':
        ratios_command()


if __name__ == '__main__':
    main()
