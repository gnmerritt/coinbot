import sys
import config
import datetime
import logging

from bot import Bot, account_value_btc
from backtest import Backtester, fetch_data_timestamp
from apis import Bitfinex, Bittrex
from db import create_db, new_session, Ticker
from durable_account import DurableAccount
from slack import setup_loggers

log = logging.getLogger('cron')


def account(sess, config, verbose=True):
    name = config['account']
    log.debug("Fetching account '{}' @ bittrex".format(name))
    account = DurableAccount.from_db(sess, name, exchange='bittrex')
    if verbose:
        value = account_value_btc(sess, account)
        log.info("{} with current value of {} BTC".format(account, value))
    return account


def update(sess, config):
    """"Pull data from the exchanges and store it in our database"""
    exchanges = {
        'Bittrex': Bittrex(parsed),
        'Bitfinex': Bitfinex(parsed)
    }
    start = datetime.datetime.utcnow()
    for name, exch in exchanges.items():
        print(name)
        for coin in exch.COINS:
            data = exch.fetch_ticker(coin)
            if data is None:
                continue
            sess.add(Ticker(data))

    sess.commit()
    elapsed = datetime.datetime.utcnow() - start
    if elapsed.seconds > 30:
        log.warn("Ran update in {}s".format(elapsed.seconds))


def tick(sess, config):
    """Run our strategies for the current time"""
    start = datetime.datetime.utcnow()
    acct = account(sess, config, verbose=False)
    bot = Bot(sess, acct, now=start)
    did_something = bot.tick(period=start)
    elapsed = datetime.datetime.utcnow() - start
    if elapsed.seconds > 30:
        log.warn("Ran tick in {}s".format(elapsed.seconds))
    if did_something:
        log.info("Strenghts at time of buy/sell:")
        strengths(sess, config)
        log.info("Account after buy/sell:")
        account(sess, config)


def strengths(sess, config):
    """Print the current relative strengths of altcoins"""
    acct = account(sess, config, verbose=False)
    now = datetime.datetime.utcnow()
    bot = Bot(sess, acct)
    strengths = bot.calculate_strengths(now, approx=True)

    msg = ["Coin strengths "
           + "(>100% = currently weaker than period, <100% = stronger)"]
    msg.append("```")
    # header row
    hours = bot.moving_avg.HOURS[1:]  # TODO: make this less fiddly
    msg.append("{} {}".format(
        "coin  ".rjust(8),
        " ".join(["{}hrs".format(h).ljust(9) for h in hours])))
    msg.append("")

    coins = list(strengths.keys())
    coins.sort()
    for coin in coins:
        try:
            price, strength = strengths.get(coin)
        except TypeError:
            strength = []
        formatted = " ".join(
            ["{}%".format(round(100 * s, 2)).ljust(9)
             for s in strength])
        msg.append("{}:  {}".format(coin.rjust(6), formatted))

    msg.append("```")
    log.info("\n".join(msg))


def query(sess, config):
    entries = sess.query(Ticker).all()
    print("got {} entries".format(len(entries)))
    print(entries)


def ipython(sess, config):
    import ipdb
    ipdb.set_trace()


def data(sess, config):
    print("Current time is {}".format(datetime.datetime.utcnow()))
    print("Earliest entry is at {}".format(fetch_data_timestamp(sess)))
    print("Latest entry is at {}"
          .format(fetch_data_timestamp(sess, oldest=False)))


def backtest(sess, config):
    tester = Backtester(sess)
    tester.run_backtest()


ACTIONS = {
    'account': account,
    'backtest': backtest,
    'data': data,
    'update': update,
    'ipython': ipython,
    'tick': tick,
    'query': query,
    'strengths': strengths,
}

if __name__ == "__main__":
    config_file = sys.argv[1]
    actions = sys.argv[2:]
    if not actions:
        actions = ['update']

    parsed = config.read_config(config_file)
    print("got config: {}".format(parsed))

    db = create_db(parsed['db'])
    sess = new_session(db)

    if parsed.get('production'):
        setup_loggers(parsed['slack'])

    for action in actions:
        func = ACTIONS.get(action)
        if func is None:
            raise ValueError("valid actions are {}".format(list(ACTIONS.keys())))
        print("--Running '{}'--".format(action))
        func(sess, parsed)
