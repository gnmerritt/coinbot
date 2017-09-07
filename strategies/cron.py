import sys
import datetime
import logging

import config
from bot import Bot
from backtest import Backtester, fetch_data_timestamp
from stop_loss import calc_change_percent
from apis import Bittrex
from db import create_db, new_session, Ticker
from durable_account import DurableAccount
from slack import setup_loggers
from util import run

log = logging.getLogger('cron')


def account(sess, config, verbose=True):
    name = config['account']
    log.debug("Fetching account '{}' @ bittrex".format(name))
    account = DurableAccount.from_db(sess, name,
                                     exchange='bittrex', ccxt=Bittrex(config))
    if verbose:
        account.respect_remote(sess)
        value = account.value_btc(sess)
        log.info("{} with current value of {} BTC".format(account, value))
        for coin in account.coins:
            btc_value = account.values_in_btc.get(coin, 0)
            percent_value = round(100 * btc_value / value, 1)
            opened = account.opened(coin)
            now = datetime.datetime.utcnow()
            change, current = calc_change_percent(sess, coin, opened, now)
            log.info(f"{coin.rjust(8)}: {btc_value} BTC ({percent_value}%). "
                     + f"Position opened on {opened.date().isoformat()}, moved {change}%.")
        log.info("Balances from exchange: {}".format(account.remote_balance()))
    return account


def update(sess, config):
    """"Pull data from the exchanges and store it in our database"""
    exchanges = {
        'Bittrex': Bittrex(config),
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
    bot = Bot(sess, acct, now=start, live=True)
    did_something = bot.tick(period=start)
    elapsed = datetime.datetime.utcnow() - start
    if elapsed.seconds > 30:
        log.warn("Ran tick in {}s".format(elapsed.seconds))
    if did_something:
        log.info("Strengths at time of buy/sell:")
        strengths(sess, config)
        log.info("Account after buy/sell:")
        account(sess, config)


def strengths(sess, config):
    """Print the current relative strengths of altcoins"""
    acct = account(sess, config, verbose=False)
    now = datetime.datetime.utcnow()
    bot = Bot(sess, acct)
    strengths = bot.calculate_strengths(now, approx=True)

    time_width = 6
    msg = ["Coin price vs BTC "
           + "(negative => currently stronger than period, positive => currently weaker). "
           + "Ordered weakest to strongest."]
    msg.append("```")
    # header row
    hours = bot.moving_avg.HOURS[1:]  # TODO: make this less fiddly
    msg.append("{} {}".format(
        "coin  ".rjust(8),
        " ".join(["{}hrs".format(h).ljust(time_width) for h in hours])))
    msg.append("")

    saw_strength = False
    coins = [c for c in strengths.keys() if strengths.get(c)]
    # sort descending on coin strength (weakest coins first)
    coins.sort(key=lambda c: strengths.get(c)[1][0], reverse=True)
    for coin in coins:
        try:
            price, strength = strengths.get(coin)
        except TypeError:
            continue
        if strength[0] < 1 and not saw_strength:
            saw_strength = True
            msg.append('   --- Strong coins below ---')
        normalized = [100 * (s - 1) for s in strength]
        formatted = " ".join(
            ["{}".format(round(s, 1)).rjust(time_width)
             for s in normalized])
        msg.append("{}:{}".format(coin.rjust(6), formatted))

    msg.append("```")
    log.info("\n".join(msg))


def ipython(sess, config):
    acct = account(sess, config)
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


def pull(sess, config):
    log.info("Running `git pull`")
    output = run(['git', 'pull'])
    log.info("```{}```".format("\n".join(output)))


ACTIONS = {
    'account': account,
    'backtest': backtest,
    'data': data,
    'update': update,
    'ipython': ipython,
    'tick': tick,
    'strengths': strengths,
    'pull': pull,
}


def main(parsed, actions):
    db = create_db(parsed['db'])
    sess = new_session(db)

    for action in actions:
        func = ACTIONS.get(action)
        if func is None:
            raise ValueError("valid actions are {}".format(list(ACTIONS.keys())))
        print("--Running '{}'--".format(action))
        func(sess, parsed)


if __name__ == "__main__":
    config_file = sys.argv[1]
    actions = sys.argv[2:]
    if not actions:
        actions = ['update']
    parsed = config.read_config(config_file)
    print("got config: {}".format(parsed))

    if 'backtest' not in actions:
        setup_loggers(parsed['slack'])

    main(parsed, actions)
