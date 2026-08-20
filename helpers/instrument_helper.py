import os
import pandas as pd

def get_instrument_token(tradingsymbol, exchange="NSE"):
    instrument_df = pd.read_csv("data/nse_instruments.csv")
    row = instrument_df[(instrument_df["tradingsymbol"] == tradingsymbol) & (instrument_df["exchange"] == exchange)
    ]
    if row.empty:
        raise ValueError(f"Instrument {tradingsymbol} not found on {exchange}")
    return int(row.iloc[0]["instrument_token"])


print("get_instrument_token ",get_instrument_token("781RJ32-SG", exchange="NSE"))