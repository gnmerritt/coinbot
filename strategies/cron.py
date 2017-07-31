import sys
import config
import datetime

import bot
from backtest import Backtester, fetch_data_timestamp
from apis import Bitfinex, Bittrex
from db import create_db, new_session, Ticker, Balance
from durable_account import DurableAccount
from slack import setup_loggers


def account(sess, config):
    name = config['account']
    print("Fetching account '{}' @ bittrex".format(name))
    account = DurableAccount.from_db(sess, name, exchange='bittrex')
    print(account)
    return account


def update(sess, config):
    """"Pull data from the exchanges and store it in our database"""
    exchanges = {
        'Bittrex': Bittrex(parsed),
        'Bitfinex': Bitfinex(parsed)
    }
    for name, exch in exchanges.items():
        print(name)
        for coin in exch.COINS:
            data = exch.fetch_ticker(coin)
            sess.add(Ticker(data))

    sess.commit()


def tick(sess, config):
    """Run our strategies for the current time"""
    acct = account(sess, config)
    bot.tick(sess, acct, period=datetime.datetime.utcnow())


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
    try:
        action = sys.argv[2]
    except IndexError:
        action = 'update'

    parsed = config.read_config(config_file)
    print("got config: {}".format(parsed))

    db = create_db(parsed['db'])
    sess = new_session(db)

    if parsed.get('production'):
        setup_loggers(parsed['slack'])

    func = ACTIONS.get(action)
    if func is None:
        raise ValueError("valid actions are {}".format(list(ACTIONS.keys())))
    print("--Running '{}'--".format(action))
    func(sess, parsed)
