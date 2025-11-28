# 🤖 Vision AI - Solana Trading Bot

AI-powered trading bot for Solana with real-time signals and subscription-based access.

[![Twitter](https://img.shields.io/badge/Twitter-@VisionAIHQ-1DA1F2?style=flat&logo=twitter)](https://x.com/VisionAIHQ)
[![Telegram](https://img.shields.io/badge/Telegram-Join-26A5E4?style=flat&logo=telegram)](https://t.me/PortalvisionAI)

---

## 🚀 Features

- **AI-Powered Predictions** - Machine learning models trained on 10,000+ tokens
- **Real-Time Trading Signals** - Automated buy/sell signals with custom strategies
- **Solana Payments** - Secure subscription system with SOL payments
- **Three Trading Tiers** - RISKY, SAFE, and ULTRA strategies
- **24/7 VIP Support** - Dedicated support for all subscribers
- **Auto-Trading** - Set it and forget it with AI-powered automation

---

## 📊 Subscription Plans

### 🔥 RISKY - Aggressive Strategy
- **1.5 SOL/week** or **4 SOL/month**
- ROI: 2-20x
- Ultra-fast execution
- AI trained on 4000+ tokens
- Custom Take Profit & Stop Loss

### 🛡️ SAFE - Conservative Strategy
- **2 SOL/week** or **6 SOL/month**
- ROI: 5x-30x
- Safety filters & AI verification
- AI trained on 6000+ tokens
- Trailing Stop Loss

### ⭐ ULTRA - Premium Strategy
- **3 SOL/week** or **10 SOL/month**
- ROI: x10-x100
- AI + Auto-compound
- Front-run top traders
- AI trained on 10,000+ tokens
- Multi-strategy approach

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
vision-ai-bot/
├── app.py                      # Flask web server
├── payment_config.py           # Solana payment configuration
├── payment_verifier.py         # Payment verification
├── templates/
│   ├── index.html             # Landing page
│   ├── bot.html               # Trading interface
│   └── about.html             # About page
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

### Payment Wallet Setup

Edit `payment_config.py` to configure your Solana wallet:

```python
# Your Solana wallet address for receiving payments
PAYMENT_WALLET_ADDRESS = 'YOUR_SOLANA_WALLET_HERE'

# Subscription prices in SOL
SUBSCRIPTION_PRICES = {
    'RISKY': 1.5,   # per week
    'SAFE': 2.0,
    'ULTRA': 3.0
}
```

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

# 5. Configure environment
nano payment_config.py  # Add your wallet address

# 6. Run with gunicorn (production)
pip3 install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

# 7. (Optional) Setup as systemd service for 24/7 operation
sudo nano /etc/systemd/system/visionai.service
```

**Systemd Service Example:**

```ini
[Unit]
Description=Vision AI Trading Bot
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
sudo systemctl enable visionai
sudo systemctl start visionai
```

---

## 🔐 Security

- **Payments:** All Solana transactions are verified on-chain
- **User Data:** SQLite database with encrypted passwords (bcrypt)
- **API Keys:** Store sensitive keys in environment variables
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
- **Email:** support@visionai.bot (configure in app)

---

## 📝 License

Proprietary - All rights reserved

---

## 🎯 Roadmap

- [x] Web interface with subscription system
- [x] Solana payment integration
- [x] AI trading models
- [x] Multi-tier subscription plans
- [ ] Mobile app (iOS/Android)
- [ ] Advanced analytics dashboard
- [ ] Telegram bot integration
- [ ] Copy-trading features

---

**🚀 Start earning with AI-powered trading signals today!**

*Payment Wallet: 89WT9zM1um2prDXqaGaYPh9KjcrjgNe4n5HYwHHX9ji5*
