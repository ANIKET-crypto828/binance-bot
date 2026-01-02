"""
Stop-Limit Orders Module for Binance Futures Trading Bot
Triggers a limit order when stop price is reached
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from binance.exceptions import BinanceAPIException
from config import get_client, setup_logging
from utils import (
    validate_symbol, validate_quantity, validate_price, validate_side,
    check_balance, format_order_response, get_current_price,
    validate_notional, ValidationError
)

logger = logging.getLogger(__name__)

def place_stop_limit_order(symbol: str, side: str, quantity: float, 
                           stop_price: float, limit_price: float,
                           time_in_force: str = 'GTC') -> dict:
    """
    Place a stop-limit order on Binance Futures
    
    Stop-limit orders trigger a limit order when the stop price is reached.
    - For SELL orders: Triggers when price drops to stop_price (stop-loss)
    - For BUY orders: Triggers when price rises to stop_price (stop-buy)
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        side: 'BUY' or 'SELL'
        quantity: Amount to trade
        stop_price: Price that triggers the limit order
        limit_price: Limit price for the triggered order
        time_in_force: Order time in force (GTC, IOC, FOK)
        
    Returns:
        dict: Order response from Binance API
        
    Raises:
        ValidationError: If validation fails
        BinanceAPIException: If order placement fails
        
    Example:
        # Stop-loss: Sell if price drops to $48,000, limit at $47,500
        place_stop_limit_order('BTCUSDT', 'SELL', 0.01, 48000, 47500)
        
        # Stop-buy: Buy if price rises to $52,000, limit at $52,500
        place_stop_limit_order('BTCUSDT', 'BUY', 0.01, 52000, 52500)
    """
    try:
        # Initialize client
        client = get_client()
        
        # Validate inputs
        logger.info(
            f"Validating stop-limit order: {side} {quantity} {symbol} "
            f"@ stop={stop_price}, limit={limit_price}"
        )
        
        side = validate_side(side)
        validate_symbol(client, symbol)
        quantity = validate_quantity(client, symbol, quantity)
        stop_price = validate_price(client, symbol, stop_price)
        limit_price = validate_price(client, symbol, limit_price)
        
        # Validate notional value
        validate_notional(client, symbol, quantity, limit_price)
        
        # Get current market price
        current_price = get_current_price(client, symbol)
        logger.info(f"Current market price: {current_price}")
        
        # Validate stop-limit price relationship
        if side == 'SELL':
            # Stop-loss: stop_price should be below current, limit below stop
            if stop_price >= current_price:
                logger.warning(
                    f"Stop-loss order: stop price {stop_price} is above or equal to "
                    f"current price {current_price}. Order will trigger immediately."
                )
            
            if limit_price > stop_price:
                raise ValidationError(
                    f"For SELL stop-limit: limit price ({limit_price}) should be "
                    f"<= stop price ({stop_price})"
                )
        
        elif side == 'BUY':
            # Stop-buy: stop_price should be above current, limit above stop
            if stop_price <= current_price:
                logger.warning(
                    f"Stop-buy order: stop price {stop_price} is below or equal to "
                    f"current price {current_price}. Order will trigger immediately."
                )
            
            if limit_price < stop_price:
                raise ValidationError(
                    f"For BUY stop-limit: limit price ({limit_price}) should be "
                    f">= stop price ({stop_price})"
                )
        
        # Check balance
        balance = check_balance(client, 'USDT')
        estimated_cost = quantity * limit_price if side == 'BUY' else 0
        
        if side == 'BUY' and estimated_cost > balance:
            raise ValidationError(
                f"Insufficient balance. Required: {estimated_cost:.2f} USDT, "
                f"Available: {balance:.2f} USDT"
            )
        
        # Place stop-limit order
        logger.info(
            f"Placing stop-limit order: {side} {quantity} {symbol} "
            f"@ stop={stop_price}, limit={limit_price}"
        )
        
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='STOP',
            timeInForce=time_in_force,
            quantity=quantity,
            price=limit_price,
            stopPrice=stop_price
        )
        
        # Log success
        logger.info(f"Stop-limit order placed successfully!")
        logger.info(format_order_response(order))
        
        # Print to console
        print("\n✓ Stop-Limit Order Placed Successfully!")
        print(format_order_response(order))
        print(f"\nCurrent Market Price: {current_price}")
        print(f"Stop Price: {stop_price}")
        print(f"Limit Price: {limit_price}")
        
        if side == 'SELL':
            print(f"\n⚠ Stop-Loss: Will trigger SELL if price drops to {stop_price}")
        else:
            print(f"\n⚠ Stop-Buy: Will trigger BUY if price rises to {stop_price}")
        
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
    CLI entry point for stop-limit orders
    
    Usage:
        python stop_limit.py SYMBOL SIDE QUANTITY STOP_PRICE LIMIT_PRICE [TIME_IN_FORCE]
        
    Examples:
        # Stop-loss: Sell if price drops to $48,000, limit at $47,500
        python stop_limit.py BTCUSDT SELL 0.01 48000 47500
        
        # Stop-buy: Buy if price rises to $52,000, limit at $52,500
        python stop_limit.py BTCUSDT BUY 0.01 52000 52500
    """
    if len(sys.argv) < 6:
        print("\nUsage: python stop_limit.py SYMBOL SIDE QUANTITY STOP_PRICE LIMIT_PRICE [TIME_IN_FORCE]")
        print("\nExamples:")
        print("  # Stop-loss example")
        print("  python stop_limit.py BTCUSDT SELL 0.01 48000 47500")
        print("\n  # Stop-buy example")
        print("  python stop_limit.py BTCUSDT BUY 0.01 52000 52500")
        print("\nArguments:")
        print("  SYMBOL        - Trading pair (e.g., BTCUSDT)")
        print("  SIDE          - BUY or SELL")
        print("  QUANTITY      - Amount to trade")
        print("  STOP_PRICE    - Price that triggers the order")
        print("  LIMIT_PRICE   - Limit price after trigger")
        print("  TIME_IN_FORCE - (Optional) GTC, IOC, or FOK (default: GTC)")
        print("\nUse Cases:")
        print("  SELL - Stop-loss protection (triggers when price falls)")
        print("  BUY  - Stop-buy entry (triggers when price rises)")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    side = sys.argv[2].upper()
    time_in_force = sys.argv[6].upper() if len(sys.argv) > 6 else 'GTC'
    
    try:
        quantity = float(sys.argv[3])
        stop_price = float(sys.argv[4])
        limit_price = float(sys.argv[5])
        
        if quantity <= 0 or stop_price <= 0 or limit_price <= 0:
            raise ValueError("All numeric values must be positive")
            
    except ValueError as e:
        print(f"\n✗ Invalid input: {e}")
        sys.exit(1)
    
    try:
        logger.info("=" * 60)
        logger.info("STOP-LIMIT ORDER REQUEST")
        logger.info(
            f"Symbol: {symbol} | Side: {side} | Quantity: {quantity} | "
            f"Stop: {stop_price} | Limit: {limit_price}"
        )
        logger.info(f"Time In Force: {time_in_force}")
        logger.info("=" * 60)
        
        place_stop_limit_order(symbol, side, quantity, stop_price, limit_price, time_in_force)
        
    except KeyboardInterrupt:
        logger.info("Stop-limit order cancelled by user")
        print("\n\n✗ Order cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Stop-limit order failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()