"""
Récupère le prix et MC en temps réel d'un token PumpFun
"""
import requests
from sol_price_fetcher import get_sol_price_usd

def get_token_price_live(mint_address):
    """
    Récupère le prix actuel d'un token PumpFun en temps réel

    Returns:
        dict avec:
        - mc_sol: Market cap en SOL
        - mc_usd: Market cap en USD
        - price_sol: Prix par token en SOL
        - price_usd: Prix par token en USD
        - success: bool
    """
    try:
        # API PumpFun pour obtenir les infos du token
        url = f"https://frontend-api.pump.fun/coins/{mint_address}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=5)  # Augmenté à 5s

        if response.status_code == 200:
            data = response.json()

            # DEBUG: Afficher les données reçues
            print(f"[PRICE_API] Token {mint_address[:8]}: usd_market_cap={data.get('usd_market_cap')}, virtual_sol={data.get('virtual_sol_reserves')}, virtual_token={data.get('virtual_token_reserves')}")

            # Récupérer market_cap directement (déjà en SOL normalement)
            mc_sol = float(data.get('usd_market_cap', 0)) / get_sol_price_usd() if 'usd_market_cap' in data else 0

            # Si on a virtual_sol_reserves et virtual_token_reserves, calculer le prix
            if 'virtual_sol_reserves' in data and 'virtual_token_reserves' in data:
                virtual_sol = float(data['virtual_sol_reserves']) / 1e9
                virtual_tokens = float(data['virtual_token_reserves']) / 1e6
                if virtual_tokens > 0:
                    price_sol = virtual_sol / virtual_tokens
                    # Calculer MC depuis le supply total
                    total_supply = float(data.get('total_supply', 1e9)) / 1e6  # Convert to tokens
                    mc_sol = price_sol * total_supply
                else:
                    price_sol = 0
            else:
                price_sol = 0

            # Convertir en USD
            sol_price_usd = get_sol_price_usd()
            mc_usd = mc_sol * sol_price_usd
            price_usd = price_sol * sol_price_usd

            print(f"[PRICE_API] Token {mint_address[:8]}: Calculated mc_usd=${mc_usd:,.0f}, mc_sol={mc_sol:.2f}")

            return {
                'mc_sol': mc_sol,
                'mc_usd': mc_usd,
                'price_sol': price_sol,
                'price_usd': price_usd,
                'sol_price_usd': sol_price_usd,
                'success': True,
                'raw_data': data  # Pour debug
            }
        else:
            print(f"[PRICE_API] ERROR Token {mint_address[:8]}: HTTP {response.status_code}")
    except Exception as e:
        print(f"[PRICE_API] EXCEPTION Token {mint_address[:8]}: {type(e).__name__}: {e}")

    return {
        'mc_sol': 0,
        'mc_usd': 0,
        'price_sol': 0,
        'price_usd': 0,
        'sol_price_usd': 0,
        'success': False
    }

# Test si lancé directement
if __name__ == '__main__':
    print('='*80)
    print('TEST PUMPFUN PRICE FETCHER')
    print('='*80)

    # Token de test (remplacer par un vrai token actif)
    test_mint = "7Pksb5Src77QGgmtk5r7xe8Teq1eSQUrcN6vN9YVpump"

    print(f'\nRécupération prix pour {test_mint}...')
    result = get_token_price_live(test_mint)

    if result['success']:
        print(f'\n[OK] Succes!')
        print(f'  MC SOL: {result["mc_sol"]:.4f} SOL')
        print(f'  MC USD: ${result["mc_usd"]:,.2f}')
        print(f'  Prix SOL: {result["price_sol"]:.10f} SOL')
        print(f'  Prix USD: ${result["price_usd"]:.10f}')
        print(f'  Prix SOL/USD: ${result["sol_price_usd"]:.2f}')
    else:
        print(f'\n[ERREUR] Echec - Token introuvable ou API indisponible')

    print('\n' + '='*80)
