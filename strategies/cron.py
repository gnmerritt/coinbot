import sys
import config
from apis import Bitfinex, Bittrex
from db import create_db, new_session, Ticker


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

ACTIONS = {
    'update': update,
    'query': query,
}

if __name__ == "__main__":
    config_file = sys.argv[1]
    try:
        action = sys.argv[2]
    except IndexError:
        action = 'update'

    parsed = config.read_config(config_file)
    print("got config")
    print(parsed)

    db = create_db(parsed['db'])
    sess = new_session(db)

    print("Running '{}'".format(action))
    func = ACTIONS[action]
    func(sess, parsed)
