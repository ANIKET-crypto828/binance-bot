"""
OCO (One-Cancels-the-Other) Orders Module for Binance Futures Trading Bot
Places take-profit and stop-loss orders simultaneously
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
    check_balance, get_current_price, validate_notional, ValidationError
)

logger = logging.getLogger(__name__)

def place_oco_order(symbol: str, side: str, quantity: float,
                    take_profit_price: float, stop_loss_price: float,
                    stop_limit_price: float) -> tuple:
    """
    Place OCO (One-Cancels-the-Other) order on Binance Futures
    
    OCO orders combine take-profit and stop-loss orders. When one executes,
    the other is automatically cancelled.
    
    Note: Binance Futures doesn't support native OCO orders, so this function
    simulates OCO by placing two separate orders and monitoring them.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        side: 'BUY' or 'SELL' (typically SELL for closing long positions)
        quantity: Amount to trade
        take_profit_price: Price for take-profit limit order
        stop_loss_price: Stop price for stop-loss order
        stop_limit_price: Limit price for stop-loss order
        
    Returns:
        tuple: (take_profit_order, stop_loss_order)
        
    Raises:
        ValidationError: If validation fails
        BinanceAPIException: If order placement fails
        
    Example:
        # After buying 0.01 BTC at $50,000:
        # Set take-profit at $52,000, stop-loss at $48,000
        place_oco_order('BTCUSDT', 'SELL', 0.01, 52000, 48000, 47500)
    """
    try:
        # Initialize client
        client = get_client()
        
        # Validate inputs
        logger.info(
            f"Validating OCO order: {side} {quantity} {symbol} | "
            f"TP={take_profit_price}, SL={stop_loss_price}"
        )
        
        side = validate_side(side)
        validate_symbol(client, symbol)
        quantity = validate_quantity(client, symbol, quantity)
        take_profit_price = validate_price(client, symbol, take_profit_price)
        stop_loss_price = validate_price(client, symbol, stop_loss_price)
        stop_limit_price = validate_price(client, symbol, stop_limit_price)
        
        # Validate notional values
        validate_notional(client, symbol, quantity, take_profit_price)
        validate_notional(client, symbol, quantity, stop_limit_price)
        
        # Get current market price
        current_price = get_current_price(client, symbol)
        logger.info(f"Current market price: {current_price}")
        
        # Validate price relationships
        if side == 'SELL':
            # For closing long positions
            if take_profit_price <= current_price:
                logger.warning(
                    f"Take-profit price {take_profit_price} is at or below "
                    f"current price {current_price}"
                )
            
            if stop_loss_price >= current_price:
                logger.warning(
                    f"Stop-loss price {stop_loss_price} is at or above "
                    f"current price {current_price}"
                )
            
            if stop_limit_price > stop_loss_price:
                raise ValidationError(
                    f"Stop-limit price ({stop_limit_price}) should be <= "
                    f"stop price ({stop_loss_price})"
                )
            
            if take_profit_price <= stop_loss_price:
                raise ValidationError(
                    f"Take-profit price ({take_profit_price}) must be > "
                    f"stop-loss price ({stop_loss_price})"
                )
        
        elif side == 'BUY':
            # For closing short positions
            if take_profit_price >= current_price:
                logger.warning(
                    f"Take-profit price {take_profit_price} is at or above "
                    f"current price {current_price}"
                )
            
            if stop_loss_price <= current_price:
                logger.warning(
                    f"Stop-loss price {stop_loss_price} is at or below "
                    f"current price {current_price}"
                )
            
            if stop_limit_price < stop_loss_price:
                raise ValidationError(
                    f"Stop-limit price ({stop_limit_price}) should be >= "
                    f"stop price ({stop_loss_price})"
                )
            
            if take_profit_price >= stop_loss_price:
                raise ValidationError(
                    f"Take-profit price ({take_profit_price}) must be < "
                    f"stop-loss price ({stop_loss_price})"
                )
        
        # Check balance
        balance = check_balance(client, 'USDT')
        logger.info(f"Available balance: {balance:.2f} USDT")
        
        # Place take-profit limit order
        logger.info(f"Placing take-profit order at {take_profit_price}")
        
        take_profit_order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=take_profit_price
        )
        
        logger.info(f"Take-profit order placed: ID={take_profit_order['orderId']}")
        
        # Place stop-loss order
        logger.info(f"Placing stop-loss order at {stop_loss_price}")
        
        try:
            stop_loss_order = client.futures_create_order(
                symbol=symbol,
                side=side,
                type='STOP',
                timeInForce='GTC',
                quantity=quantity,
                price=stop_limit_price,
                stopPrice=stop_loss_price
            )
            
            logger.info(f"Stop-loss order placed: ID={stop_loss_order['orderId']}")
            
        except Exception as e:
            # If stop-loss fails, cancel take-profit to maintain OCO integrity
            logger.error(f"Stop-loss order failed, cancelling take-profit: {e}")
            try:
                client.futures_cancel_order(
                    symbol=symbol,
                    orderId=take_profit_order['orderId']
                )
                logger.info("Take-profit order cancelled")
            except Exception as cancel_error:
                logger.error(f"Failed to cancel take-profit order: {cancel_error}")
            
            raise ValidationError(f"OCO order failed: {e}")
        
        # Log success
        logger.info("=" * 60)
        logger.info("OCO ORDER PLACED SUCCESSFULLY")
        logger.info(f"Take-Profit Order ID: {take_profit_order['orderId']}")
        logger.info(f"Stop-Loss Order ID: {stop_loss_order['orderId']}")
        logger.info("=" * 60)
        
        # Print to console
        print("\n✓ OCO Order Placed Successfully!")
        print("\n" + "=" * 60)
        print(f"Symbol: {symbol}")
        print(f"Side: {side}")
        print(f"Quantity: {quantity}")
        print(f"\nCurrent Price: {current_price}")
        print(f"Take-Profit Price: {take_profit_price}")
        print(f"Stop-Loss Price: {stop_loss_price}")
        print(f"Stop-Limit Price: {stop_limit_price}")
        print("\n" + "-" * 60)
        print(f"Take-Profit Order ID: {take_profit_order['orderId']}")
        print(f"Stop-Loss Order ID: {stop_loss_order['orderId']}")
        print("=" * 60)
        
        if side == 'SELL':
            profit_pct = ((take_profit_price - current_price) / current_price) * 100
            loss_pct = ((current_price - stop_loss_price) / current_price) * 100
            print(f"\nPotential Profit: +{profit_pct:.2f}%")
            print(f"Potential Loss: -{loss_pct:.2f}%")
            print(f"Risk/Reward Ratio: 1:{profit_pct/loss_pct:.2f}")
        
        print("\n⚠ Note: Monitor these orders. When one fills, manually cancel the other.")
        
        return take_profit_order, stop_loss_order
        
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

def monitor_oco_orders(symbol: str, tp_order_id: int, sl_order_id: int):
    """
    Monitor OCO orders and cancel the counterpart when one fills
    
    Args:
        symbol: Trading pair
        tp_order_id: Take-profit order ID
        sl_order_id: Stop-loss order ID
    """
    import time
    
    try:
        client = get_client()
        logger.info(f"Monitoring OCO orders: TP={tp_order_id}, SL={sl_order_id}")
        
        while True:
            # Check take-profit order
            tp_order = client.futures_get_order(symbol=symbol, orderId=tp_order_id)
            sl_order = client.futures_get_order(symbol=symbol, orderId=sl_order_id)
            
            if tp_order['status'] == 'FILLED':
                logger.info(f"Take-profit order filled! Cancelling stop-loss...")
                client.futures_cancel_order(symbol=symbol, orderId=sl_order_id)
                print("\n✓ Take-profit triggered! Stop-loss cancelled.")
                break
            
            if sl_order['status'] == 'FILLED':
                logger.info(f"Stop-loss order filled! Cancelling take-profit...")
                client.futures_cancel_order(symbol=symbol, orderId=tp_order_id)
                print("\n✗ Stop-loss triggered! Take-profit cancelled.")
                break
            
            time.sleep(1)  # Check every second
            
    except KeyboardInterrupt:
        logger.info("OCO monitoring stopped by user")
        print("\n\nMonitoring stopped. Orders still active.")
    except Exception as e:
        logger.error(f"Error monitoring OCO orders: {e}")

def main():
    """
    CLI entry point for OCO orders
    
    Usage:
        python oco.py SYMBOL SIDE QUANTITY TP_PRICE SL_PRICE SL_LIMIT_PRICE
        
    Examples:
        # Close long position with TP at $52k, SL at $48k
        python oco.py BTCUSDT SELL 0.01 52000 48000 47500
    """
    if len(sys.argv) != 7:
        print("\nUsage: python oco.py SYMBOL SIDE QUANTITY TP_PRICE SL_PRICE SL_LIMIT_PRICE")
        print("\nExample:")
        print("  # After buying BTC, set take-profit and stop-loss")
        print("  python oco.py BTCUSDT SELL 0.01 52000 48000 47500")
        print("\nArguments:")
        print("  SYMBOL          - Trading pair (e.g., BTCUSDT)")
        print("  SIDE            - BUY or SELL")
        print("  QUANTITY        - Amount to trade")
        print("  TP_PRICE        - Take-profit price")
        print("  SL_PRICE        - Stop-loss trigger price")
        print("  SL_LIMIT_PRICE  - Stop-loss limit price")
        print("\nTip: For long positions, use SELL side to close with profit/loss")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    side = sys.argv[2].upper()
    
    try:
        quantity = float(sys.argv[3])
        tp_price = float(sys.argv[4])
        sl_price = float(sys.argv[5])
        sl_limit_price = float(sys.argv[6])
        
        if any(x <= 0 for x in [quantity, tp_price, sl_price, sl_limit_price]):
            raise ValueError("All numeric values must be positive")
            
    except ValueError as e:
        print(f"\n✗ Invalid input: {e}")
        sys.exit(1)
    
    try:
        logger.info("=" * 60)
        logger.info("OCO ORDER REQUEST")
        logger.info(f"Symbol: {symbol} | Side: {side} | Quantity: {quantity}")
        logger.info(f"Take-Profit: {tp_price} | Stop-Loss: {sl_price}/{sl_limit_price}")
        logger.info("=" * 60)
        
        place_oco_order(symbol, side, quantity, tp_price, sl_price, sl_limit_price)
        
    except KeyboardInterrupt:
        logger.info("OCO order cancelled by user")
        print("\n\n✗ Order cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"OCO order failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()