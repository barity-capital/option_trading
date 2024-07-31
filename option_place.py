import ccxt
import time
from datetime import datetime

# Initialize exchange
exchange = ccxt.deribit({
    'apiKey': 'your_api_key',
    'secret': 'your_secret_key',
    'enableRateLimit': True,
})

# Define option details
symbol = 'BTC-29JUL24-40000-C'  # Replace with your desired option contract
order_type = 'limit'  # or 'market'
side = 'buy'  # or 'sell'
amount = 1  # number of contracts
price = 100  # price per contract

# Place an option order
order = exchange.create_order(
    symbol=symbol,
    type=order_type,
    side=side,
    amount=amount,
    price=price
)

# Log the order details to a JSON file
order_log = {
    'symbol': symbol,
    'order_id': order['id'],
    'timestamp': order['timestamp'],
    'amount': order['amount'],
    'price': order['price']
}

import json

with open('order_log.json', 'w') as f:
    json.dump(order_log, f, indent=4)

print(f"Order placed: {order_log}")

# Function to check if the option has expired
def check_option_expiry(symbol):
    option_info = exchange.fetch_ticker(symbol)
    current_time = datetime.utcnow()

    # Deribit options include expiry date in the symbol, e.g., 'BTC-29JUL24-40000-C'
    expiry_date_str = symbol.split('-')[1]  # '29JUL24'
    expiry_date = datetime.strptime(expiry_date_str, '%d%b%y')

    return current_time > expiry_date

# Check if the option has expired
is_expired = check_option_expiry(symbol)
if is_expired:
    print(f"The option {symbol} has expired.")
else:
    print(f"The option {symbol} is still active.")
