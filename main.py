"""
A call option is OTM if the underlying price is trading below the strike price of the call. A put option is OTM if the underlying's price is above the put's strike price.
"""
import ccxt
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from datetime import datetime, timedelta
import logging
import time
import schedule
import hmac
import hashlib
import requests
import json 
import atexit
from logging.handlers import RotatingFileHandler
import re
import warnings
from tqdm import tqdm
import os

warnings.filterwarnings("ignore", category=DeprecationWarning)

while True:
    try:
        time_delta = int(input("Please enter the time delta in weeks: "))
        if time_delta > 0:
            break
        else:
            print("Time delta must be a positive integer. Please try again.")
    except ValueError:
        print("Invalid input. Please enter a positive integer.")
print(f"We are using a delta of {time_delta} weeks")

while True:
    try:
        runtime = int(input("Please enter the runtime in seconds: "))
        if runtime > 0:
            break
        else:
            print("Runtime must be a positive integer. Please try again.")
    except ValueError:
        print("Invalid input. Please enter a positive integer.")
print(f"We are using a delta of {runtime} seconds")
# Configure rotating file handler
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


def sanitize_filename(filename):
    # Replace invalid characters with underscores
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def return_balance_sheet_change(filepath, destinationpath):
    try:
        with open(filepath, 'r') as config_file:
            nested_bal = json.load(config_file)
    except FileNotFoundError:
        print(f"Error: The file {filepath} does not exist.")
        return
    except json.JSONDecodeError:
        print(f"Error: The file {filepath} is not valid JSON.")
        return

    keys = list(nested_bal.keys())
    if not keys:
        print("Error: The JSON file is empty.")
        return

    first_key = keys[0]
    last_key = keys[-1]
    first_balance_sheet = nested_bal[first_key]
    last_balance_sheet = nested_bal[last_key]

    net_balance_change = subtract_balance_sheets(first_balance_sheet, last_balance_sheet)

    raw_filename = f"{first_key} to {last_key}_net_bal_change.json"
    sanitized_filename = sanitize_filename(raw_filename)
    destination_filename = sanitized_filename
    
    try:
        with open(destination_filename, 'w') as file:
            json.dump(net_balance_change, file, indent=4)
    except IOError as e:
        print(f"Error: Unable to write to file {destination_filename}. {e}")
        return

    print(f"Net balance change has been written to {destination_filename}")
    return net_balance_change

def list_to_dict(asset_list):
    """Convert a list of asset dictionaries to a dictionary with asset names as keys."""
    return {item['Asset']: item for item in asset_list}

def subtract_balance_sheets(sheet1, sheet2):
    """Subtract the balances of two balance sheets."""
    sheet1_dict = list_to_dict(sheet1)
    sheet2_dict = list_to_dict(sheet2)
    
    result_dict = {}
    
    all_assets = set(sheet1_dict.keys()).union(set(sheet2_dict.keys()))
    
    for asset in all_assets:

        free1 = sheet1_dict.get(asset, {'Free': 0.0})['Free']
        locked1 = sheet1_dict.get(asset, {'Locked': 0.0})['Locked']
        total1 = sheet1_dict.get(asset, {'Total': 0.0})['Total']
        
        free2 = sheet2_dict.get(asset, {'Free': 0.0})['Free']
        locked2 = sheet2_dict.get(asset, {'Locked': 0.0})['Locked']
        total2 = sheet2_dict.get(asset, {'Total': 0.0})['Total']
        if ((total1 -total2)!=0):
            result_dict[asset] = {
                'Asset': asset,
                'Free': free1 - free2,
                'Locked': locked1 - locked2,
                'Total': total1 - total2
            }
    
    return list(result_dict.values())

def clear_json_file(file_path):
    with open(file_path, 'w') as file:
        json.dump({}, file)  # Clears the file by writing an empty dictionary
#FINAL EXIT COMMAND
def final_command():
    print("Executing final command...")
    if total_order!=0:
        print(f"Total orders: {total_order}")
        return_balance_sheet_change("nested_dataframes.json","net_bal_change.json")
        print("Saving roi")
        save_roi_to_json(calculate_roi_from_balance_sheets("nested_dataframes.json"),"roi.json")
        print("Clearing old balance sheet")
        clear_json_file("nested_dataframes.json")
    else: 
        print("No Order placed")
    
   
    

atexit.register(final_command)

#Function to set up Deribit client
def deribit_set_up(mode):
    logger.info(f"We are in Deribit: {mode} mode")
    client_id_testnet = "m_cYdGRs"
    client_secret_testnet = "CFMj4XERdBpYU5f-xGiEeM6q29WWPh78KbOllO8I5nI"

    client_id_realnet = "VUSrWKNX"
    client_secret_realnet = "CNIEmjiKy2p-h28O4Mda1QKD8hXJ3duA5rAODdLfvwE"

    if mode == "test":
        client_id = client_id_testnet
        client_secret = client_secret_testnet
        base_url = 'https://test.deribit.com/api/v2/' # test base url
    else:
        client_id = client_id_realnet
        client_secret = client_secret_realnet
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
#Function to retrieve info
def information_for_options():
    client=deribit_set_up("test")
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
            expiry_datetime = datetime.utcfromtimestamp(expiry_timestamp) 

            # Calculate current datetime plus 20 weeks
            current_datetime = datetime.utcnow()
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
        expiry_datetime = datetime.utcfromtimestamp(expire_time/1000)
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
# Function to get access token
def get_access_token(client_id, client_secret):
    url = f'{base_url}public/auth'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.get(url, params=params)
    response_data = response.json()
    if 'result' in response_data:
        return response_data['result']['access_token']
    else:
        raise Exception('Failed to get access token: ' + response_data.get('error', {}).get('message', 'Unknown error'))
# Function to fetch account information
def fetch_account_info(access_token):
    url = f'{base_url}private/get_account_summary'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    params = {
        'currency': 'BTC'  # or 'ETH', etc.
    }
    response = requests.get(url, headers=headers, params=params)
    response_data = response.json()
    if 'result' in response_data:
        return response_data['result']
    else:
        raise Exception('Failed to fetch account information: ' + response_data.get('error', {}).get('message', 'Unknown error'))    
#Function to get account balance
def get_account_balances(symbol=None):
    api_key,api_secret=get_keys("binance_keys.json")
    client = Client(api_key, api_secret, testnet=testnet)
    time_offset=get_time_off_set("time.json")
    if time_offset:
        client.timestamp_offset = time_offset
    try:
        # Fetch account information
        account_info = client.get_account()

        # Extract balances
        balances = account_info['balances']
        balance_info = []

        # Iterate through each balance and append non-zero balances to the list
        if symbol==None:
            for balance in balances:
                asset = balance['asset']
                free_balance = float(balance['free'])
                locked_balance = float(balance['locked'])
                total_balance = free_balance + locked_balance

                if total_balance > 0:
                    balance_info.append({
                        'Asset': asset,
                        'Free': free_balance,
                        'Locked': locked_balance,
                        'Total': total_balance
                    })
        else: 
            for balance in balances:
                if balance['asset'] in symbol:
                    asset = balance['asset']
                    free_balance = float(balance['free'])
                    locked_balance = float(balance['locked'])
                    total_balance = free_balance + locked_balance

                    if total_balance > 0:
                        balance_info.append({
                            'Asset': asset,
                            'Free': free_balance,
                            'Locked': locked_balance,
                            'Total': total_balance
                        })

        return balance_info

    except Exception as e:
        print(f"An error occurred: {e}")
        return []
#Function for Displaying account balance
def display_balances(balances):
    if not balances:
        print("No balances found or an error occurred.")
        return

    print(f"{'Asset':<10} {'Free Balance':<15} {'Locked Balance':<15} {'Total Balance':<15}")
    print("="*55)
    for balance in balances:
        print(f"{balance['Asset']:<10} {balance['Free']:<15} {balance['Locked']:<15} {balance['Total']:<15}")
#Function to create signature for certain querry
def create_signature(query_string, secret_key):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
#Function for key extract
def get_keys(filepath):
    with open(filepath) as key_file:
        config = json.load(key_file)
        api_key = config['api_key']
        api_secret=config['api_secret']
    return api_key,api_secret
#Function to sync time (generate an offset)
def synchronize_time():
    api_key,api_secret=get_keys("binance_keys.json")
    client = Client(api_key, api_secret, testnet=testnet)
    try:
        server_time = client.get_server_time()
        server_timestamp = server_time['serverTime']
        local_timestamp = int(time.time() * 1000)
        time_offset = server_timestamp - local_timestamp
        with open("time.json","w") as config_file:
            json.dump(time_offset,config_file)
    except Exception as e:
        print(f"An error occurred during time synchronization: {e}")
#Function to get time_offset
def get_time_off_set(filepath):
    with open(filepath) as config_file:
        time_offset=json.load(config_file)
    return time_offset
# Function to get all open orders from Binance Spot Testnet
def get_all_open_orders():
    api_key,api_secret=get_keys("binance_keys.json")
    base_url = 'https://testnet.binance.vision'
    endpoint = '/api/v3/openOrders'
    timestamp = int(time.time() * 1000)
    query_string = f'timestamp={timestamp}'

    # Creating a signature
    signature = create_signature(query_string, api_secret)
    query_string += f'&signature={signature}'

    # Header with API key
    headers = {
        'X-MBX-APIKEY': api_key
    }

    # Sending the GET request
    url = f'{base_url}{endpoint}?{query_string}'
    response = requests.get(url, headers=headers)

    # Handling the response
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Error: {response.status_code}, Message: {response.text}')
#Function for retrieving all past orders
def get_all_past_orders(symbol, start_time=None, end_time=None, limit=500):
    """Retrieve all past orders for a given symbol on Binance Spot Testnet."""
    base_url = 'https://testnet.binance.vision'
    endpoint = '/api/v3/allOrders'
    timestamp = int(time.time() * 1000)
    api_key,api_secret=get_keys("binance_keys.json")    
    # Create query string
    query_string = f'symbol={symbol}&timestamp={timestamp}&limit={limit}'
    if start_time:
        query_string += f'&startTime={start_time}'
    if end_time:
        query_string += f'&endTime={end_time}'

    # Create signature
    signature = create_signature(query_string, api_secret)
    query_string += f'&signature={signature}'

    # Headers
    headers = {'X-MBX-APIKEY': api_key}

    # Send GET request
    url = f'{base_url}{endpoint}?{query_string}'
    response = requests.get(url, headers=headers)

    # Handle the response
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Error: {response.status_code}, Message: {response.text}')
#Function to create an option order
def create_option_order(client):
    try:
        # Construct the order
        symbol=information_for_options()[-3]
        order = client.create_market_buy_order(symbol,1)

        print(f"Order created successfully on Deribit: {order}")
        return order

    except Exception as e:
        print(f"Failed to create order: {e}")
        return None
#Function for creating a hedging order 

#Function to get the min contract amount

def round_step_size(quantity, step_size):
    return ((quantity // step_size) * step_size)

def get_lot_size(symbol):
    url = "https://api.binance.com/api/v3/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    for s in data['symbols']:
        if s['symbol'] == symbol:
            for filter in s['filters']:
                if filter['filterType'] == 'LOT_SIZE':
                    min_qty = filter['minQty']
                    step_size = filter['stepSize']
                    return float(min_qty), float(step_size)
    return None, None

def get_min_notional(symbol):
    url = "https://api.binance.com/api/v3/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    for s in data['symbols']:
        if s['symbol'] == symbol:
            for filter in s['filters']:
                if filter['filterType'] == 'MIN_NOTIONAL':
                    return float(filter['minNotional'])
    raise ValueError("No value for min_notional")            
    return None


def create_hedging_order(symbol, side, share_to_purchase):
    # Connect to Binance testnet
    api_key, api_secret = get_keys("binance_keys.json")
    client = Client(api_key, api_secret, testnet=testnet)

    # Get current price of the symbol
    

    # Adjust the share_to_purchase according to LOT_SIZE constraints
    min_qty, step_size = get_lot_size(symbol)
    if abs(share_to_purchase) < min_qty:
        raise ValueError(f"Quantity {share_to_purchase} is less than the minimum lot size {min_qty}")
    share_to_purchase = round_step_size(share_to_purchase, step_size)

    

    
    # Create a market order
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=share_to_purchase
        )
        print("Order placed successfully.")
        output_file = "order.json"
        with open(output_file, 'w') as file:
            json.dump(order, file, indent=4)
        logger.info(f"Order details saved to {output_file}")
    except BinanceAPIException as e:
        print(f"Binance API Exception: {e}")
        logger.error(f"Binance API Exception: {e}")
        raise Exception(f"An error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")
        raise Exception(f"An error occurred: {e}")
    total_order+=1
    return order


def calculate_and_place_order(symbol):
    try:
        # Load old delta value from file
        with open("old_delta.json", 'r') as file:
            old_delta = json.load(file)
        old_delta = float(old_delta)

        # Initialize Binance client
        api_key, api_secret = get_keys("binance_keys.json")
        client = Client(api_key, api_secret, testnet=testnet)

        # Get current price for the symbol
        ticker = client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])

        # Initialize Deribit client and fetch new delta and contract size
        option_info = information_for_options()
        new_delta = float(option_info[-2])
        contract_size = float(option_info[-1])

        # Calculate share to purchase
        share_to_purchase = (new_delta - old_delta) * contract_size * 15

        # Log current price and share to purchase
        logger.info(f"Current price of {symbol}: {current_price}")
        logger.info(f"Share to purchase: {share_to_purchase}")

        notional_value = current_price * share_to_purchase
        logger.info(f"The purchase order in USD is {notional_value}")

        # Check if there's a change in delta
        if share_to_purchase == 0:
            logger.info(f"{datetime.now()}: No change in delta. No order placed.")
            return

        # Check if notional value is sufficient
        if abs(notional_value) < 6:
            logger.warning(f"Notional value: {notional_value} too low, can't place order")
            return

        

        # Check if the share to purchase meets minimum lot size
        min_qty, _ = get_lot_size(symbol)
        if abs(share_to_purchase) < min_qty:
            logger.warning(f"Share to purchase too small: {share_to_purchase}")
            return

        # Determine the order side and check for sufficient liquidity if selling
        side = "BUY" if new_delta > old_delta else "SELL"
        liquid = get_account_balances(symbol)
        if side == "SELL":
            if not liquid or liquid[0]['Free'] < abs(share_to_purchase):
                raise ValueError(f"Not enough {symbol} to trade: Needed to sell {abs(share_to_purchase)}, only have {liquid[0]['Free']}")

        # Create hedging order
        print(f"Create {side} hedging order for: {symbol} for {round(abs(share_to_purchase), 6)}")
        create_hedging_order(symbol, side, round(abs(share_to_purchase), 6))
        update_time_index_balance_sheet(json_file_path)

        # Update old delta value
        old_delta = new_delta
        logger.info(f"Updated old_delta to: {old_delta}")
        with open("old_delta.json", "w") as json_file:
            json.dump(old_delta, json_file)

    except json.JSONDecodeError:
        logger.error("Error loading old delta value from file.")
    except KeyError as e:
        logger.error(f"Missing key in option information: {e}")
    except ValueError as e:
        logger.error(f"Value error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def update_time_index_balance_sheet(json_file_path):
    try: 
        with open(json_file_path, 'r') as json_file:
            nested_bal_dict = json.load(json_file)
        balances=get_account_balances()
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        nested_bal_dict[current_timestamp]=balances
        logger.info(f"Length of nested bal: {len(nested_bal_dict)}")
        with open(json_file_path, 'w') as json_file:
            json.dump(nested_bal_dict, json_file, indent=4)
    except Exception as e:
        logger.error(f"Failed to update balance sheet: {e}")


#info_after trade
def calculate_roi_from_balance_sheets(filepath):
    """
    Calculate ROI from a nested dict of balances sheet

    Default is doing the first and last. 

    Returns:
    - ROI: The Return on Investment as a percentage.
    """
    with open(filepath) as config_file:
        nested_bal=json.load(config_file)
    first_key=list(nested_bal.keys())[0]
    last_key=list(nested_bal.keys())[-1]
    first_bal=nested_bal[first_key]
    last_bal=nested_bal[last_key]

    def list_to_dict(asset_list):
        """Convert a list of asset dictionaries to a dictionary with asset names as keys."""
        return {item['Asset']: item for item in asset_list if 'Asset' in item}
    
    # Convert initial and final balance sheets to dictionaries
    initial_dict = list_to_dict(first_bal)
    final_dict = list_to_dict(last_bal)
    
    # Calculate total initial and final values
    initial_total = sum(item['Total'] for item in initial_dict.values())
    final_total = sum(item['Total'] for item in final_dict.values())
    
    # Compute the net gain or loss
    net_gain = final_total - initial_total
    
    if initial_total == 0:
        raise ValueError("Initial total value must be greater than zero.")
    
    # Calculate ROI
    roi = (net_gain / initial_total) * 100
    
    return {
        "timestamp": datetime.now().isoformat(),
        "ROI": roi
    }

def save_roi_to_json(roi_data, output_filepath):
    """
    Saves the ROI data along with a timestamp to a JSON file.
    
    Parameters:
    - roi_data (dict): The ROI data containing the ROI value and the timestamp.
    - output_filepath (str): The file path where the JSON file will be saved.
    """
    with open(output_filepath, 'w') as file:
        json.dump(roi_data, file, indent=4)


if __name__ == "__main__":
    global testnet
    testnet=False
    global total_order
    total_order=0
#     # When asks price of the OUT call (St - Ct): Ask > (St - Ct) || Ask < (St - Ct)
    
#     # Dp + Dc != 0
    # Information for options
    clear_json_file("net_bal_change.json")
    json_file_path = 'nested_dataframes.json'
    #display_balances(balances)
    expiry_datetime, share_to_purchase, symbol ,delta ,contract_size= information_for_options()
    print(f"General Information: \nExpiry_Date : {expiry_datetime}, \nDeribit symbol: {symbol}")
    symbol = re.split('[-_]', symbol)[0]
    # Append "USDT" to the first part of the split result
    symbol = symbol + "USDT"

    print(f"Converting to Binance symbol: {symbol}")
    update_time_index_balance_sheet(json_file_path)


    def job():
        synchronize_time()
        
        
        calculate_and_place_order(symbol)
        
    # Schedule the job every hour
    schedule.every(runtime).seconds.do(job)

    # Run the scheduler
    while True: 
        for _ in tqdm(range(runtime), desc="Time until next job (seconds)"):
                schedule.run_pending()
                time.sleep(1)

    # Buy option
    # account = client.fetch_balance()
    # print(account)
    # x = client.create_order(symbol = symbol, type = "market", side = "buy", amount = 1)
    # print(x)
    # Start hedging
    # hedging_with_spot(share_to_purchase)
    

    

    
