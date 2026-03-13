.PHONY: install scan dashboard test replay replay-qqq

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
CONFIG ?= config/settings.example.json
STRATEGY ?=
TICKER ?= SPY
PERIOD ?= 2y

install:
	$(PIP) install -r requirements.txt

scan:
	$(PYTHON) -m src.main --config $(CONFIG) $(if $(STRATEGY),--strategy $(STRATEGY),)

dashboard:
	streamlit run src/dashboard/app.py

test:
	$(PYTHON) -m pytest -q

replay:
	$(PYTHON) scripts/replay_signals.py --ticker $(TICKER) --period $(PERIOD)

replay-qqq:
	$(PYTHON) scripts/replay_signals.py --ticker QQQ --period 2y
