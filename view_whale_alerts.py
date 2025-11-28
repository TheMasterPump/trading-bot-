"""
VIEW WHALE ALERTS
Affiche les dernières alertes d'achats des baleines
"""
import json
from pathlib import Path
from datetime import datetime

def view_alerts():
    alerts_file = Path(__file__).parent / "whale_alerts.json"

    if not alerts_file.exists():
        print("\n[!] No alerts yet. Start the monitor first:")
        print("    python whale_monitor_live.py")
        return

    with open(alerts_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    alerts = data.get('alerts', [])
    total = len(alerts)

    print("\n" + "=" * 70)
    print("WHALE ALERTS HISTORY")
    print("=" * 70)
    print(f"Total alerts: {total}")
    print(f"Last updated: {data.get('last_updated', 'Unknown')}")
    print("=" * 70)

    if not alerts:
        print("\n[!] No alerts recorded yet")
        return

    # Afficher les 10 dernières
    print(f"\nLast {min(10, total)} alerts:\n")

    for i, alert in enumerate(reversed(alerts[-10:]), 1):
        print(f"[{i}] {alert['time']} - Wallet: {alert['wallet']}")
        print(f"    {alert['description']}")
        print(f"    Signature: {alert['signature']}")
        print()

    print("=" * 70)
    print("\n[i] To see transaction details, visit:")
    print("    https://solscan.io/tx/<signature>")

if __name__ == "__main__":
    view_alerts()
