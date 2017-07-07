import sys
import config
from apis import Bitfinex, Bittrex

if __name__ == "__main__":
    config_file = sys.argv[1]
    parsed = config.read_config(config_file)
    print("got config")
    print(parsed)

    exchanges = {
        'Bittrex': Bittrex(parsed),
        'Bitfinex': Bitfinex(parsed)
    }
    for name, exch in exchanges.items():
        print(name)
        for coin in exch.COINS:
            symbol = exch.make_symbol(coin)
            print("fetching " + symbol)
            data = exch.fetch_ticker(symbol)
            print(data)
