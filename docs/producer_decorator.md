# Producer Decorator for Freqtrade Strategies

The `@producer` decorator allows strategies to broadcast indicators to configured producers, following the same interface as the existing `@informative` decorator but in the opposite direction (broadcast vs fetch).

## Key Features

- **Drop-in Replacement**: Same parameters as `@informative` decorator
- **Zero Interface Changes**: No modifications to DataProvider or strategy interface
- **Producer/Consumer Integration**: Uses existing WebSocket infrastructure
- **Mode-aware**: Only works in dry-run/live modes, silently skipped in backtest
- **Code Reuse**: Leverages existing informative infrastructure

## Usage

### Basic Usage

```python
from freqtrade.strategy import IStrategy, producer

class MyStrategy(IStrategy):
    
    @producer('1h')  # Same interface as @informative
    def populate_producer_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Local indicators for this strategy
        return dataframe
```

### Parameters (Same as @informative)

```python
@producer(
    timeframe: str,                    # Required: Timeframe for producer data
    asset: str = "",                  # Optional: Specific asset (BTC/USDT, ETH/BTC, etc.)
    fmt: str | Callable = None,       # Optional: Column naming format
    *,                                
    candle_type: CandleType = None,    # Optional: Candle type (spot, mark, index, etc.)
    ffill: bool = True,               # Optional: Forward fill (kept for compatibility)
)
```

### Examples

#### Different Timeframes
```python
@producer('1h')
def populate_producer_1h(self, dataframe, metadata):
    return dataframe

@producer('4h') 
def populate_producer_4h(self, dataframe, metadata):
    return dataframe
```

#### Specific Assets
```python
@producer('1h', asset='BTC/USDT')
def populate_producer_btc(self, dataframe, metadata):
    # Broadcast BTC indicators for other strategies to consume
    return dataframe

@producer('15m', asset='ETH/USDT')
def populate_producer_eth(self, dataframe, metadata):
    # Broadcast ETH indicators
    return dataframe
```

#### Custom Column Formatting
```python
@producer('30m', fmt='mybot_{column}_{timeframe}')
def populate_producer_custom_format(self, dataframe, metadata):
    # Columns become: mybot_rsi_30m, mybot_sma_30m, etc.
    dataframe['rsi'] = ta.RSI(dataframe)
    return dataframe

@producer('1h', fmt=lambda column, **kwargs: f"custom_{column}")
def populate_producer_callable_format(self, dataframe, metadata):
    # Use callable formatter
    dataframe['macd'] = ta.MACD(dataframe)
    return dataframe
```

#### Different Candle Types
```python
@producer('1h', candle_type='mark')
def populate_producer_mark_price(self, dataframe, metadata):
    # Broadcast using mark price candles
    return dataframe
```

## Integration with Producer/Consumer System

The `@producer` decorator integrates seamlessly with freqtrade's existing producer/consumer architecture:

### Producer Configuration
```json
{
    "producer": {
        "enabled": true
    }
}
```

### Consumer Usage
Other freqtrade instances can consume broadcasted indicators:

```json
{
    "external_message_consumer": {
        "enabled": true,
        "producers": [
            {
                "name": "default",
                "host": "localhost", 
                "port": 8080,
                "ws_token": "your-token"
            }
        ]
    }
}
```

## Differences from @informative

| Feature | @informative | @producer |
|----------|--------------|-----------|
| **Purpose** | Fetch external data | Broadcast calculated indicators |
| **Direction** | Import data | Export data |
| **Data Flow** | Exchange → Strategy | Strategy → WebSocket |
| **Use Case** | Multi-timeframe analysis | Sharing indicators between bots |
| **Integration** | Merges into main dataframe | Broadcasts as analyzed_df |
| **Active Modes** | All modes | Dry-run and live only |

## Technical Implementation

### No Interface Changes
- Reuses existing strategy discovery mechanisms
- Leverages informative helper functions
- Uses same reflection-based metadata attachment
- Zero breaking changes

### Performance Optimizations
- Limited to 1500 candles per broadcast
- Only processes in dry-run/live modes
- Uses existing WebSocket infrastructure
- Graceful fallback if producer unavailable

### Error Handling
- Silently skipped in unsupported modes
- Warning logging for unavailable markets
- Exception handling for broadcast failures
- No impact on strategy execution

## Advanced Usage

### Multiple Producers
```python
class MultiProducerStrategy(IStrategy):
    
    @producer('1h')
    def producer_hourly(self, dataframe, metadata):
        return dataframe
    
    @producer('4h')
    def producer_4hourly(self, dataframe, metadata):
        return dataframe
    
    @producer('1h', asset='BTC/USDT')
    def producer_btc(self, dataframe, metadata):
        return dataframe
```

### Combining with Informative
```python
class HybridStrategy(IStrategy):
    
    @producer('1h')
    def broadcast_hourly(self, dataframe, metadata):
        # Broadcast our indicators
        dataframe['my_rsi'] = ta.RSI(dataframe)
        return dataframe
    
    @informative('4h')
    def fetch_4hour_data(self, dataframe, metadata):
        # Fetch external data
        dataframe['external_sma'] = ta.SMA(dataframe)
        return dataframe
    
    def populate_indicators(self, dataframe, metadata: dict) -> DataFrame:
        # Local indicators using both sources
        # dataframe includes my_rsi_1h (from producer)  
        # dataframe includes external_sma_4h (from informative)
        return dataframe
```

## Monitoring and Debugging

### Logging
Producer operations are logged:
```
DEBUG: Broadcasted producer data for BTC/USDT 1h
WARNING: Failed to broadcast producer data for ETH/USDT: Connection error
WARNING: Market XYZ/USDT is not available for producer broadcasting.
```

### WebSocket Messages
Broadcast uses same format as analyzed_df:
```json
{
    "type": "analyzed_df",
    "data": {
        "key": ["BTC/USDT", "1h", "spot"],
        "df": {/* DataFrame with indicator columns */},
        "la": "2023-01-01T00:00:00Z"
    }
}
```

## Best Practices

1. **Use meaningful timeframes**: Higher timeframes are better for sharing between strategies
2. **Limit broadcasted data**: Only broadcast essential indicators to reduce bandwidth
3. **Consistent naming**: Use clear column naming to avoid conflicts
4. **Monitor performance**: Broadcasting adds overhead, use judiciously
5. **Test thoroughly**: Verify consumer strategies can properly use broadcasted data

## Troubleshooting

### Producer Not Broadcasting
- Check runmode is dry-run or live
- Verify producer configuration is enabled
- Ensure WebSocket connection is available
- Check logs for error messages

### Data Not Available to Consumers
- Verify producer and consumer configurations match
- Check WebSocket connectivity between instances
- Ensure proper format and column naming
- Monitor for data validation errors

### Performance Issues
- Reduce broadcasted timeframe frequency
- Limit number of producer decorators
- Monitor DataFrame sizes
- Consider custom filtering strategies

This implementation provides a clean, consistent way to broadcast indicators between freqtrade instances while maintaining full compatibility with existing strategies.