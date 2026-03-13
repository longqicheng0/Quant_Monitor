"""Historical market data client powered by yfinance."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf


@dataclass
class YFinanceClient:
    """Simple data client for OHLCV fetches.

    This class is intentionally lightweight so it can later be replaced or
    extended with websocket or broker-specific real-time feeds.
    """

    auto_adjust: bool = False

    def get_ticker_name(self, ticker: str) -> str:
        """Return a human-friendly ticker name when available.

        Falls back to the ticker symbol if metadata is unavailable.
        """
        try:
            info = yf.Ticker(ticker).info
            return info.get("longName") or info.get("shortName") or ticker
        except Exception:
            return ticker

    def get_ohlcv(
        self,
        ticker: str,
        interval: str = "1d",
        period: str = "1y",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Download OHLCV data for a symbol.

        Args:
            ticker: Instrument symbol, e.g. SPY.
            interval: yfinance interval string (starter: daily).
            period: Lookback period, ignored when explicit start/end is used.
            start: Optional start date.
            end: Optional end date.

        Returns:
            DataFrame indexed by datetime with OHLCV columns.
        """
        params: dict[str, object] = {
            "tickers": ticker,
            "interval": interval,
            "auto_adjust": self.auto_adjust,
            "progress": False,
        }

        if start or end:
            params["start"] = start
            params["end"] = end
        else:
            params["period"] = period

        df = yf.download(**params)

        if df.empty:
            return df

        # yfinance can return multi-index columns for some calls. Flatten for consistency.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df
