from datetime import timedelta
from moving_avg import run_strategy as moving_avg_strat
from stop_loss import run_strategy as stop_loss_strat
from db import Ticker
from account import Account


def fetch_data_timestamp(sess, oldest=True):
    sort = Ticker.timestamp
    if not oldest:
        sort = sort.desc()
    return sess.query(Ticker).order_by(sort).first() \
        .timestamp


def account_value_btc(sess, account):
    btc = account.balance('BTC')
    for coin in account.coins:
        if coin == 'BTC':
            continue  # BTC is priced in USD, everything else in BTC
        units = account.balance(coin)
        unit_price = Ticker.current_ask(sess, coin)
        btc += units * unit_price
    return btc


class Backtester(object):
    def __init__(self, sess, step=timedelta(minutes=10)):
        self.sess = sess
        self.balances = {'BTC': 5}
        self.start_data = fetch_data_timestamp(sess, oldest=True)
        self.now = fetch_data_timestamp(sess, oldest=False)
        self.coins = [t[0] for t in sess.query(Ticker.coin).distinct().all()]
        self.coins.remove('BTC')
        self.step = step

    def run_backtest(self):
        print("Backtesting for currencies: {}".format(self.coins))
        print("Running backtest between {}->{} at {} intervals"
              .format(self.start_data, self.now, self.step))

        period = self.start_data
        account = Account(self.balances, period)
        print("\nAccount value at beginning of period ({}): {} BTC\n"
              .format(self.start_data, account_value_btc(self.sess, account)))

        while period < self.now - self.step:
            period += self.step
            self.backtest_period(period, account)

        print("\n\nTransactions:\n{}\n\n".format(account.txns))
        print("\nBalance after running backest ({}): {} BTC\n"
              .format(self.now, account_value_btc(self.sess, account)))

    def backtest_period(self, period, account):
        for coin in self.coins:
            try:
                self.apply_strategy(period, coin, account)
            except Exception as e:
                print("Got error at {},{}: {}".format(coin, period, e))
                raise e

    def apply_strategy(self, period, coin, account):
        if account.balance(coin) > 0:
            action = stop_loss_strat(self.sess, period, coin, account)
            if action:
                fraction, price = action
                units_to_sell = fraction * account.balance(coin)
                print("  Before sell: {}".format(account))
                proceeds = account.trade(coin, units_to_sell, price, period)
                account.update('BTC', proceeds, period)
                print("  After sell: {}".format(account))
                return

        bought = moving_avg_strat(self.sess, period, coin)
        if bought:
            fraction, price = bought
            to_spend = (account.balance('BTC') * 0.1) * fraction
            units_to_buy = to_spend / price

            print("  Before buy: {}".format(account))
            cost = account.trade(coin, units_to_buy, price, period)
            account.update('BTC', cost, period)
            print("  After buy: {}".format(account))
