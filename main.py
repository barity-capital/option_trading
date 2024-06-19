"""
A call option is OTM if the underlying price is trading below the strike price of the call. A put option is OTM if the underlying's price is above the put's strike price.
"""
import ccxt
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime, timedelta
import time
import schedule
import hmac
import hashlib
import requests
import json 

#Function to set up Deribit client
def deribit_set_up(mode):
    print(f"We are in: {mode} mode")
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

    print(f"The base url: {base_url} ")

    client = ccxt.deribit({
        'apiKey': client_id,
        'secret': client_secret,
        'timeout': 150000,
    })
    if mode=="test":
        client.set_sandbox_mode(True)
    return client
#Function to retrieve info
def information_for_options(client):
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
        twenty_weeks_later = current_datetime + timedelta(weeks=20)
        # Check if expiry datetime is greater than 20 weeks later
        if expiry_datetime <= twenty_weeks_later:
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
    client = Client(api_key, api_secret, testnet=True)
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
    with open(filepath) as config_file:
        config = json.load(config_file)
        api_key = config['api_key']
        api_secret=config['api_secret']
    return api_key,api_secret
#Function to sync time (generate an offset)
def synchronize_time():
    api_key,api_secret=get_keys("../binance_keys.json")
    client = Client(api_key, api_secret, testnet=True)
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
        symbol=information_for_options(client)[-3]
        order = client.create_market_buy_order(symbol,1)

        print(f"Order created successfully on Deribit: {order}")
        return order

    except Exception as e:
        print(f"Failed to create order: {e}")
        return None
#Function for creating a hedging order 
def create_hedging_order(symbol, side,share_to_purchase):

    # Connect to Binance testnet
    api_key,api_secret=get_keys("binance_keys.json")
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
      
        #print(client.get_symbol_info(symbol))        
        order = None
    
    return order
#Function to get the min contract amount
def get_min_contract_size(symbol):
    url = "https://api.binance.com/api/v3/exchangeInfo"
    response = requests.get(url)
    data = response.json()

    for s in data['symbols']:
        if s['symbol'] == symbol:
            for filter in s['filters']:
                if filter['filterType'] == 'LOT_SIZE':
                    min_qty = filter['minQty']
                    return float(min_qty)
#Function to calculate and place order
def calculate_and_place_order(symbol,old_delta):
    old_delta=float(old_delta)
    new_delta=float(information_for_options(client)[-2])
    contract_size=float(information_for_options(client)[-1])
    share_to_purchase = (new_delta - old_delta) * contract_size
    if share_to_purchase != 0:  # Only place an order if there's a change in delta
        if share_to_purchase < get_min_contract_size(symbol):
            print(f"Share to purchase too small: {share_to_purchase}")
        else:
            if new_delta > old_delta:
                side = "BUY"
            else:
                side = "SELL"
            create_hedging_order(symbol,side, abs(share_to_purchase))
    else:
        print(f"{datetime.now()}: No change in delta. No order placed.")

def update_time_index_balance_sheet(json_file_path):
    with open(json_file_path, 'r') as json_file:
        nested_bal_dict = json.load(json_file)
    balances=get_account_balances()
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    nested_bal_dict[current_timestamp]=balances
    print(len(nested_bal_dict))
    with open(json_file_path, 'w') as json_file:
        json.dump(nested_bal_dict, json_file, indent=4)
    




if __name__ == "__main__":
    
#     # When asks price of the OUT call (St - Ct): Ask > (St - Ct) || Ask < (St - Ct)
    
#     # Dp + Dc != 0
    # Information for options
    json_file_path = 'nested_dataframes.json'
    #display_balances(balances)
    client=deribit_set_up("test")
    expiry_datetime, share_to_purchase, symbol ,delta ,contract_size= information_for_options(client)
    #print(f"General Information: \nExpiry_Date : {expiry_datetime}, \nShare_to_purchase: {share_to_purchase}, \nDeribit symbol: {symbol}")
    symbol=symbol.split("-")[0]
    symbol=symbol+"USDT"
    symbol

    #print(f"Converting to Binance symbol: {symbol}")
    with open("old_delta.json", 'r') as file:

        data = json.load(file)
    old_delta = data
    
    def job():
        global old_delta
        update_time_index_balance_sheet(json_file_path)
        print("Performing delta look up")
        print(f"Calculating {symbol}'s delta")
        calculate_and_place_order(symbol,old_delta)
        old_delta=information_for_options(client)[-2]
        print(f"Updated old_delta to: {old_delta}")
        with open("old_delta.json", "w") as json_file:
            json.dump(old_delta, json_file)
    # Schedule the job every hour
    schedule.every(20).seconds.do(job)

    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(1)

    # Buy option
    # account = client.fetch_balance()
    # print(account)
    # x = client.create_order(symbol = symbol, type = "market", side = "buy", amount = 1)
    # print(x)
    # Start hedging
    # hedging_with_spot(share_to_purchase)
    

    

    
