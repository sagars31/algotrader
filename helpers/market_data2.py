"""
kite_market_data.py
====================
Reusable wrapper functions around KiteConnect's market-data endpoints:
    - Historical candle data (kite.historical_data)
    - Full quotes        (kite.quote)
    - OHLC snapshots      (kite.ohlc)
    - Last traded price   (kite.ltp)

Instruments for quote/ohlc/ltp must be passed in "EXCHANGE:TRADINGSYMBOL"
format (e.g. "NSE:INFY") or as numeric instrument_tokens.

Usage
-----
    from kite_market_data import KiteMarketData

    md = KiteMarketData(kite)   # pass an already-authenticated KiteConnect instance

    # Historical OHLC candles
    candles = md.get_historical_data(
        instrument_token=408065,   # INFY
        from_date="2024-01-01",
        to_date="2024-01-31",
        interval="day",
    )

    # LTP for multiple instruments
    ltp = md.get_ltp(["NSE:INFY", "NSE:TCS"])

    # OHLC snapshot
    ohlc = md.get_ohlc(["NSE:INFY"])

    # Full quote (depth, oi, volume, etc.)
    quote = md.get_quote(["NSE:INFY"])
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union

from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kite_market_data")

Instrument = Union[str, int]          # "NSE:INFY" or instrument_token
DateLike = Union[str, date, datetime]  # "2024-01-01" or a date/datetime object

VALID_INTERVALS = {
    "minute", "3minute", "5minute", "10minute", "15minute",
    "30minute", "60minute", "day",
}


class KiteMarketData:
    """
    Wraps KiteConnect market-data calls with input validation, batching,
    and consistent error handling so callers get [] / {} / None on failure
    instead of unhandled exceptions.
    """

    def __init__(self, kite: KiteConnect):
        """
        Parameters
        ----------
        kite : An already-authenticated KiteConnect instance
               (i.e. set_access_token() has already been called on it).
        """
        self.kite = kite

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_date(d: DateLike) -> str:
        """Convert a date/datetime/str into the 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD' string Kite expects."""
        if isinstance(d, (datetime, date)):
            return d.strftime("%Y-%m-%d %H:%M:%S") if isinstance(d, datetime) else d.strftime("%Y-%m-%d")
        return str(d)

    @staticmethod
    def _chunk(items: List[Any], size: int) -> List[List[Any]]:
        """Split a list into chunks (quote/ohlc/ltp allow max ~500 instruments per call)."""
        return [items[i:i + size] for i in range(0, len(items), size)]

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------
    def get_historical_data(
        self,
        instrument_token: int,
        from_date: DateLike,
        to_date: DateLike,
        interval: str = "day",
        continuous: bool = False,
        oi: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical OHLC(V) candles for a single instrument.

        Parameters
        ----------
        instrument_token  Numeric instrument token (from instruments() dump,
                           not the tradingsymbol).
        from_date          Start date/datetime, e.g. "2024-01-01" or "2024-01-01 09:15:00"
        to_date             End date/datetime.
        interval            One of: minute, 3minute, 5minute, 10minute, 15minute,
                            30minute, 60minute, day.
        continuous          True for continuous futures/options contract data.
        oi                  True to include open interest (F&O only).

        Returns
        -------
        List of dicts: [{"date": ..., "open": ..., "high": ..., "low": ...,
                          "close": ..., "volume": ...}, ...]
        Empty list on failure.
        """
        if interval not in VALID_INTERVALS:
            raise ValueError(f"interval must be one of {sorted(VALID_INTERVALS)}, got {interval!r}")

        try:
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=self._normalize_date(from_date),
                to_date=self._normalize_date(to_date),
                interval=interval,
                continuous=continuous,
                oi=oi,
            )
            logger.info(
                f"Fetched {len(data)} '{interval}' candles for token {instrument_token} "
                f"({from_date} -> {to_date})"
            )
            return data
        except KiteException as e:
            logger.error(f"Failed to fetch historical data for {instrument_token}: {e}")
            return []

    # ------------------------------------------------------------------
    # LTP
    # ------------------------------------------------------------------
    def get_ltp(self, instruments: Union[Instrument, List[Instrument]]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch last traded price for one or more instruments.

        Parameters
        ----------
        instruments  Single instrument or list, e.g. "NSE:INFY" or
                     ["NSE:INFY", "NSE:TCS", 408065].

        Returns
        -------
        Dict keyed by instrument string, e.g.:
            {"NSE:INFY": {"instrument_token": 408065, "last_price": 1550.5}}
        Empty dict on failure.
        """
        instruments_list = instruments if isinstance(instruments, list) else [instruments]
        result: Dict[str, Dict[str, Any]] = {}
        try:
            for batch in self._chunk(instruments_list, 500):
                result.update(self.kite.ltp(batch))
            logger.info(f"Fetched LTP for {len(instruments_list)} instrument(s)")
            return result
        except KiteException as e:
            logger.error(f"Failed to fetch LTP for {instruments_list}: {e}")
            return {}

    def get_ltp_value(self, instrument: Instrument) -> Optional[float]:
        """Convenience: return just the float LTP for a single instrument, or None."""
        data = self.get_ltp(instrument)
        entry = data.get(str(instrument))
        return entry["last_price"] if entry else None

    # ------------------------------------------------------------------
    # OHLC
    # ------------------------------------------------------------------
    def get_ohlc(self, instruments: Union[Instrument, List[Instrument]]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch OHLC + last price snapshot for one or more instruments.

        Returns
        -------
        Dict keyed by instrument string, e.g.:
            {
              "NSE:INFY": {
                  "instrument_token": 408065,
                  "last_price": 1550.5,
                  "ohlc": {"open": 1540, "high": 1560, "low": 1535, "close": 1545}
              }
            }
        Empty dict on failure.
        """
        instruments_list = instruments if isinstance(instruments, list) else [instruments]
        result: Dict[str, Dict[str, Any]] = {}
        try:
            for batch in self._chunk(instruments_list, 500):
                result.update(self.kite.ohlc(batch))
            logger.info(f"Fetched OHLC for {len(instruments_list)} instrument(s)")
            return result
        except KiteException as e:
            logger.error(f"Failed to fetch OHLC for {instruments_list}: {e}")
            return {}

    # ------------------------------------------------------------------
    # Full quote
    # ------------------------------------------------------------------
    def get_quote(self, instruments: Union[Instrument, List[Instrument]]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch the full market quote (depth, volume, OI, circuit limits, etc.)
        for one or more instruments.

        Returns
        -------
        Dict keyed by instrument string, full quote payload as documented at
        https://kite.trade/docs/connect/v3/market-quotes/
        Empty dict on failure.
        """
        instruments_list = instruments if isinstance(instruments, list) else [instruments]
        result: Dict[str, Dict[str, Any]] = {}
        try:
            # Kite recommends <= 500 instruments per quote() call
            for batch in self._chunk(instruments_list, 500):
                result.update(self.kite.quote(batch))
            logger.info(f"Fetched full quote for {len(instruments_list)} instrument(s)")
            return result
        except KiteException as e:
            logger.error(f"Failed to fetch quote for {instruments_list}: {e}")
            return {}

    # ------------------------------------------------------------------
    # Instrument lookup (handy for resolving tradingsymbol -> token)
    # ------------------------------------------------------------------
    def find_instrument_token(
        self, tradingsymbol: str, exchange: str = "NSE"
    ) -> Optional[int]:
        """
        Look up the numeric instrument_token for a tradingsymbol.
        Note: this downloads the full instrument dump for the exchange, so
        cache the result if calling repeatedly.
        """
        try:
            instruments = self.kite.instruments(exchange)
            for inst in instruments:
                if inst["tradingsymbol"] == tradingsymbol:
                    return inst["instrument_token"]
            logger.warning(f"{tradingsymbol} not found on {exchange}")
            return None
        except KiteException as e:
            logger.error(f"Failed to fetch instruments for {exchange}: {e}")
            return None


# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------
if __name__ == "__main__":
    from kiteconnect import KiteConnect

    kite = KiteConnect(api_key="your_api_key")
    kite.set_access_token("your_access_token")

    md = KiteMarketData(kite)

    # LTP
    print("LTP:", md.get_ltp(["NSE:INFY", "NSE:TCS"]))
    print("LTP (single value):", md.get_ltp_value("NSE:INFY"))

    # OHLC
    print("OHLC:", md.get_ohlc(["NSE:INFY"]))

    # Full quote
    print("Quote:", md.get_quote(["NSE:INFY"]))

    # Historical data (resolve token first)
    token = md.find_instrument_token("INFY", "NSE")
    if token:
        candles = md.get_historical_data(
            instrument_token=token,
            from_date="2024-01-01",
            to_date="2024-01-31",
            interval="day",
        )
        print(f"Fetched {len(candles)} candles")
