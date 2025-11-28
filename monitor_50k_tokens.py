"""
Surveiller les tokens qui atteignent $50K+ sur Pump.fun
Afficher ceux qui manquent dans bot_data.json pour les ajouter manuellement
"""
import requests
import json
import time
from datetime import datetime

SOL_PRICE = 200

def get_recent_tokens(limit=200):
    """Récupérer les tokens récents depuis Pump.fun"""
    try:
        url = "https://frontend-api.pump.fun/coins"
        params = {
            'limit': limit,
            'offset': 0,
            'sort': 'created_timestamp',
            'order': 'DESC'
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Erreur API: {e}")
        return []

def get_token_info(mint):
    """Récupérer les infos d'un token"""
    try:
        url = f"https://frontend-api.pump.fun/coins/{mint}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def load_bot_data():
    """Charger bot_data.json"""
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'completed': []}

def main():
    print("\n" + "="*80)
    print("SURVEILLANCE DES TOKENS $50K+ SUR PUMP.FUN")
    print("="*80)

    # Charger les données du bot
    bot_data = load_bot_data()
    existing_mints = set(t.get('mint') for t in bot_data.get('completed', []))

    print(f"\nTokens déjà dans bot_data.json: {len(existing_mints)}")
    print(f"\nRécupération des tokens récents...")

    # Récupérer les tokens récents
    recent_tokens = get_recent_tokens(200)

    if not recent_tokens:
        print("Aucun token récupéré!")
        return

    print(f"✓ {len(recent_tokens)} tokens récupérés")

    # Filtrer les tokens $50K+
    tokens_50k_plus = []

    print(f"\nAnalyse des market caps...")

    for i, token in enumerate(recent_tokens, 1):
        if i % 50 == 0:
            print(f"  [{i}/{len(recent_tokens)}]")

        mint = token.get('mint')

        # Vérifier la market cap
        # L'API retourne directement le market_cap en SOL
        market_cap_sol = token.get('usd_market_cap', 0) / SOL_PRICE if token.get('usd_market_cap') else 0

        # Si pas de market cap, récupérer les infos détaillées
        if market_cap_sol == 0:
            detailed = get_token_info(mint)
            if detailed:
                market_cap_sol = detailed.get('usd_market_cap', 0) / SOL_PRICE if detailed.get('usd_market_cap') else 0

        market_cap_usd = market_cap_sol * SOL_PRICE

        # Si >= $50K
        if market_cap_usd >= 50000:
            tokens_50k_plus.append({
                'mint': mint,
                'symbol': token.get('symbol', 'Unknown'),
                'name': token.get('name', 'Unknown'),
                'market_cap': market_cap_usd,
                'in_bot_data': mint in existing_mints
            })

        # Rate limiting
        time.sleep(0.05)

    # Trier par market cap
    tokens_50k_plus.sort(key=lambda x: x['market_cap'], reverse=True)

    # Séparer ceux qui manquent
    missing_tokens = [t for t in tokens_50k_plus if not t['in_bot_data']]
    existing_tokens = [t for t in tokens_50k_plus if t['in_bot_data']]

    print(f"\n{'='*80}")
    print(f"RÉSULTATS:")
    print(f"{'='*80}")
    print(f"\nTokens $50K+ trouvés: {len(tokens_50k_plus)}")
    print(f"  ✓ Déjà dans bot_data.json: {len(existing_tokens)}")
    print(f"  ✗ MANQUANTS: {len(missing_tokens)}")

    # Afficher les tokens existants
    if existing_tokens:
        print(f"\n{'='*80}")
        print(f"TOKENS $50K+ DÉJÀ CAPTURÉS ({len(existing_tokens)}):")
        print(f"{'='*80}\n")
        for t in existing_tokens[:10]:
            print(f"  ✓ {t['symbol']:15} ${t['market_cap']:>10,.0f}")
        if len(existing_tokens) > 10:
            print(f"  ... et {len(existing_tokens) - 10} autres")

    # Afficher les tokens manquants
    if missing_tokens:
        print(f"\n{'='*80}")
        print(f"⚠️  TOKENS $50K+ MANQUANTS ({len(missing_tokens)}):")
        print(f"{'='*80}\n")

        for i, t in enumerate(missing_tokens, 1):
            print(f"{i}. {t['symbol']:15} - ${t['market_cap']:>10,.0f}")
            print(f"   Mint: {t['mint']}")
            print(f"   Nom:  {t['name']}")
            print()

        # Sauvegarder dans un fichier
        output_file = 'missing_50k_tokens.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("TOKENS $50K+ MANQUANTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for i, t in enumerate(missing_tokens, 1):
                f.write(f"{i}. {t['symbol']} - ${t['market_cap']:,.0f}\n")
                f.write(f"   Mint: {t['mint']}\n")
                f.write(f"   Nom:  {t['name']}\n")
                f.write(f"   Commande: python add_manual_token.py {t['mint']}\n\n")

        print(f"{'='*80}")
        print(f"Liste sauvegardée dans: {output_file}")
        print(f"{'='*80}")
        print(f"\nPour ajouter un token manquant:")
        print(f"  python add_manual_token.py <mint_address>")
        print(f"\nExemple:")
        if missing_tokens:
            print(f"  python add_manual_token.py {missing_tokens[0]['mint']}")
    else:
        print(f"\n✓ Aucun token $50K+ manquant!")
        print(f"  Le bot a capturé tous les tokens à succès récents.")

if __name__ == "__main__":
    main()
