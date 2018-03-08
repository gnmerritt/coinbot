from datetime import datetime
import math

BITTREX_FEE = 0.0025


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
        units = float(units)  # sometimes we get passed Decimals
        self.update(coin, units, unit_price, period)
        fee = fees * units * unit_price
        self.fees += abs(fee)
        gross = units * unit_price
        if gross > 0:
            gross += fee
        else:
            gross -= fee
        return -1 * gross

    def update(self, coin, amount_in, price, period=None):
        amount = float(amount_in)
        if period is None:
            period = datetime.utcnow()
        current = self.balances.get(coin, 0.0)
        new = current + amount
        if new < 0:
            raise Exception("Saw overdraft of {} for {} (bal={})"
                            .format(amount, coin, self.balance(coin)))
        self.balances[coin] = new
        txn = (coin, amount, price, period)
        self.txns.append(txn)
        self.last_txns[coin] = txn

        if new == 0 and coin in self.position_open_datetimes:
            del self.position_open_datetimes[coin]
        if current == 0:
            self.position_open_datetimes[coin] = period

    def evaluate_trades(self):
        """"Return trade outcomes, normalized to amount invested.
        We will use these to calculate p, a & b to plug into the Kelly formula
        for f*, the optimal bet size. Currently this number is the same for all
        coins.
        """
        profits = []
        losses = []
        open_txns = []  # buys to evaluate

        for coin, amount, price, ts in self.txns:
            if coin == 'BTC':
                continue  # TODO: do we care about BTC?

            if amount > 0:
                open_txns.append((coin, amount, price))
            else:
                left_to_sell = amount
                iters = 0

                # search through the buys we've made to figure out if this sale
                # was profitable or a loss
                while open_txns:
                    iters += 1
                    if iters > 50:
                        break
                    buy = open_txns.pop(0)
                    buy_coin, buy_amount, buy_price = buy
                    if coin != buy_coin:
                        open_txns.append(buy)
                        continue

                    # adjust the sale in this loop iteration to the smallest
                    # of the buy or sell, for mismatched txn sizes
                    remainder = buy_amount - abs(left_to_sell)
                    selling_now = abs(left_to_sell)
                    if math.isclose(remainder, 0):
                        pass
                    elif remainder > 0:
                        # note: this path shouldn't happen in the bot b/c
                        # it sells all of an altcoin at once
                        open_txns.append((buy_coin, remainder, buy_price))
                        buy_amount = abs(left_to_sell)
                    elif remainder < 0:
                        selling_now = buy_amount

                    # calculate the percentage return
                    initial = buy_amount * buy_price
                    final = selling_now * price
                    tx_return = ((final - initial) / initial) - 2 * BITTREX_FEE

                    if tx_return > 0:
                        profits.append((coin, tx_return))
                    else:
                        losses.append((coin, tx_return))

                    left_to_sell += selling_now
                    if math.isclose(left_to_sell, 0):
                        break

                # helpful for debugging:
                # assert math.isclose(left_to_sell, 0), \
                #    f"leftover {coin}: {left_to_sell}, txns: {open_txns}"

        return profits, losses

    def save(self, *args):
        pass

    def __str__(self):
        return "Account({})".format(self.open_balances)
