"""
QUICK DATASET BUILDER
Collecte rapidement 50-100 tokens pour tester le système
"""
import json
import httpx
import time
from datetime import datetime
from pathlib import Path

class QuickDatasetBuilder:
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.tokens = []

    def fetch_trending_tokens(self):
        """Récupère les tokens trending sur DexScreener"""
        print("\n[*] Fetching trending Solana tokens...", flush=True)

        all_pairs = []

        try:
            # Méthode 1: Tokens qui ont le plus bougé (gainers and losers)
            print("[*] Fetching top gainers...", flush=True)
            url = "https://api.dexscreener.com/token-boosts/top/v1"

            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                # Extraire les tokens Solana
                for item in data:
                    if isinstance(item, dict):
                        token_address = item.get('tokenAddress')
                        chain = item.get('chainId', '')

                        if chain == 'solana' and token_address:
                            # Récupérer les détails du token
                            pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                            pair_response = self.client.get(pair_url)

                            if pair_response.status_code == 200:
                                pair_data = pair_response.json()
                                pairs = pair_data.get('pairs', [])
                                if pairs:
                                    all_pairs.extend(pairs)

                            time.sleep(0.5)  # Rate limit

        except Exception as e:
            print(f"[-] Method 1 failed: {e}", flush=True)

        # Méthode 2: Directement les paires Solana populaires
        try:
            print("[*] Fetching popular Solana pairs...", flush=True)

            # Récupérer plusieurs tokens connus pour trouver des paires
            popular_bases = [
                "So11111111111111111111111111111111111111112",  # SOL
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            ]

            for base in popular_bases:
                url = f"https://api.dexscreener.com/latest/dex/tokens/{base}"
                response = self.client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    pairs = data.get('pairs', [])

                    # Filtrer seulement Solana
                    solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                    all_pairs.extend(solana_pairs)

                time.sleep(1)

        except Exception as e:
            print(f"[-] Method 2 failed: {e}", flush=True)

        # Dédupliquer
        unique_pairs = {}
        for pair in all_pairs:
            addr = pair.get('baseToken', {}).get('address')
            if addr and addr not in unique_pairs:
                unique_pairs[addr] = pair

        final_pairs = list(unique_pairs.values())[:100]

        print(f"[+] Found {len(final_pairs)} unique Solana pairs", flush=True)
        return final_pairs

    def analyze_and_label(self, pair):
        """Analyse et labellise un token"""
        try:
            token_address = pair.get('baseToken', {}).get('address')

            if not token_address:
                return None

            price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
            price_change_6h = float(pair.get('priceChange', {}).get('h6', 0))
            price_change_1h = float(pair.get('priceChange', {}).get('h1', 0))

            # Labellisation intelligente
            if price_change_24h > 200:  # 200%+ = GEM
                label = "gem"
            elif price_change_24h < -70:  # -70% = RUG
                label = "rug"
            elif price_change_24h > 50:
                label = "potential_gem"
            elif price_change_24h < -40:
                label = "potential_rug"
            else:
                label = "unknown"

            token_data = {
                "token_address": token_address,
                "name": pair.get('baseToken', {}).get('name', 'Unknown'),
                "symbol": pair.get('baseToken', {}).get('symbol', 'UNK'),
                "price_usd": float(pair.get('priceUsd', 0)),
                "liquidity_usd": float(pair.get('liquidity', {}).get('usd', 0)),
                "volume_24h": float(pair.get('volume', {}).get('h24', 0)),
                "price_change_1h": price_change_1h,
                "price_change_6h": price_change_6h,
                "price_change_24h": price_change_24h,
                "market_cap": float(pair.get('marketCap', 0)),
                "fdv": float(pair.get('fdv', 0)),
                "txns_24h_buys": pair.get('txns', {}).get('h24', {}).get('buys', 0),
                "txns_24h_sells": pair.get('txns', {}).get('h24', {}).get('sells', 0),
                "pair_created_at": pair.get('pairCreatedAt', 0),
                "label": label,
                "collected_at": datetime.now().isoformat()
            }

            # Features calculées
            buys = token_data['txns_24h_buys']
            sells = token_data['txns_24h_sells']
            volume = token_data['volume_24h']
            mcap = token_data['market_cap']

            token_data['buy_sell_ratio'] = buys / max(sells, 1)
            token_data['volume_mcap_ratio'] = volume / max(mcap, 1)

            return token_data

        except Exception as e:
            return None

    def build_quick_dataset(self, target=100):
        """Construit rapidement un dataset"""
        print("\n" + "=" * 70, flush=True)
        print("QUICK DATASET BUILDER", flush=True)
        print("=" * 70, flush=True)
        print(f"Target: {target} tokens", flush=True)

        # Fetch tokens
        pairs = self.fetch_trending_tokens()

        print(f"\n[*] Analyzing tokens...", flush=True)

        for idx, pair in enumerate(pairs[:target]):
            token_data = self.analyze_and_label(pair)

            if token_data:
                self.tokens.append(token_data)

                if (idx + 1) % 10 == 0:
                    gems = sum(1 for t in self.tokens if 'gem' in t['label'])
                    rugs = sum(1 for t in self.tokens if 'rug' in t['label'])
                    print(f"[{len(self.tokens)}/{target}] Gems: {gems}, Rugs: {rugs}", flush=True)

            time.sleep(0.3)  # Rate limit

        self.save_dataset()

    def save_dataset(self):
        """Sauvegarde le dataset"""
        output_file = Path(__file__).parent / "training_dataset.json"

        gems = sum(1 for t in self.tokens if t['label'] == 'gem')
        rugs = sum(1 for t in self.tokens if t['label'] == 'rug')
        potential_gems = sum(1 for t in self.tokens if t['label'] == 'potential_gem')
        potential_rugs = sum(1 for t in self.tokens if t['label'] == 'potential_rug')

        data = {
            "tokens": self.tokens,
            "total": len(self.tokens),
            "gems": gems,
            "rugs": rugs,
            "potential_gems": potential_gems,
            "potential_rugs": potential_rugs,
            "unknown": len(self.tokens) - gems - rugs - potential_gems - potential_rugs,
            "last_updated": datetime.now().isoformat()
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 70, flush=True)
        print("DATASET STATISTICS", flush=True)
        print("=" * 70, flush=True)
        print(f"Total tokens:      {len(self.tokens)}", flush=True)
        print(f"Gems (>200%):      {gems}", flush=True)
        print(f"Rugs (<-70%):      {rugs}", flush=True)
        print(f"Potential Gems:    {potential_gems}", flush=True)
        print(f"Potential Rugs:    {potential_rugs}", flush=True)
        print("=" * 70, flush=True)
        print(f"\n[+] Dataset saved: {output_file}", flush=True)

        if gems + rugs + potential_gems + potential_rugs >= 30:
            print("\n[+] You have enough data to train the model!")
            print("[+] Run: python train_ml_model_advanced.py")
        else:
            print("\n[!] Need more labeled data for training")
            print(f"[!] Currently have {gems + rugs + potential_gems + potential_rugs} labeled tokens, need at least 30")

    def run(self):
        """Lance la construction"""
        try:
            self.build_quick_dataset(target=100)
        finally:
            self.client.close()


def main():
    builder = QuickDatasetBuilder()
    builder.run()


if __name__ == "__main__":
    main()
