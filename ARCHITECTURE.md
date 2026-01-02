# Architecture Documentation
## Binance Futures Trading Bot

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Architectural Patterns](#architectural-patterns)
3. [Module Design](#module-design)
4. [Data Flow](#data-flow)
5. [Error Handling Strategy](#error-handling-strategy)
6. [Security Considerations](#security-considerations)
7. [Scalability & Performance](#scalability--performance)
8. [Design Decisions](#design-decisions)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│                       (CLI Commands)                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐   │
│  │ bot.py   │  │ Order    │  │ Strategy Executors     │   │
│  │ (Main)   │  │ Modules  │  │ (TWAP, Grid)           │   │
│  └──────────┘  └──────────┘  └────────────────────────┘   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Validation   │  │ Order        │  │ Risk            │  │
│  │ Engine       │  │ Management   │  │ Management      │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     Integration Layer                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Binance API Client Wrapper                  │  │
│  │  (Authentication, Rate Limiting, Retry Logic)         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│              (Binance Futures API / Testnet)                 │
└─────────────────────────────────────────────────────────────┘

         Cross-Cutting Concerns (Applied Throughout):
    ┌──────────────┬───────────────┬─────────────────┐
    │   Logging    │ Error         │  Configuration  │
    │   System     │ Handling      │  Management     │
    └──────────────┴───────────────┴─────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Key Files |
|-----------|---------------|-----------|
| **CLI Interface** | User interaction, command parsing | `bot.py`, individual order scripts |
| **Order Modules** | Order placement logic | `market_orders.py`, `limit_orders.py` |
| **Strategy Executors** | Complex trading strategies | `twap.py`, `grid.py` |
| **Validation Engine** | Input validation, API constraints | `utils.py` |
| **Configuration** | API setup, environment management | `config.py` |
| **Logging System** | Activity tracking, debugging | `config.py` (setup) |
| **API Client** | External API communication | `python-binance` library |

---

## Architectural Patterns

### 1. Layered Architecture

The system follows a **strict layered architecture** to separate concerns:

```
┌─────────────────────────────────────┐
│  Presentation Layer (CLI)           │  ← User interaction
├─────────────────────────────────────┤
│  Application Layer (Order Logic)    │  ← Business workflows
├─────────────────────────────────────┤
│  Domain Layer (Validation/Utils)    │  ← Core business rules
├─────────────────────────────────────┤
│  Infrastructure Layer (API Client)  │  ← External services
└─────────────────────────────────────┘
```

**Benefits:**
- Clear separation of concerns
- Easy to test individual layers
- Changes in one layer don't affect others
- Maintainable and extensible

### 2. Dependency Injection Pattern

```python
# High-level modules don't depend on low-level modules
# Both depend on abstractions (Binance client interface)

class TWAPExecutor:
    def __init__(self, client, ...):  # ← Client injected
        self.client = client
        
# Usage
client = get_client()  # ← Created once
executor = TWAPExecutor(client, ...)  # ← Injected
```

**Benefits:**
- Testability (can mock API client)
- Flexibility (can swap implementations)
- Reduced coupling

### 3. Strategy Pattern

Used for different order types and trading strategies:

```python
# Each order type is a strategy
place_market_order()   # Strategy 1
place_limit_order()    # Strategy 2
place_stop_limit()     # Strategy 3

# Each can be executed independently
# All share common validation interface
```

### 4. Template Method Pattern

Used in strategy executors (TWAP, Grid):

```python
class TWAPExecutor:
    def run(self):
        self.validate()        # ← Template steps
        self.execute_chunks()  # ← Implemented
        self.report_stats()    # ← Different per strategy
```

---

## Module Design

### Core Module: `config.py`

**Purpose:** Central configuration and initialization

```
config.py
├── Environment Loading (.env)
├── API Client Creation
├── Logging Setup
└── Global Constants

Dependencies: python-dotenv, binance
Used by: All modules
```

**Key Functions:**
- `setup_logging()` - Initialize logging system
- `get_client()` - Create authenticated Binance client
- `validate_environment()` - Check required variables

**Design Decisions:**
- Singleton pattern for logger (created once on import)
- Factory pattern for client creation
- Centralized configuration (single source of truth)

---

### Core Module: `utils.py`

**Purpose:** Reusable utilities and validation

```
utils.py
├── Validation Functions
│   ├── validate_symbol()
│   ├── validate_quantity()
│   ├── validate_price()
│   └── validate_side()
├── Helper Functions
│   ├── get_current_price()
│   ├── check_balance()
│   └── format_order_response()
└── Decorators
    └── retry_on_failure()

Dependencies: binance, config
Used by: All order modules
```

**Validation Chain:**
```
User Input → validate_symbol() → validate_quantity() → validate_price()
                ↓                      ↓                     ↓
         Check existence      Apply lot size       Apply tick size
                ↓                      ↓                     ↓
         Check status         Check min/max        Check range
                ↓                      ↓                     ↓
              PASS                  PASS                  PASS
                └──────────────┬──────────────┘
                               ↓
                      Validated Parameters
```

**Error Handling:**
- Custom `ValidationError` exception
- Clear, user-friendly error messages
- Early validation (fail fast)

---

### Order Modules

#### Market Orders (`market_orders.py`)

```
User Command
      ↓
Parse Arguments (symbol, side, quantity)
      ↓
Initialize Client
      ↓
Validation Pipeline
  ├── Validate Symbol
  ├── Validate Side
  └── Validate Quantity
      ↓
Check Balance
      ↓
Place Market Order (Binance API)
      ↓
Log Result
      ↓
Display to User
```

**API Call:**
```python
client.futures_create_order(
    symbol=symbol,
    side=side,
    type='MARKET',
    quantity=quantity
)
```

#### Limit Orders (`limit_orders.py`)

Similar to market orders, plus:
- Price validation
- Time-in-force options
- Price vs. market comparison
- Notional value check

```
[Same as Market] → Additional Steps:
                        ↓
                   Validate Price
                        ↓
                   Validate Notional
                        ↓
                   Check Price vs Market
                        ↓
                   Place Limit Order
```

---

### Advanced Strategies

#### Stop-Limit Orders (`stop_limit.py`)

**Logic Flow:**
```
1. Validate all prices (stop, limit)
2. Check price relationships:
   - SELL: stop < current, limit ≤ stop
   - BUY: stop > current, limit ≥ stop
3. Place STOP order type
```

**Price Relationship Validation:**
```python
if side == 'SELL':
    assert limit_price <= stop_price
    # Prevent selling at higher limit than stop
    
if side == 'BUY':
    assert limit_price >= stop_price
    # Prevent buying at lower limit than stop
```

#### OCO Orders (`oco.py`)

**Architecture:**
```
OCO Order Request
      ↓
┌─────────────┴──────────────┐
│                            │
▼                            ▼
Take-Profit Order      Stop-Loss Order
(Limit)                (Stop-Limit)
      │                            │
      └─────────┬──────────────────┘
                ↓
        Both Orders Active
                ↓
      Monitor Both Orders
                ↓
        One Fills? → Cancel Other
```

**Note:** Binance Futures doesn't support native OCO, so we simulate:
1. Place take-profit (limit order)
2. Place stop-loss (stop order)
3. User monitors and cancels counterpart when one fills

**Future Enhancement:** Add automatic monitoring service

#### TWAP Strategy (`twap.py`)

**Class Structure:**
```python
TWAPExecutor
├── __init__()          # Initialize parameters
├── validate()          # Validate all inputs
├── execute_chunk()     # Execute single order
├── calculate_stats()   # Calculate VWAP
└── run()              # Main execution loop
```

**Execution Flow:**
```
Total Order (e.g., 1.0 BTC)
      ↓
Divide into Chunks (e.g., 10 × 0.1 BTC)
      ↓
For each chunk:
  ├── Execute Market Order
  ├── Log Execution Price
  ├── Wait Interval
  └── Repeat
      ↓
Calculate Statistics:
  ├── Total Executed Quantity
  ├── Weighted Average Price
  └── Total Cost/Proceeds
```

**Timing Algorithm:**
```python
# Maintain consistent intervals
for chunk in chunks:
    start_time = now()
    execute_chunk()
    elapsed = now() - start_time
    wait_time = max(0, interval - elapsed)
    sleep(wait_time)
```

**Statistical Calculation:**
```python
# Volume-Weighted Average Price (VWAP)
total_cost = Σ(quantity_i × price_i)
total_quantity = Σ(quantity_i)
vwap = total_cost / total_quantity
```

#### Grid Trading (`grid.py`)

**Class Structure:**
```python
GridTrader
├── __init__()              # Initialize parameters
├── calculate_grid_levels() # Calculate price levels
├── validate()              # Validate setup
├── place_initial_orders()  # Place grid orders
├── check_filled_orders()   # Monitor for fills
├── handle_filled_order()   # Replace filled orders
├── display_status()        # Show statistics
└── run()                   # Main loop
```

**Grid Calculation:**
```python
# Linear grid spacing
price_step = (upper_price - lower_price) / (num_grids - 1)
grid_levels = [lower_price + i × price_step for i in range(num_grids)]

# Example: 5 grids between 48k-52k
# Levels: 48000, 49000, 50000, 51000, 52000
```

**Order Placement Logic:**
```
Current Price: 50,000

Below Current (Buy Orders):      Above Current (Sell Orders):
├── 48,000 BUY 0.01             ├── 51,000 SELL 0.01
└── 49,000 BUY 0.01             └── 52,000 SELL 0.01

When price moves:
  ↓
Buy fills at 49,000
  ↓
Place Sell at 50,000 (next level up)
  ↓
Profit = (50,000 - 49,000) × 0.01 = 10 USDT
```

**Monitoring Loop:**
```python
while True:
    for each active order:
        check_status()
        if filled:
            calculate_profit()
            place_counterpart_order()
    sleep(check_interval)
```

---

## Data Flow

### Order Placement Flow

```
┌──────────┐
│   User   │
└────┬─────┘
     │ Command: BTCUSDT BUY 0.01
     ▼
┌─────────────────┐
│  CLI Parser     │
│  (bot.py)       │
└────┬────────────┘
     │ Parsed: {symbol: 'BTCUSDT', side: 'BUY', qty: 0.01}
     ▼
┌─────────────────┐
│  Order Module   │
│  (market.py)    │
└────┬────────────┘
     │ 1. Initialize client
     │ 2. Start validation
     ▼
┌─────────────────┐
│  Utils Module   │
│  (utils.py)     │
└────┬────────────┘
     │ validate_symbol() → ✓
     │ validate_side() → ✓
     │ validate_quantity() → ✓ (adjusted to 0.001)
     │ check_balance() → ✓ (sufficient)
     ▼
┌─────────────────┐
│  API Client     │
│  (binance)      │
└────┬────────────┘
     │ POST /fapi/v1/order
     │ {symbol, side, type: MARKET, quantity}
     ▼
┌─────────────────┐
│  Binance API    │
└────┬────────────┘
     │ Response: {orderId, status: FILLED, ...}
     ▼
┌─────────────────┐
│  Logging        │
│  (bot.log)      │
└────┬────────────┘
     │ Log: "Order 123456 executed at 50000"
     ▼
┌─────────────────┐
│  Console        │
│  Output         │
└────┬────────────┘
     │ Display: "✓ Market Order Executed Successfully!"
     ▼
   [END]
```

### Validation Data Flow

```
Raw Input
    ↓
┌───────────────────────────────┐
│  Symbol Validation            │
│  ├── Check existence          │
│  ├── Check trading status     │
│  └── Get symbol info          │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│  Quantity Validation          │
│  ├── Get LOT_SIZE filter      │
│  ├── Check min/max            │
│  ├── Apply step size          │
│  └── Round to precision       │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│  Price Validation             │
│  ├── Get PRICE_FILTER         │
│  ├── Check min/max            │
│  ├── Apply tick size          │
│  └── Round to precision       │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│  Notional Validation          │
│  ├── Calculate: qty × price   │
│  ├── Check MIN_NOTIONAL       │
│  └── Verify minimum value     │
└───────────────┬───────────────┘
                ▼
        Validated Data
```

---

## Error Handling Strategy

### Error Hierarchy

```
Exception
    ├── ValidationError (Custom)
    │   ├── Invalid symbol
    │   ├── Invalid quantity
    │   ├── Invalid price
    │   └── Insufficient balance
    │
    ├── BinanceAPIException
    │   ├── Network errors
    │   ├── Authentication errors
    │   ├── Rate limit errors
    │   └── Order rejection
    │
    └── SystemError
        ├── Configuration errors
        └── Environment errors
```

### Error Handling Patterns

#### 1. Try-Catch-Log-Rethrow
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    print(f"User-friendly message: {e}")
    raise  # Re-raise for higher level handling
```

#### 2. Validation at Entry Points
```python
# Fail fast - validate before expensive operations
def place_order(...):
    # Validate all inputs FIRST
    validate_symbol()
    validate_quantity()
    validate_price()
    
    # THEN proceed with API calls
    api_call()
```

#### 3. Retry with Exponential Backoff
```python
def retry_on_failure(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except NetworkError:
            delay = 2 ** attempt  # 1s, 2s, 4s
            sleep(delay)
    raise
```

#### 4. Graceful Degradation
```python
# TWAP: Continue with remaining chunks if one fails
for chunk in chunks:
    try:
        execute_chunk()
    except Exception as e:
        log_error(e)
        ask_user_to_continue()
        # Don't fail entire operation
```

### Error Recovery Strategies

| Error Type | Strategy | Implementation |
|------------|----------|----------------|
| Network timeout | Retry | Exponential backoff, max 3 attempts |
| Invalid input | Fail fast | Validate early, clear error messages |
| Insufficient balance | Graceful fail | Check before order, suggest alternatives |
| Rate limit | Backoff | Sleep and retry with increasing delays |
| Order rejection | Log and notify | Don't retry, inform user with details |
| API authentication | Immediate fail | Clear message, don't retry |

---

## Security Considerations

### 1. API Key Management

```
┌─────────────────────────────────────┐
│  Security Measures                  │
├─────────────────────────────────────┤
│  • .env file (never committed)      │
│  • .gitignore includes .env         │
│  • Environment variables only       │
│  • No hardcoded credentials         │
│  • API keys never logged            │
└─────────────────────────────────────┘
```

**Implementation:**
```python
# ✓ GOOD
API_KEY = os.getenv('BINANCE_API_KEY')

# ✗ BAD
API_KEY = "abc123..."  # Never do this!
```

### 2. Input Sanitization

All user inputs are validated before use:
```python
# Sanitize symbol
symbol = symbol.upper().strip()

# Validate format
if not symbol.endswith('USDT'):
    raise ValidationError("Invalid symbol format")

# Verify against whitelist
if symbol not in exchange_symbols:
    raise ValidationError("Symbol not found")
```

### 3. Logging Security

```python
# ✓ Safe logging
logger.info(f"Order placed: {order_id}")

# ✗ Dangerous logging
logger.info(f"API Key: {API_KEY}")  # Never log credentials!
```

### 4. Testnet First Approach

```python
# Default to testnet for safety
TESTNET = os.getenv('TESTNET', 'True').lower() == 'true'

# Explicit production mode required
if not TESTNET:
    logger.warning("⚠️ PRODUCTION MODE ENABLED")
```

---

## Scalability & Performance

### Performance Optimizations

#### 1. API Call Efficiency
```python
# ✓ Single call to get all info
exchange_info = client.futures_exchange_info()
symbol_info = find_symbol(exchange_info, symbol)

# ✗ Multiple calls
symbol_info = client.get_symbol_info(symbol)  # Call 1
filters = client.get_filters(symbol)          # Call 2
```

#### 2. Caching Strategy
```python
# Cache exchange info (doesn't change often)
@lru_cache(maxsize=1)
def get_exchange_info():
    return client.futures_exchange_info()
```

#### 3. Batch Operations
```python
# TWAP: Execute multiple orders efficiently
orders = []
for chunk in chunks:
    order = execute_chunk()  # Parallel possible
    orders.append(order)
```

### Scalability Considerations

#### Current Limitations
- Single-threaded execution
- Sequential order placement
- No database (state in memory)

#### Future Enhancements
```
Phase 1 (Current)      Phase 2 (Future)        Phase 3 (Advanced)
├── CLI interface      ├── Web interface       ├── Multiple accounts
├── Single account     ├── Multiple symbols    ├── Portfolio management
├── Manual execution   ├── Auto-execution      ├── ML-based strategies
└── File logging       ├── Database storage    └── Real-time analytics
                       └── Async operations
```

---

## Design Decisions

### 1. Why CLI Instead of GUI?

**Decision:** CLI-first approach

**Rationale:**
- ✅ Faster development
- ✅ Easier testing and automation
- ✅ Professional traders prefer CLI
- ✅ Easy to script and integrate
- ✅ Lower resource usage

### 2. Why Separate Files for Each Order Type?

**Decision:** Modular order modules

**Rationale:**
- ✅ Single Responsibility Principle
- ✅ Easy to test individually
- ✅ Clear organization
- ✅ Can use standalone or via bot.py
- ✅ Easy to extend with new types

### 3. Why Both Individual Scripts AND bot.py?

**Decision:** Dual interface

**Rationale:**
- ✅ Flexibility: Use what you prefer
- ✅ Direct execution for simple tasks
- ✅ Unified interface for complex workflows
- ✅ Educational: See both patterns

**Example:**
```bash
# Quick and direct
python src/market_orders.py BTCUSDT BUY 0.01

# Professional and organized
python bot.py market BTCUSDT BUY 0.01
```

### 4. Why Not Use Database?

**Decision:** File-based logging only

**Rationale:**
- ✅ Simpler setup (no DB required)
- ✅ Sufficient for single-user bot
- ✅ Easy to parse logs
- ❌ Not suitable for multi-user (future)

**Trade-off accepted:** Lose historical analysis capability for simplicity

### 5. Why Simulate OCO Instead of Native?

**Decision:** Manual OCO monitoring

**Rationale:**
- ❌ Binance Futures doesn't support native OCO
- ✅ Two separate orders provide transparency
- ✅ User has full control
- ⚠️ Requires manual monitoring (documented)

### 6. Why Python-Binance Library?

**Decision:** Use official wrapper

**Rationale:**
- ✅ Well-maintained and documented
- ✅ Handles authentication automatically
- ✅ Type safety and error handling
- ✅ Community support
- ✅ Saves development time

### 7. Why TWAP Uses Market Orders?

**Decision:** Market orders for TWAP chunks

**Rationale:**
- ✅ Guaranteed execution
- ✅ Faster completion
- ✅ Simpler logic
- ❌ Higher slippage (acceptable trade-off)

**Alternative:** Could use limit orders at mid-price for lower slippage

---

## System Constraints & Assumptions

### Constraints

| Constraint | Value | Reason |
|------------|-------|--------|
| Min order size | Varies by symbol | Binance requirement |
| Min notional | 5 USDT | Binance requirement |
| API rate limit | 1200/min | Binance limitation |
| Max position size | 100k USDT | Safety limit (configurable) |
| Precision | Symbol-dependent | Binance specification |

### Assumptions

1. **Network Reliability:** Assumes stable internet connection
2. **API Availability:** Assumes Binance API is operational
3. **User Knowledge:** Assumes user understands trading concepts
4. **Single Account:** Designed for one account, one bot instance
5. **USDT-M Futures:** Only supports USDT-margined contracts

---

## Testing Architecture

### Testing Pyramid

```
        ┌─────┐
        │  E2E │  ← Full workflow tests
        ├─────┤
        │ INT │    ← Integration tests
        ├─────┤
        │UNIT │    ← Unit tests
        ├─────┤
        │VAL  │    ← Validation tests
        └─────┘
```

**Current Implementation:** Manual testing (TESTING_GUIDE.md)

**Future:** Automated test suite

---

## Deployment Architecture

### Current: Single Instance

```
Developer Machine
    ├── Python Environment
    ├── .env file (credentials)
    ├── Bot application
    └── bot.log (output)
          ↓
    Network Layer
          ↓
    Binance API
```

### Future: Production Deployment

```
                    Load Balancer
                          ↓
        ┌────────────────┬────────────────┐
        ▼                ▼                ▼
    Bot Instance 1   Bot Instance 2   Bot Instance 3
        ↓                ↓                ↓
            Shared Database (Redis/PostgreSQL)
                          ↓
                Binance API + Message Queue
```

---

## Monitoring & Observability

### Current Logging Structure

```
bot.log
├── Timestamp
├── Log Level (INFO, WARNING, ERROR)
├── Module Name
├── Message
└── Exception Traceback (if error)
```

### Future Monitoring

```
Logging → Aggregation → Analysis → Alerts
  ↓           ↓           ↓          ↓
File    →   ELK/      → Metrics  → Email/
            Splunk       Dashboard   SMS
```

---

## Conclusion

This architecture provides:

✅ **Modularity:** Easy to extend and modify
✅ **Maintainability:** Clear structure and documentation
✅ **Reliability:** Robust error handling and validation
✅ **Security:** Safe credential management
✅ **Performance:** Efficient API usage
✅ **Scalability:** Foundation for future growth

The design prioritizes **simplicity and correctness** for the current requirements while maintaining **flexibility** for future enhancements.