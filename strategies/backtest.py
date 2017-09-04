from datetime import timedelta

from bot import Bot
from db import Ticker
from account import Account


def fetch_data_timestamp(sess, oldest=True):
    sort = Ticker.timestamp
    if not oldest:
        sort = sort.desc()
    return sess.query(Ticker).order_by(sort).first() \
        .timestamp


def account_value_btc(sess, account, now=None):
    # TODO: remove this duplicate
    btc = account.balance('BTC')
    for coin in account.coins:
        if coin == 'BTC':
            continue  # BTC is priced in USD, everything else in BTC
        units = account.balance(coin)
        unit_price = Ticker.current_ask(sess, coin, now)
        btc += units * unit_price
    return btc


class Backtester(object):
    def __init__(self, sess, step=timedelta(minutes=10)):
        self.sess = sess
        self.balances = {'BTC': 5}
        self.start_data = fetch_data_timestamp(sess, oldest=True)
        self.now = fetch_data_timestamp(sess, oldest=False)
        self.coins = Ticker.coins(sess)
        self.step = step

    def run_backtest(self):
        self.run_strategy()
        self.buy_and_hold()

    def log_value(self, account, period):
        value = account_value_btc(self.sess, account)
        print("\nAccount value at {}: {} BTC\n"
              .format(period, round(value, 3)))

    def run_strategy(self):
        print("Backtesting for currencies: {}".format(self.coins))
        print("Running backtest between {}->{} at {} intervals"
              .format(self.start_data, self.now, self.step))

        period = self.start_data
        account = Account(self.balances, period, coins=self.coins)
        start_value = account_value_btc(self.sess, account)
        bot = Bot(self.sess, account, beginning=self.start_data, now=self.now)

        i = 0
        while period < self.now - self.step:
            period += self.step
            bot.tick(period)
            i += 1
            if i % (2 * 6 * 24) == 0:  # every 2 days
                self.log_value(account, period)

        finish_value = account_value_btc(self.sess, account)
        percent_return = 100 * (finish_value - start_value) / finish_value

        print("\n\nTransactions:\n{}\n\n".format(account.txns))
        print("\nBalance after running backest ({}): {} BTC\n"
              .format(self.now, finish_value))
        print("Paid {} BTC in fees".format(account.fees))
        print("Return over period: {}%".format(round(percent_return, 2)))

        return percent_return

    def buy_and_hold(self):
        account = Account(self.balances)
        start = self.start_data + timedelta(hours=2)
        # one share of each alt, one share of BTC
        btc_per_coin = account.balance('BTC') / (len(self.coins) + 1)
        with_fees = btc_per_coin - (btc_per_coin * 0.0025)

        for coin in self.coins:
            price = Ticker.current_ask(self.sess, coin, now=start)
            if not price:
                continue
            to_buy = with_fees / price
            cost = account.trade(coin, to_buy, price, start)
            account.update('BTC', cost, self.start_data)

        start_value = account_value_btc(self.sess, account, now=start)
        print("\nBuy and hold\n")
        print("Account with initial buys: {}".format(account))
        print("Initial value: {} BTC".format(start_value))
        finish_value = account_value_btc(self.sess, account, self.now)
        percent_return = 100 * (finish_value - start_value) / finish_value
        print("Balance after buy and hold ({}): {} BTC"
              .format(self.now, finish_value))
        print("Paid {} BTC in fees".format(account.fees))
        print("Return over period: {}%".format(round(percent_return, 2)))

        return percent_return
