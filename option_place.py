import os
import ccxt
import json
from datetime import datetime
from functions import information_for_options, logger, deribit_set_up

# Initialize exchange
exchange = deribit_set_up()

def read_last_order_expiry():
    try:
        if not os.path.exists('order_log.json') or os.path.getsize('order_log.json') == 0:
            return None
        
        with open('order_log.json', 'r') as f:
            order_log = json.load(f)
            expiry_str = order_log.get('expiry_datetime')
            if expiry_str:
                return datetime.fromisoformat(expiry_str)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read order log: {e}")
        return None

def write_order_log(order, expiry_datetime):
    order_log = {
        'symbol': order['symbol'],
        'order_id': order['id'],
        'timestamp': order['timestamp'],
        'amount': order['amount'],
        'price': order.get('price', 'N/A'),  # Market orders may not have a price
        'expiry_datetime': expiry_datetime.isoformat()  # Store expiry datetime
    }
    with open('order_log.json', 'w') as f:
        json.dump(order_log, f, indent=4)

def write_price_log(order):
    price_log = {
        'order_id': order['id'],
        'price': order.get('price', 'N/A'),
        'timestamp': datetime.utcfromtimestamp(order['timestamp'] / 1000).isoformat()
    }
    with open('price_log.json', 'w') as f:
        json.dump(price_log, f, indent=4)

def place_option_order():
    # Get option details
    expiry_datetime, share_to_purchase, symbol, delta, contract_size = information_for_options()

    if symbol is None:
        print("No valid option symbol found.")
        return

    # Check if previous option has expired
    last_expiry = read_last_order_expiry()
    if last_expiry and datetime.utcnow() < last_expiry:
        print(f"Previous option has not yet expired. Waiting until {last_expiry}.")
        return

    try:
        # Define order details
        order_type = 'market'  # Market order does not require a price
        side = 'buy'  # or 'sell'
        amount = 1  # Fixed amount

        # Log details before placing order
        print(f"Placing order with symbol: {symbol}, amount: {amount}")

        # Place an option order
        order = exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            price=None  # Market order does not require a price
        )

        # Store expiry datetime in the order log
        write_order_log(order, expiry_datetime)
        # Store price in the separate price log
        write_price_log(order)

        print(f"Order placed: {order}")

    except ccxt.NetworkError as e:
        print(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        print(f"Exchange error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Place the order
place_option_order()
