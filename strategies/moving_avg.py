from datetime import timedelta
from db import Ticker


HOURS = [1, 6, 12, 24, 48, 72, 168, 336]


def run_strategy(sess, now, ticker):
    print(
        "Running moving averages strategy for '{}' at '{}'".format(ticker, now)
    )
    buckets, prices = fetch_data(sess, now, ticker)
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
    print("Averages by hour: {}".format(avg_by_hour))


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
