"""
Configuration module for Binance Futures Trading Bot
Handles API credentials, logging setup, and global settings
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from binance.client import Client

# Load environment variables
load_dotenv()

# API Credentials
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TESTNET = os.getenv('TESTNET', 'True').lower() == 'true'

# Binance Client Configuration
TESTNET_URL = 'https://testnet.binancefuture.com'

# Trading Parameters
DEFAULT_LEVERAGE = 1
POSITION_MODE = 'One-way'  # or 'Hedge'

# Logging Configuration
LOG_DIR = Path(__file__).parent.parent
LOG_FILE = LOG_DIR / 'bot.log'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# API Settings
MAX_RETRIES = 3
TIMEOUT = 10
RATE_LIMIT_BUFFER = 0.1  # seconds between requests

# Order Validation
MIN_NOTIONAL = 5  # Minimum order value in USDT
MAX_POSITION_SIZE = 100000  # Maximum position size in USDT

def setup_logging():
    """Configure logging for the entire application"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Binance Futures Trading Bot Started")
    logger.info(f"Mode: {'TESTNET' if TESTNET else 'PRODUCTION'}")
    logger.info("=" * 60)
    
    return logger

def get_client():
    """
    Initialize and return Binance Futures client
    
    Returns:
        Client: Configured Binance client instance
        
    Raises:
        ValueError: If API credentials are missing
    """
    if not API_KEY or not API_SECRET:
        raise ValueError(
            "API credentials not found. Please set BINANCE_API_KEY and "
            "BINANCE_API_SECRET in .env file"
        )
    
    client = Client(API_KEY, API_SECRET, testnet=TESTNET)
    
    if TESTNET:
        client.API_URL = TESTNET_URL
    
    logger = logging.getLogger(__name__)
    logger.info(f"Client initialized - Testnet: {TESTNET}")
    
    return client

def validate_environment():
    """
    Validate that all required environment variables are set
    
    Returns:
        bool: True if valid, raises exception otherwise
        
    Raises:
        EnvironmentError: If required variables are missing
    """
    required_vars = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please create a .env file with these variables."
        )
    
    return True

# Initialize logger on import
logger = setup_logging()

# Trading pairs configuration
SUPPORTED_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT',
    'XRPUSDT', 'DOTUSDT', 'UNIUSDT', 'LINKUSDT', 'LTCUSDT',
    'SOLUSDT', 'MATICUSDT', 'AVAXUSDT', 'ATOMUSDT'
]

# Price precision for major symbols
PRICE_PRECISION = {
    'BTCUSDT': 2,
    'ETHUSDT': 2,
    'BNBUSDT': 2,
    'ADAUSDT': 4,
    'DOGEUSDT': 5,
    'XRPUSDT': 4,
}

# Quantity precision for major symbols
QUANTITY_PRECISION = {
    'BTCUSDT': 3,
    'ETHUSDT': 3,
    'BNBUSDT': 2,
    'ADAUSDT': 0,
    'DOGEUSDT': 0,
    'XRPUSDT': 0,
}