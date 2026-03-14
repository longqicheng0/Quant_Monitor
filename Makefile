.PHONY: install scan report dashboard test replay replay-qqq backtest experiments doctor

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
CONFIG ?= config/settings.example.json
TICKERS ?=
TICKER ?= QQQ
PERIOD ?= 2y
INTERVAL ?= 1d

install:
	$(PIP) install -r requirements.txt

scan:
	$(PYTHON) -m src.main --config $(CONFIG) $(if $(TICKERS),--tickers $(TICKERS),) $(if $(INTERVAL),--interval $(INTERVAL),) $(if $(PERIOD),--period $(PERIOD),)

report:
	$(PYTHON) -m src.main --config $(CONFIG) --report $(if $(TICKERS),--tickers $(TICKERS),) $(if $(INTERVAL),--interval $(INTERVAL),) $(if $(PERIOD),--period $(PERIOD),)

dashboard:
	$(PYTHON) -m streamlit run src/dashboard/app.py

test:
	$(PYTHON) -m pytest -q

replay:
	$(PYTHON) scripts/replay_signals.py --ticker $(TICKER) --period $(PERIOD)

replay-qqq:
	$(PYTHON) scripts/replay_signals.py --ticker QQQ --period 2y

backtest:
	$(PYTHON) -m src.backtest.experiment_runner --config $(CONFIG) --strategy-family aberration --tickers $(TICKER) --interval $(INTERVAL) --period $(PERIOD) --output-prefix single_backtest

experiments:
	$(PYTHON) -m src.backtest.experiment_runner --config $(CONFIG) --strategy-family aberration

doctor:
	$(PYTHON) -m src.cli.commands --doctor --config $(CONFIG)
