"""
kite_orders.py
================
Reusable, production-friendly wrapper functions around the KiteConnect API
for authenticating and placing/modifying/cancelling/tracking orders.

Usage
-----
    from kite_orders import KiteOrderManager

    mgr = KiteOrderManager(api_key="xxx", api_secret="yyy")
    print(mgr.get_login_url())

    # after user logs in and you capture request_token from the redirect:
    mgr.authenticate(request_token="request_token_from_redirect")

    order_id = mgr.place_market_order(
        symbol="INFY", exchange="NSE", transaction_type="BUY", quantity=1
    )

    mgr.modify_order(order_id, price=1505.00, quantity=2)
    mgr.cancel_order(order_id)
    mgr.print_order_book()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kite_orders")


@dataclass
class OrderResult:
    """Simple result wrapper so callers don't have to deal with exceptions directly."""
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None


class KiteOrderManager:
    """
    Encapsulates authentication + all order-related operations for Zerodha's
    Kite Connect API. Each public method catches KiteException/generic errors
    so callers get a clean OrderResult / None instead of having to wrap every
    call in try/except themselves.
    """

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)
        self.access_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def get_login_url(self) -> str:
        """Return the URL the user must visit to log in and grant access."""
        return self.kite.login_url()

    def authenticate(self, request_token: str) -> bool:
        """
        Exchange a request_token (captured from the redirect after login)
        for an access_token, and configure the KiteConnect client to use it.
        """
        try:
            data = self.kite.generate_session(
                request_token, api_secret=self.api_secret
            )
            self.access_token = data["access_token"]
            self.kite.set_access_token(self.access_token)
            logger.info("Authenticated successfully.")
            return True
        except KiteException as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def set_existing_access_token(self, access_token: str) -> None:
        """Reuse a previously obtained access_token (e.g. cached from earlier in the day)."""
        self.access_token = access_token
        self.kite.set_access_token(access_token)

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------
    def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        product: str = "CNC",
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        validity: str = "DAY",
        variety: str = "regular",
        tag: Optional[str] = None,
    ) -> OrderResult:
        """
        Generic order placement covering MARKET / LIMIT / SL / SL-M order types.

        Parameters
        ----------
        symbol            Trading symbol, e.g. "INFY"
        exchange          "NSE", "BSE", "NFO", etc.
        transaction_type  "BUY" or "SELL"
        quantity          Number of shares/contracts
        order_type        "MARKET", "LIMIT", "SL", "SL-M"
        product           "CNC", "MIS", "NRML"
        price             Required for LIMIT and SL orders
        trigger_price     Required for SL and SL-M orders
        validity          "DAY" or "IOC"
        variety           "regular", "amo", "co", "iceberg" etc.
        tag               Optional custom tag for tracking this order
        """
        try:
            kwargs: Dict[str, Any] = dict(
                variety=variety,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=product,
                order_type=order_type,
                validity=validity,
            )
            if price is not None:
                kwargs["price"] = price
            if trigger_price is not None:
                kwargs["trigger_price"] = trigger_price
            if tag:
                kwargs["tag"] = tag

            order_id = self.kite.place_order(**kwargs)
            logger.info(f"Order placed successfully. ID: {order_id}")
            return OrderResult(success=True, order_id=order_id)

        except KiteException as e:
            logger.error(f"Order placement failed: {e}")
            return OrderResult(success=False, error=str(e))
        except Exception as e:
            logger.exception("Unexpected error while placing order")
            return OrderResult(success=False, error=str(e))

    # -- convenience wrappers for common order types -------------------

    def place_market_order(
        self, symbol: str, transaction_type: str, quantity: int,
        exchange: str = "NSE", product: str = "CNC", **kwargs
    ) -> OrderResult:
        return self.place_order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type="MARKET",
            product=product,
            **kwargs,
        )

    def place_limit_order(
        self, symbol: str, transaction_type: str, quantity: int, price: float,
        exchange: str = "NSE", product: str = "CNC", **kwargs
    ) -> OrderResult:
        return self.place_order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type="LIMIT",
            product=product,
            price=price,
            **kwargs,
        )

    def place_sl_order(
        self, symbol: str, transaction_type: str, quantity: int,
        price: float, trigger_price: float,
        exchange: str = "NSE", product: str = "MIS", **kwargs
    ) -> OrderResult:
        return self.place_order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type="SL",
            product=product,
            price=price,
            trigger_price=trigger_price,
            **kwargs,
        )

    def place_sl_m_order(
        self, symbol: str, transaction_type: str, quantity: int,
        trigger_price: float,
        exchange: str = "NSE", product: str = "MIS", **kwargs
    ) -> OrderResult:
        return self.place_order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type="SL-M",
            product=product,
            trigger_price=trigger_price,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Modify / cancel
    # ------------------------------------------------------------------
    def modify_order(
        self,
        order_id: str,
        variety: str = "regular",
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        trigger_price: Optional[float] = None,
        validity: Optional[str] = None,
    ) -> OrderResult:
        """Modify quantity/price/type/etc. on an existing pending order."""
        try:
            kwargs: Dict[str, Any] = {"variety": variety, "order_id": order_id}
            if quantity is not None:
                kwargs["quantity"] = quantity
            if price is not None:
                kwargs["price"] = price
            if order_type is not None:
                kwargs["order_type"] = order_type
            if trigger_price is not None:
                kwargs["trigger_price"] = trigger_price
            if validity is not None:
                kwargs["validity"] = validity

            self.kite.modify_order(**kwargs)
            logger.info(f"Order {order_id} modified.")
            return OrderResult(success=True, order_id=order_id)
        except KiteException as e:
            logger.error(f"Order modification failed: {e}")
            return OrderResult(success=False, order_id=order_id, error=str(e))

    def cancel_order(self, order_id: str, variety: str = "regular") -> OrderResult:
        """Cancel a pending order."""
        try:
            self.kite.cancel_order(variety=variety, order_id=order_id)
            logger.info(f"Order {order_id} cancelled.")
            return OrderResult(success=True, order_id=order_id)
        except KiteException as e:
            logger.error(f"Order cancellation failed: {e}")
            return OrderResult(success=False, order_id=order_id, error=str(e))

    # ------------------------------------------------------------------
    # Order book / status
    # ------------------------------------------------------------------
    def get_orders(self) -> List[Dict[str, Any]]:
        """Return the full order book for the day."""
        try:
            return self.kite.orders()
        except KiteException as e:
            logger.error(f"Failed to fetch orders: {e}")
            return []

    def get_order_status(self, order_id: str) -> Optional[str]:
        """Return the latest status string for a given order_id, or None if not found."""
        for o in self.get_orders():
            if o.get("order_id") == order_id:
                return o.get("status")
        return None

    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Return the full state-transition history of a single order."""
        try:
            return self.kite.order_history(order_id)
        except KiteException as e:
            logger.error(f"Failed to fetch order history for {order_id}: {e}")
            return []

    def print_order_book(self) -> None:
        """Pretty-print the current order book to stdout."""
        orders = self.get_orders()
        if not orders:
            print("No orders found.")
            return
        for o in orders:
            print(f"{o['order_id']}  {o['tradingsymbol']:<12} {o['status']}")


# ------------------------------------------------------------------
# Example usage (only runs when this file is executed directly)
# ------------------------------------------------------------------
if __name__ == "__main__":
    API_KEY = "your_api_key"
    API_SECRET = "your_api_secret"

    mgr = KiteOrderManager(api_key=API_KEY, api_secret=API_SECRET)

    # Step 1: send the user to this URL to log in
    print("Login here:", mgr.get_login_url())

    # Step 2: after redirect, capture request_token from the query string
    request_token = "request_token_from_redirect"
    if mgr.authenticate(request_token):

        # Market order
        result = mgr.place_market_order(
            symbol="INFY", transaction_type="BUY", quantity=1
        )
        print(result)

        # Limit order
        result = mgr.place_limit_order(
            symbol="INFY", transaction_type="BUY", quantity=1, price=1500.00
        )
        print(result)

        # Stop-loss order
        result = mgr.place_sl_order(
            symbol="INFY", transaction_type="SELL", quantity=1,
            price=1490.00, trigger_price=1495.00,
        )
        print(result)

        if result.success:
            mgr.modify_order(result.order_id, price=1505.00, quantity=2)
            mgr.cancel_order(result.order_id)

        mgr.print_order_book()
