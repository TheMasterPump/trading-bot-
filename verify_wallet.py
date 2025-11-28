"""
VERIFY WALLET - Check basic info
"""
import asyncio
import httpx

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def verify_wallet(wallet_address: str):
    """Vérifie les infos de base du wallet"""
    client = httpx.AsyncClient(timeout=60.0)

    print("\n" + "=" * 70)
    print("WALLET VERIFICATION")
    print("=" * 70)
    print(f"Address: {wallet_address}")
    print("=" * 70)

    # 1. Get SOL balance
    print("\n[*] Checking SOL balance...")
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet_address]
    }

    try:
        response = await client.post(rpc_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            lamports = data.get("result", {}).get("value", 0)
            sol_balance = lamports / 1e9
            print(f"[+] SOL Balance: {sol_balance:.4f} SOL (${sol_balance * 200:,.2f})")
        else:
            print(f"[!] Error getting balance: {response.status_code}")
    except Exception as e:
        print(f"[!] Error: {e}")

    # 2. Get transaction count
    print("\n[*] Getting transaction count...")

    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
    params = {
        "api-key": HELIUS_API_KEY,
        "limit": 1
    }

    try:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            print(f"[+] API accessible - wallet exists")
        else:
            print(f"[!] API Error: {response.status_code}")
            print(f"[!] Response: {response.text[:200]}")
    except Exception as e:
        print(f"[!] Error: {e}")

    # 3. Get ALL transactions summary
    print("\n[*] Fetching recent transactions...")

    all_transactions = []
    for batch in range(5):
        url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
        params = {
            "api-key": HELIUS_API_KEY,
            "limit": 100
        }

        if batch > 0 and all_transactions:
            params["before"] = all_transactions[-1].get('signature')

        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                transactions = response.json()
                if not transactions:
                    break
                all_transactions.extend(transactions)
                print(f"[+] Batch {batch + 1}: {len(transactions)} transactions")

                if len(transactions) < 100:
                    break
            else:
                print(f"[!] Error batch {batch + 1}: {response.status_code}")
                break
        except Exception as e:
            print(f"[!] Error: {e}")
            break

    print(f"\n[+] Total transactions found: {len(all_transactions)}")

    # 4. Analyze transaction types
    if all_transactions:
        print("\n[*] Analyzing transaction types...")
        types = {}
        for tx in all_transactions:
            tx_type = tx.get('type', 'UNKNOWN')
            types[tx_type] = types.get(tx_type, 0) + 1

        print("\nTransaction breakdown:")
        for tx_type, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tx_type}: {count}")

        # 5. Calculate total SOL flow
        print("\n[*] Calculating SOL flow...")
        total_sol_in = 0
        total_sol_out = 0

        for tx in all_transactions:
            native_transfers = tx.get('nativeTransfers', [])

            for transfer in native_transfers:
                from_addr = transfer.get('fromUserAccount')
                to_addr = transfer.get('toUserAccount')
                amount = transfer.get('amount', 0) / 1e9

                if to_addr == wallet_address:
                    total_sol_in += amount
                elif from_addr == wallet_address:
                    total_sol_out += amount

        net_sol = total_sol_in - total_sol_out

        print(f"\nSOL IN (received): {total_sol_in:.4f} SOL")
        print(f"SOL OUT (spent): {total_sol_out:.4f} SOL")
        print(f"NET FLOW: {net_sol:+.4f} SOL")
        print(f"\nCurrent balance: {sol_balance:.4f} SOL")

        # If net flow doesn't match balance, explain why
        if abs(net_sol - sol_balance) > 0.01:
            print(f"\n[i] Note: Net flow ({net_sol:.4f}) != Balance ({sol_balance:.4f})")
            print(f"    This is normal - net flow counts all history,")
            print(f"    balance is what's currently in wallet.")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

    await client.aclose()


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    await verify_wallet(wallet)


if __name__ == "__main__":
    asyncio.run(main())
