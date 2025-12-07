"""
VENOM Token Configuration
Configure the VENOM token contract address and requirements here.
"""

# VENOM Token Contract Address on Solana
# TODO: Replace with actual token address when launched
VENOM_TOKEN_ADDRESS = "PASTE_YOUR_VENOM_TOKEN_CONTRACT_ADDRESS_HERE"

# Minimum VENOM tokens required to unlock bot access
REQUIRED_VENOM_BALANCE = 10_000_000  # 10 million tokens

# Token decimals (standard SPL token has 9 decimals)
VENOM_DECIMALS = 9

# Feature flag - set to False to disable token verification (for testing)
ENABLE_VENOM_VERIFICATION = True

# Grace period - users can use bot for X seconds before verification kicks in
# Set to 0 to require immediate verification
VERIFICATION_GRACE_PERIOD = 0  # seconds
