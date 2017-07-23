from datetime import datetime


class Account(object):
    def __init__(self, initial_balances={}, period=None):
        if period is None:
            period = datetime.utcnow()
        self.balances = initial_balances.copy()
        self.txns = []
        self.last_txns = {}
        self.position_open_datetimes = {
            coin: period for coin, bal in self.balances.items()
            if bal > 0}

    def balance(self, coin):
        return self.balances.get(coin, 0)

    def opened(self, coin):
        return self.position_open_datetimes.get(coin)

    def last_txn(self, coin):
        return self.last_txns.get(coin)

    def update(self, coin, amount, period=None):
        if period is None:
            period = datetime.utcnow()
        current = self.balances.get(coin, 0)
        new = current + amount
        if new < 0:
            raise Exception("Saw overdraft of {} for {} (bal={})"
                            .format(amount, coin, self.balance(coin)))
        self.balances[coin] = new
        txn = (coin, amount, period)
        self.txns.append(txn)
        self.last_txns[coin] = txn

        if new == 0:
            del self.position_open_datetimes[coin]
        if current == 0:
            self.position_open_datetimes[coin] = period

    def __str__(self):
        return "Account({})".format(self.balances)
