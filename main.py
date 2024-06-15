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


mode = "test"
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


# Function to get access token
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
    
client = ccxt.deribit({
    'apiKey': client_id,
    'secret': client_secret,
    'timeout': 50000,
})
if mode=="test":
    client.set_sandbox_mode(True)

#Function 
def create_signature(query_string, secret_key):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

# Function to get all open orders from Binance Spot Testnet
def get_all_open_orders():
    api_key = 'dIgzgeXGUjuNi81pWAZAzHt1zkYcfoN4QM0oasQsVkJQmoqdkC7dilNLiETRheyU'
    api_secret = 'ZxiMdpOSzIirGkhnkEBJsNHZ92okUqBwSulFIKKeHSLbLdlPkjWN9lMx5lsJn79g'
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
def get_all_past_orders(symbol, start_time=None, end_time=None, limit=500):
    """Retrieve all past orders for a given symbol on Binance Spot Testnet."""
    base_url = 'https://testnet.binance.vision'
    endpoint = '/api/v3/allOrders'
    timestamp = int(time.time() * 1000)
    api_key = 'dIgzgeXGUjuNi81pWAZAzHt1zkYcfoN4QM0oasQsVkJQmoqdkC7dilNLiETRheyU'
    api_secret = 'ZxiMdpOSzIirGkhnkEBJsNHZ92okUqBwSulFIKKeHSLbLdlPkjWN9lMx5lsJn79g'    
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


def create_hedging_order(symbol, side,share_to_purchase):

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
      
        #print(client.get_symbol_info(symbol))        
        order = None
    
    return order

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


    
# def hedging_with_spot(symbol = share_to_purchase, type = order_type, side = side, amount = share_to_purchase, price = price):
    # def create_order(self, symbol: str, type: OrderType, side: OrderSide, amount: float, price: Num = None, params={}):



if __name__ == "__main__":
    
#     # When asks price of the OUT call (St - Ct): Ask > (St - Ct) || Ask < (St - Ct)
    
#     # Dp + Dc != 0
    # Information for options
    

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
        print("Performing delta look up")
        print(f"Calculating {symbol}'s delta")
        calculate_and_place_order(symbol,old_delta)
        old_delta=information_for_options(client)[-2]
        print(f"Updated old_delta to: {old_delta}")
        with open("old_delta.json", "w") as json_file:
            json.dump(old_delta, json_file)
    # Schedule the job every hour
    schedule.every(10).seconds.do(job)

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
    

    

    
