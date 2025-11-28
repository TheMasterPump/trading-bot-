import requests

r = requests.get('https://api.dexscreener.com/latest/dex/tokens/6EY7XfqJYw34XdWsUoes3XvxKFTbArr4eGTRsSW1Jdev')
data = r.json()
pair = data['pairs'][0] if data.get('pairs') else None

if pair:
    mc = float(pair.get('marketCap', 0))
    price = float(pair.get('priceUsd', 0))
    vol_5m = float(pair.get('volume', {}).get('m5', 0))
    change_5m = pair.get('priceChange', {}).get('m5', 0)
    buys_5m = pair.get('txns', {}).get('m5', {}).get('buys', 0)
    sells_5m = pair.get('txns', {}).get('m5', {}).get('sells', 0)
    liq = float(pair.get('liquidity', {}).get('usd', 0))

    print(f"VEIL (VEILSWAP)")
    print(f"Market Cap: ${mc:,.0f}")
    print(f"Price: ${price}")
    print(f"Volume 5m: ${vol_5m:,.0f}")
    print(f"Price Change 5m: {change_5m}%")
    print(f"Txns 5m: {buys_5m}B / {sells_5m}S")
    print(f"Liquidity: ${liq:,.0f}")
else:
    print('No data')
