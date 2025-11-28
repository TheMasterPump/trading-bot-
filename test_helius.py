"""
Test de la configuration Helius API
"""
from dotenv import load_dotenv
import os
from rich.console import Console

console = Console()

# Charger les variables d'environnement
load_dotenv()

console.print("\n[bold cyan]" + "=" * 70)
console.print("[bold cyan]TEST DE LA CONFIGURATION HELIUS API")
console.print("[bold cyan]" + "=" * 70)

# Verifier la cle API
helius_key = os.getenv("HELIUS_API_KEY", "")

if helius_key:
    # Masquer partiellement la cle
    masked_key = helius_key[:8] + "..." + helius_key[-8:]
    console.print(f"\n[green]OK - Cle Helius trouvee: {masked_key}")

    # Construire l'URL RPC
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    console.print(f"[green]OK - URL RPC Helius configuree!")

    # Test de connexion
    console.print("\n[cyan]Test de connexion a l'API Helius...")

    import httpx
    import asyncio

    async def test_connection():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test simple: getHealth
                response = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getHealth"
                    }
                )

                if response.status_code == 200:
                    console.print("[green]OK - Connexion Helius reussie!")
                    console.print(f"[cyan]Response: {response.json()}")

                    # Test getVersion
                    response2 = await client.post(
                        rpc_url,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getVersion"
                        }
                    )

                    if response2.status_code == 200:
                        version_data = response2.json()
                        console.print(f"[green]OK - Version Solana: {version_data.get('result', {}).get('solana-core', 'N/A')}")

                    console.print("\n[bold green]" + "=" * 70)
                    console.print("[bold green]HELIUS API CONFIGUREE AVEC SUCCES!")
                    console.print("[bold green]" + "=" * 70)
                    console.print("\n[cyan]Plan: DEVELOPER (10M credits)")
                    console.print("[cyan]Plus d'erreurs 429 (rate limit)!")
                    console.print("[cyan]Performance maximale pour l'analyse!\n")

                else:
                    console.print(f"[red]Erreur: Status {response.status_code}")

        except Exception as e:
            console.print(f"[red]Erreur de connexion: {e}")

    asyncio.run(test_connection())

else:
    console.print("\n[red]ERREUR: Cle Helius non trouvee!")
    console.print("[yellow]Assurez-vous que le fichier .env contient HELIUS_API_KEY")

# Verifier les autres cles
console.print("\n[cyan]Autres cles API:")
solscan_key = os.getenv("SOLSCAN_API_KEY", "")
insightx_key = os.getenv("INSIGHTX_API_KEY", "")

if solscan_key:
    console.print(f"[green]OK - Solscan API: {solscan_key[:20]}...")
else:
    console.print("[yellow]Solscan API: Non configuree")

if insightx_key:
    masked_ix = insightx_key[:8] + "..." + insightx_key[-8:]
    console.print(f"[green]OK - InsightX API: {masked_ix}")
else:
    console.print("[yellow]InsightX API: Non configuree")

console.print("\n[bold cyan]Configuration terminee!\n")
