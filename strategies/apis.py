import datetime
import logging
import time
import ccxt

log = logging.getLogger('default')


def lower_key(my_dict):
    return {k.lower(): v for k, v in my_dict.items()}


class CcxtExchange:
    def fetch_ticker(self, coin):
        symbol = self.make_symbol(coin)
        json = self.fetch_json(symbol)
        if json is None:
            return None
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

    def fetch_json(self, symbol, retries=3):
        for attempt in range(0, retries):
            try:
                return lower_key(self.ccxt.fetch_ticker(symbol))
            except Exception as e:
                if attempt >= retries - 1:
                    log.error(f"Exception fetching {symbol} from {self.name}",
                              exc_info=e.__traceback__)
                    return None
                time.sleep(3)

    def fetch_transactions(self, retries=3):
        for attempt in range(0, retries):
            try:
                history = self.ccxt.market_get_openorders()
                open = history.get('result', [])
                return [{'exchange': r.get('Exchange'), 'type': r.get('OrderType'), 'amount': r.get('Quantity'), 'remaining': r.get('QuantityRemaining')}
                        for r in open]
            except Exception as e:
                if attempt >= retries - 1:
                    log.error(f"Exception fetching transactions",
                              exc_info=e.__traceback__)
                    return None
            time.sleep(3)

    def balance(self, retries=3):
        for attempt in range(0, retries):
            try:
                json = self.ccxt.fetchBalance()
                balances = json['info']
                non_zero = {info.get('Currency'): info.get('Balance')
                            for info in balances}
                return {c: b for c, b in non_zero.items()
                        if b > 0 and c not in self.BLACKLIST}
            except Exception as e:
                if attempt >= retries - 1:
                    log.error("Exception fetching account balance",
                              exc_info=e.__traceback__)
                    return None
                time.sleep(3)


class Bittrex(CcxtExchange):
    COINS = [
        'BTC', 'DCR', 'ZEC', 'ETH', 'XRP', 'XEM', 'XMR', 'DASH',
        'LTC', 'FCT', 'GNO', 'REP', 'NXT', 'STEEM', 'BCH', 'NEO', 'GNT', 'QTUM'
    ]
    BLACKLIST = ['1ST']

    def __init__(self, config):
        self.name = 'bittrex'
        keys = config['exchanges'][self.name]
        self.ccxt = ccxt.bittrex(keys)

    def make_symbol(self, coin):
        if coin.find('BTC') == -1:
            return coin + '/BTC'
        return 'BTC/USDT'
