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

IMPORTANT — symbol resolution (confirmed live against Kite's instrument master):
  A CSV symbol does NOT always equal Kite's actual NSE trading symbol.
  Two cases cause silent "no data" if you just prefix with "NSE:":
    1. Series-suffix stocks. Some companies trade in a non-default NSE
       series (trade-to-trade "BE", SME "SM", InvIT "IV", etc.), and
       Kite's tradingsymbol includes that suffix:
         CSV "STLTECH"   -> actual "NSE:STLTECH-BE"
         CSV "E2E"       -> actual "NSE:E2E-BE"
         CSV "NHIT"      -> actual "NSE:NHIT-IV"
    2. BSE-only listings. Some stocks aren't listed on NSE at all:
         CSV "NSDL"      -> only exists as "BSE:NSDL"
         CSV "RRP"       -> only exists as "BSE:RRP"
  build_symbol_resolver() below downloads Kite's full instrument master
  once and resolves each CSV symbol correctly (preferring plain "EQ"
  series when multiple series exist, falling back to BSE when NSE has
  no listing at all) instead of guessing.
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


# Preference order when a base symbol has multiple NSE series listed.
# Lower number = preferred. Unlisted/unknown series sort last.
SERIES_PRIORITY = {"EQ": 0, "BE": 1, "BZ": 2, "BT": 3, "SM": 4, "ST": 5}


def build_symbol_resolver(kite: KiteConnect) -> dict:
    """
    Download Kite's full NSE + BSE instrument master and build a lookup
    from a bare stock symbol (as it typically appears in a research CSV,
    e.g. "STLTECH") to the correct Kite instrument key
    (e.g. "NSE:STLTECH-BE" or "BSE:NSDL" if there's no NSE listing).

    This solves two real, confirmed issues:
      - Stocks trading in a non-default NSE series (BE/BZ/BT/SM/IV/...)
        whose tradingsymbol has a "-SUFFIX" the CSV symbol lacks.
      - Stocks listed only on BSE, with no NSE listing at all.

    Parameters
    ----------
    kite : KiteConnect
        Authenticated KiteConnect instance.

    Returns
    -------
    dict
        {"STLTECH": "NSE:STLTECH-BE", "NSDL": "BSE:NSDL", "RELIANCE": "NSE:RELIANCE", ...}
    """
    nse = pd.DataFrame(kite.instruments("NSE"))
    bse = pd.DataFrame(kite.instruments("BSE"))

    nse = nse[nse["segment"] == "NSE"].copy()
    bse = bse[bse["segment"] == "BSE"].copy()

    nse["base_symbol"] = nse["tradingsymbol"].str.split("-").str[0]
    nse["series_rank"] = nse["series"].map(SERIES_PRIORITY).fillna(99)
    nse_sorted = nse.sort_values(["base_symbol", "series_rank"])
    nse_best = nse_sorted.drop_duplicates("base_symbol", keep="first")
    nse_map = {
        row.base_symbol: f"NSE:{row.tradingsymbol}"
        for row in nse_best.itertuples()
    }

    bse["base_symbol"] = bse["tradingsymbol"].str.split("-").str[0]
    bse_best = bse.drop_duplicates("base_symbol", keep="first")
    bse_map = {
        row.base_symbol: f"BSE:{row.tradingsymbol}"
        for row in bse_best.itertuples()
    }

    # NSE takes priority; only fall back to BSE if NSE has no listing
    resolver = dict(bse_map)
    resolver.update(nse_map)
    return resolver


def load_symbols_from_csv(
    csv_path: str,
    symbol_col: str = "Symbol",
    exchange: str = "NSE",
    resolver: dict | None = None,
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
        Exchange prefix to prepend when `resolver` is not used or a
        symbol isn't found in it (default "NSE").
    resolver : dict, optional
        Output of build_symbol_resolver(). When given, each symbol is
        looked up here first to get its correct Kite instrument key
        (handling series-suffix stocks like "STLTECH-BE" and BSE-only
        listings like "BSE:NSDL"). Symbols not found in the resolver
        fall back to the plain f"{exchange}:{symbol}" format.

    Returns
    -------
    list[str]
        e.g. ["NSE:RELIANCE", "NSE:STLTECH-BE", "BSE:NSDL", ...]
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

    if resolver:
        return [resolver.get(s, f"{exchange}:{s}") for s in symbols.tolist()]

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
    resolver: dict | None = None,
) -> pd.DataFrame:
    """
    Merge original CSV metadata (Rank, Stock_Name, Symbol, Sector,
    Industry, Market_Cap_Cr) with fetched quote data and save to CSV.

    Output schema:
        Rank, Stock_Name, Symbol, Sector, Industry, Market_Cap_Cr,
        last_price, prev_close, change, pct_change, resolved_instrument

    `resolved_instrument` shows exactly which Kite instrument key was
    used for each row (e.g. "NSE:STLTECH-BE" or "BSE:NSDL"), so it's
    easy to see, and audit, how each symbol was resolved.

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
        Exchange prefix used as the fallback when a symbol isn't found
        in `resolver` (must match what was used in load_symbols_from_csv).
    resolver : dict, optional
        Same resolver passed to load_symbols_from_csv — needed here so
        the merge key lines up with what was actually fetched.

    Returns
    -------
    pd.DataFrame
        The merged, final DataFrame that was written to `output_path`.
    """
    df = original_df.copy()
    bare_symbols = df[symbol_col].astype(str).str.strip()

    # Build the merge key exactly the same way load_symbols_from_csv did
    if resolver:
        df["instrument"] = bare_symbols.map(lambda s: resolver.get(s, f"{exchange}:{s}"))
    else:
        df["instrument"] = f"{exchange}:" + bare_symbols

    target_cols = ["Rank", "Stock_Name", "Symbol", "Sector", "Industry", "Market_Cap_Cr"]
    output_cols = {}
    for col in target_cols:
        source_col = symbol_col if col == "Symbol" else col
        output_cols[col] = df[source_col] if source_col in df.columns else pd.NA

    base = pd.DataFrame(output_cols)
    base["instrument"] = df["instrument"]

    # Merge in the live quote metrics fetched from Kite
    merged = base.merge(
        quotes_df[["instrument", "last_price", "prev_close", "change", "pct_change"]],
        on="instrument",
        how="left",
    )
    merged = merged.rename(columns={"instrument": "resolved_instrument"})

    merged.to_csv(output_path, index=False)
    return merged


def get_quotes_from_csv(
    kite: KiteConnect,
    csv_path: str,
    symbol_col: str = "Symbol",
    exchange: str = "NSE",
    batch_size: int = 500,
    resolver: dict | None = None,
) -> pd.DataFrame:
    """
    End-to-end convenience wrapper: read symbols from CSV -> fetch quotes,
    automatically batching if the CSV has more than `batch_size` symbols.
    Pass `resolver` (from build_symbol_resolver) to correctly handle
    series-suffix stocks and BSE-only listings.
    """
    instruments = load_symbols_from_csv(csv_path, symbol_col, exchange, resolver)
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

    print("Downloading Kite instrument master (NSE + BSE) to resolve symbols...")
    resolver = build_symbol_resolver(kite)
    print(f"Resolver built with {len(resolver)} known symbols.")

    original_df = pd.read_csv(CSV_PATH)
    quotes_df = get_quotes_from_csv(kite, CSV_PATH, resolver=resolver)

    final_df = save_quotes_to_csv(original_df, quotes_df, OUTPUT_PATH, resolver=resolver)

    matched = final_df["last_price"].notna().sum()
    print(f"Saved {len(final_df)} rows to {OUTPUT_PATH} "
          f"({matched} matched a live quote, {len(final_df) - matched} did not — "
          f"likely delisted, suspended, or not traded today).")
    print(final_df.sort_values("pct_change", ascending=False).head(20).to_string(index=False))
