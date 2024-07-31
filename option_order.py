import os
from dotenv import load_dotenv
from datetime import datetime, timedelta ,timezone
from logging.handlers import RotatingFileHandler
import logging
import ccxt
import time
import contextlib
import io


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, max_length=None):
        super().__init__(fmt, datefmt)
        self.max_length = max_length

    def format(self, record):
        if self.max_length and record.args:
            truncated_args = []
            for arg in record.args:
                if isinstance(arg, str) and len(arg) > self.max_length:
                    truncated_args.append(arg[:self.max_length] + '... [truncated]')
                else:
                    truncated_args.append(arg)
            record.args = tuple(truncated_args)
        return super().format(record)

# Configure the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define a handler with a rotating file handler
handler = RotatingFileHandler(
    filename="app_test.log",
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=5
)

# Define a custom formatter and set it to the handler
formatter = CustomFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    max_length=200  # Limit the message length to 100 characters
)
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)
# Configure rotating file handler
current_time = datetime.now()
print(current_time.strftime('%Y-%m-%d %H:%M:%S'))
load_dotenv("config.env")

time_delta = int(os.getenv('TIME_DELTA', '1'))  # Default to 1 week if not set
runtime = int(os.getenv('RUNTIME', '3600'))  # Default to 3600 seconds (1 hour) if not set
binance_api_key = os.getenv('BINANCE_API_KEY')
binance_api_secret = os.getenv('BINANCE_API_SECRET')
deribit_client_id_testnet = os.getenv('DERIBIT_CLIENT_ID_TESTNET')
deribit_client_secret_testnet = os.getenv('DERIBIT_CLIENT_SECRET_TESTNET')
deribit_client_id_realnet = os.getenv('DERIBIT_CLIENT_ID_REALNET')
deribit_client_secret_realnet = os.getenv('DERIBIT_CLIENT_SECRET_REALNET')
mode=os.getenv("MODE")

print(f"{deribit_client_id_testnet}")
print(f"{deribit_client_secret_testnet}")
print(f"We are using a delta of {time_delta} weeks")
print(f"We are using a runtime of {runtime} seconds")
def deribit_set_up():
    logger.info(f"We are in Deribit: {mode} mode")

    
    if mode == "test":
        client_id = deribit_client_id_testnet
        client_secret = deribit_client_secret_testnet
        base_url = 'https://test.deribit.com/api/v2/' # test base url
    else:
        client_id = deribit_client_id_realnet
        client_secret = deribit_client_secret_realnet
        base_url = 'https://www.deribit.com/api/v2/'

    logging.info(f"The base url: {base_url}")

    client = ccxt.deribit({
        'apiKey': client_id,
        'secret': client_secret,
        'timeout': 150000,
    })
    if mode=="test":
        client.set_sandbox_mode(True)
    return client
def information_for_options():
    client=deribit_set_up()
    try:
        markets = client.fetch_markets()
        server_time = client.fetch_time()
        # Filter option markets
        option_markets = [market for market in markets if market['type'] == 'option']
        # print("Option markets:", option_markets)
        for i in option_markets:
            # print(i["info"])
            filtered_list = []
            expiry_timestamp = float(i['info']['expiration_timestamp'])/1000
            # Convert expiry timestamp to datetime
            expiry_datetime = datetime.fromtimestamp(expiry_timestamp, timezone.utc) 

            # Calculate current datetime plus 20 weeks
            current_datetime = datetime.now(timezone.utc)
            x_weeks_later = current_datetime + timedelta(weeks=time_delta)
            # Check if expiry datetime is greater than 20 weeks later
            if expiry_datetime <= x_weeks_later:
                filtered_list.append(i)
                # if call option and strike is not none, add to list
                second_filtered_list = []
                for item in filtered_list:
                    # if item["strike"] is not None and 
                    if item["optionType"] == "call" and item["strike"] is not None:

                        second_filtered_list.append(item)
                        # third_filtered_list = []
                        # # Loop through second filtered list and get contract with longest expiration
                        # for item in second_filtered_list:
                        #     expired_time = item["expiration_timestamp"]
                            
        #                     if item["expiration_timestamp"] is not None:
        #                         third_filtered_list.append(item)
                third_filtered_list = []
                expiry_timestamp_list = []
                if len(second_filtered_list) > 0:
                    longest_expiry_contract = max(second_filtered_list, key=lambda x: x['expiry'])

        # print(longest_expiry_contract)
        # Contract symbol
        symbol = longest_expiry_contract["id"]
        # Timestamp of contract            
        expire_time = float(longest_expiry_contract["info"]["expiration_timestamp"])
        # convert expiration timestamp to datetime
        expiry_datetime = datetime.fromtimestamp(expire_time / 1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
        # Get delta
        contract_delta = client.fetch_greeks(longest_expiry_contract["symbol"])
        delta = contract_delta["info"]["greeks"]["delta"]

        # Get contract size
        # Calculate share to purchase
        contract_size = longest_expiry_contract["info"]["contract_size"]
        share_to_purchase = float(delta) * float(contract_size)


        return expiry_datetime, share_to_purchase, symbol ,delta ,contract_size
    except Exception as e:
        logger.error(f"Failed to retrieve options information: {e}")
        print("ERROR INFO for option")
        return None, None, None, None, None
def place_option_order():
    client = deribit_set_up()
    if not check_open_orders(client):
        logger.info("There are outstanding options. No new order will be placed.")
        print("There are outstanding options. No new order will be placed.")
        return None
    try:
        expiry_datetime, share_to_purchase, symbol, delta, contract_size = information_for_options()
        if expiry_datetime:
            print(f"Expiry Date: {expiry_datetime}")
            print(f"Shares to Purchase: {share_to_purchase}")
            print(f"Symbol: {symbol}")
            print(f"Delta: {delta}")
            print(f"Contract Size: {contract_size}")

            # Place the order
            order = client.create_order(symbol=symbol, type='market', side='buy', amount=1)
            print(f"Placed order: {order['id']}")
            return order['id']  # Return the order ID for tracking
        else:
            print("No options available within the specified date range.")
            return None
    except Exception as e:
        logger.error(f"An error occurred while placing the order: {e}")
        print(f"An error occurred: {e}")
        return None
def track_order(order_id):
    client = deribit_set_up()
    try:
        order_status = client.fetch_order(order_id)
        print(f"Order {order_id} Status: {order_status}")
        return order_status
    except Exception as e:
        logger.error(f"An error occurred while tracking the order: {e}")
        print(f"An error occurred: {e}")
        return None
def check_open_orders(client):
    
    try:
        open_orders = client.fetch_open_orders()
        len(open_orders)
        return len(open_orders) == 0  # Return True if there are no open orders
    except Exception as e:
        logger.error(f"An error occurred while checking open orders: {e}")
        return False
def main():
    order_id = place_option_order()
    if order_id:
        # Track the order status every minute for 10 minutes (as an example)
        for _ in range(10):
            order_status = track_order(order_id)
            time.sleep(60)  # Wait for 1 minute before checking the status again

if __name__ == "__main__":
    main()


