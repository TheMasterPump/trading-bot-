"""
CHECK PUMP.FUN TRUE P&L
Utilise les vraies données pump.fun pour calculer le P&L
"""
import asyncio
import httpx
import json
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_token_balances(wallet_address: str):
    """Récupère tous les tokens détenus"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Getting token balances...")

    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/balances"
    params = {"api-key": HELIUS_API_KEY}

    try:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            tokens = data.get('tokens', [])
            print(f"[+] Found {len(tokens)} tokens")
            await client.aclose()
            return tokens
        else:
            await client.aclose()
            return []
    except Exception as e:
        print(f"[!] Error: {e}")
        await client.aclose()
        return []


async def get_pumpfun_token_data(mint: str):
    """Récupère les données d'un token depuis pump.fun API"""
    client = httpx.AsyncClient(timeout=30.0)

    try:
        # Essayer l'API publique pump.fun
        # Note: L'API exacte peut varier, on va essayer plusieurs endpoints

        # Méthode 1: API directe pump.fun
        url = f"https://frontend-api.pump.fun/coins/{mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            await client.aclose()

            # Extraire les vraies données
            return {
                'mint': mint,
                'name': data.get('name'),
                'symbol': data.get('symbol'),
                'market_cap': data.get('market_cap', 0),
                'virtual_sol_reserves': data.get('virtual_sol_reserves', 0),
                'virtual_token_reserves': data.get('virtual_token_reserves', 0),
                'total_supply': data.get('total_supply', 0),
                'bonding_curve': data.get('bonding_curve'),
                'complete': data.get('complete', False),  # Migré ou non
                'creator': data.get('creator'),
                'uri': data.get('uri')
            }

        await client.aclose()
        return None

    except Exception as e:
        await client.aclose()
        return None


async def calculate_token_value_pumpfun(token_amount: float, token_data):
    """Calcule la vraie valeur d'un token basé sur la bonding curve pump.fun"""
    if not token_data:
        return 0

    # Formule pump.fun bonding curve
    # virtual_sol_reserves et virtual_token_reserves
    virtual_sol = float(token_data.get('virtual_sol_reserves', 0))
    virtual_tokens = float(token_data.get('virtual_token_reserves', 0))

    if virtual_sol == 0 or virtual_tokens == 0:
        return 0

    # Prix = virtual_sol / virtual_tokens
    price_per_token_sol = virtual_sol / virtual_tokens

    # Valeur totale
    value_sol = token_amount * price_per_token_sol

    return value_sol


async def get_wallet_buys(wallet_address: str):
    """Récupère tous les achats du wallet"""
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

            buys_by_token = {}

            for tx in transactions:
                if tx.get('type') != 'SWAP':
                    continue

                # Analyser les transferts
                native_transfers = tx.get('nativeTransfers', [])
                token_transfers = tx.get('tokenTransfers', [])

                sol_spent = 0
                token_bought = None

                for nt in native_transfers:
                    if nt.get('fromUserAccount') == wallet_address:
                        sol_spent += nt.get('amount', 0) / 1e9

                for tt in token_transfers:
                    if tt.get('toUserAccount') == wallet_address:
                        token_bought = {
                            'mint': tt.get('mint'),
                            'amount': tt.get('tokenAmount', 0)
                        }

                if token_bought and sol_spent > 0:
                    mint = token_bought['mint']
                    if mint not in buys_by_token:
                        buys_by_token[mint] = []

                    buys_by_token[mint].append({
                        'sol_spent': sol_spent,
                        'timestamp': tx.get('timestamp'),
                        'signature': tx.get('signature')
                    })

            await client.aclose()
            return buys_by_token

        await client.aclose()
        return {}

    except Exception as e:
        await client.aclose()
        return {}


async def analyze_pumpfun_portfolio(wallet_address: str):
    """Analyse complète du portfolio pump.fun"""

    print("\n" + "=" * 70)
    print("PUMP.FUN TRUE P&L ANALYZER")
    print("=" * 70)
    print(f"Wallet: {wallet_address}")
    print("=" * 70)

    # 1. Récupérer les tokens
    tokens = await get_token_balances(wallet_address)

    if not tokens:
        print("[!] No tokens found")
        return

    # 2. Récupérer l'historique d'achats
    print("\n[*] Fetching buy history...")
    buys_by_token = await get_wallet_buys(wallet_address)
    print(f"[+] Found buys for {len(buys_by_token)} tokens")

    # 3. Analyser chaque token avec pump.fun API
    print("\n[*] Analyzing positions with pump.fun data...")
    print("=" * 70)

    total_invested_sol = 0
    total_current_value_sol = 0
    sol_price_usd = 200

    positions = []
    pumpfun_tokens = 0
    migrated_tokens = 0

    for i, token in enumerate(tokens[:30], 1):  # Analyser les 30 premiers
        mint = token.get('mint')
        amount = token.get('amount', 0)

        if amount == 0:
            continue

        print(f"\n[{i}] Token: {mint[:16]}...")

        # Récupérer données pump.fun
        pumpfun_data = await get_pumpfun_token_data(mint)

        if not pumpfun_data:
            print(f"    [SKIP] Not a pump.fun token or no data")
            continue

        pumpfun_tokens += 1

        # Vérifier si migré
        is_complete = pumpfun_data.get('complete', False)

        if is_complete:
            migrated_tokens += 1
            print(f"    [MIGRATED] Token has graduated to Raydium")
        else:
            print(f"    [PUMP.FUN] Still on bonding curve")

        # Calculer valeur actuelle
        current_value_sol = await calculate_token_value_pumpfun(amount, pumpfun_data)

        # Récupérer combien investi
        invested_sol = 0
        if mint in buys_by_token:
            for buy in buys_by_token[mint]:
                invested_sol += buy['sol_spent']

        if invested_sol == 0:
            invested_sol = 2.0  # Valeur par défaut

        pnl_sol = current_value_sol - invested_sol
        pnl_percent = ((current_value_sol - invested_sol) / invested_sol * 100) if invested_sol > 0 else 0

        total_invested_sol += invested_sol
        total_current_value_sol += current_value_sol

        print(f"    Name: {pumpfun_data.get('name', 'Unknown')}")
        print(f"    Symbol: {pumpfun_data.get('symbol', 'Unknown')}")
        print(f"    Amount: {amount:,.0f}")
        print(f"    Invested: {invested_sol:.4f} SOL")
        print(f"    Current Value: {current_value_sol:.4f} SOL (${current_value_sol * sol_price_usd:,.2f})")
        print(f"    P&L: {pnl_sol:+.4f} SOL ({pnl_percent:+.2f}%)")

        positions.append({
            'mint': mint,
            'name': pumpfun_data.get('name'),
            'symbol': pumpfun_data.get('symbol'),
            'invested_sol': invested_sol,
            'current_value_sol': current_value_sol,
            'pnl_sol': pnl_sol,
            'pnl_percent': pnl_percent,
            'migrated': is_complete
        })

        # Petit délai pour ne pas spam l'API
        await asyncio.sleep(0.5)

    # Résumé
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Pump.fun Tokens: {pumpfun_tokens}")
    print(f"Still on bonding curve: {pumpfun_tokens - migrated_tokens}")
    print(f"Migrated to Raydium: {migrated_tokens}")
    print(f"\nTotal Invested: {total_invested_sol:.4f} SOL (${total_invested_sol * sol_price_usd:,.2f})")
    print(f"Current Value: {total_current_value_sol:.4f} SOL (${total_current_value_sol * sol_price_usd:,.2f})")

    net_pnl_sol = total_current_value_sol - total_invested_sol
    net_pnl_usd = net_pnl_sol * sol_price_usd
    roi = (net_pnl_sol / total_invested_sol * 100) if total_invested_sol > 0 else 0

    print(f"\nTRUE P&L: {net_pnl_sol:+.4f} SOL (${net_pnl_usd:+,.2f})")
    print(f"ROI: {roi:+.2f}%")

    if net_pnl_sol > 0:
        print(f"\n[PROFITABLE] Portfolio is UP ${net_pnl_usd:+,.2f}")
    else:
        print(f"\n[LOSS] Portfolio is DOWN ${abs(net_pnl_usd):,.2f}")

    # Top performers
    if positions:
        sorted_positions = sorted(positions, key=lambda x: x['pnl_percent'], reverse=True)

        print("\n--- TOP 5 WINNERS ---")
        for i, pos in enumerate(sorted_positions[:5], 1):
            status = "[MIGRATED]" if pos['migrated'] else "[PUMP.FUN]"
            print(f"{i}. {pos['name']} ({pos['symbol']}) {status}")
            print(f"   P&L: {pos['pnl_percent']:+.2f}% ({pos['pnl_sol']:+.4f} SOL)")

        print("\n--- TOP 5 LOSERS ---")
        for i, pos in enumerate(reversed(sorted_positions[-5:]), 1):
            status = "[MIGRATED]" if pos['migrated'] else "[PUMP.FUN]"
            print(f"{i}. {pos['name']} ({pos['symbol']}) {status}")
            print(f"   P&L: {pos['pnl_percent']:+.2f}% ({pos['pnl_sol']:+.4f} SOL)")

    print("=" * 70)


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    await analyze_pumpfun_portfolio(wallet)


if __name__ == "__main__":
    asyncio.run(main())
