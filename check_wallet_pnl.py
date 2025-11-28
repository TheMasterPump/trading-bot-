"""
CHECK WALLET TRUE P&L
Calcule le vrai P&L en regardant tous les mouvements SOL
"""
import asyncio
import httpx
from datetime import datetime, timedelta

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_wallet_pnl(wallet_address: str):
    """Calcule le P&L réel d'un wallet"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Analyzing wallet: {wallet_address}")
    print("[*] Fetching ALL transactions...")

    # Récupérer TOUTES les transactions
    all_transactions = []
    before_signature = None

    for batch in range(10):  # Fetch up to 1000 transactions (10 x 100)
        url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
        params = {
            "api-key": HELIUS_API_KEY,
            "limit": 100
        }

        if before_signature:
            params["before"] = before_signature

        try:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                transactions = response.json()

                if not transactions:
                    break

                all_transactions.extend(transactions)
                before_signature = transactions[-1].get('signature')

                print(f"[+] Fetched batch {batch + 1}: {len(transactions)} transactions (total: {len(all_transactions)})")

                if len(transactions) < 100:
                    break
            else:
                print(f"[!] Error: {response.status_code}")
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    print(f"[+] Total transactions fetched: {len(all_transactions)}")

    # Analyser tous les mouvements SOL
    print("\n[*] Calculating P&L...")

    total_sol_in = 0
    total_sol_out = 0
    sol_movements_by_period = {
        '24h': {'in': 0, 'out': 0, 'trades': 0},
        '7d': {'in': 0, 'out': 0, 'trades': 0},
        '30d': {'in': 0, 'out': 0, 'trades': 0},
        'all': {'in': 0, 'out': 0, 'trades': 0}
    }

    now = datetime.now()
    cutoffs = {
        '24h': now - timedelta(days=1),
        '7d': now - timedelta(days=7),
        '30d': now - timedelta(days=30)
    }

    for tx in all_transactions:
        tx_type = tx.get('type')
        timestamp = tx.get('timestamp')
        tx_date = datetime.fromtimestamp(timestamp)

        # Skip non-SWAP transactions
        if tx_type != 'SWAP':
            continue

        # Analyser les mouvements SOL
        native_transfers = tx.get('nativeTransfers', [])

        sol_in_this_tx = 0
        sol_out_this_tx = 0

        for transfer in native_transfers:
            from_addr = transfer.get('fromUserAccount')
            to_addr = transfer.get('toUserAccount')
            amount = transfer.get('amount', 0) / 1e9

            if to_addr == wallet_address:
                # SOL entrant (vente de token)
                sol_in_this_tx += amount
                total_sol_in += amount
            elif from_addr == wallet_address:
                # SOL sortant (achat de token)
                sol_out_this_tx += amount
                total_sol_out += amount

        # Mettre à jour les périodes
        for period, cutoff_date in cutoffs.items():
            if tx_date >= cutoff_date:
                sol_movements_by_period[period]['in'] += sol_in_this_tx
                sol_movements_by_period[period]['out'] += sol_out_this_tx
                sol_movements_by_period[period]['trades'] += 1

        # All time
        sol_movements_by_period['all']['in'] += sol_in_this_tx
        sol_movements_by_period['all']['out'] += sol_out_this_tx
        sol_movements_by_period['all']['trades'] += 1

    # Afficher les résultats
    print("\n" + "=" * 70)
    print("WALLET TRUE P&L REPORT")
    print("=" * 70)
    print(f"Wallet: {wallet_address}")
    print("=" * 70)

    sol_price_usd = 200  # Estimation

    for period_name, period_label in [('24h', 'Last 24 Hours'), ('7d', 'Last 7 Days'), ('30d', 'Last 30 Days'), ('all', 'All Time')]:
        data = sol_movements_by_period[period_name]

        if data['trades'] == 0:
            continue

        net_pnl_sol = data['in'] - data['out']
        net_pnl_usd = net_pnl_sol * sol_price_usd
        roi_percent = ((data['in'] - data['out']) / data['out'] * 100) if data['out'] > 0 else 0

        print(f"\n--- {period_label.upper()} ---")
        print(f"Trades: {data['trades']}")
        print(f"SOL Spent (buying tokens): {data['out']:.4f} SOL")
        print(f"SOL Received (selling tokens): {data['in']:.4f} SOL")
        print(f"Net P&L: {net_pnl_sol:+.4f} SOL")
        print(f"Net P&L (USD): ${net_pnl_usd:+,.2f}")
        print(f"ROI: {roi_percent:+.2f}%")

        if net_pnl_sol > 0:
            print(f"[PROFITABLE] +${net_pnl_usd:,.2f}")
        else:
            print(f"[LOSS] ${net_pnl_usd:,.2f}")

    print("\n" + "=" * 70)

    # Projection
    if sol_movements_by_period['24h']['trades'] > 0:
        daily_pnl = sol_movements_by_period['24h']['in'] - sol_movements_by_period['24h']['out']
        daily_pnl_usd = daily_pnl * sol_price_usd

        monthly_projection = daily_pnl * 30
        monthly_projection_usd = monthly_projection * sol_price_usd

        print("\n--- PROJECTIONS ---")
        print(f"Daily P&L: {daily_pnl:+.4f} SOL (${daily_pnl_usd:+,.2f})")
        print(f"Monthly Projection: {monthly_projection:+.4f} SOL (${monthly_projection_usd:+,.2f})")
        print("=" * 70)

    await client.aclose()
    return sol_movements_by_period


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("\n" + "=" * 70)
    print("WALLET TRUE P&L CHECKER")
    print("Calculate real profits from SOL movements")
    print("=" * 70)

    await get_wallet_pnl(wallet)


if __name__ == "__main__":
    asyncio.run(main())
