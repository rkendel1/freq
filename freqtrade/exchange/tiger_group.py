import logging
from typing import Dict, List, Optional
import pandas as pd
from freqtrade.exchange import Exchange
from freqtrade.exchange.common import retrier

# 导入老虎证券SDK
try:
    from tigeropen.tiger_open_config import TigerOpenClientConfig
    from tigeropen.quote.quote_client import QuoteClient
    from tigeropen.trade.trade_client import TradeClient
    from tigeropen.common.util.signature_utils import read_private_key
except ImportError:
    raise ImportError("请安装老虎证券SDK: pip install tigeropen")

logger = logging.getLogger(__name__)

class TigerGroupExchange(Exchange):
    """老虎证券交易所适配器。"""
    
    _ft_has = {
        "ohlcv_candle_limit": 1000,  # 每次获取K线的最大数量
    }

    def __init__(self, config: Dict[str, any]) -> None:
        super().__init__(config)
        tiger_config = config.get('tiger', {})
        # 从配置中读取老虎证券参数:cite[1]:cite[4]
        self._api_key = tiger_config.get('api_key')
        self._private_key_path = tiger_config.get('private_key')
        self._account = tiger_config.get('account')  # 环球账户，U开头:cite[1]:cite[4]
        self._sandbox = tiger_config.get('sandbox', False)
        
        # 初始化SDK客户端:cite[1]
        self._init_tiger_clients()
        self._markets = {}
        logger.info("老虎证券交易所适配器初始化完成")

    def _init_tiger_clients(self):
        """初始化老虎证券行情和交易客户端"""
        client_config = TigerOpenClientConfig(
            tiger_id=self._account,
            private_key=read_private_key(self._private_key_path),
            sandbox_debug=self._sandbox
        )
        self.quote_client = QuoteClient(client_config)
        self.trade_client = TradeClient(client_config)

    @retrier
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1d', since: Optional[int] = None, limit: Optional[int] = 1000) -> List[List]:
        """获取K线数据（OHLCV），这是回测和实盘的关键。"""
        try:
            # 将Freqtrade的时间帧映射到老虎证券的时间段
            period_map = {'1d': '1day', '1h': '60min', '15m': '15min'}
            tiger_period = period_map.get(timeframe, '1day')
            
            # 转换符号，例如将 'AAPL/USD' 转为 'AAPL'
            stock_symbol = symbol.split('/')[0]
            
            # 调用SDK获取K线数据
            bars = self.quote_client.get_kline_bars(
                symbol=stock_symbol, 
                period=tiger_period, 
                limit=limit
            )
            
            # 将数据格式转换为Freqtrade要求的格式: [时间戳, 开, 高, 低, 收, 成交量]
            ohlcv = []
            for bar in bars:
                ohlcv.append([bar.time, bar.open, bar.high, bar.low, bar.close, bar.volume])
            return ohlcv
        except Exception as e:
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            raise

    @retrier
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None) -> Dict:
        """创建订单（买入/卖出）。"""
        try:
            stock_symbol = symbol.split('/')[0]
            # 映射订单类型和方向:cite[4]
            action = 'BUY' if side == 'buy' else 'SELL'
            order_type_sdk = 'LMT' if order_type == 'limit' else 'MKT'  # 限价单或市价单
            
            # 调用SDK下单
            order_id = self.trade_client.place_order(
                account=self._account,
                symbol=stock_symbol,
                action=action,
                order_type=order_type_sdk,
                quantity=int(amount),  # 股票数量通常为整数
                limit_price=price
            )
            return {'id': order_id, 'status': 'open'}
        except Exception as e:
            logger.error(f"创建订单失败 {symbol}: {e}")
            raise

    @retrier
    def fetch_balance(self) -> Dict:
        """获取账户余额和持仓信息。"""
        try:
            # 获取账户现金余额
            assets = self.trade_client.get_assets(self._account)
            balance = {'free': {}, 'used': {}, 'total': {}}
            
            for asset in assets:
                if asset.currency == 'USD':
                    balance['free']['USD'] = float(asset.available)
                    balance['total']['USD'] = float(asset.market_value)
            
            # 获取股票持仓
            positions = self.trade_client.get_positions(self._account)
            for position in positions:
                if position.quantity > 0:
                    symbol = f"{position.symbol}/USD"
                    balance['free'][symbol] = float(position.quantity)
                    balance['total'][symbol] = float(position.quantity)
            return balance
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            raise

    # 还需要实现 cancel_order, fetch_order 等方法