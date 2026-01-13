# Exchange Support

## Overview

MYCELIUM supports **111+ cryptocurrency exchanges** through CCXT (CryptoCurrency eXchange Trading Library), providing a universal abstraction layer for both centralized (CEX) and decentralized (DEX) trading venues.

## Supported Exchanges

All exchanges supported by CCXT are automatically available in MYCELIUM. Simply change the exchange name in your configuration to switch venues.

### Popular Exchanges

**Centralized Exchanges (CEX):**
- Binance
- Bybit
- OKX
- Kraken
- KuCoin
- Coinbase / Coinbase Advanced
- Bitvavo
- Gate.io
- HTX (formerly Huobi)
- And 100+ more...

**Decentralized Exchanges (DEX):**
- Hyperliquid
- dYdX
- And more...

### Full Exchange List

For the complete list of supported exchanges, see the [CCXT documentation](https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets).

## How to Switch Exchanges

### Via Configuration File

Edit your `config.prod.json`:

```json
{
  "exchange": {
    "name": "binance",  // Change to any CCXT-supported exchange
    "key": "your-api-key",
    "secret": "your-api-secret"
  }
}
```

### Via UI

1. Navigate to the **Exchange** tab in the monitoring UI
2. Select your desired exchange from the dropdown
3. Enter API credentials
4. Save configuration

## Exchange-Specific Notes

### Fidelity Crypto (Fidelity Digital Assets)

**Status:** ⚠️ **Not Currently Supported**

Fidelity Crypto (Fidelity Digital Assets) is not currently available through CCXT and therefore cannot be used with MYCELIUM at this time.

**Alternative Options:**
- **Coinbase:** Fidelity partners with Coinbase for crypto custody services. Using Coinbase or Coinbase Advanced may provide similar functionality.
- **Future Support:** If CCXT adds Fidelity Crypto support in the future, it will automatically become available in MYCELIUM without any code changes.

### Coinbase vs Coinbase Advanced

- **coinbase:** Standard Coinbase API (retail-focused)
- **coinbaseadvanced:** Advanced trading API (lower fees, more features)
- **coinbaseinternational:** For international users

For most trading use cases, we recommend using `coinbaseadvanced`.

### DEX Support

MYCELIUM supports decentralized exchanges through CCXT's DEX connectors:
- **Hyperliquid:** Native DEX with perpetual futures
- **dYdX v4:** Decentralized perpetual exchange
- Additional DEXes as they become available in CCXT

## Adding New Exchanges

MYCELIUM automatically supports any exchange added to CCXT. To request support for a new exchange:

1. Check if it's already in CCXT: https://github.com/ccxt/ccxt/wiki/Exchange-Markets
2. If not, request it in the CCXT repository: https://github.com/ccxt/ccxt/issues
3. Once added to CCXT, it will work with MYCELIUM immediately

## API Credentials

### Security Best Practices

- ✅ Use API keys with minimal required permissions
- ✅ Enable IP whitelisting on your exchange account
- ✅ Use read-only keys for monitoring/backtesting
- ✅ Store credentials securely (environment variables or secure vault)
- ❌ Never commit API keys to version control
- ❌ Never share API secrets

### Required Permissions

For MYCELIUM to function properly, your API keys typically need:
- **Trade:** Place, cancel, and modify orders
- **Read:** View balances, positions, and order history
- **Optional:** Withdraw permissions are NOT required (and should be disabled)

## Troubleshooting

### Exchange Connection Issues

1. **Verify API Credentials:** Double-check your API key and secret
2. **Check IP Whitelist:** Ensure your server IP is whitelisted
3. **Review Rate Limits:** Some exchanges have strict rate limiting
4. **Test Connection:** Use the "Test Connection" button in the UI

### Exchange Not Listed

If an exchange is not visible in the dropdown:
1. Verify it's supported by CCXT
2. Check CCXT version: `pip show ccxt`
3. Update CCXT: `pip install --upgrade ccxt`
4. Restart the application

## Resources

- [CCXT Documentation](https://docs.ccxt.com/)
- [CCXT GitHub](https://github.com/ccxt/ccxt)
- [Supported Exchanges](https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets)
- [CCXT Manual](https://docs.ccxt.com/#/README)
