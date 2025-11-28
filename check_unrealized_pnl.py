"""
CHECK UNREALIZED P&L
Calcule la valeur actuelle des tokens détenus (positions non vendues)
"""
import asyncio
import httpx
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_token_balances(wallet_address: str):
    """Récupère tous les tokens détenus par le wallet"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Getting token balances for: {wallet_address[:16]}...")

    # Helius API pour les balances
    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/balances"
    params = {
        "api-key": HELIUS_API_KEY
    }

    try:
        response = await client.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            tokens = data.get('tokens', [])
            print(f"[+] Found {len(tokens)} tokens")
            await client.aclose()
            return tokens
        else:
            print(f"[!] Error: {response.status_code}")
            await client.aclose()
            return []

    except Exception as e:
        print(f"[!] Error: {e}")
        await client.aclose()
        return []


async def get_token_current_price(mint: str):
    """Récupère le prix actuel d'un token depuis DexScreener"""
    client = httpx.AsyncClient(timeout=30.0)

    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])

            if pairs:
                pair = pairs[0]
                price_usd = float(pair.get('priceUsd', 0))
                mcap = float(pair.get('marketCap', 0))
                liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))

                await client.aclose()
                return {
                    'price_usd': price_usd,
                    'mcap': mcap,
                    'liquidity': liquidity,
                    'price_change_24h': price_change_24h,
                    'pair_address': pair.get('pairAddress'),
                    'dex_id': pair.get('dexId')
                }

        await client.aclose()
        return None

    except Exception as e:
        await client.aclose()
        return None


async def get_wallet_transactions(wallet_address: str):
    """Récupère les transactions pour calculer le prix d'achat"""
    client = httpx.AsyncClient(timeout=60.0)

    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
    params = {
        "api-key": HELIUS_API_KEY,
        "limit": 100
    }

    try:
        response = await client.get(url, params=params)

        if response.status_code == 200:
            transactions = response.json()
            await client.aclose()
            return transactions
        else:
            await client.aclose()
            return []

    except Exception as e:
        await client.aclose()
        return []


def calculate_buy_price_sol(transactions, mint):
    """Calcule le prix d'achat moyen en SOL pour un token"""
    buys = []

    for tx in transactions:
        if tx.get('type') != 'SWAP':
            continue

        # Check if this token was bought
        token_transfers = tx.get('tokenTransfers', [])
        native_transfers = tx.get('nativeTransfers', [])

        token_bought = None
        sol_spent = 0

        for transfer in token_transfers:
            if transfer.get('mint') == mint and transfer.get('toUserAccount') == transactions[0].get('signature')[:44]:
                token_bought = transfer.get('tokenAmount', 0)

        for transfer in native_transfers:
            if transfer.get('fromUserAccount') == transactions[0].get('signature')[:44]:
                sol_spent += transfer.get('amount', 0) / 1e9

        if token_bought and sol_spent > 0:
            buys.append(sol_spent)

    if buys:
        return sum(buys) / len(buys)
    return 0


async def analyze_unrealized_pnl(wallet_address: str):
    """Analyse complète du P&L non réalisé"""

    print("\n" + "=" * 70)
    print("UNREALIZED P&L ANALYZER")
    print("=" * 70)

    # 1. Récupérer tous les tokens détenus
    tokens = await get_token_balances(wallet_address)

    if not tokens:
        print("[!] No tokens found or error")
        return

    # 2. Récupérer les transactions pour avoir les prix d'achat
    print("\n[*] Fetching transaction history...")
    transactions = await get_wallet_transactions(wallet_address)
    print(f"[+] Fetched {len(transactions)} transactions")

    # 3. Analyser chaque token
    print("\n[*] Analyzing token positions...")
    print("=" * 70)

    total_invested_sol = 0
    total_current_value_sol = 0
    sol_price_usd = 200  # Estimation

    positions = []

    for i, token in enumerate(tokens[:20], 1):  # Limiter à 20 premiers tokens
        mint = token.get('mint')
        amount = token.get('amount', 0)

        if amount == 0:
            continue

        print(f"\n[{i}] Analyzing token: {mint[:16]}...")

        # Récupérer prix actuel
        token_info = await get_token_current_price(mint)

        if not token_info:
            print(f"    [SKIP] No price info")
            continue

        price_usd = token_info['price_usd']
        mcap = token_info['mcap']

        if price_usd == 0:
            print(f"    [SKIP] Price is 0")
            continue

        # Calculer valeur actuelle
        current_value_usd = amount * price_usd

        # Estimer combien de SOL investi (on va utiliser les transactions)
        # Pour simplifier, on va chercher dans les dernières transactions
        sol_invested = 0
        for tx in transactions:
            if tx.get('type') == 'SWAP':
                token_transfers = tx.get('tokenTransfers', [])
                native_transfers = tx.get('nativeTransfers', [])

                # Check si ce token a été acheté
                for tt in token_transfers:
                    if tt.get('mint') == mint and tt.get('toUserAccount') == wallet_address:
                        # C'est un achat, calculer combien de SOL dépensé
                        for nt in native_transfers:
                            if nt.get('fromUserAccount') == wallet_address:
                                sol_invested += nt.get('amount', 0) / 1e9

        if sol_invested == 0:
            # Estimation basique
            sol_invested = 2.0  # Valeur par défaut observée

        current_value_sol = current_value_usd / sol_price_usd

        pnl_sol = current_value_sol - sol_invested
        pnl_percent = ((current_value_sol - sol_invested) / sol_invested * 100) if sol_invested > 0 else 0

        total_invested_sol += sol_invested
        total_current_value_sol += current_value_sol

        print(f"    Token: {mint[:16]}...")
        print(f"    Amount: {amount:,.0f}")
        print(f"    Price: ${price_usd:.8f}")
        print(f"    MCap: ${mcap:,.0f}")
        print(f"    Invested: {sol_invested:.4f} SOL")
        print(f"    Current Value: {current_value_sol:.4f} SOL (${current_value_usd:,.2f})")
        print(f"    P&L: {pnl_sol:+.4f} SOL ({pnl_percent:+.2f}%)")

        positions.append({
            'mint': mint,
            'invested_sol': sol_invested,
            'current_value_sol': current_value_sol,
            'pnl_sol': pnl_sol,
            'pnl_percent': pnl_percent,
            'mcap': mcap
        })

    # Résumé
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Positions: {len(positions)}")
    print(f"Total Invested: {total_invested_sol:.4f} SOL (${total_invested_sol * sol_price_usd:,.2f})")
    print(f"Current Value: {total_current_value_sol:.4f} SOL (${total_current_value_sol * sol_price_usd:,.2f})")

    net_pnl_sol = total_current_value_sol - total_invested_sol
    net_pnl_usd = net_pnl_sol * sol_price_usd
    roi = (net_pnl_sol / total_invested_sol * 100) if total_invested_sol > 0 else 0

    print(f"\nUNREALIZED P&L: {net_pnl_sol:+.4f} SOL (${net_pnl_usd:+,.2f})")
    print(f"ROI: {roi:+.2f}%")

    if net_pnl_sol > 0:
        print(f"\n[PROFITABLE] Portfolio is UP ${net_pnl_usd:+,.2f}")
    else:
        print(f"\n[LOSS] Portfolio is DOWN ${net_pnl_usd:,.2f}")

    # Top winners
    if positions:
        sorted_positions = sorted(positions, key=lambda x: x['pnl_percent'], reverse=True)

        print("\n--- TOP 5 WINNERS ---")
        for i, pos in enumerate(sorted_positions[:5], 1):
            print(f"{i}. {pos['mint'][:16]}... : {pos['pnl_percent']:+.2f}% ({pos['pnl_sol']:+.4f} SOL)")

        print("\n--- TOP 5 LOSERS ---")
        for i, pos in enumerate(sorted_positions[-5:], 1):
            print(f"{i}. {pos['mint'][:16]}... : {pos['pnl_percent']:+.2f}% ({pos['pnl_sol']:+.4f} SOL)")

    print("=" * 70)


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    await analyze_unrealized_pnl(wallet)


if __name__ == "__main__":
    asyncio.run(main())
