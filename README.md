# Aberration Strategy Monitor

Python monitoring and alerting project for the Aberration strategy.

This repository is intentionally focused on **monitoring, scanning, and signal review**. It does **not** place live orders.

## What Is the Aberration Strategy?

Aberration is a Bollinger-Band breakout and mean-reversion style workflow:

- Bollinger parameters:
  - length: `35`
  - std multiplier: `2`
  - source: `Close`
- Bands:
  - middle band = 35-period SMA of close
  - upper band = middle + 2 * rolling std
  - lower band = middle - 2 * rolling std
- Signals:
  - long entry: close crosses above upper band
  - short entry: close crosses below lower band
  - long exit: close crosses below middle band
  - short exit: close crosses above middle band

Cross logic is strict and uses the prior and current candle:

- cross above = previous close <= line and current close > line
- cross below = previous close >= line and current close < line

## What This Repo Does

- Fetches historical market data (via `yfinance`)
- Computes Bollinger bands and crossover events
- Scans multiple tickers for fresh signals
- Logs signals to CSV and/or SQLite
- Sends console alerts (with placeholders for webhook/email expansion)
- Provides a Streamlit dashboard for charting and recent events
- Includes a simple backtest module to validate behavior

## Project Structure

```text
repo_root/
  README.md
	Makefile
  requirements.txt
  .gitignore
  config/
	  settings.py
	  settings.example.json
  data/
	  raw/
	  processed/
	  logs/
  src/
	  __init__.py
	  main.py
	  scanner.py
	  strategy/
		  __init__.py
		  aberration.py
		  indicators.py
		  signals.py
	  datafeed/
		  __init__.py
		  yfinance_client.py
	  alerts/
		  __init__.py
		  alert_manager.py
	  storage/
		  __init__.py
		  signal_logger.py
	  dashboard/
		  __init__.py
		  app.py
	  backtest/
		  __init__.py
		  backtester.py
	  utils/
		  __init__.py
		  config_loader.py
		  time_utils.py
		  logger.py
  tests/
	  test_indicators.py
	  test_signals.py
	  test_backtester.py
  scripts/
	  replay_signals.py
```

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

Or with Makefile:

```bash
make install
```

3. Optional: customize `config/settings.example.json` and use it at runtime.

## Run the Terminal Scanner

```bash
python -m src.main --config config/settings.example.json
```

The scanner runs on a schedule, prints per-ticker status, emits fresh signal alerts, and writes logs if enabled.

Makefile shortcut:

```bash
make scan
```

## Run the Streamlit Dashboard

```bash
streamlit run src/dashboard/app.py
```

Makefile shortcut:

```bash
make dashboard
```

Dashboard features:

- ticker selector
- close + Bollinger chart
- long/short entry and exit markers
- latest signal status box
- recent signal table
- optional backtest summary for selected ticker

## Run Backtests

Backtest summary is available from the dashboard and through module calls in `src/backtest/backtester.py`.

Default example is daily data with ticker `SPY`.

For an offline demo that replays historical entry/exit events:

```bash
python3 scripts/replay_signals.py --ticker SPY --period 2y
```

Makefile shortcut:

```bash
make replay
```

## Testing

```bash
pytest -q
```

Makefile shortcut:

```bash
make test
```

## Development Philosophy

- Monitoring first, execution later
- Clear and modular architecture
- Beginner-friendly naming and comments
- Easy to extend into broker/websocket integrations in future

## Roadmap

- Live broker/websocket data feeds
- Discord/webhook alert integrations
- Multi-timeframe confirmation
- Trend filters (e.g., ADX, 200MA)
- Eventual paper trading and execution layer