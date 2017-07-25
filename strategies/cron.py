import sys
import config
import datetime
from backtest import Backtester, fetch_data_timestamp
from apis import Bitfinex, Bittrex
from db import create_db, new_session, Ticker
from slack import setup_loggers


def update(sess, config):
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
    'backtest': backtest,
    'data': data,
    'update': update,
    'ipython': ipython,
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

    setup_loggers(parsed['slack'])

    print("--Running '{}'--".format(action))
    func = ACTIONS[action]
    func(sess, parsed)
