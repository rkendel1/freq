# Bitkub Exchange Class สำหรับ CCXT (ต้นแบบเบื้องต้น)
from ccxt.base.exchange import Exchange
import hashlib
import hmac
import time
import requests

class bitkub(Exchange):
    def describe(self):
        return self.deep_extend(super(bitkub, self).describe(), {
            'id': 'bitkub',
            'name': 'Bitkub',
            'countries': ['TH'],
            'version': 'v1',
            'has': {
                'fetchMarkets': True,
                'fetchTicker': True,
                'fetchBalance': True,
                'createOrder': True,
                'cancelOrder': True,
            },
            'urls': {
                'api': 'https://api.bitkub.com',
                'www': 'https://www.bitkub.com',
                'docs': 'https://apidocs.bitkub.com',
            },
            'api': {
                'public': {
                    'get': [
                        'market/symbols',
                        'market/ticker',
                    ]
                },
                'private': {
                    'post': [
                        'api/market/balances',
                        'api/market/place-bid',
                        'api/market/place-ask',
                        'api/market/cancel-order',
                    ]
                }
            },
        })

    def fetch_markets(self):
        resp = self.public_get_market_symbols()
        data = resp.get('result', [])
        result = []
        for m in data:
            base = m['base_currency']
            quote = m['quote_currency']
            symbol = m['symbol']
            result.append({
                'id': symbol,
                'symbol': symbol,
                'base': base,
                'quote': quote,
                'active': m['status'] == 'ENABLED',
                'precision': {
                    'price': 2,
                    'amount': 6
                }
            })
        return result

    def fetch_ticker(self, symbol):
        resp = self.public_get_market_ticker({'sym': symbol})
        ticker = resp.get(symbol, {})
        return {
            'symbol': symbol,
            'timestamp': time.time(),
            'bid': ticker.get('bid', None),
            'ask': ticker.get('ask', None),
            'last': ticker.get('last', None),
            'baseVolume': ticker.get('vol', None),
        }

    def fetch_balance(self, params={}):
        self.check_required_credentials()
        nonce = str(int(time.time()))
        payload = {
            'ts': int(nonce)
        }
        signature = hmac.new(
            self.secret.encode('utf-8'),
            str(payload['ts']).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        headers = {
            'X-BTK-APIKEY': self.apiKey,
            'X-BTK-TIMESTAMP': nonce,
            'X-BTK-SIGN': signature
        }
        resp = requests.post(self.urls['api'] + '/api/market/balances', headers=headers, json=payload)
        return resp.json()

    # ส่วน method อื่นๆ เช่น createOrder, cancelOrder สามารถ implement ตาม Bitkub API doc
