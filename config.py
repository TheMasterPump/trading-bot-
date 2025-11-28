"""Configuration for RUG AI - Solana Security Scanner"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys (set these in .env file or environment variables)
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")  # Get free key at https://helius.dev
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY", "")  # Get free key at https://solscan.io
INSIGHTX_API_KEY = os.getenv("INSIGHTX_API_KEY", "")  # Get free key at https://insightx.network

# Solana RPC endpoints
if HELIUS_API_KEY:
    SOLANA_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
else:
    SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"  # Public RPC (rate limited)

# API URLs
SOLSCAN_API_URL = "https://api.solscan.io"
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex"

# pump.fun program ID
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

# Risk thresholds (OPTIMIZED for Pump.fun)
RISK_THRESHOLDS = {
    "WHALE_PERCENTAGE": 15,  # IMPROVED: If one wallet holds >15% = red flag (more strict)
    "TOP_10_PERCENTAGE": 70,  # IMPROVED: If top 10 holders have >70% = red flag (more strict)
    "MIN_HOLDERS": 100,       # IMPROVED: Less than 100 holders = suspicious (Pump.fun has many holders)
    "DEV_PERCENTAGE": 8,    # IMPROVED: Dev holds >8% after launch = red flag
    "MIN_LIQUIDITY_USD": 3000,  # IMPROVED: Less than $3k liquidity = very risky
    "FRESH_WALLET_PERCENTAGE": 40,  # IMPROVED: If >40% holders are fresh (<7 days) = red flag (less strict for new tokens)
    "SYBIL_PERCENTAGE": 15,  # IMPROVED: If >15% holders only buy same creator = sybil attack
    "BATCH_CREATED_WALLETS": 5,  # IMPROVED: If >5 wallets created in 24h = suspicious (more strict)
    "SAME_MINUTE_WALLETS": 3,  # NEW: If >3 wallets created in same minute = bot creation
    "INSTANT_SNIPER_PERCENTAGE": 25,  # NEW: If >25% bought in first 3 seconds = insider trading
    "WASH_TRADING_RATIO": 25,  # NEW: Volume/MCap ratio >25x = wash trading
}

# Risk scoring weights (OPTIMIZED for Pump.fun detection)
# Total = 165 (some overlap allowed for critical indicators)
RISK_WEIGHTS = {
    "whale_concentration": 15,  # REDUCED: Less critical on Pump.fun
    "holder_distribution": 12,  # REDUCED: Less critical
    "dev_holdings": 12,  # REDUCED
    "liquidity": 10,  # REDUCED: Locked on Pump.fun
    "creator_history": 15,  # INCREASED: Very important for serial ruggers
    "social_presence": 8,  # REDUCED: Nice to have but not critical
    "fresh_wallets": 20,  # INCREASED: CRITICAL indicator of fake holders
    "sniper_detection": 25,  # INCREASED: CRITICAL indicator of insider trading
    "wash_trading": 15,  # INCREASED: Important manipulation indicator
    "distribution_metrics": 10,  # Keep as is
    "pump_dump": 18,  # NEW: Important pattern for Pump.fun
    "holder_analysis": 15,  # NEW: Whale dumping & coordinated exit detection
}
