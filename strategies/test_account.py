from datetime import datetime, timedelta
import unittest
from account import Account


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
        account.update('BTC', 10, now)
        self.assertEqual(account.balance('BTC'), 10)
        self.assertEqual(account.opened('BTC'), now)
        self.assertEqual(account.last_txn('BTC'), ('BTC', 10, now))
        self.assertEqual(str(account), "Account({'BTC': 10})")

    def test_multi_txn(self):
        account = Account()
        btc_open = datetime.now()
        account.update('BTC', 20, btc_open)
        dcr_open = datetime.now() + timedelta(minutes=10)
        account.update('DCR', 5, dcr_open)
        account.update('BTC', -2)
        self.assertEqual(account.balance('BTC'), 18)
        self.assertEqual(account.opened('BTC'), btc_open)
        self.assertEqual(account.balance('DCR'), 5)
        self.assertEqual(account.opened('DCR'), dcr_open)
        self.assertEqual(len(account.txns), 3)

        account.update('DCR', -5)
        self.assertEqual(account.balance('DCR'), 0)
        self.assertFalse(account.opened('DCR'))

    def test_overdraw(self):
        account = Account()
        with self.assertRaises(Exception) as ctx:
            account.update('BTC', -10)
        self.assertIn('Saw overdraft of -10 for BTC (bal=0)', ctx.exception)

    def test_trade(self):
        account = Account()
        cost = account.trade('DCR', 10, 0.1)  # 10 @ 0.1 = 1 BTC
        self.assertEqual(cost, -1)
        self.assertEqual(account.balance('DCR'), 10)
