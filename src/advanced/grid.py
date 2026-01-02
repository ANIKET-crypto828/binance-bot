"""
Grid Trading Strategy for Binance Futures Trading Bot
Automated buy-low/sell-high within a price range
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from binance.exceptions import BinanceAPIException
from config import get_client, setup_logging
from utils import (
    validate_symbol, validate_quantity, validate_price,
    check_balance, get_current_price, ValidationError
)

logger = logging.getLogger(__name__)

class GridTrader:
    """Execute grid trading strategy"""
    
    def __init__(self, client, symbol: str, lower_price: float, upper_price: float,
                 num_grids: int, quantity_per_grid: float):
        """
        Initialize grid trader
        
        Args:
            client: Binance client instance
            symbol: Trading pair
            lower_price: Lower bound of price range
            upper_price: Upper bound of price range
            num_grids: Number of grid levels
            quantity_per_grid: Quantity to trade at each level
        """
        self.client = client
        self.symbol = symbol
        self.lower_price = lower_price
        self.upper_price = upper_price
        self.num_grids = num_grids
        self.quantity_per_grid = quantity_per_grid
        
        self.grid_levels = []
        self.buy_orders = {}
        self.sell_orders = {}
        self.filled_buys = []
        self.filled_sells = []
        self.profit_realized = 0.0
        
    def calculate_grid_levels(self):
        """Calculate grid price levels"""
        if self.num_grids < 2:
            raise ValidationError("Need at least 2 grid levels")
        
        price_step = (self.upper_price - self.lower_price) / (self.num_grids - 1)
        
        self.grid_levels = [
            self.lower_price + (i * price_step)
            for i in range(self.num_grids)
        ]
        
        # Validate each price
        self.grid_levels = [
            validate_price(self.client, self.symbol, price)
            for price in self.grid_levels
        ]
        
        logger.info(f"Grid levels calculated: {len(self.grid_levels)} levels")
        logger.debug(f"Grid prices: {self.grid_levels}")
        
    def validate(self):
        """Validate grid parameters"""
        validate_symbol(self.client, self.symbol)
        
        if self.lower_price >= self.upper_price:
            raise ValidationError("Lower price must be less than upper price")
        
        # Validate quantity
        self.quantity_per_grid = validate_quantity(
            self.client, self.symbol, self.quantity_per_grid
        )
        
        # Calculate grid levels
        self.calculate_grid_levels()
        
        # Check balance
        current_price = get_current_price(self.client, self.symbol)
        buy_levels = [p for p in self.grid_levels if p <= current_price]
        
        estimated_cost = len(buy_levels) * self.quantity_per_grid * current_price
        balance = check_balance(self.client, 'USDT')
        
        if estimated_cost > balance:
            logger.warning(
                f"Estimated cost ({estimated_cost:.2f} USDT) exceeds balance "
                f"({balance:.2f} USDT). Some buy orders may fail."
            )
        
        logger.info("Grid parameters validated")
        
    def place_initial_orders(self):
        """Place initial grid orders"""
        current_price = get_current_price(self.client, self.symbol)
        
        logger.info(f"Current price: {current_price}")
        logger.info("Placing initial grid orders...")
        
        # Place buy orders below current price
        buy_count = 0
        for price in self.grid_levels:
            if price < current_price:
                try:
                    order = self.client.futures_create_order(
                        symbol=self.symbol,
                        side='BUY',
                        type='LIMIT',
                        timeInForce='GTC',
                        quantity=self.quantity_per_grid,
                        price=price
                    )
                    
                    self.buy_orders[price] = order
                    buy_count += 1
                    logger.info(f"Buy order placed at {price}: OrderID={order['orderId']}")
                    
                except BinanceAPIException as e:
                    logger.error(f"Failed to place buy order at {price}: {e}")
        
        # Place sell orders above current price
        sell_count = 0
        for price in self.grid_levels:
            if price > current_price:
                try:
                    order = self.client.futures_create_order(
                        symbol=self.symbol,
                        side='SELL',
                        type='LIMIT',
                        timeInForce='GTC',
                        quantity=self.quantity_per_grid,
                        price=price
                    )
                    
                    self.sell_orders[price] = order
                    sell_count += 1
                    logger.info(f"Sell order placed at {price}: OrderID={order['orderId']}")
                    
                except BinanceAPIException as e:
                    logger.error(f"Failed to place sell order at {price}: {e}")
        
        print(f"\n✓ Initial orders placed:")
        print(f"  Buy orders: {buy_count}")
        print(f"  Sell orders: {sell_count}")
        print(f"  Current price: {current_price}")
        
    def check_filled_orders(self):
        """Check for filled orders and replace them"""
        filled_orders = []
        
        # Check buy orders
        for price, order in list(self.buy_orders.items()):
            try:
                status = self.client.futures_get_order(
                    symbol=self.symbol,
                    orderId=order['orderId']
                )
                
                if status['status'] == 'FILLED':
                    filled_orders.append(('BUY', price, order))
                    del self.buy_orders[price]
                    self.filled_buys.append(order)
                    
            except BinanceAPIException as e:
                logger.error(f"Error checking buy order at {price}: {e}")
        
        # Check sell orders
        for price, order in list(self.sell_orders.items()):
            try:
                status = self.client.futures_get_order(
                    symbol=self.symbol,
                    orderId=order['orderId']
                )
                
                if status['status'] == 'FILLED':
                    filled_orders.append(('SELL', price, order))
                    del self.sell_orders[price]
                    self.filled_sells.append(order)
                    
            except BinanceAPIException as e:
                logger.error(f"Error checking sell order at {price}: {e}")
        
        # Replace filled orders
        for side, price, filled_order in filled_orders:
            self.handle_filled_order(side, price, filled_order)
        
        return len(filled_orders)
    
    def handle_filled_order(self, side: str, price: float, order: dict):
        """
        Handle filled order and place counterpart order
        
        Args:
            side: 'BUY' or 'SELL'
            price: Fill price
            order: Filled order details
        """
        logger.info(f"{side} order filled at {price}")
        print(f"\n✓ {side} order filled at {price}")
        
        try:
            if side == 'BUY':
                # Buy filled, place sell order at next grid level above
                sell_price = min([p for p in self.grid_levels if p > price])
                
                sell_order = self.client.futures_create_order(
                    symbol=self.symbol,
                    side='SELL',
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=self.quantity_per_grid,
                    price=sell_price
                )
                
                self.sell_orders[sell_price] = sell_order
                
                logger.info(f"Placed SELL order at {sell_price}")
                print(f"  → Placed SELL order at {sell_price}")
                
            else:  # SELL
                # Sell filled, place buy order at next grid level below
                buy_price = max([p for p in self.grid_levels if p < price])
                
                buy_order = self.client.futures_create_order(
                    symbol=self.symbol,
                    side='BUY',
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=self.quantity_per_grid,
                    price=buy_price
                )
                
                self.buy_orders[buy_price] = buy_order
                
                # Calculate profit
                profit = (price - buy_price) * self.quantity_per_grid
                self.profit_realized += profit
                
                logger.info(f"Placed BUY order at {buy_price}, Profit: {profit:.2f}")
                print(f"  → Placed BUY order at {buy_price}")
                print(f"  💰 Profit: {profit:.2f} USDT")
                
        except BinanceAPIException as e:
            logger.error(f"Failed to place counterpart order: {e}")
            print(f"  ✗ Failed to place counterpart order: {e}")
    
    def display_status(self):
        """Display current grid status"""
        current_price = get_current_price(self.client, self.symbol)
        
        print("\n" + "=" * 60)
        print(f"Grid Status - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        print(f"Symbol: {self.symbol}")
        print(f"Current Price: {current_price}")
        print(f"Grid Range: {self.lower_price} - {self.upper_price}")
        print(f"\nActive Orders:")
        print(f"  Buy orders: {len(self.buy_orders)}")
        print(f"  Sell orders: {len(self.sell_orders)}")
        print(f"\nExecution Stats:")
        print(f"  Buys filled: {len(self.filled_buys)}")
        print(f"  Sells filled: {len(self.filled_sells)}")
        print(f"  Realized profit: {self.profit_realized:.2f} USDT")
        print("=" * 60)
    
    def run(self, check_interval: int = 5):
        """
        Run grid trading strategy
        
        Args:
            check_interval: Seconds between order checks
        """
        try:
            # Validation
            logger.info("=" * 60)
            logger.info("STARTING GRID TRADING")
            logger.info(f"Symbol: {self.symbol}")
            logger.info(f"Price Range: {self.lower_price} - {self.upper_price}")
            logger.info(f"Grid Levels: {self.num_grids}")
            logger.info(f"Quantity per Grid: {self.quantity_per_grid}")
            logger.info("=" * 60)
            
            self.validate()
            
            # Display grid plan
            print("\n" + "=" * 60)
            print("GRID TRADING SETUP")
            print("=" * 60)
            print(f"Symbol: {self.symbol}")
            print(f"Price Range: {self.lower_price} - {self.upper_price}")
            print(f"Grid Levels: {self.num_grids}")
            print(f"Quantity per Grid: {self.quantity_per_grid}")
            print(f"\nGrid Prices:")
            for i, price in enumerate(self.grid_levels, 1):
                print(f"  Level {i:2d}: {price}")
            print("=" * 60)
            
            input("\nPress ENTER to start grid trading (or Ctrl+C to cancel)...")
            
            # Place initial orders
            self.place_initial_orders()
            
            print("\n🔄 Grid trading active. Press Ctrl+C to stop.")
            print(f"   Checking orders every {check_interval} seconds...\n")
            
            # Main loop
            iteration = 0
            while True:
                time.sleep(check_interval)
                iteration += 1
                
                filled_count = self.check_filled_orders()
                
                # Display status periodically
                if iteration % 12 == 0:  # Every minute with 5s interval
                    self.display_status()
                
        except KeyboardInterrupt:
            logger.info("Grid trading stopped by user")
            print("\n\n⏸ Grid trading stopped")
            self.cleanup()
            
        except Exception as e:
            logger.error(f"Grid trading error: {e}", exc_info=True)
            print(f"\n✗ Error: {e}")
            self.cleanup()
            raise
    
    def cleanup(self):
        """Cancel all active orders"""
        print("\n🧹 Cancelling active orders...")
        
        cancelled = 0
        
        # Cancel buy orders
        for price, order in self.buy_orders.items():
            try:
                self.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=order['orderId']
                )
                cancelled += 1
                logger.info(f"Cancelled buy order at {price}")
            except Exception as e:
                logger.error(f"Failed to cancel buy order at {price}: {e}")
        
        # Cancel sell orders
        for price, order in self.sell_orders.items():
            try:
                self.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=order['orderId']
                )
                cancelled += 1
                logger.info(f"Cancelled sell order at {price}")
            except Exception as e:
                logger.error(f"Failed to cancel sell order at {price}: {e}")
        
        print(f"✓ Cancelled {cancelled} orders")
        self.display_status()

def main():
    """CLI entry point for grid trading"""
    parser = argparse.ArgumentParser(
        description='Execute Grid Trading strategy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Grid trade BTC between $48k-$52k with 10 levels
  python grid.py BTCUSDT 48000 52000 --grids 10 --quantity 0.01

  # Grid trade ETH with 5 levels
  python grid.py ETHUSDT 2800 3200 --grids 5 --quantity 0.1
        """
    )
    
    parser.add_argument('symbol', type=str, help='Trading pair (e.g., BTCUSDT)')
    parser.add_argument('lower_price', type=float, help='Lower price bound')
    parser.add_argument('upper_price', type=float, help='Upper price bound')
    parser.add_argument('--grids', type=int, default=10,
                       help='Number of grid levels (default: 10)')
    parser.add_argument('--quantity', type=float, required=True,
                       help='Quantity per grid level')
    parser.add_argument('--interval', type=int, default=5,
                       help='Check interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    # Validation
    if args.lower_price >= args.upper_price:
        print("✗ Error: Lower price must be less than upper price")
        sys.exit(1)
    
    if args.grids < 2:
        print("✗ Error: Need at least 2 grid levels")
        sys.exit(1)
    
    if args.quantity <= 0:
        print("✗ Error: Quantity must be positive")
        sys.exit(1)
    
    try:
        client = get_client()
        trader = GridTrader(
            client=client,
            symbol=args.symbol.upper(),
            lower_price=args.lower_price,
            upper_price=args.upper_price,
            num_grids=args.grids,
            quantity_per_grid=args.quantity
        )
        
        trader.run(check_interval=args.interval)
        
    except KeyboardInterrupt:
        print("\n\nGrid trading stopped")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Grid trading failed: {e}")
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()