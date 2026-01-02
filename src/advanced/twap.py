"""
TWAP (Time-Weighted Average Price) Strategy for Binance Futures Trading Bot
Splits large orders into smaller chunks executed over time
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from binance.exceptions import BinanceAPIException
from config import get_client, setup_logging
from utils import (
    validate_symbol, validate_quantity, validate_side,
    check_balance, get_current_price, ValidationError
)

logger = logging.getLogger(__name__)

class TWAPExecutor:
    """Execute TWAP strategy for large orders"""
    
    def __init__(self, client, symbol: str, side: str, total_quantity: float,
                 num_chunks: int, interval_seconds: int):
        """
        Initialize TWAP executor
        
        Args:
            client: Binance client instance
            symbol: Trading pair
            side: BUY or SELL
            total_quantity: Total amount to trade
            num_chunks: Number of smaller orders
            interval_seconds: Time between orders
        """
        self.client = client
        self.symbol = symbol
        self.side = side
        self.total_quantity = total_quantity
        self.num_chunks = num_chunks
        self.interval_seconds = interval_seconds
        self.chunk_size = total_quantity / num_chunks
        self.executed_orders = []
        self.failed_orders = []
        
    def validate(self):
        """Validate TWAP parameters"""
        validate_symbol(self.client, self.symbol)
        self.side = validate_side(self.side)
        
        # Validate chunk size
        self.chunk_size = validate_quantity(self.client, self.symbol, self.chunk_size)
        
        # Recalculate total based on adjusted chunk size
        self.total_quantity = self.chunk_size * self.num_chunks
        
        logger.info(f"TWAP validated: {self.num_chunks} chunks of {self.chunk_size} {self.symbol}")
        
    def execute_chunk(self, chunk_num: int) -> dict:
        """
        Execute a single chunk order
        
        Args:
            chunk_num: Chunk number (for logging)
            
        Returns:
            dict: Order response
        """
        try:
            logger.info(f"Executing chunk {chunk_num}/{self.num_chunks}: {self.chunk_size} {self.symbol}")
            
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=self.side,
                type='MARKET',
                quantity=self.chunk_size
            )
            
            self.executed_orders.append(order)
            
            executed_qty = float(order.get('executedQty', 0))
            avg_price = float(order.get('avgPrice', 0))
            
            logger.info(
                f"Chunk {chunk_num} executed: "
                f"Qty={executed_qty}, AvgPrice={avg_price}, "
                f"OrderID={order['orderId']}"
            )
            
            return order
            
        except BinanceAPIException as e:
            logger.error(f"Chunk {chunk_num} failed: {e}")
            self.failed_orders.append({
                'chunk': chunk_num,
                'error': str(e),
                'timestamp': datetime.now()
            })
            raise
    
    def calculate_statistics(self) -> dict:
        """
        Calculate execution statistics
        
        Returns:
            dict: Execution statistics
        """
        if not self.executed_orders:
            return {}
        
        total_executed = sum(float(o.get('executedQty', 0)) for o in self.executed_orders)
        
        # Calculate weighted average price
        total_cost = sum(
            float(o.get('executedQty', 0)) * float(o.get('avgPrice', 0))
            for o in self.executed_orders
        )
        avg_price = total_cost / total_executed if total_executed > 0 else 0
        
        return {
            'total_executed': total_executed,
            'average_price': avg_price,
            'num_orders': len(self.executed_orders),
            'num_failed': len(self.failed_orders),
            'total_cost': total_cost if self.side == 'BUY' else 0,
            'total_proceeds': total_cost if self.side == 'SELL' else 0
        }
    
    def run(self):
        """Execute TWAP strategy"""
        try:
            # Validation
            logger.info("=" * 60)
            logger.info("STARTING TWAP EXECUTION")
            logger.info(f"Symbol: {self.symbol}")
            logger.info(f"Side: {self.side}")
            logger.info(f"Total Quantity: {self.total_quantity}")
            logger.info(f"Chunks: {self.num_chunks}")
            logger.info(f"Chunk Size: {self.chunk_size}")
            logger.info(f"Interval: {self.interval_seconds}s")
            logger.info("=" * 60)
            
            self.validate()
            
            # Check balance
            balance = check_balance(self.client, 'USDT')
            current_price = get_current_price(self.client, self.symbol)
            estimated_cost = self.total_quantity * current_price
            
            if self.side == 'BUY' and estimated_cost > balance:
                raise ValidationError(
                    f"Insufficient balance. Required: ~{estimated_cost:.2f} USDT, "
                    f"Available: {balance:.2f} USDT"
                )
            
            # Print execution plan
            print("\n" + "=" * 60)
            print("TWAP EXECUTION PLAN")
            print("=" * 60)
            print(f"Symbol: {self.symbol}")
            print(f"Side: {self.side}")
            print(f"Total Quantity: {self.total_quantity}")
            print(f"Number of Chunks: {self.num_chunks}")
            print(f"Chunk Size: {self.chunk_size}")
            print(f"Interval: {self.interval_seconds} seconds")
            print(f"Total Duration: ~{self.num_chunks * self.interval_seconds / 60:.1f} minutes")
            print(f"Current Price: {current_price}")
            print(f"Estimated Cost: {estimated_cost:.2f} USDT" if self.side == 'BUY' else '')
            print("=" * 60)
            
            input("\nPress ENTER to start execution (or Ctrl+C to cancel)...")
            
            start_time = datetime.now()
            
            # Execute chunks
            for chunk_num in range(1, self.num_chunks + 1):
                chunk_start = datetime.now()
                
                try:
                    order = self.execute_chunk(chunk_num)
                    
                    print(f"\n✓ Chunk {chunk_num}/{self.num_chunks} executed")
                    print(f"  OrderID: {order['orderId']}")
                    print(f"  Quantity: {order.get('executedQty')}")
                    print(f"  Price: {order.get('avgPrice')}")
                    
                except Exception as e:
                    print(f"\n✗ Chunk {chunk_num}/{self.num_chunks} failed: {e}")
                    
                    # Ask user if they want to continue
                    if chunk_num < self.num_chunks:
                        response = input("\nContinue with remaining chunks? (y/n): ")
                        if response.lower() != 'y':
                            logger.info("TWAP execution cancelled by user")
                            break
                
                # Wait for next interval (except for last chunk)
                if chunk_num < self.num_chunks:
                    # Calculate actual wait time to maintain intervals
                    elapsed = (datetime.now() - chunk_start).total_seconds()
                    wait_time = max(0, self.interval_seconds - elapsed)
                    
                    if wait_time > 0:
                        next_chunk_time = datetime.now() + timedelta(seconds=wait_time)
                        print(f"\n⏳ Waiting {wait_time:.1f}s until next chunk...")
                        print(f"   Next execution at: {next_chunk_time.strftime('%H:%M:%S')}")
                        time.sleep(wait_time)
            
            # Calculate and display statistics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            stats = self.calculate_statistics()
            
            print("\n" + "=" * 60)
            print("TWAP EXECUTION COMPLETE")
            print("=" * 60)
            print(f"Total Duration: {duration:.1f} seconds ({duration/60:.2f} minutes)")
            print(f"Orders Executed: {stats.get('num_orders', 0)}/{self.num_chunks}")
            print(f"Orders Failed: {stats.get('num_failed', 0)}")
            print(f"Total Quantity: {stats.get('total_executed', 0):.8f}")
            print(f"Average Price: {stats.get('average_price', 0):.2f}")
            
            if self.side == 'BUY':
                print(f"Total Cost: {stats.get('total_cost', 0):.2f} USDT")
            else:
                print(f"Total Proceeds: {stats.get('total_proceeds', 0):.2f} USDT")
            
            print("=" * 60)
            
            logger.info("TWAP execution completed successfully")
            logger.info(f"Statistics: {stats}")
            
            return stats
            
        except KeyboardInterrupt:
            logger.info("TWAP execution interrupted by user")
            print("\n\n✗ Execution cancelled by user")
            print(f"\nPartial execution: {len(self.executed_orders)}/{self.num_chunks} chunks completed")
            raise
            
        except Exception as e:
            logger.error(f"TWAP execution failed: {e}", exc_info=True)
            raise

def main():
    """CLI entry point for TWAP strategy"""
    parser = argparse.ArgumentParser(
        description='Execute TWAP (Time-Weighted Average Price) strategy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Buy 1 BTC split into 10 orders over 60 minutes
  python twap.py BTCUSDT BUY 1.0 --chunks 10 --duration 60

  # Sell 0.5 BTC split into 5 orders with 120s intervals
  python twap.py ETHUSDT SELL 0.5 --chunks 5 --interval 120
        """
    )
    
    parser.add_argument('symbol', type=str, help='Trading pair (e.g., BTCUSDT)')
    parser.add_argument('side', type=str, help='BUY or SELL')
    parser.add_argument('quantity', type=float, help='Total quantity to trade')
    parser.add_argument('--chunks', type=int, default=10, 
                       help='Number of chunks (default: 10)')
    parser.add_argument('--duration', type=float, default=None,
                       help='Total duration in minutes')
    parser.add_argument('--interval', type=int, default=None,
                       help='Interval between chunks in seconds')
    
    args = parser.parse_args()
    
    # Calculate interval
    if args.duration and not args.interval:
        args.interval = int((args.duration * 60) / args.chunks)
    elif not args.interval:
        args.interval = 60  # Default 60 seconds
    
    # Validation
    if args.quantity <= 0:
        print("✗ Error: Quantity must be positive")
        sys.exit(1)
    
    if args.chunks <= 0:
        print("✗ Error: Number of chunks must be positive")
        sys.exit(1)
    
    if args.interval <= 0:
        print("✗ Error: Interval must be positive")
        sys.exit(1)
    
    try:
        client = get_client()
        executor = TWAPExecutor(
            client=client,
            symbol=args.symbol.upper(),
            side=args.side.upper(),
            total_quantity=args.quantity,
            num_chunks=args.chunks,
            interval_seconds=args.interval
        )
        
        executor.run()
        
    except KeyboardInterrupt:
        print("\n\nExecution interrupted")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"TWAP failed: {e}")
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()