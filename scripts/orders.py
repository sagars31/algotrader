from kiteconnect import KiteConnect

# ------------------------------------------------------------------
# 1. Setup & Authentication
# ------------------------------------------------------------------
api_key = "your_api_key"
api_secret = "your_api_secret"

kite = KiteConnect(api_key=api_key)

# Step 1: Get login url, redirect user there
print(kite.login_url())

# Step 2: After login, Kite redirects to your redirect_url with a
# request_token as a query param. Use it to generate a session.
request_token = "request_token_from_redirect"
data = kite.generate_session(request_token, api_secret=api_secret)

access_token = data["access_token"]
kite.set_access_token(access_token)

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