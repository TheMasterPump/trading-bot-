"""
WHALE MONITOR LIVE - Surveillance 24/7 des 259 baleines
Détecte les nouveaux achats en temps réel et envoie des alertes
"""
import json
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from config import HELIUS_API_KEY

class WhaleMonitorLive:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.wallets = []
        self.last_signatures = {}  # Garde en mémoire les transactions déjà vues
        self.new_buys = []

    async def load_wallets(self):
        """Charge les 259 wallets de baleines"""
        wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

        with open(wallet_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            wallets = data.get('wallets', [])
            self.wallets = [w['address'] for w in wallets if not w['address'].startswith('EXEMPLE')]

        print(f"[+] Loaded {len(self.wallets)} whale wallets to monitor", flush=True)

    async def get_recent_transactions(self, wallet_address: str):
        """Récupère les dernières transactions d'un wallet"""
        try:
            url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
            params = {
                "api-key": HELIUS_API_KEY,
                "limit": 5
            }

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()

            return []

        except Exception:
            return []

    async def detect_token_buy(self, tx, wallet_address: str):
        """Détecte si une transaction est un achat de token"""
        try:
            signature = tx.get('signature')
            tx_type = tx.get('type')

            # Éviter les doublons
            if signature in self.last_signatures:
                return None

            self.last_signatures[signature] = True

            # Limiter la taille du cache
            if len(self.last_signatures) > 10000:
                # Garder seulement les 5000 plus récents
                keys = list(self.last_signatures.keys())
                for k in keys[:5000]:
                    del self.last_signatures[k]

            # Chercher les swaps/achats
            if tx_type in ['SWAP', 'TRANSFER']:
                description = tx.get('description', '')
                timestamp = tx.get('timestamp', 0)

                # Essayer d'extraire le token acheté
                # Dans la description Helius, chercher "bought" ou "swapped"
                if 'bought' in description.lower() or 'swapped' in description.lower():

                    alert = {
                        'wallet': wallet_address[:16] + "...",
                        'signature': signature,
                        'type': tx_type,
                        'description': description,
                        'time': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S') if timestamp else 'Unknown',
                        'timestamp': timestamp
                    }

                    return alert

            return None

        except Exception:
            return None

    async def monitor_wallet(self, wallet_address: str):
        """Monitore un wallet spécifique"""
        transactions = await self.get_recent_transactions(wallet_address)

        for tx in transactions:
            alert = await self.detect_token_buy(tx, wallet_address)
            if alert:
                self.new_buys.append(alert)
                self.display_alert(alert)

    def display_alert(self, alert):
        """Affiche une alerte"""
        print("\n" + "=" * 70, flush=True)
        print("NEW WHALE BUY DETECTED!", flush=True)
        print("=" * 70, flush=True)
        print(f"Wallet: {alert['wallet']}", flush=True)
        print(f"Time: {alert['time']}", flush=True)
        print(f"Type: {alert['type']}", flush=True)
        print(f"Description: {alert['description']}", flush=True)
        print(f"Signature: {alert['signature']}", flush=True)
        print("=" * 70, flush=True)

        # Sauvegarder dans un fichier
        self.save_alert(alert)

    def save_alert(self, alert):
        """Sauvegarde l'alerte dans un fichier"""
        alerts_file = Path(__file__).parent / "whale_alerts.json"

        # Charger les alertes existantes
        alerts = []
        if alerts_file.exists():
            try:
                with open(alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    alerts = data.get('alerts', [])
            except:
                alerts = []

        # Ajouter la nouvelle
        alerts.append(alert)

        # Garder seulement les 100 dernières
        alerts = alerts[-100:]

        # Sauvegarder
        with open(alerts_file, 'w', encoding='utf-8') as f:
            json.dump({
                'alerts': alerts,
                'total': len(alerts),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

    async def monitor_loop(self):
        """Boucle principale de monitoring"""
        print("\n" + "=" * 70, flush=True)
        print("WHALE MONITOR LIVE - 24/7 SURVEILLANCE", flush=True)
        print("=" * 70, flush=True)
        print(f"Monitoring {len(self.wallets)} whale wallets", flush=True)
        print("Press Ctrl+C to stop", flush=True)
        print("=" * 70, flush=True)

        cycle = 0

        while True:
            try:
                cycle += 1
                start_time = datetime.now()

                print(f"\n[{start_time.strftime('%H:%M:%S')}] Cycle #{cycle} - Scanning {len(self.wallets)} wallets...", flush=True)

                # Monitorer par batches de 10 wallets
                batch_size = 10
                for i in range(0, len(self.wallets), batch_size):
                    batch = self.wallets[i:i+batch_size]

                    # Monitorer ce batch en parallèle
                    tasks = [self.monitor_wallet(wallet) for wallet in batch]
                    await asyncio.gather(*tasks)

                    # Petite pause entre batches
                    await asyncio.sleep(0.5)

                elapsed = (datetime.now() - start_time).total_seconds()

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle #{cycle} complete in {elapsed:.1f}s - {len(self.new_buys)} alerts total", flush=True)

                # Attendre 30 secondes avant le prochain cycle
                await asyncio.sleep(30)

            except KeyboardInterrupt:
                print("\n[!] Stopping monitor...", flush=True)
                break
            except Exception as e:
                print(f"[!] Error in monitoring loop: {e}", flush=True)
                await asyncio.sleep(5)

    async def run(self):
        """Lance le monitoring"""
        await self.load_wallets()
        await self.monitor_loop()

    async def close(self):
        """Ferme le client"""
        await self.client.aclose()


async def main():
    monitor = WhaleMonitorLive()

    try:
        await monitor.run()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...", flush=True)
    finally:
        await monitor.close()
        print("[+] Monitor stopped", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
