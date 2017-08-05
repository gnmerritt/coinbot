from datetime import datetime


class Account(object):
    def __init__(self, initial_balances={}, period=None, opens=None, coins=[]):
        if period is None:
            period = datetime.utcnow()
        self.balances = initial_balances.copy()
        for coin in coins:
            if coin not in self.balances:
                self.balances[coin] = 0.0
        self.txns = []
        self.last_txns = {}
        if opens is None:
            self.position_open_datetimes = {
                coin: period for coin, bal in self.balances.items()
                if bal > 0}
        else:
            self.position_open_datetimes = opens
        self.fees = 0

    @property
    def coins(self):
        return [c for c, v in self.balances.items() if v > 0]

    @property
    def all_coins(self):
        return list(self.balances.keys())

    @property
    def open_balances(self):
        return {c: b for c, b in self.balances.items() if b > 0}

    def balance(self, coin):
        return self.balances.get(coin, 0)

    def opened(self, coin):
        return self.position_open_datetimes.get(coin)

    def last_txn(self, coin):
        return self.last_txns.get(coin)

    def trade(self, coin, units, unit_price, period=None, fees=0.0025):
        self.update(coin, units, period)
        fee = fees * units * unit_price
        self.fees += abs(fee)
        gross = units * unit_price
        if gross > 0:
            gross += fee
        else:
            gross -= fee
        return -1 * gross

    def update(self, coin, amount_in, period=None):
        amount = float(amount_in)
        if period is None:
            period = datetime.utcnow()
        current = self.balances.get(coin, 0.0)
        new = current + amount
        if new < 0:
            raise Exception("Saw overdraft of {} for {} (bal={})"
                            .format(amount, coin, self.balance(coin)))
        self.balances[coin] = new
        txn = (coin, amount, period)
        self.txns.append(txn)
        self.last_txns[coin] = txn

        if new == 0 and coin in self.position_open_datetimes:
            del self.position_open_datetimes[coin]
        if current == 0:
            self.position_open_datetimes[coin] = period

    def save(self, *args):
        pass

    def __str__(self):
        return "Account({})".format(self.open_balances)
