from decimal import localcontext, ROUND_DOWN, Decimal


def crypto_truncate(amount):
    d = Decimal(amount)
    with localcontext() as ctx:
        ctx.rounding = ROUND_DOWN
        return d.quantize(Decimal('0.00000001'))
