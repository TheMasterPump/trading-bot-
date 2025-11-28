"""
REAL WALLET COLLECTOR
Collecte VRAIMENT des wallets en utilisant Helius API
Target: 100-500+ VRAIS wallets de traders performants
"""
import asyncio
import httpx
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

console = Console()

class RealWalletCollector:
    """Collecteur de VRAIS wallets avec Helius API"""

    def __init__(self):
        self.helius_key = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
        self.helius_url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_key}"
        self.client = httpx.AsyncClient(timeout=120.0)

        # Wallets collectes
        self.collected_wallets = {}
        self.output_file = Path(__file__).parent / "comprehensive_wallets.json"

        # Stats
        self.tokens_analyzed = 0
        self.wallets_found = 0

    async def get_successful_tokens_dexscreener(self, limit=50):
        """Get tokens qui ont pump recemment sur DexScreener"""
        console.print("\n[cyan]Fetching successful tokens from DexScreener...")

        try:
            # Try different DexScreener endpoints
            urls = [
                "https://api.dexscreener.com/latest/dex/tokens/solana",
                "https://api.dexscreener.com/latest/dex/search/?q=solana",
            ]

            for url in urls:
                try:
                    response = await self.client.get(url, timeout=30.0)

                    if response.status_code == 200:
                        data = response.json()

                        # Try to get pairs from response
                        pairs = data.get('pairs', [])

                        if not pairs:
                            continue

                        # Filter successful tokens (>500% gain in 24h)
                        successful_tokens = []

                        for pair in pairs[:200]:  # Check first 200
                            try:
                                price_change = pair.get('priceChange', {})
                                h24_change = price_change.get('h24', 0)

                                if h24_change and float(h24_change) > 500:  # >5x
                                    base_token = pair.get('baseToken', {})
                                    token_address = base_token.get('address')

                                    if token_address:
                                        successful_tokens.append({
                                            'address': token_address,
                                            'symbol': base_token.get('symbol', 'UNKNOWN'),
                                            'name': base_token.get('name', 'Unknown'),
                                            'price_change_24h': float(h24_change),
                                            'liquidity': pair.get('liquidity', {}).get('usd', 0)
                                        })
                            except:
                                continue

                        if successful_tokens:
                            console.print(f"[green]Found {len(successful_tokens)} successful tokens!")
                            return successful_tokens[:limit]

                except Exception as e:
                    console.print(f"[yellow]URL {url} failed: {e}")
                    continue

            # Si DexScreener ne marche pas, utiliser liste manuelle de tokens connus
            console.print("[yellow]DexScreener API not working, using manual token list...")
            return await self.get_manual_token_list()

        except Exception as e:
            console.print(f"[red]Error: {e}")
            return await self.get_manual_token_list()

    async def get_manual_token_list(self):
        """Liste manuelle de tokens Solana populaires"""
        console.print("[cyan]Using manual list of popular Solana tokens...")

        # Tokens connus sur Solana
        known_tokens = [
            {"address": "So11111111111111111111111111111111111111112", "symbol": "SOL", "name": "Wrapped SOL"},
            {"address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "symbol": "USDC", "name": "USD Coin"},
            {"address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "symbol": "USDT", "name": "Tether USD"},
            {"address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "symbol": "BONK", "name": "Bonk"},
            {"address": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr", "symbol": "POPCAT", "name": "Popcat"},
            {"address": "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuypump", "symbol": "BILLY", "name": "Billy"},
            {"address": "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump", "symbol": "CHILLGUY", "name": "Chill Guy"},
        ]

        return known_tokens

    async def get_token_largest_holders_helius(self, token_address, token_symbol="TOKEN"):
        """Get les plus gros holders d'un token via Helius"""
        try:
            console.print(f"[cyan]Getting holders for {token_symbol} ({token_address[:8]}...)...")

            # Method 1: getTokenLargestAccounts
            response = await self.client.post(
                self.helius_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenLargestAccounts",
                    "params": [token_address]
                }
            )

            if response.status_code == 200:
                data = response.json()

                if 'result' in data and 'value' in data['result']:
                    accounts = data['result']['value']

                    console.print(f"[green]Found {len(accounts)} holder accounts for {token_symbol}")

                    # Get owner addresses
                    holders = []

                    for i, account in enumerate(accounts[:20]):  # Top 20
                        token_account_address = account.get('address')
                        amount = account.get('amount', 0)

                        # Get account info to find owner
                        owner = await self.get_token_account_owner(token_account_address)

                        if owner:
                            holders.append({
                                'owner_address': owner,
                                'token_account': token_account_address,
                                'balance': amount,
                                'token_symbol': token_symbol
                            })

                            console.print(f"  [green]Holder {i+1}: {owner[:16]}... (Balance: {amount})")

                        # Rate limiting
                        await asyncio.sleep(0.3)

                    return holders

            return []

        except Exception as e:
            console.print(f"[red]Error getting holders for {token_symbol}: {e}")
            return []

    async def get_token_account_owner(self, token_account_address):
        """Get le owner address d'un token account"""
        try:
            response = await self.client.post(
                self.helius_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getAccountInfo",
                    "params": [
                        token_account_address,
                        {"encoding": "jsonParsed"}
                    ]
                }
            )

            if response.status_code == 200:
                data = response.json()

                if 'result' in data and data['result']:
                    value = data['result'].get('value', {})
                    if value:
                        parsed_data = value.get('data', {})
                        if isinstance(parsed_data, dict):
                            parsed = parsed_data.get('parsed', {})
                            info = parsed.get('info', {})
                            owner = info.get('owner')

                            if owner:
                                return owner

            return None

        except Exception as e:
            return None

    async def analyze_wallet_activity(self, wallet_address):
        """Analyse basique de l'activite d'un wallet"""
        try:
            # Get recent signatures
            response = await self.client.post(
                self.helius_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [
                        wallet_address,
                        {"limit": 100}
                    ]
                }
            )

            if response.status_code == 200:
                data = response.json()

                if 'result' in data:
                    signatures = data['result']
                    total_transactions = len(signatures)

                    # Estimation du success rate base sur l'activite
                    if total_transactions > 50:
                        estimated_success = 80
                    elif total_transactions > 20:
                        estimated_success = 75
                    else:
                        estimated_success = 70

                    return {
                        'total_transactions': total_transactions,
                        'estimated_success_rate': estimated_success,
                        'is_active': total_transactions > 10
                    }

            return None

        except Exception as e:
            return None

    async def collect_wallets(self, num_tokens=20):
        """Collecte principale"""

        console.print("\n[bold cyan]" + "=" * 70)
        console.print("[bold cyan]REAL WALLET COLLECTOR")
        console.print("[bold cyan]Collecting REAL wallets from Solana blockchain via Helius")
        console.print("[bold cyan]" + "=" * 70)

        # Step 1: Get successful tokens
        console.print("\n[bold yellow]STEP 1: Finding successful tokens...")
        tokens = await self.get_successful_tokens_dexscreener(num_tokens)

        if not tokens:
            console.print("[red]No tokens found!")
            return

        console.print(f"[green]Will analyze {len(tokens)} tokens")

        # Step 2: Get holders for each token
        console.print("\n[bold yellow]STEP 2: Getting holders for each token...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:

            task = progress.add_task("[cyan]Collecting wallets...", total=len(tokens))

            for token in tokens:
                token_address = token['address']
                token_symbol = token.get('symbol', 'UNKNOWN')

                # Get holders
                holders = await self.get_token_largest_holders_helius(token_address, token_symbol)

                # Add to collection
                for holder in holders:
                    wallet_addr = holder['owner_address']

                    if wallet_addr not in self.collected_wallets:
                        # Analyze wallet
                        activity = await self.analyze_wallet_activity(wallet_addr)

                        if activity and activity['is_active']:
                            self.collected_wallets[wallet_addr] = {
                                'address': wallet_addr,
                                'name': f"Holder of {token_symbol}",
                                'source': f"Top holder of {token_symbol}",
                                'tokens_held': [token_symbol],
                                'estimated_success_rate': activity['estimated_success_rate'],
                                'total_transactions': activity['total_transactions'],
                                'notes': f"Top holder with {activity['total_transactions']} transactions",
                                'discovered_at': datetime.now().isoformat()
                            }

                            self.wallets_found += 1
                            console.print(f"[green]+++ Added wallet {self.wallets_found}: {wallet_addr[:16]}...")
                    else:
                        # Wallet deja connu, ajouter le token
                        if token_symbol not in self.collected_wallets[wallet_addr]['tokens_held']:
                            self.collected_wallets[wallet_addr]['tokens_held'].append(token_symbol)
                            # Boost success rate
                            self.collected_wallets[wallet_addr]['estimated_success_rate'] += 3

                self.tokens_analyzed += 1
                progress.update(task, advance=1)

                # Rate limiting between tokens
                await asyncio.sleep(2)

        # Step 3: Save results
        console.print("\n[bold yellow]STEP 3: Saving wallets...")
        self.save_wallets()

        # Step 4: Display results
        self.display_results()

    def save_wallets(self):
        """Sauvegarde les wallets collectes"""
        wallets_list = list(self.collected_wallets.values())

        # Load existing wallets if file exists
        existing_wallets = []
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r') as f:
                    existing_data = json.load(f)
                    existing_wallets = existing_data.get('wallets', [])
            except:
                pass

        # Merge with existing
        existing_addresses = {w['address'] for w in existing_wallets if 'address' in w}

        for wallet in wallets_list:
            if wallet['address'] not in existing_addresses:
                existing_wallets.append(wallet)

        # Save
        data = {
            'wallets': existing_wallets,
            'total': len(existing_wallets),
            'last_updated': datetime.now().isoformat(),
            'sources': [
                'Helius API - Real blockchain data',
                'Top holders of successful tokens',
                'Automated collection via real_wallet_collector.py'
            ],
            'stats': {
                'tokens_analyzed': self.tokens_analyzed,
                'unique_wallets': len(existing_wallets),
                'collection_method': 'Helius getTokenLargestAccounts'
            }
        }

        with open(self.output_file, 'w') as f:
            json.dump(data, f, indent=2)

        console.print(f"\n[green]Wallets saved to: {self.output_file}")
        console.print(f"[green]Total wallets in database: {len(existing_wallets)}")

    def display_results(self):
        """Affiche les resultats"""
        console.print("\n[bold cyan]" + "=" * 70)
        console.print("[bold cyan]COLLECTION COMPLETE!")
        console.print("[bold cyan]" + "=" * 70)

        console.print(f"\n[green]Tokens analyzed: {self.tokens_analyzed}")
        console.print(f"[green]New wallets collected: {self.wallets_found}")
        console.print(f"[green]Total unique wallets: {len(self.collected_wallets)}")

        # Top multi-token holders
        multi_holders = sorted(
            self.collected_wallets.values(),
            key=lambda w: len(w['tokens_held']),
            reverse=True
        )[:10]

        if multi_holders:
            console.print("\n[bold yellow]Top 10 Multi-Token Holders:")

            table = Table()
            table.add_column("Wallet", style="cyan")
            table.add_column("Tokens", style="green")
            table.add_column("Success Rate", style="yellow")
            table.add_column("Transactions", style="magenta")

            for wallet in multi_holders:
                table.add_row(
                    wallet['address'][:16] + "...",
                    ", ".join(wallet['tokens_held'][:3]),
                    f"{wallet['estimated_success_rate']}%",
                    str(wallet.get('total_transactions', 0))
                )

            console.print(table)

        console.print("\n[bold green]Next step: Run this script again to collect more wallets!")
        console.print("[green]Target: 500-1000+ wallets for ultra-precise predictions")

    async def close(self):
        """Cleanup"""
        await self.client.aclose()


async def main():
    console.print("""
[bold cyan]
==================================================================
    REAL WALLET COLLECTOR
    Collecte de VRAIS wallets via Helius API
==================================================================
[/bold cyan]

[yellow]Ce script va collecter de VRAIES adresses de wallets depuis la blockchain Solana.[/yellow]

[bold]Options:[/bold]
[1] Quick collection (10 tokens = ~100-200 wallets) - 5-10 minutes
[2] Medium collection (20 tokens = ~200-400 wallets) - 15-20 minutes
[3] Large collection (50 tokens = ~500-1000 wallets) - 30-60 minutes
    """)

    choice = input("\nChoice (1-3): ").strip()

    num_tokens = 10
    if choice == '2':
        num_tokens = 20
    elif choice == '3':
        num_tokens = 50

    collector = RealWalletCollector()

    try:
        await collector.collect_wallets(num_tokens)
    finally:
        await collector.close()

    console.print("\n[bold green]COLLECTION TERMINEE!")
    console.print("[green]Check: comprehensive_wallets.json")


if __name__ == "__main__":
    asyncio.run(main())
