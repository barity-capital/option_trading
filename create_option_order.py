from infor_before_trade import information_for_options


def create_option_order(symbol, market_type, quantity, side):
    """
    Create an order for an option trade.

    Parameters:
    symbol (str): The symbol for the option.
    market_type (str): The type of market (e.g., 'market').
    quantity (int): The quantity of the option to trade.
    side (str): The side of the trade ('buy' or 'sell').

    Returns:
    dict: Details of the created order.
    """
    try:
        # Assuming information_for_option is a function that retrieves necessary data for the order
        option_info = information_for_options(symbol)
        
        # Construct the order
        order = {
            'symbol': symbol,
            'market_type': market_type,
            'quantity': quantity,
            'side': side,
            'option_details': option_info  # Including details retrieved from the function
        }


        print(f"Order created successfully: {order}")
        return order
    
    except Exception as e:
        print(f"Failed to create order: {e}")
        return None

# Example usage
