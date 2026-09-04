-- Query 1: Total Companies Count (Exit Criterion: 92)
SELECT COUNT(*) AS total_companies FROM companies;

-- Query 2: Profit & Loss Record Count
SELECT COUNT(*) AS pl_records FROM profitandloss;

-- Query 3: Balance Sheet Record Count
SELECT COUNT(*) AS bs_records FROM balancesheet;

-- Query 4: Cash Flow Record Count
SELECT COUNT(*) AS cf_records FROM cashflow;

-- Query 5: Stock Prices Record Count
SELECT COUNT(*) AS price_records FROM stock_prices;

-- Query 6: Check Year Coverage per Company
SELECT company_id, COUNT(year) AS active_years 
FROM profitandloss 
GROUP BY company_id 
ORDER BY active_years ASC;

-- Query 7: Companies with < 5 Years Data
SELECT company_id, COUNT(year) AS years_count 
FROM profitandloss 
GROUP BY company_id 
HAVING years_count < 5;

-- Query 8: Check Foreign Key Integrity
PRAGMA foreign_key_check;