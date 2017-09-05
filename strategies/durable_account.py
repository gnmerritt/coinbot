from account import Account
from db import Balance, Ticker


class DurableAccount(Account):
    def __init__(self, name, exchange, ccxt, balances={}, opens=None, coins=[]):
        super().__init__(balances, opens=opens, coins=coins)
        self.name = name
        self.exchange = exchange
        self.ccxt = ccxt
        self.values_in_btc = {}

    def __str__(self):
        return "DurableAccount(name={}, exchange={}, balances={})" \
               .format(self.name, self.exchange, self.open_balances)

    def save(self, sess):
        old_balances, _ = \
            DurableAccount.fetch_balances(sess, self.name, self.exchange)
        changed = {c: b for c, b in self.balances.items()
                   if b != old_balances.get(c)}
        for coin, balance in changed.items():
            attrs = {'coin': coin, 'name': self.name, 'exchange': self.exchange}
            if balance == 0.0:
                Balance.remove(sess, **attrs)
            else:
                Balance.upsert(sess, balance, **attrs)
        sess.commit()

    def value_btc(self, sess, now=None):
        btc = self.balance('BTC')
        self.values_in_btc['BTC'] = btc
        for coin in self.coins:
            if coin == 'BTC':
                continue  # BTC is priced in USD, everything else in BTC
            units = self.balance(coin)
            unit_price = Ticker.current_ask(sess, coin, now)
            value = units * unit_price
            self.values_in_btc[coin] = value
            btc += value
        return btc

    def remote_balance(self):
        return self.ccxt.balance()

    def place_order(self, ticker, amount, price):
        symbol = self.ccxt.make_symbol(ticker)
        if amount > 0:
            return self.ccxt.ccxt.create_limit_buy_order(symbol, amount, price)
        else:
            return self.ccxt.ccxt.create_limit_sell_order(symbol, abs(amount), price)

    @staticmethod
    def from_db(sess, name, exchange, ccxt):
        if not name or not exchange:
            raise ValueError("Must specify acount name and exchange")
        balances, opens = DurableAccount.fetch_balances(sess, name, exchange)
        coins = Ticker.coins(sess)
        return DurableAccount(name, exchange, ccxt, balances, opens, coins)

    @staticmethod
    def fetch_balances(sess, name, exchange):
        balances = sess.query(Balance) \
            .filter(Balance.name == name) \
            .filter(Balance.exchange == exchange) \
            .filter(Balance.balance > 0) \
            .all()
        opened = {b.coin: b.opened for b in balances}
        balances = {b.coin: b.balance for b in balances}
        return balances, opened
