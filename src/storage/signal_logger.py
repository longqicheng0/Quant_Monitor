"""Signal logging to CSV or SQLite."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import asdict
from pathlib import Path

from src.scanner import SignalEvent


class SignalLogger:
    """Persist signal events to local storage."""

    def __init__(
        self,
        enabled: bool = True,
        csv_path: str = "data/logs/signals.csv",
        sqlite_path: str = "data/logs/signals.db",
        use_sqlite: bool = False,
    ):
        self.enabled = enabled
        self.csv_path = Path(csv_path)
        self.sqlite_path = Path(sqlite_path)
        self.use_sqlite = use_sqlite

        if self.enabled:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            if self.use_sqlite:
                self._init_sqlite()

    def _init_sqlite(self) -> None:
        """Create SQLite table if not present."""
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    event_time TEXT,
                    strategy_name TEXT,
                    ticker TEXT,
                    timeframe TEXT,
                    signal_type TEXT,
                    close REAL,
                    middle_band REAL,
                    upper_band REAL,
                    lower_band REAL,
                    open_price REAL,
                    range_value REAL,
                    upper_trigger REAL,
                    lower_trigger REAL,
                    bar_time TEXT
                )
                """
            )
            self._ensure_column(conn, "signals", "strategy_name", "TEXT")
            self._ensure_column(conn, "signals", "open_price", "REAL")
            self._ensure_column(conn, "signals", "range_value", "REAL")
            self._ensure_column(conn, "signals", "upper_trigger", "REAL")
            self._ensure_column(conn, "signals", "lower_trigger", "REAL")
            conn.commit()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, sql_type: str) -> None:
        existing = conn.execute(f"PRAGMA table_info({table})").fetchall()
        names = {row[1] for row in existing}
        if column not in names:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")

    def log(self, event: SignalEvent) -> None:
        """Store one signal event."""
        if not self.enabled:
            return

        if self.use_sqlite:
            self._log_sqlite(event)
        else:
            self._log_csv(event)

    def _log_csv(self, event: SignalEvent) -> None:
        row = asdict(event)
        file_exists = self.csv_path.exists()
        with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def _log_sqlite(self, event: SignalEvent) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO signals
                (
                    event_time,
                    strategy_name,
                    ticker,
                    timeframe,
                    signal_type,
                    close,
                    middle_band,
                    upper_band,
                    lower_band,
                    open_price,
                    range_value,
                    upper_trigger,
                    lower_trigger,
                    bar_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_time,
                    event.strategy_name,
                    event.ticker,
                    event.timeframe,
                    event.signal_type,
                    event.close,
                    event.middle_band,
                    event.upper_band,
                    event.lower_band,
                    event.open_price,
                    event.range_value,
                    event.upper_trigger,
                    event.lower_trigger,
                    event.bar_time,
                ),
            )
            conn.commit()
