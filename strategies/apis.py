import datetime
import ccxt


def lower_key(my_dict):
    return {k.lower(): v for k, v in my_dict.items()}


class CcxtExchange:
    def fetch_ticker(self, coin):
        symbol = self.make_symbol(coin)
        json = lower_key(self.ccxt.fetch_ticker(symbol))
        info = lower_key(json['info'])
        timestamp = datetime.datetime.utcfromtimestamp(json['timestamp'] / 1e3)
        values = {
            'exchange': self.name,
            'coin': coin,
            'timestamp': timestamp,
            'bid': json['bid'],
            'ask': json['ask'],
            'last': json['last'],
            'volume': info['volume']
        }
        return values


class Bittrex(CcxtExchange):
    COINS = [
        'BTC', 'DCR', 'ZEC', 'ETH', 'XRP', 'XEM', 'XMR', 'DASH',
        'LTC', 'FCT', 'GNO', 'REP', 'NXT', 'STEEM'
    ]

    def __init__(self, config):
        self.name = 'bittrex'
        keys = config['exchanges'][self.name]
        self.ccxt = ccxt.bittrex(keys)

    def make_symbol(self, coin):
        if coin.find('BTC') == -1:
            return 'BTC-' + coin
        return 'USDT-BTC'


class Bitfinex(CcxtExchange):
    COINS = [
        'BTC', 'ZEC', 'ETH', 'XRP', 'DSH', 'XMR', 'LTC', 'IOT'
    ]

    def __init__(self, config):
        self.name = 'bitfinex'
        keys = config['exchanges'][self.name]
        self.ccxt = ccxt.bitfinex(keys)

    def make_symbol(self, coin):
        if coin.find('BTC') == -1:
            return coin + 'BTC'
        return 'BTCUSD'
