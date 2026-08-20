import os
import webbrowser
from kiteconnect import KiteConnect


#API_KEY = os.getenv("KITE_API_KEY")
#API_SECRET = os.getenv("KITE_API_SECRET")
API_KEY = "v8n7x6hl0vx77fgm"
API_SECRET = "ic47rixb137ys6k60b4yecjh0yohkzm6"


def login_to_kite():

    if not API_KEY or not API_SECRET:
        raise ValueError(
            "Please set KITE_API_KEY and KITE_API_SECRET environment variables."
        )

    # Create Kite client
    kite = KiteConnect(api_key=API_KEY)

    # Generate Zerodha login URL
    login_url = kite.login_url()

    print("Opening Zerodha Kite login...")
    print(login_url)

    # Open browser
    webbrowser.open(login_url)

    # After successful login, Zerodha redirects to your
    # registered redirect URL with request_token.
    request_token = input("\nEnter the request_token from the redirect URL: ").strip()

    print(request_token)

    if not request_token:
        raise ValueError("Request token cannot be empty.")

    # Exchange request_token for access_token
    session_data = kite.generate_session(
        request_token,
        api_secret=API_SECRET
    )

    access_token = session_data["access_token"]
    print("access_token",access_token)

    # Set access token
    kite.set_access_token(access_token)

    print("\nLogin successful!")
    print("User ID:", session_data.get("user_id"))
    print("User Name:", session_data.get("user_name"))

    return kite


if __name__ == "__main__":

    kite = login_to_kite()
    # Create Kite client
    #kite = KiteConnect(api_key=API_KEY)
    #kite.set_access_token("jTJ96e5ITC1nebeBvb2n0JXroaJf4Ehc")

    # Test API call
    holdings = kite.holdings()

    print("\nKite Holdings:")
    print(holdings)
