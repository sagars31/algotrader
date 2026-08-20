"""
Get live data of a particular stock using Zerodha Kite Connect API.

Setup:
    pip install kiteconnect

You need:
    - api_key       : from your Kite Connect app (developers.kite.trade)
    - api_secret     : from your Kite Connect app
    - request_token  : generated fresh each day via the login flow (see below)

This script shows TWO ways to get "live" data:
    1. Polling LTP/quote via REST API (simple, good for occasional checks)
    2. Streaming tick-by-tick data via WebSocket (KiteTicker) - true live/real-time data
"""

from kiteconnect import KiteConnect, KiteTicker
import time

# ---------------------------------------------------------------------------
# STEP 1: AUTHENTICATION
# ---------------------------------------------------------------------------
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

kite = KiteConnect(api_key=API_KEY)

# 1a. Print this URL, open it in browser, log in, and Zerodha will redirect
#     you to your registered redirect URL with a `request_token` in the query string.
print("Login URL:", kite.login_url())

# 1b. Paste the request_token you got from the redirect URL here
REQUEST_TOKEN = "paste_request_token_here"

data = kite.generate_session(REQUEST_TOKEN, api_secret=API_SECRET)
access_token = data["access_token"]

kite.set_access_token(access_token)
print("Access token generated:", access_token)

# ---------------------------------------------------------------------------
# STEP 2: SIMPLE APPROACH - Poll LTP / full quote for a particular stock
# ---------------------------------------------------------------------------
# Instrument format: "EXCHANGE:TRADINGSYMBOL", e.g. "NSE:RELIANCE", "NSE:TCS"

STOCK = "NSE:RELIANCE"

def get_ltp_once(symbol):
    ltp_data = kite.ltp(symbol)
    print(ltp_data)
    return ltp_data[symbol]["last_price"]

def get_full_quote_once(symbol):
    quote = kite.quote(symbol)
    q = quote[symbol]
    print(f"Symbol: {symbol}")
    print(f"Last Price: {q['last_price']}")
    print(f"Open: {q['ohlc']['open']}  High: {q['ohlc']['high']}  "
          f"Low: {q['ohlc']['low']}  Close (prev): {q['ohlc']['close']}")
    print(f"Volume: {q.get('volume')}")
    return q

def poll_ltp(symbol, interval_seconds=5, iterations=10):
    """Repeatedly fetch LTP every few seconds (simple polling, not true streaming)."""
    for _ in range(iterations):
        price = get_ltp_once(symbol)
        print(f"{symbol} LTP: {price}")
        time.sleep(interval_seconds)

# Example usage (uncomment to run):
# get_ltp_once(STOCK)
# get_full_quote_once(STOCK)
# poll_ltp(STOCK, interval_seconds=5, iterations=5)

# ---------------------------------------------------------------------------
# STEP 3: TRUE LIVE DATA - WebSocket streaming via KiteTicker
# ---------------------------------------------------------------------------
# This pushes tick data to you in real time instead of you polling for it.
# You need the instrument_token (not the trading symbol) for subscription.

def get_instrument_token(symbol):
    """symbol like 'NSE:RELIANCE' -> returns instrument_token"""
    quote = kite.quote(symbol)
    return quote[symbol]["instrument_token"]

def start_live_ticker(symbol):
    instrument_token = get_instrument_token(symbol)
    print(f"Instrument token for {symbol}: {instrument_token}")

    kws = KiteTicker(API_KEY, access_token)

    def on_ticks(ws, ticks):
        # ticks is a list of dicts with live market data
        for tick in ticks:
            print(tick)

    def on_connect(ws, response):
        # Subscribe to the instrument once connected
        ws.subscribe([instrument_token])
        # MODE_FULL gives market depth, MODE_QUOTE gives OHLC+LTP, MODE_LTP gives only LTP
        ws.set_mode(ws.MODE_FULL, [instrument_token])

    def on_close(ws, code, reason):
        ws.stop()

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    kws.connect()  # blocking call; runs until stopped

# Example usage (uncomment to run):
# start_live_ticker(STOCK)
