import sqlite3

conn = sqlite3.connect('smart_wallets.db')
cursor = conn.cursor()

# Compter les wallets
cursor.execute('SELECT COUNT(*) FROM tracked_wallets')
count = cursor.fetchone()[0]
print(f'Wallets dans la base: {count}')

# Top 5 wallets
cursor.execute('SELECT wallet_address, smart_score, success_rate FROM tracked_wallets ORDER BY smart_score DESC LIMIT 5')
print('\nTop 5 wallets:')
for row in cursor.fetchall():
    print(f'  {row[0][:16]}... - Score: {row[1]}, Success: {row[2]}%')

conn.close()
