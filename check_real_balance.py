import requests
from database_bot import db

email = "bnlnknp@gmail.com"

# Récupérer l'utilisateur
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
user = cursor.fetchone()

if not user:
    print(f"Utilisateur non trouve")
    exit()

user_id = user['id']

# Récupérer le wallet
wallet = db.get_wallet(user_id)
if not wallet:
    print("Wallet non trouve")
    exit()

wallet_address = wallet['address']
print(f"\n=== VERIFICATION BALANCE REELLE ===")
print(f"Wallet: {wallet_address}\n")

# Vérifier la balance REELLE sur la blockchain
try:
    # Utiliser RPC Solana pour obtenir la balance réelle
    rpc_url = "https://api.mainnet-beta.solana.com"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet_address]
    }

    response = requests.post(rpc_url, json=payload, timeout=10)
    data = response.json()

    if 'result' in data and 'value' in data['result']:
        lamports = data['result']['value']
        sol_balance = lamports / 1_000_000_000  # Convertir lamports en SOL

        print(f"[BLOCKCHAIN] Balance reelle: {sol_balance:.9f} SOL")

        # Comparer avec la DB
        db_balance = wallet.get('balance_sol', 0)
        print(f"[DATABASE] Balance en cache: {db_balance:.9f} SOL")

        if abs(sol_balance - db_balance) > 0.0001:
            print(f"\n[!] ATTENTION: La balance DB n'est pas a jour!")
            print(f"    Difference: {sol_balance - db_balance:.9f} SOL")
        else:
            print(f"\n[OK] La balance DB est a jour")

        # Convertir en USD (prix approximatif)
        try:
            cg_response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=5)
            sol_price = cg_response.json().get('solana', {}).get('usd', 0)
            usd_value = sol_balance * sol_price
            print(f"\n[USD] Valeur: ${usd_value:.2f} (@ ${sol_price:.2f}/SOL)")
        except:
            print("\n[USD] Impossible de recuperer le prix SOL")

    else:
        print(f"[ERREUR] Reponse invalide du RPC: {data}")

except Exception as e:
    print(f"[ERREUR] Impossible de verifier la balance: {e}")

print("\n" + "="*60)
