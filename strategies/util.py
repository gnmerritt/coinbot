from decimal import ROUND_DOWN, Decimal
from subprocess import check_output


def crypto_truncate(amount):
    d = Decimal(amount)
    return d.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)


def run(args, split="\n"):
    output_byt = check_output(args)
    return output_byt.decode("utf-8").split(split)
