PYTHON ?= python
APP := src.main

.PHONY: load test report dashboard api ratios clean

load:
	$(PYTHON) -m src.main load

test:
	$(PYTHON) -m pytest tests --html=reports/pytest_report.html -q

report:
	$(PYTHON) -c "from src.reports.tearsheet import generate_tearsheets; from src.reports.sector_report import generate_sector_reports, generate_portfolio_summary; generate_tearsheets(); generate_sector_reports(); generate_portfolio_summary()"

dashboard:
	$(PYTHON) -m streamlit run src/dashboard/app.py --server.port 8501

api:
	$(PYTHON) -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

ratios:
	$(PYTHON) -m src.main ratios

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; [p.unlink() for p in Path('.').rglob('*.pyc')]; shutil.rmtree('.pytest_cache', ignore_errors=True)"
