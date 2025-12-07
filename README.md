# 🐍 VENOM AI - Solana Trading Bot

AI-powered trading bot for Solana with real-time signals and token-based access.

[![Twitter](https://img.shields.io/badge/Twitter-@VisionAIHQ-1DA1F2?style=flat&logo=twitter)](https://x.com/VisionAIHQ)
[![Telegram](https://img.shields.io/badge/Telegram-Join-26A5E4?style=flat&logo=telegram)](https://t.me/PortalvisionAI)

---

## 🚀 Features

- **AI-Powered Predictions** - Machine learning models trained on 10,000+ tokens
- **Real-Time Trading Signals** - Automated buy/sell signals with custom strategies
- **Token-Based Access** - Hold VENOM tokens to unlock bot access
- **Blockchain Verification** - Automatic on-chain token balance verification
- **Non-Custodial** - Users control their own wallets and private keys
- **Auto-Trading** - Set it and forget it with AI-powered automation

---

## 🐍 Token-Based Access

### 🔑 VENOM Access
- **Hold 10,000,000 VENOM tokens** in your Solana wallet
- One-time token purchase - no recurring fees
- Token retains market value - can sell anytime
- Automatic blockchain verification
- Full bot access with all features
- No subscriptions or monthly payments

**How it works:**
1. Buy VENOM tokens on a Solana DEX (Raydium, Jupiter, etc.)
2. Hold 10M+ VENOM tokens in your Solana wallet
3. Connect your wallet in the bot
4. Automatic verification grants instant access
5. Keep trading as long as you hold the tokens

---

## ⚡ Quick Start

### 1. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python app.py
```

→ Open: http://localhost:5000

### 2. Deploy to Production

See [Deployment Guide](#-deployment) below for VPS setup instructions.

---

## 🏗️ Project Structure

```
venom-ai-bot/
├── app.py                      # Flask web server
├── venom_config.py             # VENOM token configuration
├── venom_verifier.py           # Token balance verification
├── VENOM_SETUP.md              # Token setup guide
├── templates/
│   ├── index.html             # Landing page
│   ├── bot.html               # Trading interface
│   └── about.html             # Documentation page
├── models/                     # AI models (ML/DL)
│   ├── migration_classifier_latest.pkl
│   ├── price_regressor_latest.pkl
│   ├── runner_classifier_latest.pkl
│   └── roi_predictor_*.pkl
├── static/                     # CSS, JS, images
└── requirements.txt            # Python dependencies
```

---

## 🔧 Configuration

### VENOM Token Setup

Edit `venom_config.py` to configure your token:

```python
# VENOM Token Contract Address on Solana
VENOM_TOKEN_ADDRESS = "YOUR_VENOM_TOKEN_CONTRACT_ADDRESS_HERE"

# Minimum VENOM tokens required to unlock bot access
REQUIRED_VENOM_BALANCE = 10_000_000  # 10 million tokens

# Token decimals (standard SPL token = 9)
VENOM_DECIMALS = 9

# Enable/disable verification (set False for testing)
ENABLE_VENOM_VERIFICATION = True
```

See `VENOM_SETUP.md` for complete setup instructions.

---

## 🌐 Deployment

### Recommended: Hetzner VPS (€4.90/month)

**Server Specs for 100+ users:**
- 4GB RAM
- 2 CPU cores
- 40GB SSD
- Ubuntu 22.04

**Setup Steps:**

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and dependencies
sudo apt install python3 python3-pip git -y

# 3. Clone repository
git clone https://github.com/TheMasterPump/trading-bot-.git
cd trading-bot-

# 4. Install requirements
pip3 install -r requirements.txt

# 5. Configure VENOM token
nano venom_config.py  # Add your token contract address

# 6. Run with gunicorn (production)
pip3 install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

# 7. (Optional) Setup as systemd service for 24/7 operation
sudo nano /etc/systemd/system/venomai.service
```

**Systemd Service Example:**

```ini
[Unit]
Description=VENOM AI Trading Bot
After=network.target

[Service]
User=your-username
WorkingDirectory=/path/to/trading-bot-
ExecStart=/usr/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable venomai
sudo systemctl start venomai
```

---

## 🔐 Security

- **Token Verification:** All token balances verified on-chain via Solana RPC
- **Non-Custodial:** Users control their own private keys and wallets
- **User Data:** SQLite database with encrypted passwords (bcrypt)
- **Private Keys:** AES-256 encryption for stored wallet keys
- **HTTPS:** Use Nginx reverse proxy with SSL/TLS in production

---

## 📈 AI Models

The bot uses multiple machine learning models:

- **Migration Classifier** - Detects when tokens will migrate to Raydium
- **Price Regressor** - Predicts price movements
- **Runner Classifier** - Identifies high-growth potential tokens
- **ROI Predictor** - Estimates potential returns (ensemble model)

All models are pre-trained and included in the `models/` directory.

---

## 🛠️ Development

### Requirements
- Python 3.8+
- Flask 2.x
- scikit-learn
- pandas, numpy
- solana-py (for payment verification)

### Database
- SQLite (default, perfect for 100-500 users)
- Upgrade to PostgreSQL for 1000+ users

---

## 📞 Support

- **Twitter:** [@VisionAIHQ](https://x.com/VisionAIHQ)
- **Telegram:** [Join Community](https://t.me/PortalvisionAI)
- **Documentation:** Full setup guide in `VENOM_SETUP.md`

---

## 📝 License

Proprietary - All rights reserved

---

## 🎯 Roadmap

- [x] Web interface with user authentication
- [x] AI trading models (94.74% accuracy)
- [x] Real-time token scanner
- [x] VENOM token integration
- [x] Blockchain verification system
- [ ] Mobile app (iOS/Android)
- [ ] Advanced analytics dashboard
- [ ] Telegram bot integration
- [ ] Public API for developers

---

**🐍 Start earning with VENOM AI-powered trading signals today!**
