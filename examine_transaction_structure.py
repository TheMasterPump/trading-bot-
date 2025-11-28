"""
EXAMINE TRANSACTION STRUCTURE
Regarder la structure reelle des transactions pour comprendre
"""
import asyncio
import httpx
import json

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def examine_transactions(wallet_address: str):
    """Examine les 10 premieres transactions en detail"""
    client = httpx.AsyncClient(timeout=60.0)

    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
    params = {
        "api-key": HELIUS_API_KEY,
        "limit": 50
    }

    try:
        response = await client.get(url, params=params)

        if response.status_code == 200:
            transactions = response.json()

            print(f"[+] Fetched {len(transactions)} transactions\n")

            # Compter les types
            type_counts = {}
            swap_count = 0
            buy_count = 0
            sell_count = 0

            for i, tx in enumerate(transactions, 1):
                tx_type = tx.get('type')
                description = tx.get('description', '')

                type_counts[tx_type] = type_counts.get(tx_type, 0) + 1

                if tx_type == 'SWAP':
                    swap_count += 1

                    # Analyser les transferts
                    native_transfers = tx.get('nativeTransfers', [])
                    token_transfers = tx.get('tokenTransfers', [])

                    print(f"\n--- SWAP #{swap_count} (Transaction #{i}) ---")
                    print(f"Description: {description}")
                    print(f"Signature: {tx.get('signature')[:32]}...")

                    # Afficher les native transfers
                    print(f"\nNative Transfers ({len(native_transfers)}):")
                    for nt in native_transfers:
                        from_addr = nt.get('fromUserAccount', '')
                        to_addr = nt.get('toUserAccount', '')
                        amount = nt.get('amount', 0) / 1e9

                        from_label = "WALLET" if from_addr == wallet_address else from_addr[:16]
                        to_label = "WALLET" if to_addr == wallet_address else to_addr[:16]

                        direction = ""
                        if from_addr == wallet_address:
                            direction = "[OUT]"
                            buy_count += 1
                        elif to_addr == wallet_address:
                            direction = "[IN]"
                            sell_count += 1

                        print(f"  {direction} {amount:.4f} SOL: {from_label} -> {to_label}")

                    # Afficher les token transfers
                    print(f"\nToken Transfers ({len(token_transfers)}):")
                    for tt in token_transfers:
                        from_addr = tt.get('fromUserAccount', '')
                        to_addr = tt.get('toUserAccount', '')
                        mint = tt.get('mint', '')
                        amount = tt.get('tokenAmount', 0)

                        from_label = "WALLET" if from_addr == wallet_address else from_addr[:16]
                        to_label = "WALLET" if to_addr == wallet_address else to_addr[:16]

                        direction = ""
                        if from_addr == wallet_address:
                            direction = "[SELL]"
                        elif to_addr == wallet_address:
                            direction = "[BUY]"

                        print(f"  {direction} {amount:,.0f} tokens ({mint[:16]}...)")
                        print(f"        {from_label} -> {to_label}")

                    # Determiner si c'est un achat ou une vente
                    is_buy = any(tt.get('toUserAccount') == wallet_address for tt in token_transfers)
                    is_sell = any(tt.get('fromUserAccount') == wallet_address for tt in token_transfers)

                    print(f"\nType: {'BUY' if is_buy else 'SELL' if is_sell else 'UNKNOWN'}")

                    if swap_count >= 15:  # Limiter a 15 swaps
                        break

            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Transaction Types:")
            for tx_type, count in type_counts.items():
                print(f"  {tx_type}: {count}")

            print(f"\nSwaps Analyzed: {swap_count}")
            print(f"SOL OUT (buys): {buy_count}")
            print(f"SOL IN (sells): {sell_count}")

            await client.aclose()

    except Exception as e:
        print(f"[!] Error: {e}")
        await client.aclose()


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("=" * 70)
    print("TRANSACTION STRUCTURE EXAMINER")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print("=" * 70)

    await examine_transactions(wallet)


if __name__ == "__main__":
    asyncio.run(main())
