import pandas as pd
nifty500_df = pd.read_csv("data/nifty500.csv")
niftyall_df = pd.read_csv("data/nse_equity.csv")
nifty500_df.columns = nifty500_df.columns.str.strip()  # clean up any whitespace in headers
print(nifty500_df.head())
print(nifty500_df.columns.tolist())

sector_counts = nifty500_df.groupby("Sector")["Symbol"].count().sort_values(ascending=False)
sector_counts = nifty500_df.groupby("Sector")["Symbol"].count().sort_values(ascending=False)
print(sector_counts)