import unittest
from decimal import Decimal

from .util import crypto_truncate


class TestUtil(unittest.TestCase):
    def test_rounding(self):
        self.assertEqual(Decimal('11188.36140127'),
                         crypto_truncate(11188.361401279999))
        self.assertEqual(Decimal('11188.36140127'),
                         crypto_truncate(Decimal(11188.361401279999)))
        self.assertEqual(11188.36140127,
                         float(crypto_truncate(11188.361401279999)))
        self.assertEqual(Decimal('-2162.60633012'),
                         crypto_truncate(-2162.60633012))
