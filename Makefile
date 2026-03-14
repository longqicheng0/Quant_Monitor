.PHONY: install scan report dashboard test replay replay-qqq backtest experiments doctor ezsim

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
CONFIG ?= config/settings.example.json
TICKERS ?=
TICKER ?= QQQ
PERIOD ?= 2y
INTERVAL ?= 1d

ifeq ($(firstword $(MAKECMDGOALS)),ezsim)
EZSIM_TICKER := $(word 2,$(MAKECMDGOALS))
EZSIM_INTERVAL := $(word 3,$(MAKECMDGOALS))
EZSIM_PERIOD := $(word 4,$(MAKECMDGOALS))
ifneq ($(EZSIM_TICKER),)
$(eval $(EZSIM_TICKER):;@:)
endif
ifneq ($(EZSIM_INTERVAL),)
$(eval $(EZSIM_INTERVAL):;@:)
endif
ifneq ($(EZSIM_PERIOD),)
$(eval $(EZSIM_PERIOD):;@:)
endif
endif

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

ezsim:
	$(PYTHON) scripts/ezSim.py $(EZSIM_TICKER) $(EZSIM_INTERVAL) $(EZSIM_PERIOD)
