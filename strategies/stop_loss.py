import logging

from db import Ticker

log = logging.getLogger('default')

DROP_PERCENT = 0.04


def run_strategy(sess, now, ticker, account, debug=False):
    if account.balance(ticker) == 0:
        return None
    open_time = account.opened(ticker)
    peak = Ticker.peak(sess, ticker, start_time=open_time, now=now)
    current = Ticker.current_ask(sess, ticker, now)
    if current is None or peak is None:
        return None

    drop_percent = (current - peak) / peak
    if drop_percent < -DROP_PERCENT:
        log.info("Sell of '{}' ask {} @ {} (down {}%)"
                 .format(ticker, current, now, round(drop_percent * 100, 2)))
        return -1, current
