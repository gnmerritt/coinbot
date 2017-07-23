from datetime import timedelta
from moving_avg import run_strategy as moving_avg_strat
from db import Ticker


def fetch_data_timestamp(sess, oldest=True):
    sort = Ticker.timestamp
    if not oldest:
        sort = sort.desc()
    return sess.query(Ticker).order_by(sort).first() \
        .timestamp


def run_backtest(sess):
    start_data = fetch_data_timestamp(sess, oldest=True)
    coins = [t[0] for t in sess.query(Ticker.coin).distinct().all()]
    print("Backtesting for currencies: {}".format(coins))

    now = fetch_data_timestamp(sess, oldest=False)
    delta = timedelta(minutes=10)
    print("Running backtest between {}->{} at {} intervals"
          .format(start_data, now, delta))

    for coin in coins:
        print("\nChecking {}\n".format(coin))
        period = start_data
        while period < now - delta:
            period += delta
            moving_avg_strat(sess, period, coin)
