from binance.client import Client
from binance.exceptions import BinanceAPIException
from infor_before_trade import information_for_options
from datetime import datetime, timedelta
import time

def create_hedging_order(symbol, side,share_to_purchase):
    """
    Create a hedging order on Binance testnet.

    Parameters:
    api_key (str): Your Binance testnet API key.
    api_secret (str): Your Binance testnet API secret.
    symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
    side (str): 'BUY' or 'SELL' order.
    share_to_purchase (float): Amount of the asset to purchase.

    Returns:
    dict: Response from Binance API with order details.
    """
    # Connect to Binance testnet
    api_key = 'ZQatsB1ChLN5LDHH2fMr7rj9lgiYBLs5NlF1HgagdyepcoOAYnV3kDsVXGkXKrgb'
    api_secret = 'aM9Jzg7gp6LKiKxzXB7H7F0IPj72D33KiDZr8Own4ByvRRTqUTzVeXbfmDIcFx9b'
    client = Client(api_key, api_secret, testnet=True)
    # Get current price of the symbol
    ticker = client.get_symbol_ticker(symbol=symbol)
    current_price = float(ticker['price'])
    print(f"Current price of {symbol}: {current_price}")
    print(f"Share to purchase: {share_to_purchase} ")
    # Create a market order
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=float (share_to_purchase)
        )
        print("Order placed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        order = None
    
    return order

def calculate_and_place_order(symbol,old_delta):
    old_delta=float(old_delta)
    new_delta=float(information_for_options(client)[-2])
    contract_size=float(information_for_options(client)[-1])
    share_to_purchase = (new_delta - old_delta) * contract_size
    if share_to_purchase != 0:  # Only place an order if there's a change in delta
        if new_delta > old_delta:
            side = "BUY"
        else:
            side = "SELL"
        create_hedging_order(symbol,side, abs(share_to_purchase))
    else:
        print(f"{datetime.now()}: No change in delta. No order placed.")
