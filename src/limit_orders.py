"""
Limit Orders Module for Binance Futures Trading Bot
Places orders at specific price levels
"""

import sys
import logging
from binance.exceptions import BinanceAPIException
from config import get_client, setup_logging
from utils import (
    validate_symbol, validate_quantity, validate_price, validate_side,
    check_balance, format_order_response, get_current_price, 
    validate_notional, ValidationError
)

logger = logging.getLogger(__name__)

def place_limit_order(symbol: str, side: str, quantity: float, price: float, 
                      time_in_force: str = 'GTC') -> dict:
    """
    Place a limit order on Binance Futures
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        side: 'BUY' or 'SELL'
        quantity: Amount to trade
        price: Limit price
        time_in_force: Order time in force (GTC, IOC, FOK)
        
    Returns:
        dict: Order response from Binance API
        
    Raises:
        ValidationError: If validation fails
        BinanceAPIException: If order placement fails
    """
    try:
        # Initialize client
        client = get_client()
        
        # Validate inputs
        logger.info(f"Validating limit order: {side} {quantity} {symbol} @ {price}")
        side = validate_side(side)
        validate_symbol(client, symbol)
        quantity = validate_quantity(client, symbol, quantity)
        price = validate_price(client, symbol, price)
        
        # Validate notional value
        validate_notional(client, symbol, quantity, price)
        
        # Get current market price for comparison
        current_price = get_current_price(client, symbol)
        logger.info(f"Current market price: {current_price}")
        
        # Warn if limit price is far from market
        price_diff_pct = abs((price - current_price) / current_price * 100)
        if price_diff_pct > 5:
            logger.warning(
                f"Limit price {price} is {price_diff_pct:.2f}% away from "
                f"market price {current_price}"
            )
        
        # Check balance
        balance = check_balance(client, 'USDT')
        estimated_cost = quantity * price if side == 'BUY' else 0
        
        if side == 'BUY' and estimated_cost > balance:
            raise ValidationError(
                f"Insufficient balance. Required: {estimated_cost:.2f} USDT, "
                f"Available: {balance:.2f} USDT"
            )
        
        logger.info(f"Available balance: {balance:.2f} USDT")
        
        # Place limit order
        logger.info(f"Placing limit order: {side} {quantity} {symbol} @ {price}")
        
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='LIMIT',
            timeInForce=time_in_force,
            quantity=quantity,
            price=price
        )
        
        # Log success
        logger.info(f"Limit order placed successfully!")
        logger.info(format_order_response(order))
        
        # Print to console
        print("\n✓ Limit Order Placed Successfully!")
        print(format_order_response(order))
        print(f"\nCurrent Market Price: {current_price}")
        print(f"Your Limit Price: {price}")
        print(f"Difference: {price_diff_pct:.2f}%")
        
        return order
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        print(f"\n✗ Validation Error: {e}")
        raise
        
    except BinanceAPIException as e:
        logger.error(f"Binance API error: {e}")
        print(f"\n✗ Order Failed: {e}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n✗ Unexpected Error: {e}")
        raise

def check_order_status(order_id: int, symbol: str) -> dict:
    """
    Check the status of a limit order
    
    Args:
        order_id: Order ID to check
        symbol: Trading pair
        
    Returns:
        dict: Order status information
    """
    try:
        client = get_client()
        order = client.futures_get_order(symbol=symbol, orderId=order_id)
        
        logger.info(f"Order status: {order['status']}")
        return order
        
    except BinanceAPIException as e:
        logger.error(f"Failed to get order status: {e}")
        raise

def cancel_limit_order(order_id: int, symbol: str) -> dict:
    """
    Cancel a pending limit order
    
    Args:
        order_id: Order ID to cancel
        symbol: Trading pair
        
    Returns:
        dict: Cancellation response
    """
    try:
        client = get_client()
        result = client.futures_cancel_order(symbol=symbol, orderId=order_id)
        
        logger.info(f"Order {order_id} cancelled successfully")
        print(f"\n✓ Order {order_id} cancelled successfully")
        
        return result
        
    except BinanceAPIException as e:
        logger.error(f"Failed to cancel order: {e}")
        print(f"\n✗ Cancellation Failed: {e}")
        raise

def main():
    """
    CLI entry point for limit orders
    
    Usage:
        python limit_orders.py SYMBOL SIDE QUANTITY PRICE [TIME_IN_FORCE]
        
    Examples:
        python limit_orders.py BTCUSDT BUY 0.01 50000
        python limit_orders.py ETHUSDT SELL 0.1 3000 IOC
    """
    if len(sys.argv) < 5:
        print("\nUsage: python limit_orders.py SYMBOL SIDE QUANTITY PRICE [TIME_IN_FORCE]")
        print("\nExamples:")
        print("  python limit_orders.py BTCUSDT BUY 0.01 50000")
        print("  python limit_orders.py ETHUSDT SELL 0.1 3000 IOC")
        print("\nArguments:")
        print("  SYMBOL        - Trading pair (e.g., BTCUSDT)")
        print("  SIDE          - BUY or SELL")
        print("  QUANTITY      - Amount to trade")
        print("  PRICE         - Limit price")
        print("  TIME_IN_FORCE - (Optional) GTC, IOC, or FOK (default: GTC)")
        print("\nTime In Force:")
        print("  GTC - Good Till Cancel (default)")
        print("  IOC - Immediate or Cancel")
        print("  FOK - Fill or Kill")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    side = sys.argv[2].upper()
    time_in_force = sys.argv[5].upper() if len(sys.argv) > 5 else 'GTC'
    
    try:
        quantity = float(sys.argv[3])
        price = float(sys.argv[4])
        
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be positive")
            
    except ValueError as e:
        print(f"\n✗ Invalid input: {e}")
        sys.exit(1)
    
    try:
        logger.info("=" * 60)
        logger.info("LIMIT ORDER REQUEST")
        logger.info(f"Symbol: {symbol} | Side: {side} | Quantity: {quantity} | Price: {price}")
        logger.info(f"Time In Force: {time_in_force}")
        logger.info("=" * 60)
        
        place_limit_order(symbol, side, quantity, price, time_in_force)
        
    except KeyboardInterrupt:
        logger.info("Limit order cancelled by user")
        print("\n\n✗ Order cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Limit order failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()