"""
Script pour demarrer le bot via l'API Flask
"""
import requests
import json

BASE_URL = "http://localhost:5001"

# 1. Login
print("[1] Login...")
login_data = {
    'email': 'sultancrpy@hotmail.com',
    'password': 'sultan123'
}

session = requests.Session()
response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
print(f"   Login response: {response.status_code}")

if response.status_code != 200:
    print(f"   [ERROR] Login failed: {response.text}")
    exit(1)

print(f"   [OK] Logged in!")

# 2. Start bot
print("\n[2] Starting bot...")
bot_config = {
    'strategy': 'AI_PREDICTIONS',
    'risk_level': 'MEDIUM',
    'stop_loss': 25,
    'tp_strategy': 'SIMPLE_MULTIPLIER',
    'tp_multiplier': 2.0
}

response = session.post(f"{BASE_URL}/api/bot/start", json=bot_config)
print(f"   Start bot response: {response.status_code}")
print(f"   Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    if data.get('success'):
        print(f"\n   [OK] Bot started!")
        print(f"   Message: {data.get('message')}")
    else:
        print(f"\n   [ERROR] {data.get('error')}")
else:
    print(f"\n   [ERROR] HTTP {response.status_code}: {response.text}")

# 3. Check status
print("\n[3] Checking bot status...")
response = session.get(f"{BASE_URL}/api/bot/status")
if response.status_code == 200:
    data = response.json()
    print(f"   Bot running: {data.get('is_running')}")
    print(f"   Simulation mode: {data.get('simulation_mode')}")
    print(f"   Balance: {data.get('virtual_balance')} SOL")
else:
    print(f"   [ERROR] Status check failed")
