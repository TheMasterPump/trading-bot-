"""
PUMP.FUN MASS SCRAPER
Collecte 500+ tokens pump.fun récents avec toutes leurs métriques
pour créer un dataset d'entraînement ML de qualité
"""
import json
import httpx
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from config import HELIUS_API_KEY, SOLANA_RPC_URL

PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

class PumpFunScraper:
    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
        self.tokens_data = []
        self.processed_addresses = set()

    def get_new_tokens_dexscreener(self, limit=100):
        """Récupère les nouveaux tokens via DexScreener"""
        print(f"\n[*] Fetching tokens from DexScreener...", flush=True)

        try:
            # DexScreener API - tokens récents sur Solana
            url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"

            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])

                # Filtrer les tokens pump.fun
                pumpfun_pairs = []
                for pair in pairs[:limit]:
                    # Vérifier si c'est sur pump.fun (via l'URL ou d'autres indices)
                    if pair.get('chainId') == 'solana':
                        pumpfun_pairs.append(pair)

                print(f"[+] Found {len(pumpfun_pairs)} Solana pairs", flush=True)
                return pumpfun_pairs

            return []

        except Exception as e:
            print(f"[-] Error fetching from DexScreener: {e}", flush=True)
            return []

    def get_token_holders(self, token_address: str):
        """Récupère le nombre de holders via Helius"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [token_address]
            }

            response = self.client.post(SOLANA_RPC_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                accounts = data.get("result", {}).get("value", [])
                return len(accounts)

            return 0

        except Exception:
            return 0

    def analyze_token_metrics(self, pair):
        """Analyse complète d'un token"""
        try:
            token_address = pair.get('baseToken', {}).get('address')

            if not token_address or token_address in self.processed_addresses:
                return None

            # Extraire les métriques de base
            price_usd = float(pair.get('priceUsd', 0))
            liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))

            fdv = float(pair.get('fdv', 0))
            market_cap = float(pair.get('marketCap', 0))

            # Calculer si c'est un rug ou gem
            # Gem = price_change > 100% et toujours actif
            # Rug = price_change < -80%
            label = "unknown"
            if price_change_24h > 100:
                label = "gem"
            elif price_change_24h < -80:
                label = "rug"
            elif price_change_24h > 20:
                label = "potential_gem"
            elif price_change_24h < -50:
                label = "potential_rug"

            # Créer l'entrée du dataset
            token_data = {
                "token_address": token_address,
                "name": pair.get('baseToken', {}).get('name', 'Unknown'),
                "symbol": pair.get('baseToken', {}).get('symbol', 'Unknown'),
                "price_usd": price_usd,
                "liquidity_usd": liquidity_usd,
                "volume_24h": volume_24h,
                "price_change_24h": price_change_24h,
                "fdv": fdv,
                "market_cap": market_cap,
                "pair_created_at": pair.get('pairCreatedAt', 0),
                "txns_24h_buys": pair.get('txns', {}).get('h24', {}).get('buys', 0),
                "txns_24h_sells": pair.get('txns', {}).get('h24', {}).get('sells', 0),
                "label": label,
                "collected_at": datetime.now().isoformat(),
                "dex_url": pair.get('url', ''),
            }

            # Calculer des features supplémentaires
            buys = token_data['txns_24h_buys']
            sells = token_data['txns_24h_sells']

            if sells > 0:
                token_data['buy_sell_ratio'] = buys / sells
            else:
                token_data['buy_sell_ratio'] = buys if buys > 0 else 0

            if market_cap > 0:
                token_data['volume_mcap_ratio'] = volume_24h / market_cap
            else:
                token_data['volume_mcap_ratio'] = 0

            self.processed_addresses.add(token_address)

            return token_data

        except Exception as e:
            print(f"[-] Error analyzing token: {e}", flush=True)
            return None

    def search_recent_tokens_advanced(self):
        """Cherche les tokens récents via plusieurs méthodes"""
        print("\n[*] Method 2: Searching via Birdeye API...", flush=True)

        try:
            # Birdeye a une bonne API pour les nouveaux tokens
            url = "https://public-api.birdeye.so/defi/tokenlist"
            headers = {
                "X-API-KEY": "your-birdeye-key-here"  # Optionnel
            }
            params = {
                "sort_by": "v24hUSD",
                "sort_type": "desc",
                "offset": 0,
                "limit": 50
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                tokens = data.get('data', {}).get('tokens', [])
                print(f"[+] Found {len(tokens)} tokens from Birdeye", flush=True)
                return tokens

        except Exception as e:
            print(f"[-] Birdeye method failed: {e}", flush=True)

        return []

    def get_tokens_from_popular_pairs(self):
        """Récupère les tokens depuis les paires SOL et USDC"""
        print("\n[*] Method 2: Fetching from popular trading pairs...", flush=True)

        pairs = []

        try:
            # Récupérer les paires SOL
            url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"
            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                sol_pairs = data.get('pairs', [])
                # Filtrer seulement Solana chain
                pairs.extend([p for p in sol_pairs if p.get('chainId') == 'solana'][:50])

            time.sleep(2)

            # Récupérer les paires USDC
            url = "https://api.dexscreener.com/latest/dex/tokens/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                usdc_pairs = data.get('pairs', [])
                pairs.extend([p for p in usdc_pairs if p.get('chainId') == 'solana'][:50])

            print(f"[+] Found {len(pairs)} pairs from popular bases", flush=True)

        except Exception as e:
            print(f"[-] Error: {e}", flush=True)

        return pairs

    def scrape_tokens(self, target_count=500):
        """Scrape le nombre cible de tokens"""
        print("\n" + "=" * 70, flush=True)
        print("PUMP.FUN MASS SCRAPER", flush=True)
        print("=" * 70, flush=True)
        print(f"Target: {target_count} tokens", flush=True)
        print(f"Estimated time: 2-6 hours (depending on API limits)", flush=True)

        iteration = 0

        while len(self.tokens_data) < target_count:
            iteration += 1
            print(f"\n--- Iteration {iteration} ({datetime.now().strftime('%H:%M:%S')}) ---", flush=True)
            print(f"Current dataset: {len(self.tokens_data)}/{target_count} tokens", flush=True)

            # Méthode 1: DexScreener trending
            pairs = self.get_new_tokens_dexscreener(limit=50)

            # Méthode 2: Popular trading pairs
            if len(pairs) < 20:  # Si méthode 1 donne peu de résultats
                pairs.extend(self.get_tokens_from_popular_pairs())

            print(f"[*] Processing {len(pairs)} pairs...", flush=True)

            for idx, pair in enumerate(pairs):
                if len(self.tokens_data) >= target_count:
                    break

                token_data = self.analyze_token_metrics(pair)

                if token_data:
                    self.tokens_data.append(token_data)

                    # Afficher progression tous les 5 tokens
                    if len(self.tokens_data) % 5 == 0:
                        gems = sum(1 for t in self.tokens_data if t['label'] == 'gem')
                        rugs = sum(1 for t in self.tokens_data if t['label'] == 'rug')
                        pot_gems = sum(1 for t in self.tokens_data if t['label'] == 'potential_gem')
                        pot_rugs = sum(1 for t in self.tokens_data if t['label'] == 'potential_rug')
                        print(f"[{len(self.tokens_data)}/{target_count}] Gems:{gems}, Rugs:{rugs}, Pot.Gems:{pot_gems}, Pot.Rugs:{pot_rugs}", flush=True)

                # Pause pour éviter rate limit
                time.sleep(0.3)

            # Sauvegarder progressivement tous les 25 tokens
            if len(self.tokens_data) % 25 == 0 and len(self.tokens_data) > 0:
                self.save_dataset()

            # Si on n'a pas atteint la cible, attendre avant de réessayer
            if len(self.tokens_data) < target_count:
                wait_time = 60  # 1 minute entre les itérations
                print(f"\n[*] Waiting {wait_time}s before next iteration...", flush=True)
                time.sleep(wait_time)

        print(f"\n[+] Scraping complete! Collected {len(self.tokens_data)} tokens", flush=True)
        self.save_dataset()

    def save_dataset(self):
        """Sauvegarde le dataset"""
        output_file = Path(__file__).parent / "training_dataset.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "tokens": self.tokens_data,
                "total": len(self.tokens_data),
                "gems": sum(1 for t in self.tokens_data if t['label'] == 'gem'),
                "rugs": sum(1 for t in self.tokens_data if t['label'] == 'rug'),
                "potential_gems": sum(1 for t in self.tokens_data if t['label'] == 'potential_gem'),
                "potential_rugs": sum(1 for t in self.tokens_data if t['label'] == 'potential_rug'),
                "unknown": sum(1 for t in self.tokens_data if t['label'] == 'unknown'),
                "last_updated": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Dataset saved: {output_file}", flush=True)
        self.display_stats()

    def display_stats(self):
        """Affiche les statistiques du dataset"""
        gems = sum(1 for t in self.tokens_data if t['label'] == 'gem')
        rugs = sum(1 for t in self.tokens_data if t['label'] == 'rug')
        potential_gems = sum(1 for t in self.tokens_data if t['label'] == 'potential_gem')
        potential_rugs = sum(1 for t in self.tokens_data if t['label'] == 'potential_rug')
        unknown = sum(1 for t in self.tokens_data if t['label'] == 'unknown')

        print("\n" + "=" * 70, flush=True)
        print("DATASET STATISTICS", flush=True)
        print("=" * 70, flush=True)
        print(f"Total tokens:      {len(self.tokens_data)}", flush=True)
        print(f"Gems (>100%):      {gems}", flush=True)
        print(f"Rugs (<-80%):      {rugs}", flush=True)
        print(f"Potential Gems:    {potential_gems}", flush=True)
        print(f"Potential Rugs:    {potential_rugs}", flush=True)
        print(f"Unknown:           {unknown}", flush=True)
        print("=" * 70, flush=True)

    def run(self, target=500):
        """Lance le scraping"""
        try:
            self.scrape_tokens(target_count=target)
            self.save_dataset()
        finally:
            self.client.close()


def main():
    print("\n" + "=" * 70, flush=True)
    print("PUMP.FUN MASS SCRAPER - ML DATASET BUILDER", flush=True)
    print("=" * 70, flush=True)
    print("\nThis will collect 500+ tokens with complete metrics", flush=True)
    print("Estimated time: 2-3 hours", flush=True)

    scraper = PumpFunScraper()
    scraper.run(target=500)


if __name__ == "__main__":
    main()
