from datetime import timedelta
from db import Ticker

HOURS = [1, 3, 6, 12, 24, 48, 72, 168, 240]


def run_strategy(sess, now, ticker, debug=False):
    if debug:
        print("Running moving averages strategy for '{}' at '{}'"
              .format(ticker, now))
    buckets, prices = fetch_data(sess, now, ticker)
    hour_avgs = avg_by_hour(now, buckets, prices)
    if debug:
        print("Averages by hour: {}".format(hour_avgs))

    last_hour = hour_avgs[1]
    percent_strength = [hour_avgs[hour] / last_hour for hour in HOURS[1:]]

    weak_buy = all_above(percent_strength[:4], 1.07)  # past 24 hours
    strong_buy = all_above(percent_strength, 1.14)  # past 10 days

    buy_str = "buy of '{}' ask {} @ {}".format(ticker, last_hour, now)
    if strong_buy:
        print("Strong " + buy_str)
        return (1, ticker)
    if weak_buy:
        print("Weak " + buy_str)
        return (0.5, ticker)

    if debug:
        print("No " + buy_str)
    return None


def all_above(list, threshold):
    for i in list:
        if i <= threshold:
            return False
    return True


def avg_by_hour(now, buckets, prices):
    strengths_by_hours = {}
    deltas = {h: now - timedelta(hours=h) for h in HOURS}

    for b in buckets:
        bucket_prices = prices[b]
        for k, hour in deltas.items():
            if b < hour:
                continue
            current = strengths_by_hours.get(k, [])
            added = current + bucket_prices
            strengths_by_hours[k] = added

    avg_by_hour = {k: sum(p) / len(p) for k, p in strengths_by_hours.items()}
    return avg_by_hour


def fetch_data(sess, now, ticker):
    time_cutoff = now - timedelta(hours=max(HOURS))
    alt_raw = sess.query(Ticker) \
        .filter(Ticker.coin == ticker) \
        .filter(Ticker.timestamp < now) \
        .filter(Ticker.timestamp > time_cutoff) \
        .all()
    buckets, prices = bucket_15m(alt_raw)
    return buckets, prices


# https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object-python
def roundTime(dt, dateDelta=timedelta(minutes=15)):
    roundTo = dateDelta.total_seconds()
    seconds = (dt - dt.min).seconds
    # // is a floor division, not a comment on following line:
    rounding = (seconds+roundTo / 2) // roundTo * roundTo
    return dt + timedelta(0, rounding-seconds, -dt.microsecond)


def bucket_15m(tickers):
    bucketed = {}
    for t in tickers:
        bucket = roundTime(t.timestamp)
        contents = bucketed.get(bucket, [])
        contents.append(t.ask)
        bucketed[bucket] = contents

    buckets = list(bucketed.keys())
    buckets.sort()
    return buckets, bucketed
