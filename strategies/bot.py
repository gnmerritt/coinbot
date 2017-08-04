import datetime
import logging

from moving_avg import MovingAverage
from stop_loss import run_strategy as stop_loss_strat

log = logging.getLogger('default')
txns = logging.getLogger('txns')


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
        to_spend = (self.account.balance('BTC') * 0.1) * fraction
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
