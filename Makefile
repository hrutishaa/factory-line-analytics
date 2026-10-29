PY=.venv/bin/python
all: setup run test
setup:
	test -d .venv || python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
data/raw/ai4i2020.csv:
	mkdir -p data/raw && curl -sL -o /tmp/ai4i.zip "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip" && unzip -o /tmp/ai4i.zip -d data/raw
run: data/raw/ai4i2020.csv
	cd src && ../$(PY) -m fla.run_all
test:
	$(PY) -m pytest -q
serve:
	cd src && ../$(PY) -m uvicorn fla.api:app --port 8000
.PHONY: all setup run test serve
screenshot:
	google-chrome --headless=new --no-sandbox --hide-scrollbars --window-size=1440,1520 --virtual-time-budget=15000 --screenshot=reports/figures/dashboard.png file://$(CURDIR)/reports/dashboard.html
handoff:
	cd src && ../$(PY) -m fla.alerts && cat ../reports/shift_handoff.md
.PHONY: screenshot handoff
