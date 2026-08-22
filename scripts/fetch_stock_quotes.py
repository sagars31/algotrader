"""
Fetch live quotes from Kite Connect for stocks listed in a CSV file
(e.g. nse_equity.csv).

CSV format expected:
    Rank,Stock_Name,Symbol,Sector,Industry,Market_Cap_Cr,Source_File
    1,Reliance Industries Ltd.,RELIANCE,Crude Oil,Refineries,1770056.06,sectors\\crudeoil.csv
    2,Bharti Airtel Ltd.,BHARTIARTL,Telecom,Telecommunication - Service Provider,1243237.94,sectors\\telecom.csv
    ...

Notes on NSE equities in Kite Connect:
- Equities are quoted under the "NSE" exchange using their exact trading
  symbol, e.g. "NSE:RELIANCE", "NSE:TCS", "NSE:M&M" (special characters
  like "&" in symbols are passed through as-is, confirmed live).
- Kite quote keys must be in "EXCHANGE:SYMBOL" format — a bare symbol like
  "RELIANCE" silently returns no data.
- With 5,800+ stocks, this file well exceeds Kite's 500-instruments-per-call
  limit, so batching (see fetch_quotes) is required, not optional, here.
- A handful of duplicate symbols may exist in the source CSV (e.g. the same
  stock listed under multiple sector files); fetch_quotes() de-duplicates
  automatically before querying.
"""

import time
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
import pandas as pd
from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv

from utils import utils 
load_dotenv()


def load_symbols_from_csv(
    csv_path: str,
    symbol_col: str = "Symbol",
    exchange: str = "NSE",
) -> list[str]:
    """
    Read symbols from a CSV, skip blank/missing values, and format each
    as a Kite instrument key ("EXCHANGE:SYMBOL").

    CONFIRMED LIVE: Kite's quote() API silently drops any instrument key
    that isn't in "EXCHANGE:SYMBOL" format — a bare symbol like "RELIANCE"
    returns no data, while "NSE:RELIANCE" works. So the exchange prefix
    is required, not optional. Special characters in symbols (e.g. "&" in
    "M&M") pass through fine without extra escaping.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.
    symbol_col : str
        Column containing the trading symbol.
    exchange : str
        Exchange prefix to prepend (default "NSE").

    Returns
    -------
    list[str]
        e.g. ["NSE:RELIANCE", "NSE:TCS", "NSE:M&M", ...]
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


def chunk_list(items: list, batch_size: int = 500) -> list[list]:
    """
    Split a list into consecutive chunks of at most `batch_size` items.

    Kite's quote()/ohlc()/ltp() endpoints accept a HARD MAXIMUM of 500
    instruments per call — passing more either raises an error or gets
    silently truncated depending on the client. Any watchlist larger
    than 500 (e.g. a full sector or the Nifty 500 constituent list)
    must be split and queried across multiple calls.

    Parameters
    ----------
    items : list
        Full list of instrument keys.
    batch_size : int
        Max items per chunk (default 500 — Kite's per-call limit).

    Returns
    -------
    list[list]
        e.g. [ [500 items], [500 items], [247 items] ]
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def fetch_quotes(
    kite: KiteConnect,
    instruments: list[str],
    batch_size: int = 500,
    pause_between_batches: float = 0.34,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Fetch quotes for a (potentially large) list of instruments, batching
    automatically whenever the list exceeds Kite's 500-instrument-per-call
    limit, and return a single combined DataFrame.

    Parameters
    ----------
    kite : KiteConnect
        Authenticated KiteConnect instance.
    instruments : list[str]
        e.g. ["NSE:NIFTY 50", "NSE:NIFTY MIDCAP 150", ...] — any length.
    batch_size : int
        Max instruments per API call (default 500 — Kite's hard limit).
    pause_between_batches : float
        Seconds to sleep between batches. Kite's quote endpoints are
        rate-limited to ~3 requests/second; a small pause avoids
        HTTP 429 (Too Many Requests) errors on large watchlists that
        need several batches back-to-back.
    verbose : bool
        Print progress per batch (useful for large multi-batch runs).

    Returns
    -------
    pd.DataFrame with columns:
        instrument, last_price, prev_close, change, pct_change,
        open, high, low, volume
    """
    # De-duplicate while preserving order — avoids wasting quota on repeats
    seen = set()
    deduped = []
    for inst in instruments:
        if inst not in seen:
            seen.add(inst)
            deduped.append(inst)

    batches = chunk_list(deduped, batch_size)
    rows = []

    if verbose:
        print(f"Fetching {len(deduped)} instruments in {len(batches)} batch(es) "
              f"of up to {batch_size} each...")

    for batch_num, batch in enumerate(batches, start=1):
        if verbose:
            print(f"  Batch {batch_num}/{len(batches)}: {len(batch)} instruments...")

        try:
            quotes = kite.quote(batch)
        except Exception as exc:
            # Don't let one bad batch kill the whole run — log and continue
            print(f"  ⚠ Batch {batch_num} failed: {exc}")
            continue

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

        # Respect Kite's rate limit when there are more batches to go
        if batch_num < len(batches) and pause_between_batches > 0:
            time.sleep(pause_between_batches)

    return pd.DataFrame(rows)


def save_quotes_to_csv(
    original_df: pd.DataFrame,
    quotes_df: pd.DataFrame,
    output_path: str,
    symbol_col: str = "Symbol",
    exchange: str = "NSE",
) -> pd.DataFrame:
    """
    Merge original CSV metadata (Rank, Stock_Name, Symbol, Sector,
    Industry, Market_Cap_Cr) with fetched quote data and save to CSV.

    Output schema:
        Rank, Stock_Name, Symbol, Sector, Industry, Market_Cap_Cr,
        last_price, prev_close, change, pct_change

    Any target column missing from the source CSV is filled with NaN
    rather than raising an error, so this works even on partial data.

    Parameters
    ----------
    original_df : pd.DataFrame
        The raw CSV data as loaded by pd.read_csv (e.g. nse_equity.csv).
    quotes_df : pd.DataFrame
        Output of fetch_quotes() — must contain an 'instrument' column
        in "EXCHANGE:SYMBOL" format plus last_price/prev_close/etc.
    output_path : str
        Where to write the resulting CSV.
    symbol_col : str
        Column in original_df holding the bare symbol (pre-prefix).
    exchange : str
        Exchange prefix used when quotes were fetched (must match what
        was used in load_symbols_from_csv, so the merge key lines up).

    Returns
    -------
    pd.DataFrame
        The merged, final DataFrame that was written to `output_path`.
    """
    df = original_df.copy()

    # Build the merge key matching quotes_df's 'instrument' column
    df["instrument"] = f"{exchange}:" + df[symbol_col].astype(str).str.strip()

    target_cols = ["Rank", "Stock_Name", "Symbol", "Sector", "Industry", "Market_Cap_Cr"]
    output_cols = {}
    for col in target_cols:
        source_col = symbol_col if col == "Symbol" else col
        output_cols[col] = df[source_col] if source_col in df.columns else pd.NA

    base = pd.DataFrame(output_cols)
    base["instrument"] = df["instrument"]

    # Merge in the live quote metrics fetched from Kite
    merged = base.merge(
        quotes_df[["instrument","open", "high", "low", "volume", "last_price", "prev_close", "change", "pct_change"]],
        on="instrument",
        how="left",
    )
    merged = merged.drop(columns=["instrument"])

    merged.to_csv(output_path, index=False)
    return merged


def get_quotes_from_csv(
    kite: KiteConnect,
    csv_path: str,
    symbol_col: str = "Symbol",
    exchange: str = "NSE",
    batch_size: int = 500,
) -> pd.DataFrame:
    """
    End-to-end convenience wrapper: read symbols from CSV -> fetch quotes,
    automatically batching if the CSV has more than `batch_size` symbols.
    """
    instruments = load_symbols_from_csv(csv_path, symbol_col, exchange)
    if not instruments:
        raise ValueError("No valid symbols found in CSV")
    return fetch_quotes(kite, instruments, batch_size=batch_size)


if __name__ == "__main__":
    API_KEY = os.getenv("KITE_API_KEY")
    API_SECRET = os.getenv("KITE_API_SECRET")
    kite = KiteConnect(api_key=API_KEY)
    access_token=utils.read_from_file("data/access_token.txt").strip()
    kite.set_access_token(access_token)

    CSV_PATH = "data/nse_equity.csv"
    OUTPUT_PATH = "data/nse_equity_quotes.csv"

    original_df = pd.read_csv(CSV_PATH)
    quotes_df = get_quotes_from_csv(kite, CSV_PATH)

    final_df = save_quotes_to_csv(original_df, quotes_df, OUTPUT_PATH)
    print(f"Saved {len(final_df)} rows to {OUTPUT_PATH}")
    print(final_df.sort_values("pct_change", ascending=False).head(20).to_string(index=False))
