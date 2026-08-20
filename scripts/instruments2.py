import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
import os
from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta
from kiteconnect import KiteConnect
from utils import utils

API_KEY = os.getenv("KITE_API_KEY")
kite = KiteConnect(api_key=API_KEY)

access_token = utils.read_from_file("data/access_token.txt")
kite.set_access_token(access_token)
print("Login successful. Access token:", access_token)

instruments = kite.instruments("NSE")  # returns a big list of dicts
instrument_df = pd.DataFrame(instruments)

def get_instrument_token(tradingsymbol, exchange="NSE"):
    row = instrument_df[
        (instrument_df["tradingsymbol"] == tradingsymbol)
        & (instrument_df["exchange"] == exchange)
    ]
    if row.empty:
        raise ValueError(f"Instrument {tradingsymbol} not found on {exchange}")
    return int(row.iloc[0]["instrument_token"])

reliance_token = get_instrument_token("RELIANCE")
print("RELIANCE instrument token:", reliance_token)


# ============================================
# STEP 3: Fetch LIVE / LAST TRADED PRICE (LTP)
# ============================================

ltp_data = kite.ltp(["NSE:RELIANCE", "NSE:INFY"])
print("LTP data:", ltp_data)


# ============================================
# STEP 4: Fetch full market quote (OHLC, volume, depth, etc.)
# ============================================

quote_data = kite.quote(["NSE:RELIANCE"])
print("Quote data:", quote_data)


# ============================================
# STEP 5: Fetch OHLC only (lighter than full quote)
# ============================================

ohlc_data = kite.ohlc(["NSE:RELIANCE", "NSE:TCS"])
print("OHLC data:", ohlc_data)


# ============================================
# STEP 6: Fetch HISTORICAL data (candles)
# ============================================

to_date = datetime.now()
from_date = to_date - timedelta(days=30)

historical_data = kite.historical_data(
    instrument_token=reliance_token,
    from_date=from_date,
    to_date=to_date,
    interval="day",          # options: minute, day, 3minute, 5minute, 15minute,
                              # 30minute, 60minute, etc.
    continuous=False,
    oi=False
)

hist_df = pd.DataFrame(historical_data)
print(hist_df.head())

# Save to CSV if needed
hist_df.to_csv("reliance_historical.csv", index=False)
print("Saved historical data to reliance_historical.csv")