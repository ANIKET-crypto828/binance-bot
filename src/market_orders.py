"""
Market Orders Module for Binance Futures Trading Bot
Executes immediate buy/sell orders at current market price
"""

import sys
import logging
from binance.exceptions import BinanceAPIException
from config import get_client, setup_logging
from utils import (
    validate_symbol, validate_quantity, validate_side,
    check_balance, format_order_response, ValidationError
)

logger = logging.getLogger(__name__)

def place_market_order(symbol: str, side: str, quantity: float) -> dict:
    """
    Place a market order on Binance Futures
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        side: 'BUY' or 'SELL'
        quantity: Amount to trade
        
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
        logger.info(f"Validating market order: {side} {quantity} {symbol}")
        side = validate_side(side)
        validate_symbol(client, symbol)
        quantity = validate_quantity(client, symbol, quantity)
        
        # Check balance
        balance = check_balance(client, 'USDT')
        logger.info(f"Available balance: {balance:.2f} USDT")
        
        # Place market order
        logger.info(f"Placing market order: {side} {quantity} {symbol}")
        
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        
        # Log success
        logger.info(f"Market order placed successfully!")
        logger.info(format_order_response(order))
        
        # Print to console
        print("\n✓ Market Order Executed Successfully!")
        print(format_order_response(order))
        
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

def main():
    """
    CLI entry point for market orders
    
    Usage:
        python market_orders.py SYMBOL SIDE QUANTITY
        
    Examples:
        python market_orders.py BTCUSDT BUY 0.01
        python market_orders.py ETHUSDT SELL 0.1
    """
    if len(sys.argv) != 4:
        print("\nUsage: python market_orders.py SYMBOL SIDE QUANTITY")
        print("\nExamples:")
        print("  python market_orders.py BTCUSDT BUY 0.01")
        print("  python market_orders.py ETHUSDT SELL 0.1")
        print("\nArguments:")
        print("  SYMBOL   - Trading pair (e.g., BTCUSDT)")
        print("  SIDE     - BUY or SELL")
        print("  QUANTITY - Amount to trade")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    side = sys.argv[2].upper()
    
    try:
        quantity = float(sys.argv[3])
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
    except ValueError as e:
        print(f"\n✗ Invalid quantity: {e}")
        sys.exit(1)
    
    try:
        logger.info("=" * 60)
        logger.info("MARKET ORDER REQUEST")
        logger.info(f"Symbol: {symbol} | Side: {side} | Quantity: {quantity}")
        logger.info("=" * 60)
        
        place_market_order(symbol, side, quantity)
        
    except KeyboardInterrupt:
        logger.info("Market order cancelled by user")
        print("\n\n✗ Order cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Market order failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()