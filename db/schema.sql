PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sectors (
    sector_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_name TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    sector_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sector_id) REFERENCES sectors(sector_id)
);

CREATE TABLE IF NOT EXISTS documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    url TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS prosandcons (
    prosandcons_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    point TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS analysis (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    year INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS profitandloss (
    profitandloss_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    sales REAL,
    expenses REAL,
    opm REAL,
    net_profit REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS balancesheet (
    balancesheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    total_assets REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS cashflow (
    cashflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    operating_cash_flow REAL,
    investing_cash_flow REAL,
    financing_cash_flow REAL,
    net_cash_flow REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS stock_prices (
    stock_price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    close_price REAL,
    volume INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS financial_ratios (
    financial_ratio_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    pe_ratio REAL,
    debt_to_equity REAL,
    roe REAL,
    roce REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE INDEX IF NOT EXISTS idx_companies_sector_id ON companies(sector_id);
CREATE INDEX IF NOT EXISTS idx_profitandloss_company_year ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_balancesheet_company_year ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cashflow_company_year ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_stock_prices_company_id ON stock_prices(company_id);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_company_year ON financial_ratios(company_id, year);

CREATE TABLE IF NOT EXISTS peer_percentiles (
    peer_percentile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    peer_group_name TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    percentile_rank REAL,
    year INTEGER,
    UNIQUE(company_id, peer_group_name, metric, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);
CREATE INDEX IF NOT EXISTS idx_peer_percentiles_group ON peer_percentiles(peer_group_name, metric);