"""
PUMPFUN MONITOR - Utilise la nouvelle API PumpPortal WebSocket
"""
import asyncio
import websockets
import json
from rich.console import Console
from datetime import datetime

console = Console()

class PumpFunMonitor:
    """Moniteur de nouveaux tokens via PumpPortal WebSocket"""

    def __init__(self, api_key=None):
        # URL de l'API WebSocket
        if api_key:
            self.ws_url = f"wss://pumpportal.fun/api/data?api-key={api_key}"
        else:
            self.ws_url = "wss://pumpportal.fun/api/data"

        self.new_tokens = []
        self.latest_trades = []

    async def subscribe_new_tokens(self, callback=None):
        """S'abonne aux nouveaux tokens"""
        console.print(f"[cyan]Connexion a PumpPortal WebSocket...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                console.print("[green]Connecte! Ecoute des nouveaux tokens...")

                # S'abonner aux nouveaux tokens
                subscribe_message = {
                    "method": "subscribeNewToken"
                }
                await websocket.send(json.dumps(subscribe_message))
                console.print("[green]Abonne aux nouveaux tokens!")

                # Ecouter les messages
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        # Traiter le nouveau token
                        if callback:
                            await callback(data)
                        else:
                            await self.handle_new_token(data)

                    except websockets.exceptions.ConnectionClosed:
                        console.print("[yellow]Connexion fermee. Reconnexion...")
                        await asyncio.sleep(5)
                        break

        except Exception as e:
            console.print(f"[red]Erreur WebSocket: {e}")

    async def subscribe_token_trade(self, token_address, callback=None):
        """S'abonne aux trades d'un token specifique"""
        console.print(f"[cyan]Connexion pour tracker {token_address[:8]}...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                console.print("[green]Connecte!")

                # S'abonner aux trades du token
                subscribe_message = {
                    "method": "subscribeTokenTrade",
                    "keys": [token_address]
                }
                await websocket.send(json.dumps(subscribe_message))
                console.print(f"[green]Abonne aux trades de {token_address[:8]}!")

                # Ecouter les messages
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        if callback:
                            await callback(data)
                        else:
                            await self.handle_trade(data)

                    except websockets.exceptions.ConnectionClosed:
                        console.print("[yellow]Connexion fermee.")
                        break

        except Exception as e:
            console.print(f"[red]Erreur WebSocket: {e}")

    async def get_latest_tokens(self, count=10, timeout=30):
        """Recupere les derniers tokens (attend pendant timeout secondes)"""
        console.print(f"[cyan]Recuperation des {count} derniers tokens...")
        console.print(f"[cyan]Ecoute pendant {timeout} secondes...")

        self.new_tokens = []

        async def collect_token(data):
            """Collecte les tokens"""
            if 'mint' in data or 'signature' in data:
                self.new_tokens.append(data)
                token_addr = data.get('mint', data.get('signature', 'Unknown'))
                console.print(f"[green]Nouveau token detecte: {token_addr[:8]}...")

                if len(self.new_tokens) >= count:
                    console.print(f"[green]OK - {count} tokens collectes!")

        try:
            # Connexion avec timeout
            async with asyncio.timeout(timeout):
                await self.subscribe_new_tokens(callback=collect_token)

        except asyncio.TimeoutError:
            console.print(f"[yellow]Timeout atteint. {len(self.new_tokens)} tokens collectes.")

        except Exception as e:
            console.print(f"[red]Erreur: {e}")

        return self.new_tokens

    async def handle_new_token(self, data):
        """Gere un nouveau token"""
        console.print("\n[bold green]" + "=" * 70)
        console.print("[bold green]NOUVEAU TOKEN DETECTE!")
        console.print("[bold green]" + "=" * 70)

        console.print(f"[cyan]Heure: {datetime.now().strftime('%H:%M:%S')}")

        # Afficher les infos disponibles
        for key, value in data.items():
            console.print(f"[white]{key}: {value}")

        console.print("=" * 70 + "\n")

    async def handle_trade(self, data):
        """Gere un trade"""
        console.print(f"\n[cyan]Trade detecte: {datetime.now().strftime('%H:%M:%S')}")

        for key, value in data.items():
            console.print(f"[white]  {key}: {value}")


async def test_pumpfun_api():
    """Test de l'API PumpFun"""
    console.print("\n[bold cyan]" + "=" * 70)
    console.print("[bold cyan]TEST DE L'API PUMPPORTAL")
    console.print("[bold cyan]" + "=" * 70)

    # Creer le moniteur
    monitor = PumpFunMonitor()

    # Recuperer les derniers tokens
    tokens = await monitor.get_latest_tokens(count=5, timeout=60)

    if tokens:
        console.print(f"\n[bold green]OK - {len(tokens)} tokens recuperes!")
        console.print("\n[cyan]Liste des tokens:")

        for i, token in enumerate(tokens, 1):
            mint = token.get('mint', token.get('signature', 'Unknown'))
            console.print(f"[white]{i}. {mint}")

        return [t.get('mint', t.get('signature')) for t in tokens]
    else:
        console.print("\n[yellow]Aucun token recupere.")
        return []


if __name__ == "__main__":
    # Test
    asyncio.run(test_pumpfun_api())
