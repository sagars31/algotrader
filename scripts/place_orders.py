import os
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from utils import utils
from helpers import orders

load_dotenv()
api_key = os.getenv("KITE_API_KEY")

kite = KiteConnect(api_key=api_key)
access_token=utils.read_from_file("data/access_token.txt").strip()
kite.set_access_token(access_token)

def multiple_orders():
    # Place multiple orders
    order1_id = orders.place_order(
        tradingsymbol="INFY",
        transaction_type=kite.TRANSACTION_TYPE_BUY,
        quantity=1,
        product=kite.PRODUCT_CNC,
        order_type=kite.ORDER_TYPE_MARKET
    )

    order2_id = orders.place_order(
        tradingsymbol="TCS",
        transaction_type=kite.TRANSACTION_TYPE_SELL,
        quantity=1,
        product=kite.PRODUCT_CNC,
        order_type=kite.ORDER_TYPE_MARKET
    )

    return order1_id, order2_id
orders.place_order(
    tradingsymbol="INFY",

