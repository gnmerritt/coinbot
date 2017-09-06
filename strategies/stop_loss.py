import logging
from datetime import timedelta

from db import Ticker

log = logging.getLogger('default')

DROP_PERCENT = 4
MIN_HOLD_TIME = timedelta(hours=24)


def run_strategy(sess, now, ticker, account, debug=False):
    if account.balance(ticker) == 0:
        return None
    open_time = account.opened(ticker)
    first_sell = open_time + MIN_HOLD_TIME
    if now <= first_sell:
        log.debug("Min holding time hasn't passed yet for {}".format(ticker))
        return None

    change, current = calc_change_percent(sess, ticker, first_sell, now)
    if change < -DROP_PERCENT:
        log.info("Sell of '{}' ask {} @ {} (down {}%)"
                 .format(ticker, current, now, change))
        return -1, current


def calc_change_percent(sess, ticker, start_time, now):
    peak = Ticker.peak(sess, ticker, start_time=start_time, now=now)
    current = Ticker.current_ask(sess, ticker, now)
    if current is None or peak is None:
        log.error(f"Could not get current/peak for {ticker} at s={start_time} n={now}: c={current}, p={peak}")
        return 0, current

    return round(100 * (current - peak) / peak, 2), current
