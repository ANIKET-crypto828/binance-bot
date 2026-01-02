"""
Binance Futures Trading Bot
A comprehensive CLI-based trading bot for Binance USDT-M Futures

Author: [Your Name]
Version: 1.0.0
"""

__version__ = '1.0.0'
__author__ = '[Your Name]'

from . import config
from . import utils
from . import market_orders
from . import limit_orders

__all__ = [
    'config',
    'utils',
    'market_orders',
    'limit_orders',
]