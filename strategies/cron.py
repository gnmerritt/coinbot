import sys
import config
import datetime
import logging

from bot import Bot
from backtest import Backtester, fetch_data_timestamp, account_value_btc
from apis import Bitfinex, Bittrex
from db import create_db, new_session, Ticker, Balance
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
            sess.add(Ticker(data))

    sess.commit()
    elapsed = datetime.datetime.utcnow() - start
    log.info("Ran update in {}s".format(elapsed.seconds))


def tick(sess, config):
    """Run our strategies for the current time"""
    start = datetime.datetime.utcnow()
    acct = account(sess, config, verbose=False)
    bot = Bot(sess, acct, now=start)
    bot.tick(period=start)
    elapsed = datetime.datetime.utcnow() - start
    log.info("Ran tick in {}s".format(elapsed.seconds))


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
