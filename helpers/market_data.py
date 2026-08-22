from __future__ import annotations
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
import os
import webbrowser
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from utils import utils

load_dotenv()

api_key = os.getenv("KITE_API_KEY")

kite = KiteConnect(api_key=api_key)
access_token=utils.read_from_file("data/access_token.txt").strip()
kite.set_access_token(access_token)

candles = kite.historical_data(
        instrument_token=341249,
        from_date="2026-01-01",
        to_date="2026-01-31",
        interval="day",
    )

#ltp = kite.ltp(["NSE:INFY", "NSE:TCS"])
#ohlc = kite.ohlc(["NSE:INFY"])
quote = kite.quote(["NSE:TCS", "NSE:RELIANCE", "NSE:HDFCBANK", "NSE:ICICIBANK", "NSE:SBIN", "NSE:AXISBANK", "NSE:KOTAKBANK", "NSE:BAJFINANCE", "NSE:HDFC", "NSE:ITC", "NSE:TATASTEEL", "NSE:LT", "NSE:MARUTI", "NSE:BHARTIARTL", "NSE:ASIANPAINT", "NSE:NESTLEIND", "NSE:HCLTECH", "NSE:TECHM", "NSE:INFY"])
# print("LTP:", ltp)
# print("OHLC:", ohlc)
print("Quote:", quote)
#print(f"Fetched {len(candles)} candles for INFY in Jan 2026",candles)