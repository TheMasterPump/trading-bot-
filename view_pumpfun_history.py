"""
VIEW PUMP.FUN SNIPER HISTORY
Affiche l'historique des trades du bot pump.fun
"""
import json
from pathlib import Path

def view_history():
    history_file = Path(__file__).parent / "pumpfun_sniper_history.json"

    if not history_file.exists():
        print("\n[!] No trading history yet")
        print("[!] The bot is still waiting for whale trades on pump.fun")
        return

    with open(history_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    trades = data.get('trades', [])
    total = len(trades)

    print("\n" + "=" * 70)
    print("PUMP.FUN SNIPER BOT - HISTORY")
    print("=" * 70)
    print(f"Total trades: {total}")
    print(f"Active positions: {data.get('active_positions', 0)}")
    print(f"Last updated: {data.get('last_updated', 'Unknown')}")
    print("=" * 70)

    if not trades:
        print("\n[!] No trades yet - bot is monitoring for whale buys")
        return

    # Calculer les stats
    buys = [t for t in trades if t['action'] == 'BUY']
    sells = [t for t in trades if t['action'] == 'SELL']

    print(f"\nBuys: {len(buys)}")
    print(f"Sells: {len(sells)}")

    if sells:
        profits = [t['profit_percent'] for t in sells]
        avg_profit = sum(profits) / len(profits)
        wins = len([p for p in profits if p > 0])
        losses = len([p for p in profits if p <= 0])

        print(f"\nWin rate: {(wins / len(sells) * 100):.1f}%")
        print(f"Average profit: {avg_profit:+.2f}%")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")

    # Afficher les derniers trades
    print(f"\n{'='*70}")
    print("RECENT TRADES (Last 10)")
    print("=" * 70)

    for trade in reversed(trades[-10:]):
        if trade['action'] == 'BUY':
            print(f"\n[BUY] {trade['time']}")
            print(f"  Token: {trade['token'][:16]}...")
            print(f"  Price: ${trade['price']:.8f}")
            print(f"  Amount: {trade['amount_sol']} SOL")
            print(f"  Whale: {trade.get('whale_wallet', 'Unknown')[:16]}...")
            print(f"  Platform: {trade.get('platform', 'Unknown')}")
            print(f"  Mode: {'SIMULATION' if trade.get('simulated') else 'REAL'}")
        else:
            print(f"\n[SELL] {trade['time']}")
            print(f"  Token: {trade['token'][:16]}...")
            print(f"  Buy: ${trade['buy_price']:.8f}")
            print(f"  Sell: ${trade['sell_price']:.8f}")
            print(f"  Profit: {trade['profit_percent']:+.2f}%")
            print(f"  Reason: {trade['reason']}")
            print(f"  Mode: {'SIMULATION' if trade.get('simulated') else 'REAL'}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    view_history()
