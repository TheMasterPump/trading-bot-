import json

MINT = "7dHrUD4RVi1rEs77e41xpsSm3HFp9nQXgPMnqbqbpump"

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Chercher le token
for token in data.get('completed', []):
    if token.get('mint') == MINT:
        print(f"=== TOKEN TROUVE ===")
        print(f"Symbol: {token.get('symbol', '???')}")
        print(f"Mint: {token.get('mint')}")
        print(f"Final MC: ${token.get('final_mc', 0):,.0f}")
        print(f"Is Runner: {token.get('is_runner', False)}")
        print(f"Early Runner: {token.get('early_runner', False)}")
        print(f"Migration Detected: {token.get('migration_detected', False)}")
        print(f"Pump Time: {token.get('pump_time', '?')} secondes")
        print(f"")
        print(f"=== SNAPSHOTS ===")
        if token.get('10s'):
            print(f"10s:  ${token['10s'].get('mc', 0):>10,.0f} | {token['10s'].get('txn', 0):>3} txn | {token['10s'].get('buy_ratio', 0)*100:.1f}% buys")
        if token.get('15s'):
            print(f"15s:  ${token['15s'].get('mc', 0):>10,.0f} | {token['15s'].get('txn', 0):>3} txn | {token['15s'].get('buy_ratio', 0)*100:.1f}% buys")
        if token.get('30s'):
            print(f"30s:  ${token['30s'].get('mc', 0):>10,.0f} | {token['30s'].get('txn', 0):>3} txn | {token['30s'].get('buy_ratio', 0)*100:.1f}% buys")
        if token.get('1min'):
            print(f"1min: ${token['1min'].get('mc', 0):>10,.0f} | {token['1min'].get('txn', 0):>3} txn | {token['1min'].get('buy_ratio', 0)*100:.1f}% buys")
        if token.get('2min'):
            print(f"2min: ${token['2min'].get('mc', 0):>10,.0f} | {token['2min'].get('txn', 0):>3} txn | {token['2min'].get('buy_ratio', 0)*100:.1f}% buys")
        if token.get('5min'):
            print(f"5min: ${token['5min'].get('mc', 0):>10,.0f} | {token['5min'].get('txn', 0):>3} txn | {token['5min'].get('buy_ratio', 0)*100:.1f}% buys")
        break
else:
    print("Token pas trouvé dans completed")
