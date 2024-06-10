"""
A call option is OTM if the underlying price is trading below the strike price of the call. A put option is OTM if the underlying's price is above the put's strike price.
"""
import ccxt
from infor_before_trade import information_for_options
import requests

mode = "test"

client_id_testnet = "kXV7l7Pe"
client_secret_testnet = "cnvhFL3uFdU4YQvlSj6TR7KtbHZWg_g5YYt4rn-WkTw"

client_id_realnet = "VUSrWKNX"
client_secret_realnet = "CNIEmjiKy2p-h28O4Mda1QKD8hXJ3duA5rAODdLfvwE"

if mode == "test":
    client_id = client_id_testnet
    client_secret = client_secret_testnet
else:
    client_id = client_id_realnet
    client_secret = client_secret_realnet

# Base URL for Deribit API
base_url = 'https://www.deribit.com/api/v2/'

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
    
client = ccxt.deribit({
    'clientId': client_id,
    'clientSecret': client_secret,
    'timeout': 50000,
})


# def hedging_with_spot(symbol = share_to_purchase, type = order_type, side = side, amount = share_to_purchase, price = price):
    # def create_order(self, symbol: str, type: OrderType, side: OrderSide, amount: float, price: Num = None, params={}):



if __name__ == "__main__":
    
#     # When asks price of the OUT call (St - Ct): Ask > (St - Ct) || Ask < (St - Ct)
    
#     # Dp + Dc != 0
    # Information for options
    # expiry_datetime, share_to_purchase, symbol = information_for_options(client)
    access_token = get_access_token(client_id, client_secret)
    account_info = fetch_account_info(access_token)
    print(account_info)

    # Buy option
    # account = client.fetch_balance()
    # print(account)
    # x = client.create_order(symbol = symbol, type = "market", side = "buy", amount = 1)
    # print(x)
    # Start hedging
    # hedging_with_spot(share_to_purchase)
    

    

    
