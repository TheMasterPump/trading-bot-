"""
Analyse la base de données SQLite pour trouver TOUS les trades et migrations
"""
import sqlite3
import json

print('='*80)
print('ANALYSE COMPLETE - BASE DE DONNEES')
print('='*80)

# Connexion à la base de données
try:
    conn = sqlite3.connect('learning_db.sqlite')
    cursor = conn.cursor()

    # Lister les tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'\nTables dans la DB: {[t[0] for t in tables]}')

    # Chercher la table des trades
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f'  {table_name}: {count} lignes')

    # Analyser la table trades si elle existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
    if cursor.fetchone():
        print(f'\n{"="*80}')
        print('ANALYSE DES TRADES')
        print('='*80)

        # Récupérer tous les trades
        cursor.execute("SELECT * FROM trades")
        trades = cursor.fetchall()

        # Récupérer les noms des colonnes
        cursor.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f'\nColonnes: {columns}')
        print(f'Total trades: {len(trades)}')

        # Convertir en dictionnaires
        trades_list = []
        for trade in trades:
            trade_dict = dict(zip(columns, trade))
            trades_list.append(trade_dict)

        # Analyser les migrations
        migrations = []
        near_migrations = []
        reached_2x = []

        for t in trades_list:
            exit_mc = t.get('exit_mc', 0)
            entry_mc = t.get('entry_mc', 0)

            if exit_mc >= 69000:
                migrations.append(t)
            elif exit_mc >= 50000:
                near_migrations.append(t)

            if entry_mc > 0 and exit_mc / entry_mc >= 2.0:
                reached_2x.append(t)

        print(f'\n{"="*80}')
        print('RESULTATS')
        print('='*80)
        print(f'\nTotal trades: {len(trades_list)}')
        print(f'Migrations (>= 69K): {len(migrations)} ({len(migrations)/len(trades_list)*100:.1f}%)')
        print(f'Proches (50-69K): {len(near_migrations)} ({len(near_migrations)/len(trades_list)*100:.1f}%)')
        print(f'Atteint 2x: {len(reached_2x)} ({len(reached_2x)/len(trades_list)*100:.1f}%)')

        if migrations:
            print(f'\n{"="*80}')
            print('TOKENS QUI ONT MIGRE (>= 69K)')
            print('='*80)
            for t in sorted(migrations, key=lambda x: x.get('exit_mc', 0), reverse=True)[:20]:
                symbol = t.get('symbol', 'Unknown')
                entry_mc = t.get('entry_mc', 0)
                exit_mc = t.get('exit_mc', 0)
                profit = ((exit_mc / entry_mc) - 1) * 100 if entry_mc > 0 else 0
                is_win = t.get('is_win', False)

                print(f'\n{symbol}')
                print(f'  Entry MC: ${entry_mc:,.0f}')
                print(f'  Exit MC: ${exit_mc:,.0f}')
                print(f'  Profit: {profit:+.1f}%')
                print(f'  Win: {"YES" if is_win else "NO"}')

        # Statistiques
        wins = [t for t in trades_list if t.get('is_win', False)]
        losses = [t for t in trades_list if not t.get('is_win', False)]

        print(f'\n{"="*80}')
        print('STATISTIQUES GLOBALES')
        print('='*80)
        print(f'\nWins: {len(wins)} ({len(wins)/len(trades_list)*100:.1f}%)')
        print(f'Losses: {len(losses)} ({len(losses)/len(trades_list)*100:.1f}%)')

        # MC moyen
        if trades_list:
            avg_exit_mc = sum(t.get('exit_mc', 0) for t in trades_list) / len(trades_list)
            max_exit_mc = max(t.get('exit_mc', 0) for t in trades_list)
            print(f'\nMC moyen sortie: ${avg_exit_mc:,.0f}')
            print(f'MC max atteint: ${max_exit_mc:,.0f}')

        # Distribution MC sortie
        print(f'\n{"="*80}')
        print('DISTRIBUTION MC DE SORTIE')
        print('='*80)

        ranges = [
            (0, 5000, '< 5K'),
            (5000, 10000, '5-10K'),
            (10000, 20000, '10-20K'),
            (20000, 30000, '20-30K'),
            (30000, 50000, '30-50K'),
            (50000, 69000, '50-69K'),
            (69000, 100000, '69-100K (MIGRE)'),
            (100000, 1000000, '>100K (MIGRE+)'),
        ]

        print(f'\n{"MC Range":<20} {"Count":<10} {"Percent":<10}')
        print('-'*40)

        for min_mc, max_mc, label in ranges:
            count = len([t for t in trades_list if min_mc <= t.get('exit_mc', 0) < max_mc])
            pct = count / len(trades_list) * 100 if trades_list else 0
            print(f'{label:<20} {count:<10} {pct:<9.1f}%')

    conn.close()

except Exception as e:
    print(f'\nErreur: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '='*80)
