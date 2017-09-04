import datetime
import logging

from moving_avg import MovingAverage
from stop_loss import run_strategy as stop_loss_strat
from db import Ticker

log = logging.getLogger('default')
txns = logging.getLogger('txns')


class Bot(object):
    MAX_COIN_HOLDING = 0.15  # don't hold too much of a single coin

    def __init__(self, sess, account, beginning=None, now=None, live=False):
        self.sess = sess
        self.account = account
        self.beginning = beginning
        self.now = now if now is not None else datetime.datetime.utcnow()
        self.moving_avg = MovingAverage(sess)
        self.live = live

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
        action = False
        for coin in self.account.all_coins:
            if coin == 'BTC':
                continue  # TODO
            try:
                action = action or self.tick_coin(period, coin)
            except Exception as e:
                log.error("Got error at {},{}: {}".format(coin, period, e))
                raise e
        return action

    def tick_coin(self, period, coin):
        sold = self.check_sells(coin, period)
        if sold:
            self.account.save(self.sess)
            return True
        bought = self.check_buys(coin, period)
        if bought:
            self.account.save(self.sess)
            return True
        return False

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
        acct_value = self.account.value_btc(self.sess, now=period)

        coin_holding_btc = self.account.balance(coin) * price
        coin_holding_percent = round(coin_holding_btc / acct_value, 2)
        if coin_holding_percent > self.MAX_COIN_HOLDING:
            txns.warn("Wanted to buy {}, but already holding {}%"
                      .format(coin, 100 * coin_holding_percent))
            return False

        to_spend = acct_value * 0.05 * fraction
        with_fees = to_spend * 1.003
        if with_fees > self.account.balance('BTC'):
            to_spend = 0.997 * self.account.balance('BTC')
        if to_spend < 0.001:
            txns.warn(f"Wanted to buy {coin}, but no BTC available")
            return False
        units_to_buy = to_spend / price
        make_transaction(self.account, coin, units_to_buy, price, period, self.live)
        return True


def make_transaction(account, coin, units, price, period, live=False):
    verb = "Buy" if units > 0 else "Sell"
    log.debug("  Before {}: {}".format(verb, account))
    cost = account.trade(coin, units, price, period)
    txns.warn("{}: {} {} of {} @ {} BTC ({})"
              .format(str(period), verb, units, coin, price, cost))
    account.update('BTC', cost, period)
    log.warn("  After {}: {}".format(verb, account))
    if live:
        account.place_order(coin, units, price)
        txns.warn("{} {} order placed: {}x{} @ {}"
                  .format(account.exchange, verb, coin, units, price))
