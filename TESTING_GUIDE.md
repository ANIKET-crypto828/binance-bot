# Testing Guide - Binance Futures Trading Bot

## Pre-Testing Checklist

- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with API credentials
- [ ] `TESTNET=True` set in `.env` (for safe testing)
- [ ] Testnet account funded with test USDT

## Getting Testnet Credentials

1. Visit [Binance Futures Testnet](https://testnet.binancefuture.com)
2. Login with your email
3. Navigate to API Management
4. Create new API key
5. Enable "Futures" permissions
6. Copy API Key and Secret to `.env`
7. Get test funds from the testnet faucet

## Testing Each Order Type

### 1. Market Orders

**Test Case 1.1: Basic Buy Market Order**
```bash
python src/market_orders.py BTCUSDT BUY 0.001
```

**Expected Results:**
- Order executes immediately
- Log entry created in `bot.log`
- Console shows order ID and execution price
- Balance decreases by approximately (quantity × market_price)

**Test Case 1.2: Basic Sell Market Order**
```bash
python src/market_orders.py BTCUSDT SELL 0.001
```

**Expected Results:**
- Order executes immediately
- Position closed or reversed
- Balance increases

**Test Case 1.3: Invalid Symbol**
```bash
python src/market_orders.py INVALIDUSDT BUY 0.001
```

**Expected Results:**
- Validation error message
- No order placed
- Error logged

**Test Case 1.4: Insufficient Balance**
```bash
python src/market_orders.py BTCUSDT BUY 100
```

**Expected Results:**
- Error message about insufficient balance
- No order placed

---

### 2. Limit Orders

**Test Case 2.1: Buy Limit Below Market**
```bash
# First check current price, then place order 5% below
python src/limit_orders.py BTCUSDT BUY 0.001 45000
```

**Expected Results:**
- Order placed successfully
- Order status: NEW
- Order appears in open orders
- Order ID returned

**Test Case 2.2: Sell Limit Above Market**
```bash
python src/limit_orders.py BTCUSDT SELL 0.001 55000
```

**Test Case 2.3: Immediate Fill (IOC)**
```bash
python src/limit_orders.py BTCUSDT BUY 0.001 60000 IOC
```

**Expected Results:**
- Order fills immediately or cancels
- Status: FILLED or CANCELED

---

### 3. Stop-Limit Orders

**Test Case 3.1: Stop-Loss (SELL)**
```bash
# Place stop-loss 5% below current price
python src/advanced/stop_limit.py BTCUSDT SELL 0.001 47000 46500
```

**Expected Results:**
- Order placed with status: NEW
- Order triggers when price hits 47000
- Limit order placed at 46500

**Test Case 3.2: Stop-Buy (BUY)**
```bash
# Place stop-buy 5% above current price
python src/advanced/stop_limit.py BTCUSDT BUY 0.001 52000 52500
```

**Test Case 3.3: Invalid Price Relationship**
```bash
# Limit price higher than stop price for SELL (should fail)
python src/advanced/stop_limit.py BTCUSDT SELL 0.001 47000 48000
```

**Expected Results:**
- Validation error
- Clear error message explaining price relationship

---

### 4. OCO Orders

**Test Case 4.1: Standard OCO for Long Position**
```bash
# First buy some BTC
python src/market_orders.py BTCUSDT BUY 0.001

# Then place OCO to manage the position
python src/advanced/oco.py BTCUSDT SELL 0.001 52000 48000 47500
```

**Expected Results:**
- Two orders placed: take-profit and stop-loss
- Both orders visible in open orders
- Order IDs returned for both

**Test Case 4.2: Monitor OCO Execution**
- Manually adjust testnet price (if possible) or wait for market movement
- Observe that when one order fills, you manually cancel the other

**Manual Test:**
- Check both orders in Binance Futures testnet interface
- Verify quantities and prices

---

### 5. TWAP Strategy

**Test Case 5.1: Basic TWAP**
```bash
# Split 0.01 BTC into 5 chunks over 5 minutes
python src/advanced/twap.py BTCUSDT BUY 0.01 --chunks 5 --duration 5
```

**Expected Results:**
- Execution plan displayed
- 5 market orders placed over 5 minutes
- Average price calculated
- All orders logged

**Test Case 5.2: TWAP with Custom Interval**
```bash
# 10 chunks with 30-second intervals
python src/advanced/twap.py BTCUSDT SELL 0.01 --chunks 10 --interval 30
```

**Expected Results:**
- Orders spaced exactly 30 seconds apart
- Total execution time: ~5 minutes

**Test Case 5.3: TWAP Interruption**
```bash
python src/advanced/twap.py BTCUSDT BUY 0.01 --chunks 10 --duration 5
# Press Ctrl+C after 2-3 chunks
```

**Expected Results:**
- Graceful shutdown
- Partial execution statistics displayed
- Number of completed chunks shown

---

### 6. Grid Trading

**Test Case 6.1: Basic Grid Setup**
```bash
# Grid between 48k-52k with 5 levels
python src/advanced/grid.py BTCUSDT 48000 52000 --grids 5 --quantity 0.001
```

**Expected Results:**
- Grid levels calculated and displayed
- Buy orders placed below current price
- Sell orders placed above current price
- All order IDs logged

**Test Case 6.2: Grid Execution**
- Let grid run for 5-10 minutes
- Observe as orders fill and get replaced
- Check profit tracking

**Expected Results:**
- Filled orders automatically replaced
- Profit calculated on sell orders
- Status displayed periodically

**Test Case 6.3: Grid Cleanup**
```bash
# Start grid and stop with Ctrl+C
python src/advanced/grid.py BTCUSDT 48000 52000 --grids 5 --quantity 0.001
# Wait 1 minute, then Ctrl+C
```

**Expected Results:**
- All open orders cancelled
- Final statistics displayed
- Clean shutdown

---

## Validation Testing

### Input Validation Tests

**Test Invalid Symbol:**
```bash
python src/market_orders.py BTC-USDT BUY 0.001
```

**Test Negative Quantity:**
```bash
python src/market_orders.py BTCUSDT BUY -0.001
```

**Test Zero Quantity:**
```bash
python src/limit_orders.py BTCUSDT BUY 0 50000
```

**Test Invalid Side:**
```bash
python src/market_orders.py BTCUSDT PURCHASE 0.001
```

**Test Below Minimum Quantity:**
```bash
python src/market_orders.py BTCUSDT BUY 0.00000001
```

---

## Log File Verification

After each test, verify `bot.log` contains:

- [ ] Timestamp for each action
- [ ] Order parameters (symbol, side, quantity, price)
- [ ] Order IDs
- [ ] Execution results
- [ ] Error messages (for failed tests)
- [ ] API responses

**Sample Log Entry:**
```
2025-01-01 12:00:00 - INFO - Market order placed: BTCUSDT BUY 0.001
2025-01-01 12:00:01 - INFO - Order executed: orderId=123456, status=FILLED
```

---

## Performance Testing

### Latency Test
```bash
time python src/market_orders.py BTCUSDT BUY 0.001
```

**Expected:** < 2 seconds total execution time

### Multiple Orders Test
```bash
for i in {1..5}; do
    python src/market_orders.py BTCUSDT BUY 0.001
    sleep 2
done
```

**Expected:** All orders execute successfully

---

## Error Handling Tests

**Network Timeout:**
- Disconnect internet briefly
- Attempt to place order
- Verify retry mechanism

**API Key Error:**
- Use invalid API key
- Verify clear error message

**Rate Limiting:**
- Place many orders rapidly
- Verify rate limit handling

---

## Integration Testing

### Complete Trading Workflow

1. **Open Position:**
   ```bash
   python src/market_orders.py BTCUSDT BUY 0.001
   ```

2. **Set OCO Protection:**
   ```bash
   python src/advanced/oco.py BTCUSDT SELL 0.001 52000 48000 47500
   ```

3. **Monitor Position:**
   - Check balance
   - Verify open orders
   - Monitor logs

4. **Close Position:**
   - Wait for OCO trigger OR
   - Manually close with market order

---

## Screenshot Requirements for Report

For each test, capture:

1. **Command execution:**
   - Terminal showing command and output

2. **Bot log:**
   - Relevant log entries

3. **Binance Interface:**
   - Open orders
   - Order history
   - Filled orders

4. **Balance verification:**
   - Before and after screenshots

---

## Common Issues and Solutions

**Issue: "Invalid API key"**
- Solution: Check `.env` file, regenerate keys

**Issue: "Insufficient balance"**
- Solution: Get testnet funds from faucet

**Issue: "Symbol not found"**
- Solution: Use correct format (BTCUSDT not BTC-USDT)

**Issue: "Quantity below minimum"**
- Solution: Increase quantity to meet minimum

---

## Test Completion Checklist

- [ ] All core orders tested (market, limit)
- [ ] All advanced orders tested (stop-limit, OCO, TWAP, grid)
- [ ] Input validation working correctly
- [ ] Error handling working correctly
- [ ] Logs generated properly
- [ ] Screenshots captured for report
- [ ] Performance acceptable
- [ ] Clean shutdown tested

---

## Next Steps

1. Complete all tests on testnet
2. Document results with screenshots
3. Create `report.pdf` with findings
4. Test on production with minimal amounts
5. Deploy for actual trading

**Remember:** Always test thoroughly on testnet before using real funds!