"""
Récupère le prix de SOL en temps réel depuis CoinGecko
Cache le prix pour éviter trop de requêtes
"""
import requests
from datetime import datetime, timedelta

class SolPriceFetcher:
    def __init__(self):
        self.cache_duration = 30  # Secondes - mettre à jour toutes les 30s
        self.last_update = None
        self.cached_price = 200.0  # Prix par défaut si API échoue
        self.api_url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"

    def get_price(self):
        """Récupère le prix SOL/USD en temps réel depuis CoinGecko"""
        # Vérifier si le cache est encore valide
        if (self.last_update and
            datetime.now() - self.last_update < timedelta(seconds=self.cache_duration)):
            return self.cached_price

        # Fetch depuis CoinGecko
        try:
            response = requests.get(self.api_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                price = float(data['solana']['usd'])

                # Mettre à jour le cache
                self.cached_price = price
                self.last_update = datetime.now()

                return price
        except Exception as e:
            # En cas d'erreur, retourner le prix en cache
            print(f"[WARN] Erreur fetch prix SOL: {e}, utilisation cache: ${self.cached_price:.2f}")
            pass

        return self.cached_price

    def get_price_info(self):
        """Retourne le prix avec info sur l'âge du cache"""
        price = self.get_price()
        age = (datetime.now() - self.last_update).total_seconds() if self.last_update else 0
        return {
            'price': price,
            'age_seconds': age,
            'timestamp': self.last_update,
            'is_cached': age < self.cache_duration
        }

# Instance globale
sol_price_fetcher = SolPriceFetcher()

# Fonction rapide pour avoir le prix
def get_sol_price_usd():
    """Fonction simple pour récupérer le prix SOL"""
    return sol_price_fetcher.get_price()

# Test si lancé directement
if __name__ == '__main__':
    import time

    print('='*80)
    print('TEST SOL PRICE FETCHER - COINGECKO')
    print('='*80)

    fetcher = SolPriceFetcher()

    # Test 1: Premier fetch
    print('\n[Test 1] Premier fetch depuis CoinGecko...')
    info = fetcher.get_price_info()
    print(f"Prix SOL: ${info['price']:.2f} USD")
    print(f"Cache: {info['is_cached']}")
    print(f"Age: {info['age_seconds']:.1f}s")

    # Test 2: Fetch depuis cache (devrait être instantané)
    print('\n[Test 2] Fetch depuis cache...')
    start = time.time()
    price = fetcher.get_price()
    elapsed = time.time() - start
    print(f"Prix SOL: ${price:.2f} USD")
    print(f"Temps: {elapsed*1000:.1f}ms (devrait etre <1ms)")

    # Test 3: Multiple fetches rapides (pour voir le cache)
    print('\n[Test 3] 5 fetches rapides (devrait utiliser cache)...')
    for i in range(5):
        start = time.time()
        price = fetcher.get_price()
        elapsed = time.time() - start
        info = fetcher.get_price_info()
        print(f"  Fetch {i+1}: ${price:.2f} en {elapsed*1000:.1f}ms (cache: {info['is_cached']})")

    print('\n' + '='*80)
    print('Tests termines')
    print(f"Prix SOL actuel: ${fetcher.get_price():.2f} USD")
    print('='*80)
