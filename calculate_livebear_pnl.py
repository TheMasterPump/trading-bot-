"""
CALCULATE LIVEBEAR P&L
Analyser les 63 transactions LIVEBEAR pour calculer le vrai P&L
"""
import asyncio
import httpx
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
LIVEBEAR_MINT = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"
WALLET = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

# Les 63 signatures trouvées
LIVEBEAR_SIGNATURES = [
    "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"
]

async def get_transaction_detail(signature: str, client, rpc_url):
    """Get transaction details"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }

    try:
        response = await client.post(rpc_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get('result')
    except:
        pass
    return None


async def analyze_livebear_transactions():
    """Analyze all LIVEBEAR transactions"""

    print("=" * 70)
    print("LIVEBEAR P&L CALCULATOR")
    print("=" * 70)
    print(f"Wallet: {WALLET[:16]}...")
    print(f"Token: LIVEBEAR")
    print(f"Transactions: {len(LIVEBEAR_SIGNATURES)}")
    print("=" * 70)

    client = httpx.AsyncClient(timeout=60.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    print(f"\n[*] Fetching transaction details...")

    transactions = []
    for i, sig in enumerate(LIVEBEAR_SIGNATURES):
        tx = await get_transaction_detail(sig, client, rpc_url)
        if tx:
            transactions.append({'signature': sig, 'tx': tx})

        if (i + 1) % 10 == 0:
            print(f"    Progress: {i + 1}/{len(LIVEBEAR_SIGNATURES)}")

    print(f"\n[+] Fetched {len(transactions)} transaction details")

    # Analyze each transaction
    print(f"\n[*] Analyzing transactions...")

    buys = []
    sells = []

    for item in transactions:
        tx = item['tx']
        sig = item['signature']

        # Get timestamp
        block_time = tx.get('blockTime')
        if block_time:
            tx_date = datetime.fromtimestamp(block_time)
        else:
            tx_date = None

        # Get SOL balance change for wallet
        meta = tx.get('meta', {})
        pre_balances = meta.get('preBalances', [])
        post_balances = meta.get('postBalances', [])

        # Get account keys
        account_keys = []
        if 'transaction' in tx:
            message = tx['transaction'].get('message', {})
            if 'accountKeys' in message:
                account_keys = [acc.get('pubkey') if isinstance(acc, dict) else acc for acc in message['accountKeys']]

        # Find wallet index
        wallet_index = -1
        for idx, key in enumerate(account_keys):
            if key == WALLET:
                wallet_index = idx
                break

        sol_change = 0
        if wallet_index >= 0 and wallet_index < len(pre_balances) and wallet_index < len(post_balances):
            sol_change = (post_balances[wallet_index] - pre_balances[wallet_index]) / 1e9

        # Determine if buy or sell by looking at token balance changes
        post_token_balances = meta.get('postTokenBalances', [])
        pre_token_balances = meta.get('preTokenBalances', [])

        is_buy = False
        is_sell = False
        token_amount = 0

        # Check if tokens increased (buy) or decreased (sell)
        for post_bal in post_token_balances:
            if post_bal.get('mint') == LIVEBEAR_MINT and post_bal.get('owner') == WALLET:
                post_amount = float(post_bal.get('uiTokenAmount', {}).get('uiAmount', 0))

                # Find matching pre balance
                pre_amount = 0
                for pre_bal in pre_token_balances:
                    if (pre_bal.get('mint') == LIVEBEAR_MINT and
                        pre_bal.get('owner') == WALLET and
                        pre_bal.get('accountIndex') == post_bal.get('accountIndex')):
                        pre_amount = float(pre_bal.get('uiTokenAmount', {}).get('uiAmount', 0))
                        break

                token_change = post_amount - pre_amount
                token_amount = abs(token_change)

                if token_change > 0:
                    is_buy = True
                elif token_change < 0:
                    is_sell = True

        trade_data = {
            'signature': sig,
            'date': tx_date,
            'sol_change': sol_change,
            'token_amount': token_amount,
            'is_buy': is_buy,
            'is_sell': is_sell
        }

        if is_buy:
            buys.append(trade_data)
        elif is_sell:
            sells.append(trade_data)

    await client.aclose()

    # Calculate P&L
    print(f"\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    total_sol_spent = sum(abs(b['sol_change']) for b in buys)
    total_sol_received = sum(abs(s['sol_change']) for s in sells)

    pnl_sol = total_sol_received - total_sol_spent
    pnl_usd = pnl_sol * 200

    print(f"\nBuys: {len(buys)}")
    print(f"Sells: {len(sells)}")

    print(f"\nTotal SOL Spent: {total_sol_spent:.4f} SOL (${total_sol_spent * 200:.2f})")
    print(f"Total SOL Received: {total_sol_received:.4f} SOL (${total_sol_received * 200:.2f})")

    print(f"\nP&L: {pnl_sol:+.4f} SOL (${pnl_usd:+.2f})")

    if pnl_usd > 0:
        roi = (pnl_sol / total_sol_spent * 100) if total_sol_spent > 0 else 0
        print(f"ROI: +{roi:.2f}%")
        print(f"\n[SUCCESS] LIVEBEAR was PROFITABLE!")
        print(f"[PROFIT] +${pnl_usd:.2f}")
    else:
        print(f"\n[LOSS] LIVEBEAR lost money")

    # Show sample trades
    print(f"\n" + "=" * 70)
    print("SAMPLE TRADES")
    print("=" * 70)

    print(f"\nFirst 5 Buys:")
    for i, buy in enumerate(buys[:5], 1):
        date_str = buy['date'].strftime('%Y-%m-%d %H:%M') if buy['date'] else 'Unknown'
        print(f"  {i}. {date_str} - {abs(buy['sol_change']):.4f} SOL - {buy['token_amount']:,.0f} tokens")

    print(f"\nFirst 5 Sells:")
    for i, sell in enumerate(sells[:5], 1):
        date_str = sell['date'].strftime('%Y-%m-%d %H:%M') if sell['date'] else 'Unknown'
        print(f"  {i}. {date_str} - {abs(sell['sol_change']):.4f} SOL - {sell['token_amount']:,.0f} tokens")

    print("\n" + "=" * 70)


async def main():
    await analyze_livebear_transactions()


if __name__ == "__main__":
    asyncio.run(main())
