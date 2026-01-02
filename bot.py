#!/usr/bin/env python3
"""
Binance Futures Trading Bot - Main Entry Point
Unified CLI interface for all order types
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import setup_logging, validate_environment
from market_orders import place_market_order
from limit_orders import place_limit_order
from advanced.stop_limit import place_stop_limit_order
from advanced.oco import place_oco_order
from advanced.twap import TWAPExecutor, get_client
from advanced.grid import GridTrader

logger = logging.getLogger(__name__)

def print_banner():
    """Print bot banner"""
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║         BINANCE FUTURES TRADING BOT v1.0                   ║
    ║                                                            ║
    ║    Professional CLI-based trading bot for Binance Futures ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """
    print(banner)

def create_parser():
    """Create argument parser with subcommands"""
    parser = argparse.ArgumentParser(
        description='Binance Futures Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Market order
  python bot.py market BTCUSDT BUY 0.01
  
  # Limit order
  python bot.py limit BTCUSDT BUY 0.01 50000
  
  # Stop-limit order
  python bot.py stop-limit BTCUSDT SELL 0.01 48000 47500
  
  # OCO order
  python bot.py oco BTCUSDT SELL 0.01 52000 48000 47500
  
  # TWAP strategy
  python bot.py twap BTCUSDT BUY 1.0 --chunks 10 --duration 60
  
  # Grid trading
  python bot.py grid BTCUSDT 48000 52000 --grids 10 --quantity 0.01

For detailed help on each command, use:
  python bot.py COMMAND --help
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Order type')
    
    # Market order
    market_parser = subparsers.add_parser('market', help='Place market order')
    market_parser.add_argument('symbol', help='Trading pair (e.g., BTCUSDT)')
    market_parser.add_argument('side', help='BUY or SELL')
    market_parser.add_argument('quantity', type=float, help='Order quantity')
    
    # Limit order
    limit_parser = subparsers.add_parser('limit', help='Place limit order')
    limit_parser.add_argument('symbol', help='Trading pair')
    limit_parser.add_argument('side', help='BUY or SELL')
    limit_parser.add_argument('quantity', type=float, help='Order quantity')
    limit_parser.add_argument('price', type=float, help='Limit price')
    limit_parser.add_argument('--tif', default='GTC', 
                            help='Time in force (GTC/IOC/FOK)')
    
    # Stop-limit order
    stop_parser = subparsers.add_parser('stop-limit', help='Place stop-limit order')
    stop_parser.add_argument('symbol', help='Trading pair')
    stop_parser.add_argument('side', help='BUY or SELL')
    stop_parser.add_argument('quantity', type=float, help='Order quantity')
    stop_parser.add_argument('stop_price', type=float, help='Stop trigger price')
    stop_parser.add_argument('limit_price', type=float, help='Limit price')
    stop_parser.add_argument('--tif', default='GTC', help='Time in force')
    
    # OCO order
    oco_parser = subparsers.add_parser('oco', help='Place OCO order')
    oco_parser.add_argument('symbol', help='Trading pair')
    oco_parser.add_argument('side', help='BUY or SELL')
    oco_parser.add_argument('quantity', type=float, help='Order quantity')
    oco_parser.add_argument('tp_price', type=float, help='Take-profit price')
    oco_parser.add_argument('sl_price', type=float, help='Stop-loss price')
    oco_parser.add_argument('sl_limit', type=float, help='Stop-loss limit price')
    
    # TWAP strategy
    twap_parser = subparsers.add_parser('twap', help='Execute TWAP strategy')
    twap_parser.add_argument('symbol', help='Trading pair')
    twap_parser.add_argument('side', help='BUY or SELL')
    twap_parser.add_argument('quantity', type=float, help='Total quantity')
    twap_parser.add_argument('--chunks', type=int, default=10, 
                           help='Number of chunks')
    twap_parser.add_argument('--duration', type=float, 
                           help='Duration in minutes')
    twap_parser.add_argument('--interval', type=int, 
                           help='Interval in seconds')
    
    # Grid trading
    grid_parser = subparsers.add_parser('grid', help='Execute grid trading')
    grid_parser.add_argument('symbol', help='Trading pair')
    grid_parser.add_argument('lower', type=float, help='Lower price bound')
    grid_parser.add_argument('upper', type=float, help='Upper price bound')
    grid_parser.add_argument('--grids', type=int, default=10, 
                           help='Number of grids')
    grid_parser.add_argument('--quantity', type=float, required=True,
                           help='Quantity per grid')
    grid_parser.add_argument('--interval', type=int, default=5,
                           help='Check interval in seconds')
    
    return parser

def execute_market(args):
    """Execute market order"""
    place_market_order(
        symbol=args.symbol.upper(),
        side=args.side.upper(),
        quantity=args.quantity
    )

def execute_limit(args):
    """Execute limit order"""
    place_limit_order(
        symbol=args.symbol.upper(),
        side=args.side.upper(),
        quantity=args.quantity,
        price=args.price,
        time_in_force=args.tif
    )

def execute_stop_limit(args):
    """Execute stop-limit order"""
    place_stop_limit_order(
        symbol=args.symbol.upper(),
        side=args.side.upper(),
        quantity=args.quantity,
        stop_price=args.stop_price,
        limit_price=args.limit_price,
        time_in_force=args.tif
    )

def execute_oco(args):
    """Execute OCO order"""
    place_oco_order(
        symbol=args.symbol.upper(),
        side=args.side.upper(),
        quantity=args.quantity,
        take_profit_price=args.tp_price,
        stop_loss_price=args.sl_price,
        stop_limit_price=args.sl_limit
    )

def execute_twap(args):
    """Execute TWAP strategy"""
    client = get_client()
    
    # Calculate interval if duration is provided
    interval = args.interval
    if args.duration and not interval:
        interval = int((args.duration * 60) / args.chunks)
    elif not interval:
        interval = 60
    
    executor = TWAPExecutor(
        client=client,
        symbol=args.symbol.upper(),
        side=args.side.upper(),
        total_quantity=args.quantity,
        num_chunks=args.chunks,
        interval_seconds=interval
    )
    
    executor.run()

def execute_grid(args):
    """Execute grid trading"""
    client = get_client()
    
    trader = GridTrader(
        client=client,
        symbol=args.symbol.upper(),
        lower_price=args.lower,
        upper_price=args.upper,
        num_grids=args.grids,
        quantity_per_grid=args.quantity
    )
    
    trader.run(check_interval=args.interval)

def main():
    """Main entry point"""
    try:
        # Validate environment
        validate_environment()
        
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()
        
        if not args.command:
            print_banner()
            parser.print_help()
            return
        
        # Execute command
        logger.info(f"Executing command: {args.command}")
        
        if args.command == 'market':
            execute_market(args)
        elif args.command == 'limit':
            execute_limit(args)
        elif args.command == 'stop-limit':
            execute_stop_limit(args)
        elif args.command == 'oco':
            execute_oco(args)
        elif args.command == 'twap':
            execute_twap(args)
        elif args.command == 'grid':
            execute_grid(args)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)
        
        logger.info("Command completed successfully")
        
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user")
        logger.info("Operation cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()