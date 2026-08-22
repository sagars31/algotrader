import os
import pandas as pd
from kiteconnect import KiteConnect

def get_instrument_token(tradingsymbol, exchange="NSE"):
    instrument_df = pd.read_csv("data/nse_instruments.csv")
    row = instrument_df[(instrument_df["tradingsymbol"] == tradingsymbol) & (instrument_df["exchange"] == exchange)]
    if row.empty:
        raise ValueError(f"Instrument {tradingsymbol} not found on {exchange}")
    return int(row.iloc[0]["instrument_token"])

def download_instruments_tokens():
    kite = KiteConnect(api_key=os.getenv("KITE_API_KEY"))
    instruments = kite.instruments("NSE")
    instrument_df = pd.DataFrame(instruments)
    instrument_df.to_csv("data/nse_instruments.csv", index=False)