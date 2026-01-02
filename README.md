# Binance Futures Order Bot

A professional CLI-based trading bot for Binance USDT-M Futures supporting multiple order types with robust logging and validation.

## Features

### Core Orders
- ✅ **Market Orders**: Instant execution at current market price
- ✅ **Limit Orders**: Execute at specified price or better

### Advanced Orders
- ✅ **Stop-Limit Orders**: Trigger limit order when stop price is hit
- ✅ **OCO (One-Cancels-the-Other)**: Place take-profit and stop-loss simultaneously
- ✅ **TWAP (Time-Weighted Average Price)**: Split large orders into smaller chunks over time
- ✅ **Grid Orders**: Automated buy-low/sell-high within a price range

### Additional Features
- Comprehensive input validation
- Structured logging with timestamps
- Error handling and recovery
- Position management
- Real-time market data integration

## Project Structure

```
binance-bot/
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration and API setup
│   ├── utils.py                  # Utility functions and validators
│   ├── market_orders.py          # Market order implementation
│   ├── limit_orders.py           # Limit order implementation
│   └── advanced/
│       ├── __init__.py
│       ├── stop_limit.py         # Stop-Limit orders
│       ├── oco.py                # OCO orders
│       ├── twap.py               # TWAP strategy
│       └── grid.py               # Grid trading strategy
│
├── bot.log                       # Auto-generated logs
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
├── report.pdf                    # Analysis and documentation
└── README.md                     # This file
```

## Prerequisites

- Python 3.8 or higher
- Binance account with Futures trading enabled
- API Key and Secret from Binance

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/ANIKET-crypto828/binance-bot
cd binance-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure API credentials**

Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
TESTNET=True  # Set to False for production
```

**⚠️ Security Warning**: Never commit `.env` file to Git. It's already in `.gitignore`.

## API Setup Instructions

1. **Create Binance Account**: Sign up at [binance.com](https://www.binance.com)

2. **Enable Futures Trading**: 
   - Go to Futures section
   - Complete verification if required

3. **Generate API Keys**:
   - Navigate to API Management
   - Create new API key
   - Enable "Futures" permissions
   - Save API Key and Secret securely

4. **Testnet (Recommended for Testing)**:
   - Use [testnet.binancefuture.com](https://testnet.binancefuture.com)
   - Get testnet API keys (separate from production)
   - Set `TESTNET=True` in `.env`

## Usage

### Market Orders

Execute immediate buy/sell at current market price:

```bash
# Buy 0.01 BTC at market price
python src/market_orders.py BTCUSDT BUY 0.01

# Sell 0.01 BTC at market price
python src/market_orders.py BTCUSDT SELL 0.01
```

### Limit Orders

Place orders at specific price levels:

```bash
# Buy 0.01 BTC at $50,000
python src/limit_orders.py BTCUSDT BUY 0.01 50000

# Sell 0.01 BTC at $52,000
python src/limit_orders.py BTCUSDT SELL 0.01 52000
```

### Stop-Limit Orders

Trigger limit order when stop price is reached:

```bash
# Stop-loss: Sell 0.01 BTC if price drops to $48,000, limit at $47,500
python src/advanced/stop_limit.py BTCUSDT SELL 0.01 48000 47500

# Stop-buy: Buy 0.01 BTC if price rises to $52,000, limit at $52,500
python src/advanced/stop_limit.py BTCUSDT BUY 0.01 52000 52500
```

### OCO Orders

Place take-profit and stop-loss simultaneously:

```bash
# Take profit at $52,000, stop-loss at $48,000 for 0.01 BTC
python src/advanced/oco.py BTCUSDT SELL 0.01 52000 48000 47500

# Arguments: symbol side quantity take_profit_price stop_price stop_limit_price
```

### TWAP Orders

Split large orders into smaller chunks over time:

```bash
# Buy 1 BTC split into 10 orders over 60 minutes
python src/advanced/twap.py BTCUSDT BUY 1.0 --chunks 10 --duration 60

# Custom interval (in seconds)
python src/advanced/twap.py BTCUSDT SELL 0.5 --chunks 5 --interval 120
```

### Grid Orders

Automated buy-low/sell-high within price range:

```bash
# Create grid between $48,000-$52,000 with 10 levels, 0.01 BTC per level
python src/advanced/grid.py BTCUSDT 48000 52000 --grids 10 --quantity 0.01

# Run until manually stopped with Ctrl+C
```

## Configuration Options

Edit `src/config.py` for advanced settings:

- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `MAX_RETRIES`: API call retry attempts
- `TIMEOUT`: Request timeout in seconds
- `POSITION_MODE`: Hedge or One-way mode

## Logging

All operations are logged to `bot.log` with:
- Timestamps
- Order details
- API responses
- Error traces
- Execution results

Example log entry:
```
2025-01-01 12:00:00 - INFO - Market order placed: BTCUSDT BUY 0.01
2025-01-01 12:00:01 - INFO - Order executed: orderId=123456, status=FILLED
```

## Validation

The bot validates:
- ✅ Symbol format and availability
- ✅ Quantity (min/max limits, step size)
- ✅ Price levels (tick size, reasonable ranges)
- ✅ Balance sufficiency
- ✅ API credentials
- ✅ Network connectivity

## Error Handling

Robust error handling for:
- Network failures (auto-retry)
- Insufficient balance
- Invalid parameters
- API rate limits
- Order rejections

## Testing

Run with testnet first:
```bash
# Set TESTNET=True in .env
python src/market_orders.py BTCUSDT BUY 0.01
```

## Common Issues

**Issue**: `Invalid API key`
- **Solution**: Verify API key in `.env`, check IP whitelist on Binance

**Issue**: `Insufficient balance`
- **Solution**: Deposit funds or reduce order quantity

**Issue**: `Symbol not found`
- **Solution**: Use correct symbol format (e.g., BTCUSDT not BTC-USDT)

## Safety Notes

1. **Start with Testnet**: Always test strategies on testnet first
2. **Small Quantities**: Begin with minimal amounts in production
3. **Stop-Loss**: Always use stop-loss orders to limit risk
4. **Monitor**: Keep bot.log open while running
5. **API Security**: Never share API keys, enable IP whitelist

## Advanced Usage

### Combining Strategies

```python
# Example: Place market order, then set OCO for risk management
python src/market_orders.py BTCUSDT BUY 0.01
python src/advanced/oco.py BTCUSDT SELL 0.01 52000 48000 47500
```

### Batch Operations

Create a shell script for multiple orders:
```bash
#!/bin/bash
python src/limit_orders.py BTCUSDT BUY 0.01 49000
python src/limit_orders.py BTCUSDT BUY 0.01 48000
python src/limit_orders.py BTCUSDT BUY 0.01 47000
```

## Performance

- Average order execution: <200ms
- TWAP precision: ±5 seconds per interval
- Grid rebalancing: Real-time on fills

## Dependencies

See `requirements.txt`:
- `python-binance`: Binance API wrapper
- `python-dotenv`: Environment variable management
- `requests`: HTTP library

## Contributing

This is an assignment project. For questions, contact your instructor.

## License

Educational use only. Trade at your own risk.

## Disclaimer

**⚠️ IMPORTANT**: Cryptocurrency trading involves substantial risk of loss. This bot is for educational purposes. Always:
- Test thoroughly on testnet
- Start with amounts you can afford to lose
- Understand the strategies before using
- Monitor positions actively
- Use proper risk management

The developers are not responsible for any trading losses.

## Support

For issues or questions:
- Check `bot.log` for error details
- Review Binance API documentation
- Contact: aniketsantra78@gmail.com

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-01