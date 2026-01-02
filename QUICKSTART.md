# Quick Start Guide - Binance Futures Trading Bot

Get up and running in 5 minutes!

## Step 1: Prerequisites (2 minutes)

```bash
# Check Python version (need 3.8+)
python --version

# Clone or download the project
cd binance-bot
```

## Step 2: Install Dependencies (1 minute)

```bash
# Install required packages
pip install -r requirements.txt
```

## Step 3: Setup API Keys (2 minutes)

### Get Testnet Keys (Recommended for first time)

1. Visit: https://testnet.binancefuture.com
2. Login with email
3. Go to API Management
4. Create new key with "Futures" permission
5. Copy API Key and Secret

### Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env file (use nano, vim, or any text editor)
nano .env
```

**Add your credentials:**
```
BINANCE_API_KEY=paste_your_key_here
BINANCE_API_SECRET=paste_your_secret_here
TESTNET=True
```

Save and exit.

## Step 4: Test Your Setup (30 seconds)

```bash
# Run a simple validation test
python -c "from src.config import validate_environment; validate_environment(); print('✓ Setup successful!')"
```

## Step 5: Place Your First Order! (30 seconds)

### Option A: Using Individual Scripts

```bash
# Market order - Buy 0.001 BTC at current price
python src/market_orders.py BTCUSDT BUY 0.001
```

### Option B: Using Main Bot Interface

```bash
# Same market order using unified interface
python bot.py market BTCUSDT BUY 0.001
```

**Success!** You should see:
```
✓ Market Order Executed Successfully!
===========================================================
Order ID: 123456
Symbol: BTCUSDT
Side: BUY
...
```

## Quick Command Reference

### Core Orders
```bash
# Market Order
python bot.py market BTCUSDT BUY 0.01

# Limit Order
python bot.py limit BTCUSDT BUY 0.01 50000
```

### Advanced Orders
```bash
# Stop-Limit (Stop-Loss)
python bot.py stop-limit BTCUSDT SELL 0.01 48000 47500

# OCO (Take-Profit + Stop-Loss)
python bot.py oco BTCUSDT SELL 0.01 52000 48000 47500

# TWAP (Split order over time)
python bot.py twap BTCUSDT BUY 1.0 --chunks 10 --duration 60

# Grid Trading
python bot.py grid BTCUSDT 48000 52000 --grids 10 --quantity 0.01
```

## Common First-Time Issues

**"Invalid API key"**
- Check `.env` file exists
- Verify keys are correct (no extra spaces)
- Ensure API has Futures permission

**"Insufficient balance"**
- Get testnet funds: https://testnet.binancefuture.com
- Click "Get Test Funds" or similar
- Reduce order quantity

**"Module not found"**
- Run: `pip install -r requirements.txt`
- Ensure you're in project root directory

## Next Steps

1. ✓ You've placed your first order!
2. Read [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive testing
3. Review [README.md](README.md) for detailed documentation
4. Try advanced strategies (TWAP, Grid)
5. When ready, switch to production (set `TESTNET=False`)

## Getting Help

- Check logs: `cat bot.log`
- Review error messages carefully
- Verify on Binance interface: https://testnet.binancefuture.com

## Safety Reminders

⚠️ **Always:**
- Test on testnet first
- Start with small amounts
- Use stop-loss orders
- Monitor your positions
- Never share API keys

---

**You're ready to trade! Happy trading! 🚀**