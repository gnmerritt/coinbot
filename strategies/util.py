from decimal import ROUND_DOWN, Decimal


def crypto_truncate(amount):
    d = Decimal(amount)
    return d.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
