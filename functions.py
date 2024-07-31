import ccxt
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from datetime import datetime, timedelta
import logging
import json
import hmac
import hashlib
import requests
import atexit
from logging.handlers import RotatingFileHandler
import re
import warnings
import os

warnings.filterwarnings("ignore", category=DeprecationWarning)

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
    max_length=200  # Limit the message length to 200 characters
)
handler.setFormatter(formatter)
logger.addHandler(handler)

def sanitize_filename(filename):
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

    sanitized_filename = sanitize_filename(f"{first_key} to {last_key}_net_bal_change.json")
    
    try:
        with open(sanitized_filename, 'w') as file:
            json.dump(net_balance_change, file, indent=4)
    except IOError as e:
        print(f"Error: Unable to write to file {sanitized_filename}. {e}")
        return

    print(f"Net balance change has been written to {sanitized_filename}")
    return net_balance_change

def list_to_dict(asset_list):
    return {item['Asset']: item for item in asset_list}

def subtract_balance_sheets(sheet1, sheet2):
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
        if (total1 - total2) != 0:
            result_dict[asset] = {
                'Asset': asset,
                'Free': free1 - free2,
                'Locked': locked1 - locked2,
                'Total': total1 - total2
            }
    
    return list(result_dict.values())

def clear_json_file(file_path):
    with open(file_path, 'w') as file:
        json.dump({}, file)

def final_command():
    print("Executing final command...")
    total_order = 0  # Placeholder for the actual total_order variable
    if total_order != 0:
        print(f"Total orders: {total_order}")
        return_balance_sheet_change("nested_dataframes.json", "net_bal_change.json")
        print("Saving ROI")
        # Placeholder for save_roi_to_json and calculate_roi_from_balance_sheets functions
        clear_json_file("nested_dataframes.json")
    else:
        print("No Order placed")
    clear_json_file("nested_dataframes.json")

atexit.register(final_command)

def deribit_set_up(mode, deribit_client_id_testnet, deribit_client_secret_testnet, deribit_client_id_realnet, deribit_client_secret_realnet):
    logger.info(f"We are in Deribit: {mode} mode")

    if mode == "test":
        client_id = deribit_client_id_testnet
        client_secret = deribit_client_secret_testnet
        base_url = 'https://test.deribit.com/api/v2/'  # test base url
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
    if mode == "test":
        client.set_sandbox_mode(True)
    return client

def information_for_options(client, time_delta):
    try:
        markets = client.fetch_markets()
        server_time = client.fetch_time()
        option_markets = [market for market in markets if market['type'] == 'option']
        filtered_list = []
        for i in option_markets:
            expiry_timestamp = float(i['info']['expiration_timestamp']) / 1000
            expiry_datetime = datetime.utcfromtimestamp(expiry_timestamp)
            current_datetime = datetime.utcnow()
            x_weeks_later = current_datetime + timedelta(weeks=time_delta)
            if expiry_datetime <= x_weeks_later:
                filtered_list.append(i)

        second_filtered_list = [item for item in filtered_list if item["optionType"] == "call" and item["strike"] is not None]
        if second_filtered_list:
            longest_expiry_contract = max(second_filtered_list, key=lambda x: x['expiry'])
            symbol = longest_expiry_contract["id"]
            expire_time = float(longest_expiry_contract["info"]["expiration_timestamp"])
            expiry_datetime = datetime.utcfromtimestamp(expire_time / 1000)
            contract_delta = client.fetch_greeks(longest_expiry_contract["symbol"])
            delta = contract_delta["info"]["greeks"]["delta"]
            contract_size = longest_expiry_contract["info"]["contract_size"]
            share_to_purchase = float(delta) * float(contract_size)
            return expiry_datetime, share_to_purchase, symbol, delta, contract_size
    except Exception as e:
        logger.error(f"Failed to retrieve options information: {e}")
    return None, None, None, None, None

def create_signature(query_string, secret_key):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def place_option_order(client, symbol, side, quantity, price=None, order_type='LIMIT'):
    try:
        order = client.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=quantity,
            price=price
        )
        return order
    except BinanceAPIException as e:
        logger.error(f"Binance API Exception: {e}")
    except BinanceOrderException as e:
        logger.error(f"Binance Order Exception: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    return None

def log_order_to_json(order, filepath='orders_log.json'):
    try:
        with open(filepath, 'a') as file:
            json.dump(order, file, indent=4)
            file.write('\n')
    except IOError as e:
        logger.error(f"Error writing order to JSON file: {e}")
