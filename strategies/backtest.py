from datetime import timedelta
import random
import statistics as s
from timeit import default_timer as timer
from multiprocessing import Pool
from tqdm import tqdm
import logging

from bot import Bot, account_value_btc
from db import Ticker, create_db, new_session
from account import Account

SECS_DAY = 60 * 60 * 24

log = logging.getLogger('backtest')
log.setLevel(logging.INFO)


def fetch_data_timestamp(sess, oldest=True):
    sort = Ticker.timestamp
    if not oldest:
        sort = sort.desc()
    return sess.query(Ticker).order_by(sort).first().timestamp


class BacktestResult(object):
    def __init__(self, start, end, step, start_val, finish_val, fees, txns,
                 out_of_btc, hit_coin_limit, high, low):
        self.start = start
        self.end = end
        self.step = step
        self.start_val = start_val
        self.finish_val = finish_val
        self.fees = fees
        self.txns = txns
        self.out_of_btc = out_of_btc
        self.hit_coin_limit = hit_coin_limit
        self.high = high
        self.low = low
        self.percent_return = 100 * (finish_val - start_val) / finish_val

    def print_results(self):
        log.debug("Ran backtest between {}->{} at {} intervals"
                  .format(self.start, self.end, self.step))
        log.debug("Balance after running backest {} BTC\n"
                  .format(self.finish_val))
        log.debug("Paid {} BTC in fees".format(round(self.fees, 8)))
        log.debug("Transactions: {}".format(len(self.txns)))
        log.debug("Missed buys: out of BTC: {}, hit coin limit: {}"
                  .format(self.out_of_btc, self.hit_coin_limit))
        if self.high is not None or self.low is not None:
            log.debug("High: {}, Low: {}".format(self.high, self.low))
        log.debug("Return over period: {}%"
                  .format(round(self.percent_return, 2)))


class Backtester(object):
    def __init__(self, sess, db_loc, step=timedelta(minutes=10)):
        self.db_loc = db_loc
        self.balances = {'BTC': 5}
        self.step = step
        self.coins = Ticker.coins(sess)
        self.start_data = fetch_data_timestamp(sess, oldest=True)
        self.end_data = fetch_data_timestamp(sess, oldest=False)

        # quiet other logs down to avoid spam
        default = logging.getLogger('default')
        default.setLevel(logging.ERROR)
        txns = logging.getLogger('txns')
        txns.setLevel(logging.ERROR)

    def run_backtest(self, num_trials, trial_days, threads=1):
        log.warn("Finding intervals between {} and {}"
                 .format(self.start_data, self.end_data))

        intervals = [self.make_interval(timedelta(days=trial_days))
                     for i in range(num_trials)]
        func_args = [[i, self.coins, self.db_loc, self.step, self.balances]
                     for i in intervals]

        timing_start = timer()
        with Pool(threads) as p:
            results = [r for r in
                       tqdm(p.imap_unordered(evaluate_interval, func_args),
                            total=len(func_args), ncols=80)]
        timing_end = timer()
        elapsed_mins = (timing_end - timing_start) / 60.0

        beat_buy_hold = 0
        pos_return = 0
        returns = []
        length = []

        for r in results:
            strat, bah = r

            returns.append(strat.percent_return)
            length.append((strat.end - strat.start).total_seconds() / SECS_DAY)
            if strat.percent_return > 0:
                pos_return += 1
            if strat.percent_return > bah.percent_return:
                beat_buy_hold += 1

        log.warn("\n\nAggregate across-trials results:\n")
        log.warn("{} trials took {} mins to process"
                 .format(num_trials, round(elapsed_mins, 1)))
        log.warn("Average trial length: {} days (set to {})"
                 .format(round(s.mean(length), 2), trial_days))
        log.warn("Positive return: {}/{}"
                 .format(pos_return, num_trials))
        log.warn("Returns median: {}%, mean: {}%, stdev: {}%"
                 .format(round(s.median(returns), 2), round(s.mean(returns), 2),
                         round(s.stdev(returns), 2)))
        log.warn("Outperformed buy-and-hold: {}/{}"
                 .format(beat_buy_hold, num_trials))

    def make_interval(self, length):
        data_range = self.end_data - self.start_data - (5 * self.step)
        start = self.start_data + random.random() * data_range
        end = min(self.end_data, start + length)
        return (start, end)


def log_value(account, period, sess):
    value = round(account_value_btc(sess, account), 3)
    log.debug("\nAccount value at {}: {} BTC".format(period, value))
    return value


def evaluate_interval(tup):
    strat = run_strategy(*tup)
    bah = buy_and_hold(*tup)
    return (strat, bah)


def run_strategy(interval, coins, db_loc, step, balances):
    start, stop = interval

    log.debug("Backtesting for currencies: {}".format(coins))
    log.debug("Running backtest between {}->{} at {} intervals"
              .format(start, stop, step))

    db = create_db(db_loc)
    sess = new_session(db)

    period = start
    account = Account(balances, period, coins=coins)
    start_value = account_value_btc(sess, account)
    bot = Bot(sess, account, beginning=start, now=stop)
    low = high = start_value

    i = 0
    while period < stop - step:
        period += step
        bot.tick(period)
        i += 1
        if i % (0.5 * 6 * 24) == 0:  # twice per day
            value = log_value(account, period, sess)
            low = min(low, value)
            high = max(high, value)

    finish_value = account_value_btc(sess, account)
    low = min(low, finish_value)
    high = max(high, finish_value)

    results = BacktestResult(
        start, stop, step,
        start_value, finish_value,
        account.fees, account.txns, bot.out_of_btc, bot.hit_coin_limit,
        high, low
    )
    results.print_results()

    return results


def buy_and_hold(interval, coins, db_loc, step, balances):
    start, stop = interval
    start = start + timedelta(hours=1)  # TODO: why?
    account = Account(balances)
    # one share of each alt, one share of BTC
    btc_per_coin = account.balance('BTC') / (len(coins) + 1)
    with_fees = btc_per_coin - (btc_per_coin * 0.0025)

    db = create_db(db_loc)
    sess = new_session(db)

    for coin in coins:
        price = Ticker.current_ask(sess, coin, now=start)
        if not price:
            continue
        to_buy = with_fees / price
        cost = account.trade(coin, to_buy, price, start)
        account.update('BTC', cost, start)

    start_value = account_value_btc(sess, account, now=start)
    finish_value = account_value_btc(sess, account, stop)
    low = min(start_value, finish_value)
    high = max(start_value, finish_value)

    results = BacktestResult(
        start, stop, step,
        start_value, finish_value, account.fees, account.txns,
        out_of_btc=0, hit_coin_limit=0, high=high, low=low
    )
    log.debug("\nBuy and hold\n")
    results.print_results()

    return results
