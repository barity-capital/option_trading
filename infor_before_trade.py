from datetime import datetime, timedelta
import json

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


    return expiry_datetime, share_to_purchase, symbol ,delta