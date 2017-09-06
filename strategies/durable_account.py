import datetime
import logging
from account import Account
from db import Balance, Ticker

log = logging.getLogger('default')
BTC_DIFF_THRESH = 0.001  # one thousandth, about $4


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

    def respect_remote(self, sess):
        changed = 0
        remote_balances = self.remote_balance()
        coins = set(self.balances.keys()).union(remote_balances.keys())

        for coin in coins:
            remote_balance = remote_balances.get(coin, 0)
            local_balance = self.balance(coin)
            if local_balance == remote_balance:
                continue

            allowed_diff = self.get_allowed_diff(sess, coin)
            actual_diff = remote_balance - local_balance
            if abs(actual_diff) < allowed_diff:
                perc = round(100 * actual_diff / local_balance, 1)
                log.warn(f"Updating local {coin} to match remote ({actual_diff} / {perc}%)")
                self.balances[coin] = remote_balance
                changed += 1
            else:
                log.debug(f"{coin} difference too big to auto-correct: {actual_diff} > {allowed_diff}")

        if changed > 0:
            self.save(sess)
            log.warn(f" Updated {changed} coins to match remote balances")

    def get_allowed_diff(self, sess, coin):
        if coin == 'BTC':
            return BTC_DIFF_THRESH
        now = datetime.datetime.utcnow()
        current = Ticker.current_ask(sess, coin, now)
        if current is None:
            current = 1
        return BTC_DIFF_THRESH / current  # in terms of the coin

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
