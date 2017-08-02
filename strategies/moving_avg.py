import logging
from datetime import timedelta

from db import Ticker

log = logging.getLogger('default')


def all_above(list, threshold):
    for i in list:
        if i <= threshold:
            return False
    return True


# https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object-python
def roundTime(dt, dateDelta=timedelta(minutes=15)):
    roundTo = dateDelta.total_seconds()
    seconds = (dt - dt.min).seconds
    # // is a floor division, not a comment on following line:
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt + timedelta(0, rounding - seconds, -dt.microsecond)


def bucket_15m(tickers):
    bucketed = {}
    for t in tickers:
        bucket = roundTime(t.timestamp)
        contents = bucketed.get(bucket, [])
        contents.append(t.ask)
        bucketed[bucket] = contents
    return bucketed


class MovingAverage(object):
    HOURS = [1, 6, 12, 24, 48, 72, 120]
    WEAK = 1.07
    STRONG = 1.12

    def __init__(self, sess):
        self.sess = sess
        self.prices = {}

    def run_strategy(self, now, ticker):
        log.debug("Running moving averages strategy for '{}' at '{}'"
                  .format(ticker, now))
        if self.prices.get(ticker) is None:
            self.fetch_data(ticker, now)

        hour_avgs = self.avg_by_hour(now, ticker)
        if hour_avgs is None:
            return None
        log.debug("Averages by hour: {}".format(hour_avgs))

        current_price = hour_avgs.get(1)
        if current_price is None:
            log.debug("No price for {} @ {}".format(ticker, now))
            return None
        percent_strength = [hour_avgs[hour] / current_price
                            for hour in self.HOURS[1:]]

        # past 24 hours
        weak_buy = all_above(percent_strength[:3], self.WEAK)
        # past 7 days
        strong_buy = weak_buy and all_above(percent_strength, self.STRONG)

        buy_str = "buy of '{}' ask {} @ {}".format(ticker, current_price, now)
        if strong_buy:
            log.info("Strong " + buy_str)
            return 1, current_price
        if weak_buy:
            log.info("Weak " + buy_str)
            return 0.5, current_price

        log.debug("No " + buy_str)
        log.debug("  weak {}".format([p > self.WEAK for p in percent_strength[:3]]))
        log.debug("  strong {}".format([p > self.STRONG for p in percent_strength[2:]]))
        return None

    def avg_by_hour(self, now, ticker):
        # datetime cutoffs for each hour bucket e.g. 24hrs ago
        deltas = {h: now - timedelta(hours=h) for h in self.HOURS}
        # the most data we need to make a decision for this 'now'
        time_cutoff = now - timedelta(hours=max(self.HOURS))
        prices = self.prices.get(ticker, {})

        min_timestamp = now
        strengths_by_hours = {}

        for b, bucket_prices in prices.items():
            if b > now or b < time_cutoff:
                continue
            min_timestamp = min(min_timestamp, b)
            for k, hour in deltas.items():
                if b < hour:
                    continue
                current = strengths_by_hours.get(k, [])
                added = current + bucket_prices
                strengths_by_hours[k] = added

        # don't make a decision if we are missing more than 24hr of data
        needed_timestamp = time_cutoff + timedelta(hours=24)
        if min_timestamp > needed_timestamp:
            return None

        return {k: sum(p) / len(p)
                for k, p in strengths_by_hours.items()}

    def fetch_data(self, ticker, now, beginning=None):
        if beginning is not None:
            time_cutoff = beginning
        else:
            time_cutoff = now - timedelta(hours=max(self.HOURS))

        alt_raw = self.sess.query(Ticker) \
            .filter(Ticker.coin == ticker) \
            .filter(Ticker.timestamp < now) \
            .filter(Ticker.timestamp > time_cutoff) \
            .all()

        self.prices[ticker] = bucket_15m(alt_raw)
