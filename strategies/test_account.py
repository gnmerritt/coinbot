from datetime import datetime, timedelta
import unittest
from .account import Account


class TestAccount(unittest.TestCase):
    def test_initial(self):
        account = Account()
        self.assertEqual(account.balance('BTC'), 0)
        self.assertEqual(account.opened('BTC'), None)
        self.assertIsNone(account.last_txn('BTC'), None)
        self.assertFalse(account.txns)
        self.assertEqual(str(account), "Account({})")

    def test_txn(self):
        now = datetime.utcnow()
        account = Account()
        account.update('BTC', 10, 10000, now)
        self.assertEqual(account.balance('BTC'), 10.0)
        self.assertEqual(account.opened('BTC'), now)
        self.assertEqual(account.last_txn('BTC'), ('BTC', 10, 10000, now))
        self.assertEqual(str(account), "Account({'BTC': 10.0})")

    def test_multi_txn(self):
        account = Account()
        btc_open = datetime.now()
        account.update('BTC', 20, 10000, btc_open)
        dcr_open = datetime.now() + timedelta(minutes=10)
        account.update('DCR', 5, 0.1, dcr_open)
        account.update('BTC', -2, 9000)
        self.assertEqual(account.balance('BTC'), 18)
        self.assertEqual(account.opened('BTC'), btc_open)
        self.assertEqual(account.balance('DCR'), 5)
        self.assertEqual(account.opened('DCR'), dcr_open)
        self.assertEqual(len(account.txns), 3)

        profits, losses = account.evaluate_trades()
        self.assertEqual(profits, [])
        self.assertEqual(len(losses), 1)
        self.assertEqual(losses[0][0], 'BTC')
        # 10% loss, plus 2x the transaction fee
        self.assertAlmostEqual(losses[0][1], -0.105)

        account.update('DCR', -5, 0.08)
        self.assertEqual(account.balance('DCR'), 0)
        self.assertFalse(account.opened('DCR'))

        profits, losses = account.evaluate_trades()
        self.assertEqual(len(losses), 2)
        dcr_loss = losses[1]
        self.assertEqual(dcr_loss[0], 'DCR')
        self.assertAlmostEqual(dcr_loss[1], -0.205)

    def test_profit(self):
        account = Account()
        account.update('DCR', 5, 0.1)
        account.update('DCR', 5, 0.2)
        account.update('DCR', -10, 1)
        self.assertEqual(account.balance('DCR'), 0)
        profits, losses = account.evaluate_trades()
        self.assertFalse(losses)
        self.assertEqual(len(profits), 2)
        self.assertAlmostEqual(profits[0][1], 8.995)
        self.assertAlmostEqual(profits[1][1], 3.995)

    def test_overdraw(self):
        account = Account()
        with self.assertRaises(Exception) as ctx:
            account.update('BTC', -10, 14000)
        self.assertIn('Saw overdraft of -10.0 for BTC (bal=0)',
                      str(ctx.exception))

    def test_buy(self):
        account = Account()
        cost = account.trade('DCR', 10, 0.1)  # 10 @ 0.1 = 1 BTC
        self.assertEqual(cost, -1.0025)
        self.assertEqual(account.balance('DCR'), 10)
        self.assertAlmostEqual(account.fees, 0.0025)

    def test_sell(self):
        account = Account()
        account.update('DCR', 10, 0.1)
        proceeds = account.trade('DCR', -5, 0.1)
        self.assertEqual(proceeds, 0.49875)
        self.assertEqual(account.balance('DCR'), 5.0)
        self.assertAlmostEqual(account.fees, 0.00125)
        # selling an asset for the same price costs us 2x a fee
        self.assertEqual(account.evaluate_trades(), ([], [('DCR', -0.005)]))

    def test_delete_empty(self):
        account = Account()
        account.update('ETH', 0, 0.5)
        self.assertEqual(account.balance('ETH'), 0)
        self.assertEqual(account.balance('FOO'), 0)
