import datetime
import logging

from moving_avg import MovingAverage
from stop_loss import run_strategy as stop_loss_strat
from db import Ticker

log = logging.getLogger('default')
txns = logging.getLogger('txns')


def account_value_btc(sess, account, now=None):
    btc = account.balance('BTC')
    for coin in account.coins:
        if coin == 'BTC':
            continue  # BTC is priced in USD, everything else in BTC
        units = account.balance(coin)
        unit_price = Ticker.current_ask(sess, coin, now)
        btc += units * unit_price
    return btc


class Bot(object):
    def __init__(self, sess, account, beginning=None, now=None):
        self.sess = sess
        self.account = account
        self.beginning = beginning
        self.now = now if now is not None else datetime.datetime.utcnow()
        self.moving_avg = MovingAverage(sess)

        if beginning is not None and now is not None:
            log.info("prefetching data from Bot: {} -> {}"
                     .format(beginning, now))
            for ticker in account.all_coins:
                self.moving_avg.fetch_data(ticker, now, beginning)

    def calculate_strengths(self, period, approx=False):
        return {
            coin: self.moving_avg.calculate_strengths(period, coin, approx)
            for coin in self.account.all_coins}

    def tick(self, period):
        for coin in self.account.all_coins:
            if coin == 'BTC':
                continue  # TODO
            try:
                self.tick_coin(period, coin)
            except Exception as e:
                log.error("Got error at {},{}: {}".format(coin, period, e))
                raise e

    def tick_coin(self, period, coin):
        sold = self.check_sells(coin, period)
        if sold:
            self.account.save()
            return
        bought = self.check_buys(coin, period)
        if bought:
            self.account.save()

    def check_sells(self, coin, period):
        if self.account.balance(coin) <= 0:
            return False
        action = stop_loss_strat(self.sess, period, coin, self.account)
        if not action:
            return False

        fraction, price = action
        units_to_sell = fraction * self.account.balance(coin)
        make_transaction(self.account, coin, units_to_sell, price, period)
        return True

    def check_buys(self, coin, period):
        action = self.moving_avg.run_strategy(period, coin)
        if not action:
            return False

        fraction, price = action
        acct_value = account_value_btc(self.sess, self.account, now=period)
        to_spend = acct_value * 0.05 * fraction
        with_fees = to_spend * 1.003
        if with_fees > self.account.balance('BTC'):
            to_spend = 0.997 * self.account.balance('BTC')
        if to_spend < 0.001:
            log.warn(f"Wanted to buy {coin}, but no BTC available")
            return False
        units_to_buy = to_spend / price
        make_transaction(self.account, coin, units_to_buy, price, period)
        return True


def make_transaction(account, coin, units, price, period):
    verb = "Buy" if units > 0 else "Sell"
    log.debug("  Before {}: {}".format(verb, account))
    cost = account.trade(coin, units, price, period)
    txns.warn("{}: {} {} of {} @ {} BTC ({})"
              .format(str(period), verb, units, coin, price, cost))
    account.update('BTC', cost, period)
    log.warn("  After {}: {}".format(verb, account))
