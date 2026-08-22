import pandas as pd
from kiteconnect import KiteConnect


def load_symbols_from_csv(
    csv_path: str,
    symbol_col: str = "Symbol",
    exchange: str = "NSE",
) -> list[str]:
    """
    Read symbols from a CSV, skip blank/missing values, and format each
    as a Kite instrument key ("EXCHANGE:SYMBOL").

    CONFIRMED LIVE (2026-08-21): Kite's quote() API silently drops any
    instrument key that isn't in "EXCHANGE:SYMBOL" format — a bare
    symbol like "NIFTY 50" returns no data, while "NSE:NIFTY 50" works.
    So the exchange prefix is required, not optional.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.
    symbol_col : str
        Column containing the trading symbol / index name.
    exchange : str
        Exchange prefix to prepend (default "NSE" — correct for
        broad-based NSE indices).

    Returns
    -------
    list[str]
        e.g. ["NSE:NIFTY 50", "NSE:NIFTY NEXT 50", ...]
    """
    df = pd.read_csv(csv_path)

    if symbol_col not in df.columns:
        raise ValueError(f"Column '{symbol_col}' not found in {csv_path}")

    symbols = (
        df[symbol_col]
        .dropna()
        .astype(str)
        .str.strip()
    )
    symbols = symbols[symbols != ""]  # drop empty strings after strip

    return [f"{exchange}:{s}" for s in symbols.tolist()]


def fetch_quotes(kite: KiteConnect, instruments: list[str]) -> pd.DataFrame:
    """
    Fetch quotes for a list of instruments in batches (Kite allows up to
    500 instruments per quote() call) and return a tidy DataFrame.

    Parameters
    ----------
    kite : KiteConnect
        Authenticated KiteConnect instance.
    instruments : list[str]
        e.g. ["NSE:NIFTY 50", "NSE:NIFTY MIDCAP 150"]

    Returns
    -------
    pd.DataFrame with columns:
        instrument, last_price, prev_close, change, pct_change,
        open, high, low, volume
    """
    BATCH_SIZE = 500
    rows = []
    if len(instruments) > BATCH_SIZE:
        for i in range(0, len(instruments), BATCH_SIZE):
            batch = instruments[i: i + BATCH_SIZE]
            quotes = kite.quote(batch)
            for instrument, data in quotes.items():
                last_price = data.get("last_price")
                ohlc = data.get("ohlc", {})
                prev_close = ohlc.get("close")
                change = None
                pct_change = None
                if last_price is not None and prev_close:
                    change = round(last_price - prev_close, 2)
                    pct_change = round((change / prev_close) * 100, 2)

                rows.append({
                    "instrument": instrument,
                    "last_price": last_price,
                    "prev_close": prev_close,
                    "change": change,
                    "pct_change": pct_change,
                    "open": ohlc.get("open"),
                    "high": ohlc.get("high"),
                    "low": ohlc.get("low"),
                    "volume": data.get("volume"),
                })

    return pd.DataFrame(rows)


def get_quotes_from_csv(
    kite: KiteConnect,
    csv_path: str,
    symbol_col: str = "Symbol",
    exchange: str = "NSE",
) -> pd.DataFrame:
    """
    End-to-end convenience wrapper: read symbols from CSV -> fetch quotes.
    """
    instruments = load_symbols_from_csv(csv_path, symbol_col, exchange)
    if not instruments:
        raise ValueError("No valid symbols found in CSV")
    return fetch_quotes(kite, instruments)


if __name__ == "__main__":
    API_KEY = "your_api_key"
    ACCESS_TOKEN = "your_access_token"

    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)

    CSV_PATH = "/mnt/user-data/uploads/broad_based_indices.csv"

    df = get_quotes_from_csv(kite, CSV_PATH)

    df_sorted = df.sort_values("pct_change", ascending=False)
    print(df_sorted.to_string(index=False))
