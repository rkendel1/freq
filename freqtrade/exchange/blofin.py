import logging
import time
from datetime import datetime
from typing import Any

import ccxt

from freqtrade.constants import Config, ExchangeConfig
from freqtrade.enums import MarginMode, TradingMode
from freqtrade.exceptions import DDosProtection, OperationalException, TemporaryError
from freqtrade.exchange import Exchange
from freqtrade.exchange.common import retrier
from freqtrade.exchange.exchange_types import CcxtOrder


logger = logging.getLogger(__name__)


class Blofin(Exchange):
    """
    BloFin exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.
    """

    _ft_has: dict = {
        "stoploss_on_exchange": False,  # BloFin may not support stop-loss orders on exchange
        "ohlcv_candle_limit": 5000,
        "trades_pagination": "id",
        "trades_pagination_arg": "fromId",
        "l2_limit_range": [1, 200],
        "l2_limit_range_required": False,
    }

    _supported_trading_mode_margin_pairs = [
        (TradingMode.FUTURES, MarginMode.CROSS),
        (TradingMode.FUTURES, MarginMode.ISOLATED),
    ]

    def __init__(self, config: Config, *, exchange_config: ExchangeConfig | None = None, **kwargs):
        """
        Initialize the BloFin exchange.
        """
        logger.info("Initializing BloFin exchange")
        super().__init__(config, exchange_config=exchange_config, **kwargs)
        
        # Override ccxt's fetchFundingHistory with our custom implementation
        self._api.fetchFundingHistory = self._ccxt_fetch_funding_history

    def _ccxt_fetch_funding_history(self, symbol=None, since=None, limit=None, params={}):
        """
        Wrapper method to make our custom fetchFundingHistory compatible with ccxt calls.
        """
        return self.fetchFundingHistory(symbol, since, limit, params)

    def get_tickers(self, symbols=None, *, cached=False, market_type=None):
        """
        Override get_tickers for BloFin exchange.
        Fix quoteVolume by mapping from BloFin's volCurrency24h.
        """
        tickers = super().get_tickers(symbols, cached=cached, market_type=market_type)
        
        # Fix quoteVolume for BloFin tickers
        fixed_count = 0
        for symbol, ticker in tickers.items():
            if ticker.get('quoteVolume') is None and ticker.get('info'):
                # BloFin provides volume in volCurrency24h
                vol_currency = ticker['info'].get('volCurrency24h')
                if vol_currency is not None:
                    try:
                        ticker['quoteVolume'] = float(vol_currency)
                        fixed_count += 1
                    except (ValueError, TypeError):
                        # Fallback to baseVolume if conversion fails
                        ticker['quoteVolume'] = ticker.get('baseVolume', 0)
                        
        if fixed_count > 0:
            logger.debug("🔧 BloFin: Fixed quoteVolume for %d tickers", fixed_count)
        return tickers

    @retrier
    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """
        Fetch order from exchange.
        BloFin doesn't have a direct fetchOrder method, so we emulate it
        using fetchOpenOrders and fetchClosedOrders.
        """
        if params is None:
            params = {}

        try:
            # First try to find in open orders
            open_orders = self._api.fetch_open_orders(pair, params=params)
            for order in open_orders:
                if order['id'] == order_id:
                    return order

            # If not found in open orders, try closed orders
            closed_orders = self._api.fetch_closed_orders(pair, params=params)
            for order in closed_orders:
                if order['id'] == order_id:
                    return order

            # If still not found, raise an error
            raise ccxt.OrderNotFound(f"Order {order_id} not found for {pair}")

        except ccxt.BaseError as e:
            logger.error("Error fetching order %s for %s: %s", order_id, pair, e)
            raise

    def _set_leverage(
        self,
        leverage: float,
        pair: str | None = None,
        accept_fail: bool = False,
    ):
        """
        Set leverage for BloFin exchange.
        BloFin requires integer leverage values.
        """
        logger.info("🔧 _set_leverage called with leverage=%s (type: %s) for pair=%s", leverage, type(leverage), pair)
        
        if self._config["dry_run"] or not self.exchange_has("setLeverage"):
            logger.info("🔧 Skipping leverage setting: dry_run=%s, "
                       "has_setLeverage=%s", self._config['dry_run'],
                       self.exchange_has('setLeverage'))
            return

        try:
            # Ensure leverage is an integer for BloFin (this is the key fix)
            leverage_int = int(round(leverage))
            logger.info("🔧 Converting leverage %s -> %s (integer)", leverage, leverage_int)
            
            # Get margin mode for BloFin API (required parameter)
            configured_margin_mode = self._config.get("margin_mode", "cross")
            if configured_margin_mode == "isolated":
                blofin_margin_mode = "isolated"
            else:
                blofin_margin_mode = "cross"

            logger.info("⚖️ Setting leverage for %s to %sx with marginMode=%s", pair, leverage_int, blofin_margin_mode)
            # BloFin API requires marginMode to be passed in params
            params = {'marginMode': blofin_margin_mode}
            res = self._api.set_leverage(symbol=pair, leverage=leverage_int, params=params)
            self._log_exchange_response("set_leverage", res)
            logger.info("🔧 Successfully set leverage for %s to %sx with marginMode=%s", pair, leverage_int, blofin_margin_mode)
        except ccxt.DDoSProtection as e:
            logger.warning("🔧 Rate limit exceeded when setting leverage for %s", pair)
            raise DDosProtection(e) from e
        except (ccxt.BadRequest, ccxt.OperationRejected, ccxt.InsufficientFunds) as e:
            logger.error("🔧 Failed to set leverage for %s: %s", pair, e)
            if not accept_fail:
                raise TemporaryError(
                    f"Could not set leverage due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.BaseError as e:
            logger.error("🔧 Unexpected error setting leverage for %s: %s", pair, e)
            if not accept_fail:
                raise OperationalException(e) from e

    def _lev_prep(self, pair: str, leverage: float, side: str, accept_fail: bool = False):
        """
        Leverage preparation for BloFin.
        Ensures leverage is set before trades.
        """
        if self._config["dry_run"]:
            return

        logger.info("🔧 Preparing leverage for %s: %sx, side: %s", pair, leverage, side)

        try:
            # Ensure leverage is properly set for this pair
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=accept_fail)
        except Exception as e:
            logger.error("🔧 Failed to prepare leverage for %s: %s", pair, e)
            if not accept_fail:
                raise

    def set_margin_mode(self, pair: str, margin_mode: MarginMode, accept_fail: bool = False):
        """
        Set margin mode for BloFin exchange.
        """
        logger.info("🔧 set_margin_mode called: pair=%s, margin_mode=%s", pair, margin_mode)
        
        if self._config["dry_run"]:
            logger.info("🔧 Dry run mode, skipping margin mode setting")
            return

        if not self.exchange_has("setMarginMode"):
            logger.warning("🔧 Exchange doesn't support setMarginMode")
            return

        try:
            # Convert freqtrade MarginMode to BloFin margin mode string
            if margin_mode == MarginMode.ISOLATED:
                blofin_margin_mode = "isolated"
            elif margin_mode == MarginMode.CROSS:
                blofin_margin_mode = "cross"
            else:
                logger.error("🔧 Unsupported margin mode: %s", margin_mode)
                if not accept_fail:
                    raise OperationalException(f"Unsupported margin mode: {margin_mode}")
                return

            logger.info("🔧 Setting margin mode for %s to %s", pair, blofin_margin_mode)
            res = self._api.set_margin_mode(symbol=pair, marginMode=blofin_margin_mode)
            self._log_exchange_response("set_margin_mode", res)
            logger.info("🔧 Successfully set margin mode for %s to %s", pair, blofin_margin_mode)
                        
        except ccxt.DDoSProtection as e:
            logger.warning("🔧 Rate limit exceeded when setting margin mode for %s", pair)
            raise DDosProtection(e) from e
        except (ccxt.BadRequest, ccxt.OperationRejected) as e:
            logger.error("🔧 Failed to set margin mode for %s: %s", pair, e)
            if not accept_fail:
                raise TemporaryError(
                    f"Could not set margin mode due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.BaseError as e:
            logger.error("🔧 Unexpected error setting margin mode for %s: %s", pair, e)
            if not accept_fail:
                raise OperationalException(e) from e

    def get_margin_mode(self, pair: str) -> MarginMode:
        """
        Get current margin mode for a trading pair.
        """
        logger.info("🔧 get_margin_mode called for pair=%s", pair)
        
        if self._config["dry_run"]:
            # In dry run, return the configured margin mode
            configured_mode = self._config.get("margin_mode", "cross")
            if configured_mode == "isolated":
                return MarginMode.ISOLATED
            else:
                return MarginMode.CROSS

        if not self.exchange_has("fetchMarginMode"):
            logger.warning("🔧 Exchange doesn't support fetchMarginMode, defaulting to cross")
            return MarginMode.CROSS

        try:
            logger.info("🔧 Fetching margin mode for %s", pair)
            margin_mode_data = self._api.fetch_margin_mode(symbol=pair)
            
            if margin_mode_data:
                # Parse the margin mode from the response
                margin_mode_str = margin_mode_data.get('marginMode', 'cross')
                if margin_mode_str == "isolated":
                    return MarginMode.ISOLATED
                else:
                    return MarginMode.CROSS
            else:
                logger.warning("🔧 No margin mode data for %s, defaulting to cross", pair)
                return MarginMode.CROSS
                
        except ccxt.BaseError as e:
            logger.warning("🔧 Error fetching margin mode for %s: %s, defaulting to cross", pair, e)
            return MarginMode.CROSS

    def _get_params(
        self,
        side: str,
        ordertype: str,
        leverage: float,
        reduceOnly: bool,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Override _get_params to include BloFin-specific parameters like margin mode and leverage.
        """
        # Get base parameters from parent
        params = super()._get_params(side, ordertype, leverage, reduceOnly, time_in_force)
        
        # Add BloFin-specific parameters for futures trading
        if self.trading_mode == TradingMode.FUTURES:
            # Add margin mode parameter
            configured_margin_mode = self._config.get("margin_mode", "cross")
            if configured_margin_mode == "isolated":
                blofin_margin_mode = "isolated"
            else:
                blofin_margin_mode = "cross"
            
            params['marginMode'] = blofin_margin_mode
            logger.info("🛒 Adding marginMode=%s to order parameters", blofin_margin_mode)
            
            # # Add leverage parameter if leverage > 1
            # if leverage and leverage > 1:
            #     # Ensure leverage is an integer for BloFin
            #     leverage_int = int(round(leverage))
            #     leverage_int = max(1, min(leverage_int, 100))  # Clamp to reasonable range
            #     params['leverage'] = leverage_int
            #     logger.info("🛒 Adding leverage=%s to order parameters", leverage_int)
        
        return params

    def create_order(
        self,
        *,
        pair: str,
        ordertype: str,
        side: str,
        amount: float,
        rate: float,
        leverage: float,
        reduceOnly: bool = False,
        time_in_force: str = "GTC",
    ) -> CcxtOrder:
        """
        Override create_order to ensure leverage is set before creating the order.
        Margin mode is automatically included via _get_params() method.
        """
        logger.info(
            f"🛒 create_order called: pair={pair}, side={side}, "
            f"amount={amount}, rate={rate}, leverage={leverage} (type: {type(leverage)})"
        )
        
        # Ensure leverage is set before creating order
        if leverage and leverage > 1:
            logger.info("⚖️ Setting leverage %sx for %s before creating order", leverage, pair)
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=True)
        else:
            logger.info("🛒 No leverage setting needed (leverage=%s)", leverage)

        # Call parent create_order method - margin mode will be added via _get_params()
        result = super().create_order(
            pair=pair,
            ordertype=ordertype,
            side=side,
            amount=amount,
            rate=rate,
            leverage=leverage,
            reduceOnly=reduceOnly,
            time_in_force=time_in_force,
        )
        
        logger.info("🛒 Order created successfully: %s", result.get('id', 'unknown_id'))
        return result

    def get_max_leverage(self, pair: str, stake_amount: float | None) -> float:
        """
        Get maximum leverage for a trading pair from BloFin.
        Tries to fetch real leverage limits, falls back to conservative defaults.
        """
        logger.info("🔧 get_max_leverage called for pair=%s, stake_amount=%s", pair, stake_amount)
        
        if self.trading_mode != TradingMode.FUTURES:
            logger.info("🔧 Not futures mode, returning 1.0")
            return 1.0
        
        # First check if we have leverage tiers loaded
        if hasattr(self, '_leverage_tiers') and pair in self._leverage_tiers:
            logger.info("🔧 Using cached leverage tiers for %s", pair)
            return super().get_max_leverage(pair, stake_amount)
        
        # Try to fetch leverage information directly from BloFin
        try:
            logger.info("🔧 Attempting to fetch leverage info for %s from BloFin", pair)
            
            # Method 1: Try fetchMarketLeverageTiers if supported
            if self.exchange_has("fetchMarketLeverageTiers"):
                logger.info("🔧 Fetching market leverage tiers for %s", pair)
                tiers = self._api.fetch_market_leverage_tiers(pair)
                if tiers:
                    # Extract max leverage from tiers
                    max_leverage = max(tier.get('maxLeverage', 1.0) for tier in tiers)
                    logger.info("🔧 Found max leverage %s for %s from market tiers", max_leverage, pair)
                    return float(max_leverage)
            
            # Method 2: Try fetchLeverageTiers if supported
            if self.exchange_has("fetchLeverageTiers"):
                logger.info("🔧 Fetching all leverage tiers from BloFin")
                all_tiers = self._api.fetch_leverage_tiers()
                if pair in all_tiers:
                    pair_tiers = all_tiers[pair]
                    max_leverage = max(tier.get('maxLeverage', 1.0) for tier in pair_tiers)
                    logger.info("🔧 Found max leverage %s for %s from leverage tiers", max_leverage, pair)
                    return float(max_leverage)
            
            # Method 3: Check market limits
            if pair in self.markets:
                market = self.markets[pair]
                if 'limits' in market and 'leverage' in market['limits']:
                    leverage_limit = market['limits']['leverage']
                    if leverage_limit and 'max' in leverage_limit and leverage_limit['max']:
                        max_leverage = float(leverage_limit['max'])
                        logger.info("🔧 Found max leverage %s for %s from market limits", max_leverage, pair)
                        return max_leverage
            
            # Method 4: Try to get from market info
            if pair in self.markets:
                market = self.markets[pair]
                if 'info' in market and market['info']:
                    market_info = market['info']
                    # Look for common leverage fields in market info
                    for field in ['maxLeverage', 'max_leverage', 'leverageMax', 'leverage_max']:
                        if field in market_info and market_info[field]:
                            max_leverage = float(market_info[field])
                            logger.info("🔧 Found max leverage %s for %s from market info field %s", 
                                       max_leverage, pair, field)
                            return max_leverage
                            
        except Exception as e:
            logger.warning("🔧 Failed to fetch leverage info for %s: %s", pair, e)
        
        # Fallback: Return reasonable defaults based on pair type
        if pair in self.markets:
            market = self.markets[pair]
            base_currency = market.get('base', '').upper()
            
            # Higher leverage for major pairs, lower for altcoins
            if base_currency in ['BTC', 'ETH', 'BNB']:
                max_leverage = 100.0
                logger.info("🔧 Using major pair default leverage %s for %s", max_leverage, pair)
            elif base_currency in ['ADA', 'SOL', 'AVAX', 'MATIC', 'DOT', 'LINK']:
                max_leverage = 75.0
                logger.info("🔧 Using popular altcoin default leverage %s for %s", max_leverage, pair)
            else:
                max_leverage = 50.0
                logger.info("🔧 Using conservative default leverage %s for %s", max_leverage, pair)
        else:
            max_leverage = 20.0
            logger.info("🔧 Using ultra-conservative default leverage %s for unknown pair %s", max_leverage, pair)
        
        return max_leverage

    def load_leverage_tiers(self) -> dict[str, list[dict]]:
        """
        Load leverage tiers from BloFin if supported.
        """
        if self.trading_mode != TradingMode.FUTURES:
            return {}
            
        logger.info("🔧 Loading leverage tiers from BloFin")
        
        try:
            # Try to use parent implementation first
            if self.exchange_has("fetchLeverageTiers") or self.exchange_has("fetchMarketLeverageTiers"):
                logger.info("🔧 BloFin supports leverage tiers, using parent implementation")
                return super().load_leverage_tiers()
            else:
                logger.info("🔧 BloFin doesn't support leverage tiers API, returning empty dict")
                return {}
                
        except Exception as e:
            logger.warning("🔧 Failed to load leverage tiers from BloFin: %s", e)
            return {}

    def dry_run_liquidation_price(
        self,
        pair: str,
        open_rate: float,
        is_short: bool,
        amount: float,
        stake_amount: float,
        leverage: float,
        wallet_balance: float,
        open_trades: list,
    ) -> float | None:
        """
        Important: Must be implemented to prevent errors in the margin mode

        Calculate the liquidation price for dry-run mode.
        In dry-run, we can return a reasonable estimate or None.
        """
        return None

    def fetch_funding_rates(self, symbols: list[str] | None = None) -> dict[str, dict[str, float]]:
        """
        Fetch funding rates for the given symbols.
        :param symbols: List of symbols to fetch funding rates for
        :return: Dict of funding rates for the given symbols
        """
        logger.info("🔧 fetch_funding_rates called for symbols: %s", symbols)
        
        try:
            if self.trading_mode != TradingMode.FUTURES:
                logger.info("🔧 Not futures mode, returning empty funding rates")
                return {}
            
            if symbols is None:
                # If no symbols specified, use all available pairs
                symbols = list(self.markets.keys())
                logger.info("🔧 Using all available symbols: %s pairs", len(symbols))
            
            # BloFin supports fetchFundingRate but not fetchFundingRates (plural)
            # So we need to fetch each symbol individually
            funding_rates = {}
            
            for symbol in symbols:
                try:
                    logger.info("🔧 Fetching funding rate for %s", symbol)
                    rate_data = self._api.fetch_funding_rate(symbol)
                    
                    if rate_data:
                        funding_rates[symbol] = {
                            'fundingRate': rate_data.get('fundingRate', 0.0),
                            'fundingTimestamp': rate_data.get('fundingTimestamp'),
                            'nextFundingTime': rate_data.get('nextFundingTime'),
                            'info': rate_data.get('info', {})
                        }
                        logger.info("🔧 Got funding rate for %s: %s", symbol, rate_data.get('fundingRate', 0.0))
                    else:
                        logger.warning("🔧 No funding rate data for %s", symbol)
                        
                except ccxt.BaseError as e:
                    logger.warning("🔧 Failed to fetch funding rate for %s: %s", symbol, e)
                    continue
            
            logger.info("🔧 Successfully fetched funding rates for %s symbols", len(funding_rates))
            return funding_rates
            
        except ccxt.DDoSProtection as e:
            logger.warning("🔧 Rate limit exceeded when fetching funding rates")
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            logger.error("🔧 Exchange error fetching funding rates: %s", e)
            raise TemporaryError(
                f"Error fetching funding rates due to {e.__class__.__name__}. Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            logger.error("🔧 Unexpected error fetching funding rates: %s", e)
            raise OperationalException(e) from e

    def fetchFundingHistory(self, symbol=None, since=None, limit=None, params={}):
        """
        Custom implementation of fetchFundingHistory for BloFin.
        
        BloFin's ccxt implementation reports fetchFundingHistory as supported but throws
        NotSupported error. This custom implementation uses the asset/bills endpoint
        to retrieve actual funding payments.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT:USDT')
            since: Timestamp in milliseconds to start from
            limit: Maximum number of entries to return
            params: Additional parameters
            
        Returns:
            List of funding history entries with standardized format:
            [
                {
                    'info': {...},           # Raw API response
                    'symbol': 'BTC/USDT:USDT',
                    'code': 'USDT',
                    'timestamp': 1234567890000,
                    'datetime': '2023-01-01T00:00:00.000Z',
                    'id': 'bill_id',
                    'amount': -0.001,        # Funding fee amount (negative = paid)
                    'type': 'funding'
                }
            ]
        """
        logger.info("🔧 fetchFundingHistory called for %s, since: %s, limit: %s", symbol, since, limit)
        
        try:
            # BloFin uses asset/bills to get funding payments
            # We need to filter for funding-related bill types
            request_params = {}
            if since is not None:
                request_params['after'] = str(since)
            if limit is not None:
                request_params['limit'] = str(limit)
            else:
                request_params['limit'] = '100'  # Default limit
                
            # Get bills from BloFin
            response = self._api.private_get_asset_bills(request_params)
            bills = response.get('data', [])
            
            logger.info("🔧 Retrieved %s bills from BloFin", len(bills))
            
            # Log first few bills to understand structure
            if bills:
                logger.info("🔧 Sample bill structure: %s", bills[0])
                
                # Log bill types for debugging
                bill_types = set()
                account_transfers = 0
                instrument_bills = 0
                
                for bill in bills[:10]:  # Check first 10 bills
                    if 'type' in bill:
                        bill_types.add(bill['type'])
                    if 'fromAccount' in bill or 'toAccount' in bill:
                        account_transfers += 1
                    if 'instId' in bill and bill['instId']:
                        instrument_bills += 1
                
                logger.info("🔧 Bill analysis - Types found: %s, Account transfers: %d, Instrument bills: %d", 
                           list(bill_types), account_transfers, instrument_bills)
            
            # Filter for funding-related bills and parse them
            funding_history = []
            for bill in bills:
                # BloFin bills might not have a 'type' field, so check for funding indicators
                # Look for bills that are funding-related based on available fields
                is_funding_related = False
                
                # Check various possible indicators of funding payments
                if 'type' in bill:
                    bill_type = bill.get('type', '').lower()
                    is_funding_related = any(keyword in bill_type for keyword in ['funding', 'fund'])
                else:
                    # If no type field, look for other indicators
                    # Funding payments usually have instId (instrument) and specific patterns
                    has_instrument = bool(bill.get('instId'))
                    has_transfer_accounts = 'fromAccount' in bill or 'toAccount' in bill
                    
                    # Skip account transfers (funding <-> trading)
                    if has_transfer_accounts:
                        from_account = bill.get('fromAccount', '')
                        to_account = bill.get('toAccount', '')
                        if from_account in ['funding', 'trading'] or to_account in ['funding', 'trading']:
                            continue  # Skip account transfers
                    
                    # Look for funding-specific patterns
                    if has_instrument and not has_transfer_accounts:
                        # This might be a position-related bill (could include funding)
                        is_funding_related = True
                
                if is_funding_related:
                    inst_id = bill.get('instId', '')
                    if symbol is None or self.safe_symbol(inst_id) == symbol:
                        parsed_entry = self._parse_funding_history_entry(bill)
                        if parsed_entry:
                            funding_history.append(parsed_entry)
            
            logger.info("🔧 Found %s funding history entries after filtering", len(funding_history))
            return funding_history
            
        except Exception as e:
            logger.error("🔧 Error in custom fetchFundingHistory: %s", e)
            # Return empty list instead of raising exception to allow fallback
            return []

    def _parse_funding_history_entry(self, bill):
        """Parse a bill entry into funding history format."""
        try:
            timestamp = self.safe_integer(bill, 'ts')
            
            # BloFin bills may use different fields for amount based on structure
            amount = (self.safe_float(bill, 'amount') or 
                     self.safe_float(bill, 'bal') or 
                     self.safe_float(bill, 'balChg') or 
                     self.safe_float(bill, 'size'))
            
            inst_id = bill.get('instId', '')
            symbol = self.safe_symbol(inst_id) if inst_id else None
            
            # Get currency from various possible fields
            currency = (bill.get('currency') or 
                       bill.get('ccy') or 
                       bill.get('settleCcy'))
            
            return {
                'info': bill,
                'symbol': symbol,
                'code': currency,
                'timestamp': timestamp,
                'datetime': self.iso8601(timestamp) if timestamp else None,
                'id': bill.get('transferId') or bill.get('billId') or bill.get('id'),
                'amount': amount,
                'type': bill.get('type', 'funding'),
            }
        except Exception as e:
            logger.warning("🔧 Error parsing funding history entry: %s", e)
            return None

    def _get_funding_fees_from_exchange(
        self, pair: str, since: int | None
    ) -> list[dict[str, Any]]:
        """
        Fetch funding fees from exchange using custom fetchFundingHistory.
        """
        logger.info("🔧 _get_funding_fees_from_exchange called for %s, since: %s", pair, since)
        
        try:
            # Use our custom fetchFundingHistory method directly
            funding_history = self.fetchFundingHistory(symbol=pair, since=since)
            
            if funding_history:
                logger.info("🔧 Found %s funding history entries for %s", len(funding_history), pair)
                return funding_history
            else:
                logger.info("🔧 No funding history found for %s", pair)
                return []
                
        except Exception as e:
            logger.warning("🔧 Error fetching funding history for %s: %s", pair, e)
            # Return empty list to fallback to calculation method
            return []
            
            if funding_history:
                logger.info("🔧 Found %s funding history entries for %s", len(funding_history), pair)
                return funding_history
            else:
                logger.info("🔧 No funding history found for %s", pair)
                return []
                
        except ccxt.BaseError as e:
            logger.warning("🔧 Error fetching funding history for %s: %s", pair, e)
            # Return empty list to fallback to calculation method
            return []

    def get_funding_fees(
        self, pair: str, amount: float, is_short: bool, open_date: datetime
    ) -> float:
        """
        Calculate funding fees for a position.
        Enhanced to use funding rate history when funding history is not available.
        """
        logger.info("🔧 get_funding_fees called for %s, amount: %s, is_short: %s", pair, amount, is_short)
        
        try:
            # Try to get funding fees from exchange first
            since_timestamp = int(open_date.timestamp() * 1000)  # Convert to milliseconds
            funding_history = self._get_funding_fees_from_exchange(pair, since_timestamp)
            
            if funding_history:
                # Calculate actual funding fees from exchange data
                total_funding = 0.0
                for entry in funding_history:
                    funding_amount = entry.get('amount', 0.0)
                    if funding_amount:
                        total_funding += funding_amount
                
                logger.info("🔧 Calculated funding fees from exchange: %s", total_funding)
                return total_funding
            else:
                # Fallback to calculation using funding rate history
                logger.info("🔧 Funding history not available, trying funding rate history...")
                try:
                    # Use fetchFundingRateHistory which BloFin supports
                    rate_history = self._api.fetch_funding_rate_history(pair, since=since_timestamp, limit=100)
                    
                    if rate_history:
                        logger.info("🔧 Found %s funding rate entries for calculation", len(rate_history))
                        
                        # Calculate funding fees from rate history
                        total_funding = 0.0
                        position_notional = amount  # Assuming amount is in quote currency (USDT)
                        
                        for rate_entry in rate_history:
                            funding_rate = rate_entry.get('fundingRate', 0.0)
                            if funding_rate:
                                # Funding fee = position_notional * funding_rate
                                # Long positions pay when funding rate is positive
                                # Short positions receive when funding rate is positive
                                fee = position_notional * funding_rate
                                if is_short:
                                    fee = -fee  # Short positions have opposite fee direction
                                total_funding += fee
                                
                        logger.info("🔧 Calculated funding fees from rate history: %s", total_funding)
                        return total_funding
                    else:
                        logger.info("🔧 No funding rate history available either")
                        return 0.0
                        
                except ccxt.BaseError as e:
                    logger.warning("🔧 Error fetching funding rate history: %s", e)
                    return 0.0
                
        except Exception as e:
            logger.warning("🔧 Error calculating funding fees for %s: %s", pair, e)
            # Fallback to 0.0 to avoid breaking trades
            return 0.0