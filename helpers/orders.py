import os
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from utils import utils

load_dotenv()
api_key = os.getenv("KITE_API_KEY")

kite = KiteConnect(api_key=api_key)
access_token=utils.read_from_file("data/access_token.txt").strip()
kite.set_access_token(access_token)

def place_order(tradingsymbol, transaction_type, quantity, product, order_type, price=None, trigger_price=None):
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NSE,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=product,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            validity=kite.VALIDITY_DAY,
        )
        print(f"Order placed. ID: {order_id}")
        return order_id
    except Exception as e:
        print(f"Order placement failed: {e}")
        return None
# ------------------------------------------------------------------
# 2. Placing a regular (market/limit) order
# ------------------------------------------------------------------
try:
    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NSE,
        tradingsymbol="INFY",
        transaction_type=kite.TRANSACTION_TYPE_BUY,
        quantity=1,
        product=kite.PRODUCT_CNC,       # CNC / MIS / NRML
        order_type=kite.ORDER_TYPE_MARKET,  # MARKET / LIMIT / SL / SL-M
        validity=kite.VALIDITY_DAY,
    )
    print(f"Order placed. ID: {order_id}")
except Exception as e:
    print(f"Order placement failed: {e}")

# ------------------------------------------------------------------
# 3. Placing a LIMIT order with a specific price
# ------------------------------------------------------------------
try:
    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NSE,
        tradingsymbol="INFY",
        transaction_type=kite.TRANSACTION_TYPE_BUY,
        quantity=1,
        product=kite.PRODUCT_CNC,
        order_type=kite.ORDER_TYPE_LIMIT,
        price=1500.00,
        validity=kite.VALIDITY_DAY,
    )
    print(f"Limit order placed. ID: {order_id}")
except Exception as e:
    print(f"Order placement failed: {e}")

# ------------------------------------------------------------------
# 4. Placing a Stop-Loss (SL) order
# ------------------------------------------------------------------
try:
    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NSE,
        tradingsymbol="INFY",
        transaction_type=kite.TRANSACTION_TYPE_SELL,
        quantity=1,
        product=kite.PRODUCT_MIS,
        order_type=kite.ORDER_TYPE_SL,
        price=1490.00,        # trigger execution price
        trigger_price=1495.00,
        validity=kite.VALIDITY_DAY,
    )
    print(f"SL order placed. ID: {order_id}")
except Exception as e:
    print(f"Order placement failed: {e}")

# ------------------------------------------------------------------
# 5. Modifying an order
# ------------------------------------------------------------------
try:
    kite.modify_order(
        variety=kite.VARIETY_REGULAR,
        order_id=order_id,
        price=1505.00,
        quantity=2,
    )
    print("Order modified.")
except Exception as e:
    print(f"Order modification failed: {e}")

# ------------------------------------------------------------------
# 6. Cancelling an order
# ------------------------------------------------------------------
try:
    kite.cancel_order(
        variety=kite.VARIETY_REGULAR,
        order_id=order_id,
    )
    print("Order cancelled.")
except Exception as e:
    print(f"Order cancellation failed: {e}")

# ------------------------------------------------------------------
# 7. Checking order status / order book
# ------------------------------------------------------------------
orders = kite.orders()
for o in orders:
    print(o["order_id"], o["tradingsymbol"], o["status"])