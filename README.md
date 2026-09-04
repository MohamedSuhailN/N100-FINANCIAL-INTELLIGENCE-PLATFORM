# Nifty 100 Data Foundation

A production-ready Sprint 1 data platform for the Nifty 100 financial analytics project. The project ingests Excel files, normalizes core financial fields, validates data quality rules, loads clean records into SQLite, and generates audit and validation reports.

## Architecture

```text
+-------------------+    +---------------------+    +-------------------+
| Excel Files       | -> | ETL Pipeline        | -> | SQLite Database   |
| data/raw/*.xlsx   |    | normalize + validate |    | db/nifty100.db    |
+-------------------+    +---------------------+    +-------------------+
         |                             |
         v                             v
   raw audit + validation reports     SQL analytics layer
```

## Folder Structure

```text
.
├── .env
├── .env.example
├── Makefile
├── requirements.txt
├── README.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── output/
│       ├── load_audit.csv
│       └── validation_failures.csv
├── db/
│   ├── schema.sql
│   └── nifty100.db
├── notebooks/
│   └── exploratory_queries.sql
├── src/
│   ├── config.py
│   ├── main.py
│   ├── etl/
│   │   ├── loader.py
│   │   ├── validator.py
│   │   ├── normaliser.py
│   │   ├── audit.py
│   │   └── utils.py
│   └── models/
│       └── tables.py
└── tests/
    └── etl/
        ├── test_normaliser.py
        ├── test_validator.py
        └── test_loader.py
```

## Installation

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and set values as needed.

- `DATA_DIR`: base data directory
- `RAW_DIR`: raw Excel input directory
- `PROCESSED_DIR`: processed files directory
- `OUTPUT_DIR`: export directory for CSV reports
- `DB_PATH`: SQLite database path
- `SCHEMA_PATH`: schema SQL file path
- `LOG_LEVEL`: application log level

## Make Commands

```bash
make load
make test
make report
make dashboard
make api
make ratios
make clean
```

## ETL Workflow

1. Discover Excel files in `data/raw`.
2. Read every sheet in all workbooks.
3. Normalize ticker, year, company, currency, and percentage fields.
4. Validate using DQ-01 through DQ-16.
5. Stop when critical issues are detected.
6. Load valid records into SQLite.
7. Generate `load_audit.csv` and `validation_failures.csv`.
8. Run foreign key integrity checks.

## Database Schema Summary

The SQLite schema includes the following core tables:

- companies
- profitandloss
- balancesheet
- cashflow
- analysis
- documents
- prosandcons
- sectors
- stock_prices
- financial_ratios

## DQ Rules

- DQ-01: Primary key uniqueness
- DQ-02: Composite PK check `(company_id, year)`
- DQ-03: Foreign key integrity
- DQ-04: Balance sheet equation within 1%
- DQ-05: OPM cross-check
- DQ-06: Positive sales
- DQ-07: Net cash consistency
- DQ-08: Tax rate validation
- DQ-09: Dividend cap
- DQ-10: EPS sign consistency
- DQ-11: Duplicate ticker
- DQ-12: Missing year coverage
- DQ-13: URL validation
- DQ-14: Negative assets
- DQ-15: Invalid sector mapping
- DQ-16: Financial ratio completeness

## Sprint Deliverables

- Excel ingestion and normalization utilities
- DQ validator with audit generation
- SQLite schema and transactional load process
- Unit tests for normalisation, validation, and loader behaviour
- Exploratory SQL analytics queries
- Documentation and execution make targets

## Expected Outputs

After `make load` the project creates:

- `data/nifty100.db`
- `data/output/load_audit.csv`
- `data/output/validation_failures.csv`

## Sprint 4 Dashboard and Valuation

Launch the Streamlit application with:

```bash
streamlit run src/dashboard/app.py
```

The dashboard provides eight screens: Home overview, Company profile, Custom screener, Peer comparison, 10-year trends, Sector analytics, Capital allocation, and Annual reports. Valuation exports can be generated with `src.analytics.valuation.export_valuation()` and are written to `output/valuation_summary.xlsx` and `output/valuation_flags.csv`.

## License

Internal project use.
