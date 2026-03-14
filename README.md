# Aberration Strategy Monitor

This repository is a monitoring and decision-support tool built around one strategy: Aberration.

It does not execute live trades.

## Main Workflows

1. Daily report mode that outputs one decision per ticker:
- TRADE_TOMORROW
- WATCH_TOMORROW
- NO_TRADE
2. Scanner mode for fresh signal detection and logging
3. Streamlit dashboard for charting and review
4. Baseline vs filtered Aberration experiments
5. Historical replay charts for one ticker

## Quick Start

Install:
python3 -m pip install -r requirements.txt

Doctor check:
make doctor

Generate daily report:
make report

Run one scan:
python3 -m src.main --once

Open dashboard:
make dashboard

Run experiments:
make experiments

Run tests:
make test

## Configuration

Default config file: config/settings.example.json

Important sections:
1. strategy
2. monitor
3. filters
4. alerts
5. logging
6. backtest
7. experiment

Important monitor keys:
1. tickers
2. interval
3. period
4. scan_interval_seconds

## Make Targets

1. make install
2. make doctor
3. make scan
4. make report
5. make dashboard
6. make backtest
7. make experiments
8. make replay
9. make test

Examples:
make report TICKERS=QQQ,NVDA,MSFT
make scan TICKERS=AAPL,AMZN INTERVAL=1d PERIOD=1y
make backtest TICKER=QQQ PERIOD=2y

## Outputs

Typical files:
1. data/processed/daily_report_YYYY-MM-DD.csv
2. data/processed/experiment_results.csv
3. data/logs/signals.csv

## Project Structure

config/
scripts/
src/
  cli/
  core/
  strategy/
  datafeed/
  alerts/
  storage/
  dashboard/
  backtest/
  research/
tests/

## Notes

1. Dashboard exit code 130 is normal when stopped with Ctrl+C.
2. The repository is for analysis and monitoring, not execution.
