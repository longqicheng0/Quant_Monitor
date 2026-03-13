# Multi-Strategy Monitor

Python monitoring and alerting project for breakout strategies.

This repository is intentionally focused on monitoring, scanning, visualization, and signal logging. It does not place live orders.

## Overview

Supported strategies:

1. `aberration` (Bollinger breakout/mean-reversion style)
2. `dual_thrust` (daily open-based breakout)

Supported workflows:

1. Scheduled terminal scanner
2. Streamlit dashboard
3. Historical replay script with chart + summary + trades table
4. Strategy backtesting (both strategies)
5. Signal persistence to CSV or SQLite

## Strategy Definitions

### Aberration

Defaults:

1. Bollinger length: `35`
2. Standard deviation multiplier: `2.0`
3. Source: `Close`

Bands:

1. `middle_band = SMA(close, 35)`
2. `upper_band = middle_band + 2 * rolling_std(close, 35)`
3. `lower_band = middle_band - 2 * rolling_std(close, 35)`

Signals:

1. `LONG_ENTRY`: close crosses above `upper_band`
2. `SHORT_ENTRY`: close crosses below `lower_band`
3. `LONG_EXIT`: close crosses below `middle_band`
4. `SHORT_EXIT`: close crosses above `middle_band`

### Dual Thrust

Defaults:

1. Lookback `N = 20`
2. Multiplier `K = 1.5`

Previous completed-day values:

1. `HH = highest high over previous N completed days`
2. `LL = lowest low over previous N completed days`
3. `HC = highest close over previous N completed days`
4. `LC = lowest close over previous N completed days`

Range and triggers:

1. `range_value = max(HH - LC, HC - LL)`
2. `upper_trigger = today_open + K * range_value`
3. `lower_trigger = today_open - K * range_value`

Signals and flips:

1. `LONG_ENTRY` on cross above `upper_trigger`
2. `SHORT_ENTRY` on cross below `lower_trigger`
3. If currently short and long signal appears: `SHORT_EXIT_ON_FLIP_TO_LONG`
4. If currently long and short signal appears: `LONG_EXIT_ON_FLIP_TO_SHORT`

Dual Thrust assumptions in current implementation:

1. Daily logic first (`1d` recommended)
2. Trigger levels are fixed for the day once open is known
3. Range uses previous completed bars only (no lookahead)

## Crossover Rules

Shared strict crossover helpers:

1. Cross above: previous price `<=` previous line and current price `>` current line
2. Cross below: previous price `>=` previous line and current price `<` current line

Implemented in `src/strategy/signals.py`.

## Repository Structure

```text
repo_root/
	README.md
	Makefile
	requirements.txt
	.gitignore
	LICENSE
	config/
		settings.py
		settings.example.json
	data/
		raw/
		processed/
		logs/
	scripts/
		replay_signals.py
	src/
		__init__.py
		main.py
		scanner.py
		strategy/
			__init__.py
			indicators.py
			signals.py
			aberration.py
			dual_thrust.py
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
			logger.py
			time_utils.py
	tests/
		test_indicators.py
		test_signals.py
		test_dual_thrust.py
		test_backtester.py
```

## Installation

1. Create and activate virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Makefile equivalent:

```bash
make install
```

## Configuration

Default config file: `config/settings.example.json`

Top-level sections:

1. `strategy`
2. `monitor`
3. `alerts`
4. `logging`
5. `backtest`

Key strategy fields:

1. `strategy_name`: `aberration` or `dual_thrust`
2. `bollinger_length`
3. `bollinger_multiplier`
4. `dual_thrust_lookback`
5. `dual_thrust_multiplier`

Monitor fields:

1. `tickers`: list of symbols
2. `timeframe`: default `1d`
3. `history_period`: yfinance period (`6mo`, `1y`, `2y`, etc.)
4. `scan_interval_seconds`

Alert fields:

1. `enabled`
2. `console`
3. `webhook_url` (placeholder path currently)

Logging fields:

1. `enabled`
2. `csv_path`
3. `sqlite_path`
4. `use_sqlite`

Backtest fields:

1. `enabled`
2. `default_ticker`
3. `start_date`
4. `end_date`

## Running the Scanner (CLI)

Run with config:

```bash
python3 -m src.main --config config/settings.example.json
```

Override strategy at runtime:

```bash
python3 -m src.main --config config/settings.example.json --strategy aberration
python3 -m src.main --config config/settings.example.json --strategy dual_thrust
```

Makefile:

```bash
make scan
make scan STRATEGY=aberration
make scan STRATEGY=dual_thrust
```

Scanner behavior:

1. Downloads recent OHLCV for each configured ticker
2. Applies selected strategy
3. Classifies latest signal with state tracking (`flat`, `long`, `short`)
4. Prints one status line per ticker
5. Emits alert for fresh signal
6. Logs signal event (CSV or SQLite)
7. Repeats on schedule until `Ctrl+C`

`Exit code 130` after stopping is normal when interrupted by `Ctrl+C`.

## Dashboard

Run dashboard:

```bash
python3 -m streamlit run src/dashboard/app.py
```

Makefile:

```bash
make dashboard
```

Dashboard supports:

1. Strategy selector (`aberration`, `dual_thrust`)
2. Ticker selector
3. Price chart with strategy overlays
4. Signal markers
5. Latest signal status box
6. Recent signal events table (strategy-aware)
7. Optional backtest summary and curve chart

## Replay Script

Purpose: one-shot historical replay for a ticker with chart output.

Command:

```bash
python3 scripts/replay_signals.py --ticker SPY --interval 1d --period 2y
```

Useful flags:

1. `--ticker`
2. `--interval`
3. `--period`
4. `--max-events`
5. `--save-csv`
6. `--save-plot`
7. `--show-plot`

Makefile:

```bash
make replay
make replay TICKER=QQQ PERIOD=2y
```

Default plot output path:

1. `data/processed/<ticker>_replay.png`

## Backtesting

Backtesting module: `src/backtest/backtester.py`

Implemented:

1. `run_aberration_backtest(...)`
2. `run_dual_thrust_backtest(...)`
3. `run_backtest(strategy_name=...)` dispatcher

Metrics returned:

1. `total_return`
2. `annualized_return`
3. `buy_and_hold_return`
4. `max_drawdown`
5. `sharpe_ratio`
6. `num_trades`
7. `win_rate`

Both strategies assume one position at a time.

## Logging and Alerting

Signal logging module: `src/storage/signal_logger.py`

Logged fields include:

1. `event_time`
2. `strategy_name`
3. `ticker`
4. `timeframe`
5. `signal_type`
6. `close`
7. `bar_time`
8. Aberration levels: `middle_band`, `upper_band`, `lower_band`
9. Dual Thrust levels: `open_price`, `range_value`, `upper_trigger`, `lower_trigger`

Alert module: `src/alerts/alert_manager.py`

Console format includes strategy tag, for example:

1. `[ABERRATION] ...`
2. `[DUAL_THRUST] ...`

Webhook behavior is currently a placeholder.

## Testing

Run tests:

```bash
python3 -m pytest -q
```

Makefile:

```bash
make test
```

Current test coverage includes:

1. Indicators
2. Crossovers and signal classification
3. Dual Thrust range/trigger/no-lookahead behavior
4. Backtest execution for both strategies

## Common Commands

```bash
make install
make test
make replay TICKER=SPY PERIOD=2y
make scan STRATEGY=aberration
make scan STRATEGY=dual_thrust
make dashboard
```

## Troubleshooting

1. `make: streamlit: No such file or directory`
Fix: use `python3 -m streamlit run src/dashboard/app.py` or reinstall deps.

2. `ModuleNotFoundError` from scripts
Fix: run commands from repo root.

3. `NotOpenSSLWarning` from urllib3 on macOS
This is a warning in this setup and does not block scanner/dashboard/replay.

4. No signals appearing
Check ticker, interval, period, and whether enough history exists for lookback/warmup.

## Development Philosophy

1. Monitoring first, no execution layer
2. Modular architecture and strategy plug-in style
3. Beginner-readable code and clear naming
4. Minimal, safe extensions over rewrites

## Roadmap

1. Live broker/websocket data adapters
2. Real webhook/Discord/email alert integrations
3. Multi-timeframe confirmation
4. Trend filters (ADX, 200MA, etc.)
5. Paper trading and eventual execution layer