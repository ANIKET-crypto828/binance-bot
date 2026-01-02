"""
Utility functions and validators for Binance Futures Trading Bot
Includes input validation, formatting, and helper functions
"""

import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Dict, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_symbol(client: Client, symbol: str) -> bool:
    """
    Validate that symbol exists and is tradeable
    
    Args:
        client: Binance client instance
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        
    Returns:
        bool: True if valid
        
    Raises:
        ValidationError: If symbol is invalid
    """
    try:
        exchange_info = client.futures_exchange_info()
        symbols = [s['symbol'] for s in exchange_info['symbols']]
        
        if symbol not in symbols:
            raise ValidationError(
                f"Invalid symbol: {symbol}. Symbol not found on Binance Futures."
            )
        
        # Check if symbol is trading
        symbol_info = next(s for s in exchange_info['symbols'] if s['symbol'] == symbol)
        if symbol_info['status'] != 'TRADING':
            raise ValidationError(
                f"Symbol {symbol} is not currently trading (status: {symbol_info['status']})"
            )
        
        logger.info(f"Symbol validation passed: {symbol}")
        return True
        
    except BinanceAPIException as e:
        logger.error(f"API error during symbol validation: {e}")
        raise ValidationError(f"Failed to validate symbol: {e}")

def get_symbol_info(client: Client, symbol: str) -> Dict[str, Any]:
    """
    Get detailed information about a symbol
    
    Args:
        client: Binance client instance
        symbol: Trading pair symbol
        
    Returns:
        dict: Symbol information including filters
    """
    try:
        exchange_info = client.futures_exchange_info()
        symbol_info = next(
            (s for s in exchange_info['symbols'] if s['symbol'] == symbol),
            None
        )
        
        if not symbol_info:
            raise ValidationError(f"Symbol {symbol} not found")
        
        return symbol_info
        
    except BinanceAPIException as e:
        logger.error(f"Failed to get symbol info: {e}")
        raise

def validate_quantity(client: Client, symbol: str, quantity: float) -> float:
    """
    Validate and adjust quantity according to symbol filters
    
    Args:
        client: Binance client instance
        symbol: Trading pair symbol
        quantity: Order quantity
        
    Returns:
        float: Validated and adjusted quantity
        
    Raises:
        ValidationError: If quantity is invalid
    """
    try:
        symbol_info = get_symbol_info(client, symbol)
        
        # Get LOT_SIZE filter
        lot_size_filter = next(
            f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'
        )
        
        min_qty = float(lot_size_filter['minQty'])
        max_qty = float(lot_size_filter['maxQty'])
        step_size = float(lot_size_filter['stepSize'])
        
        # Validate range
        if quantity < min_qty:
            raise ValidationError(
                f"Quantity {quantity} is below minimum {min_qty} for {symbol}"
            )
        
        if quantity > max_qty:
            raise ValidationError(
                f"Quantity {quantity} exceeds maximum {max_qty} for {symbol}"
            )
        
        # Adjust to step size
        precision = len(str(step_size).rstrip('0').split('.')[-1])
        adjusted_qty = round(quantity - (quantity % step_size), precision)
        
        if adjusted_qty != quantity:
            logger.warning(
                f"Quantity adjusted from {quantity} to {adjusted_qty} "
                f"to match step size {step_size}"
            )
        
        logger.info(f"Quantity validation passed: {adjusted_qty} {symbol}")
        return adjusted_qty
        
    except (StopIteration, KeyError) as e:
        logger.error(f"Failed to validate quantity: {e}")
        raise ValidationError(f"Could not find required filters for {symbol}")

def validate_price(client: Client, symbol: str, price: float) -> float:
    """
    Validate and adjust price according to symbol filters
    
    Args:
        client: Binance client instance
        symbol: Trading pair symbol
        price: Order price
        
    Returns:
        float: Validated and adjusted price
        
    Raises:
        ValidationError: If price is invalid
    """
    try:
        symbol_info = get_symbol_info(client, symbol)
        
        # Get PRICE_FILTER
        price_filter = next(
            f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'
        )
        
        min_price = float(price_filter['minPrice'])
        max_price = float(price_filter['maxPrice'])
        tick_size = float(price_filter['tickSize'])
        
        # Validate range
        if price < min_price:
            raise ValidationError(
                f"Price {price} is below minimum {min_price} for {symbol}"
            )
        
        if price > max_price:
            raise ValidationError(
                f"Price {price} exceeds maximum {max_price} for {symbol}"
            )
        
        # Adjust to tick size
        precision = len(str(tick_size).rstrip('0').split('.')[-1])
        adjusted_price = round(price - (price % tick_size), precision)
        
        if adjusted_price != price:
            logger.warning(
                f"Price adjusted from {price} to {adjusted_price} "
                f"to match tick size {tick_size}"
            )
        
        logger.info(f"Price validation passed: {adjusted_price} for {symbol}")
        return adjusted_price
        
    except (StopIteration, KeyError) as e:
        logger.error(f"Failed to validate price: {e}")
        raise ValidationError(f"Could not find required filters for {symbol}")

def validate_side(side: str) -> str:
    """
    Validate order side
    
    Args:
        side: Order side ('BUY' or 'SELL')
        
    Returns:
        str: Uppercase validated side
        
    Raises:
        ValidationError: If side is invalid
    """
    side = side.upper()
    if side not in ['BUY', 'SELL']:
        raise ValidationError(
            f"Invalid side: {side}. Must be 'BUY' or 'SELL'"
        )
    return side

def get_current_price(client: Client, symbol: str) -> float:
    """
    Get current market price for a symbol
    
    Args:
        client: Binance client instance
        symbol: Trading pair symbol
        
    Returns:
        float: Current market price
    """
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
        logger.debug(f"Current price for {symbol}: {price}")
        return price
        
    except BinanceAPIException as e:
        logger.error(f"Failed to get current price: {e}")
        raise

def check_balance(client: Client, asset: str = 'USDT') -> float:
    """
    Check available balance for an asset
    
    Args:
        client: Binance client instance
        asset: Asset to check (default: 'USDT')
        
    Returns:
        float: Available balance
    """
    try:
        account = client.futures_account()
        balance = next(
            (float(b['availableBalance']) for b in account['assets'] if b['asset'] == asset),
            0.0
        )
        logger.info(f"Available {asset} balance: {balance}")
        return balance
        
    except BinanceAPIException as e:
        logger.error(f"Failed to check balance: {e}")
        raise

def format_order_response(order: Dict[str, Any]) -> str:
    """
    Format order response for logging and display
    
    Args:
        order: Order response from Binance API
        
    Returns:
        str: Formatted order information
    """
    return (
        f"\n{'='*60}\n"
        f"Order ID: {order.get('orderId')}\n"
        f"Symbol: {order.get('symbol')}\n"
        f"Side: {order.get('side')}\n"
        f"Type: {order.get('type')}\n"
        f"Quantity: {order.get('origQty')}\n"
        f"Price: {order.get('price', 'MARKET')}\n"
        f"Status: {order.get('status')}\n"
        f"Time: {order.get('updateTime')}\n"
        f"{'='*60}"
    )

def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0):
    """
    Retry decorator for API calls
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Function result or raises last exception
    """
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except BinanceAPIException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(delay * (attempt + 1))
        return None
    return wrapper

def calculate_notional_value(quantity: float, price: float) -> float:
    """
    Calculate notional value of an order
    
    Args:
        quantity: Order quantity
        price: Order price
        
    Returns:
        float: Notional value (quantity * price)
    """
    return quantity * price

def validate_notional(client: Client, symbol: str, quantity: float, price: float) -> bool:
    """
    Validate that order meets minimum notional value
    
    Args:
        client: Binance client instance
        symbol: Trading pair symbol
        quantity: Order quantity
        price: Order price
        
    Returns:
        bool: True if valid
        
    Raises:
        ValidationError: If notional value is too low
    """
    try:
        symbol_info = get_symbol_info(client, symbol)
        
        # Get MIN_NOTIONAL filter
        min_notional_filter = next(
            (f for f in symbol_info['filters'] if f['filterType'] == 'MIN_NOTIONAL'),
            None
        )
        
        if min_notional_filter:
            min_notional = float(min_notional_filter['notional'])
            notional_value = calculate_notional_value(quantity, price)
            
            if notional_value < min_notional:
                raise ValidationError(
                    f"Order value {notional_value:.2f} USDT is below minimum "
                    f"{min_notional:.2f} USDT for {symbol}"
                )
        
        logger.info(f"Notional value validation passed for {symbol}")
        return True
        
    except StopIteration:
        logger.warning(f"No MIN_NOTIONAL filter found for {symbol}")
        return True