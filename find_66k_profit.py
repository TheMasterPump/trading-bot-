"""
FIND THE 66K PROFIT
Analyser TOUTES les metriques possibles pour trouver le 66K
"""
import asyncio
import httpx
from datetime import datetime, timedelta

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_all_transactions(wallet_address: str):
    """Recupere TOUTES les transactions"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching ALL transactions...")

    all_transactions = []
    before_signature = None

    for batch in range(20):  # Up to 2000 transactions
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

                print(f"[+] Batch {batch + 1}: {len(transactions)} transactions (total: {len(all_transactions)})")

                if len(transactions) < 100:
                    break
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    await client.aclose()
    return all_transactions


async def calculate_all_metrics(wallet_address: str, transactions):
    """Calcule TOUTES les metriques possibles"""

    print("\n" + "=" * 70)
    print("ANALYZING ALL POSSIBLE METRICS")
    print("=" * 70)

    # SOL price
    sol_price = 200

    # Metriques de base
    total_sol_spent = 0
    total_sol_received = 0
    total_swaps = 0

    # Par periode
    now = datetime.now()
    last_7_days = now - timedelta(days=7)
    last_24h = now - timedelta(hours=24)

    sol_spent_7d = 0
    sol_received_7d = 0
    sol_spent_24h = 0
    sol_received_24h = 0

    # Tokens achetes/vendus
    tokens_bought = {}
    tokens_sold = {}

    for tx in transactions:
        tx_type = tx.get('type')
        timestamp = tx.get('timestamp')
        tx_date = datetime.fromtimestamp(timestamp)

        if tx_type != 'SWAP':
            continue

        total_swaps += 1

        # Analyser les transferts
        native_transfers = tx.get('nativeTransfers', [])
        token_transfers = tx.get('tokenTransfers', [])

        sol_in = 0
        sol_out = 0

        for nt in native_transfers:
            from_addr = nt.get('fromUserAccount')
            to_addr = nt.get('toUserAccount')
            amount = nt.get('amount', 0) / 1e9

            if to_addr == wallet_address:
                sol_in += amount
                total_sol_received += amount

                if tx_date >= last_7_days:
                    sol_received_7d += amount
                if tx_date >= last_24h:
                    sol_received_24h += amount

            elif from_addr == wallet_address:
                sol_out += amount
                total_sol_spent += amount

                if tx_date >= last_7_days:
                    sol_spent_7d += amount
                if tx_date >= last_24h:
                    sol_spent_24h += amount

        # Tracker les tokens
        for tt in token_transfers:
            mint = tt.get('mint')
            amount = tt.get('tokenAmount', 0)

            if tt.get('toUserAccount') == wallet_address:
                # ACHAT
                if mint not in tokens_bought:
                    tokens_bought[mint] = {'amount': 0, 'sol_spent': 0, 'count': 0}
                tokens_bought[mint]['amount'] += amount
                tokens_bought[mint]['sol_spent'] += sol_out
                tokens_bought[mint]['count'] += 1

            elif tt.get('fromUserAccount') == wallet_address:
                # VENTE
                if mint not in tokens_sold:
                    tokens_sold[mint] = {'amount': 0, 'sol_received': 0, 'count': 0}
                tokens_sold[mint]['amount'] += amount
                tokens_sold[mint]['sol_received'] += sol_in
                tokens_sold[mint]['count'] += 1

    # AFFICHER TOUTES LES METRIQUES
    print("\n--- TRADING VOLUME METRICS ---")
    total_volume_sol = total_sol_spent + total_sol_received
    total_volume_usd = total_volume_sol * sol_price
    print(f"Total SOL Volume (spent + received): {total_volume_sol:.4f} SOL")
    print(f"Total USD Volume: ${total_volume_usd:,.2f}")
    print(f"Total Swaps: {total_swaps}")

    print("\n--- REALIZED P&L (SOL MOVEMENTS) ---")
    realized_pnl_sol = total_sol_received - total_sol_spent
    realized_pnl_usd = realized_pnl_sol * sol_price
    print(f"SOL Spent (buying): {total_sol_spent:.4f} SOL (${total_sol_spent * sol_price:,.2f})")
    print(f"SOL Received (selling): {total_sol_received:.4f} SOL (${total_sol_received * sol_price:,.2f})")
    print(f"Net P&L: {realized_pnl_sol:+.4f} SOL (${realized_pnl_usd:+,.2f})")

    print("\n--- LAST 7 DAYS ---")
    pnl_7d = sol_received_7d - sol_spent_7d
    pnl_7d_usd = pnl_7d * sol_price
    print(f"SOL Spent: {sol_spent_7d:.4f} SOL (${sol_spent_7d * sol_price:,.2f})")
    print(f"SOL Received: {sol_received_7d:.4f} SOL (${sol_received_7d * sol_price:,.2f})")
    print(f"P&L 7d: {pnl_7d:+.4f} SOL (${pnl_7d_usd:+,.2f})")
    volume_7d = (sol_spent_7d + sol_received_7d) * sol_price
    print(f"Trading Volume 7d: ${volume_7d:,.2f}")

    print("\n--- LAST 24 HOURS ---")
    pnl_24h = sol_received_24h - sol_spent_24h
    pnl_24h_usd = pnl_24h * sol_price
    print(f"P&L 24h: {pnl_24h:+.4f} SOL (${pnl_24h_usd:+,.2f})")
    volume_24h = (sol_spent_24h + sol_received_24h) * sol_price
    print(f"Trading Volume 24h: ${volume_24h:,.2f}")

    print("\n--- TOKEN STATS ---")
    print(f"Unique Tokens Bought: {len(tokens_bought)}")
    print(f"Unique Tokens Sold: {len(tokens_sold)}")

    # Calculer total investi dans tokens non vendus
    unsold_tokens = set(tokens_bought.keys()) - set(tokens_sold.keys())
    total_invested_unsold = sum(tokens_bought[mint]['sol_spent'] for mint in unsold_tokens)
    print(f"Tokens still held: {len(unsold_tokens)}")
    print(f"SOL invested in unsold tokens: {total_invested_unsold:.4f} SOL (${total_invested_unsold * sol_price:,.2f})")

    print("\n" + "=" * 70)
    print("POSSIBLE 66K METRICS:")
    print("=" * 70)

    # Tester differentes interpretations de "66K"
    metrics = {
        "Total Trading Volume (USD)": total_volume_usd,
        "Total SOL Spent (USD)": total_sol_spent * sol_price,
        "Total SOL Received (USD)": total_sol_received * sol_price,
        "7-day Trading Volume": volume_7d,
        "Invested in Unsold Tokens": total_invested_unsold * sol_price,
        "Total SOL Volume": total_volume_sol * sol_price,
        "Number of Swaps * 1000": total_swaps * 1000
    }

    for metric_name, value in metrics.items():
        if 60000 <= value <= 70000:
            print(f"\n[!!!] POSSIBLE MATCH: {metric_name}")
            print(f"      Value: ${value:,.2f}")
            print(f"      This could be the 66K you're seeing!")

    print("\n" + "=" * 70)

    return {
        'total_volume_usd': total_volume_usd,
        'realized_pnl_usd': realized_pnl_usd,
        'pnl_7d_usd': pnl_7d_usd,
        'tokens_bought': len(tokens_bought),
        'tokens_sold': len(tokens_sold)
    }


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("\n" + "=" * 70)
    print("FIND THE 66K PROFIT")
    print("Analyzing ALL possible metrics")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print("=" * 70)

    # Get all transactions
    transactions = await get_all_transactions(wallet)
    print(f"\n[+] Total transactions: {len(transactions)}")

    # Calculate all metrics
    metrics = await calculate_all_metrics(wallet, transactions)

    print("\n[*] Analysis complete!")


if __name__ == "__main__":
    asyncio.run(main())
