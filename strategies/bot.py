import logging

from moving_avg import run_strategy as moving_avg_strat
from stop_loss import run_strategy as stop_loss_strat

log = logging.getLogger('default')
txns = logging.getLogger('txns')


def tick(sess, account, period):
    for coin in account.all_coins:
        if coin == 'BTC':
            continue  # TODO
        try:
            tick_coin(sess, account, period, coin)
        except Exception as e:
            log.error("Got error at {},{}: {}".format(coin, period, e))
            raise e


def tick_coin(sess, account, period, coin):
    sold = check_sells(sess, account, coin, period)
    if sold:
        account.save()
        return
    bought = check_buys(sess, account, coin, period)
    if bought:
        account.save()


def check_sells(sess, account, coin, period):
    if account.balance(coin) <= 0:
        return False
    action = stop_loss_strat(sess, period, coin, account)
    if not action:
        return False

    fraction, price = action
    units_to_sell = fraction * account.balance(coin)
    make_transaction(account, coin, units_to_sell, price, period)
    return True


def check_buys(sess, account, coin, period):
    action = moving_avg_strat(sess, period, coin)
    if not action:
        return False

    fraction, price = action
    to_spend = (account.balance('BTC') * 0.1) * fraction
    units_to_buy = to_spend / price
    make_transaction(account, coin, units_to_buy, price, period)
    return True


def make_transaction(account, coin, units, price, period):
    verb = "Buy" if units > 0 else "Sell"
    log.debug("  Before {}: {}".format(verb, account))
    cost = account.trade(coin, units, price, period)
    txns.warn("{}: {} {} of {} @ {} BTC"
              .format(str(period), verb, units, coin, price))
    account.update('BTC', cost, period)
    log.warn("  After {}: {}".format(verb, account))
