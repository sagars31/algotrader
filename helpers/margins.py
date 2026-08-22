import os
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from utils import utils
from utils import json_utils

load_dotenv()
api_key = os.getenv("KITE_API_KEY")

kite = KiteConnect(api_key=api_key)
access_token=utils.read_from_file("data/access_token.txt").strip()
kite.set_access_token(access_token)

def save_margins_to_file():
    margins = kite.margins()
    json_utils.write_json_to_file("data/margins.json", margins)
    print("Margins data fetched successfully.",margins)

def get_equity_live_balance():
    json = json_utils.read_json_from_file("data/margins.json")
    live_balance = json.get("equity", {}).get("available", {}).get("live_balance", 0.0)
    return live_balance

def get_equity_opening_balance():
    json = json_utils.read_json_from_file("data/margins.json")
    opening_balance = json.get("equity", {}).get("available", {}).get("opening_balance", 0.0)
    return opening_balance

#save_margins_to_file(filename="data/margins.json")
print("Live balance:", get_equity_live_balance())