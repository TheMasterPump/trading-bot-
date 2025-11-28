"""
SMART ALERTS SYSTEM
Envoie des alertes automatiques quand on detecte un token qui va pump!
Discord + Telegram notifications
"""
import asyncio
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()

class SmartAlertsSystem:
    """Systeme d'alertes intelligentes"""

    def __init__(self):
        # Discord webhook
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL', '')

        # Telegram bot
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

        self.client = httpx.AsyncClient(timeout=30.0)

        # Criteres d'alerte
        self.alert_criteria = {
            'min_viral_potential': 70,  # 70% viral potential minimum
            'max_market_cap': 100000,   # Max 100k market cap
            'min_twitter_sentiment': 50, # Sentiment positif
            'max_rug_probability': 20,   # Max 20% chance de rug
            'min_multiplier': 5.0        # Minimum 5x potential
        }

    def should_alert(self, prediction_data):
        """Determine si on doit alerter pour ce token"""
        try:
            features = prediction_data.get('features', {})
            price_pred = prediction_data.get('price_prediction', {})
            category_pred = prediction_data.get('category_prediction', {})

            # Critere 1: Market cap < 100k
            market_cap = features.get('market_cap_usd', 0)
            if market_cap > self.alert_criteria['max_market_cap']:
                return False, "Market cap trop eleve"

            # Critere 2: Viral potential > 70%
            viral_potential = features.get('viral_potential', 0)
            if viral_potential < self.alert_criteria['min_viral_potential']:
                return False, f"Viral potential faible ({viral_potential}%)"

            # Critere 3: Twitter sentiment positif
            twitter_sentiment = features.get('twitter_sentiment', 0)
            if twitter_sentiment < self.alert_criteria['min_twitter_sentiment']:
                return False, f"Sentiment pas assez positif ({twitter_sentiment})"

            # Critere 4: Pas de rug
            rug_probability = category_pred.get('probabilities', {}).get('RUG', 100)
            if rug_probability > self.alert_criteria['max_rug_probability']:
                return False, f"Risque de rug trop eleve ({rug_probability}%)"

            # Critere 5: Multiplier > 5x
            multiplier = price_pred.get('potential_multiplier', 0)
            if multiplier < self.alert_criteria['min_multiplier']:
                return False, f"Multiplier trop faible ({multiplier}x)"

            # Critere 6: Pas deja au top
            is_at_top = price_pred.get('is_at_top', False)
            if is_at_top:
                return False, "Token deja au top"

            # Tous les criteres passes!
            return True, "ALERTE - Tous criteres valides!"

        except Exception as e:
            console.print(f"[red]Erreur should_alert: {e}")
            return False, str(e)

    async def send_discord_alert(self, token_address, prediction_data, alert_score):
        """Envoie alerte Discord"""
        if not self.discord_webhook:
            return False

        try:
            features = prediction_data.get('features', {})
            price_pred = prediction_data.get('price_prediction', {})
            category_pred = prediction_data.get('category_prediction', {})

            # Construire le message
            embed = {
                "title": f"🚀 ALERTE PUMP DETECTE! Score: {alert_score}/100",
                "description": f"Token: `{token_address[:16]}...`",
                "color": 0x00ff00,  # Vert
                "fields": [
                    {
                        "name": "💰 Prix & Potentiel",
                        "value": f"Prix: ${price_pred.get('current_price', 0):.8f}\n"
                                f"Market Cap: ${price_pred.get('current_mcap', 0):,.0f}\n"
                                f"**Potentiel: {price_pred.get('potential_multiplier', 0):.1f}x**",
                        "inline": True
                    },
                    {
                        "name": "📊 Categorie",
                        "value": f"**{category_pred.get('category', 'N/A')}**\n"
                                f"Confiance: {category_pred.get('confidence', 0):.1f}%\n"
                                f"Rug Risk: {category_pred.get('probabilities', {}).get('RUG', 0):.1f}%",
                        "inline": True
                    },
                    {
                        "name": "🐦 Twitter Signals",
                        "value": f"Mentions: {features.get('twitter_mentions', 0)}\n"
                                f"Engagement: {features.get('twitter_engagement', 0):,.0f}\n"
                                f"Sentiment: {features.get('twitter_sentiment', 0):.0f}/100\n"
                                f"Influencers: {features.get('twitter_influencers', 0)}",
                        "inline": True
                    },
                    {
                        "name": "🔥 Viral Metrics",
                        "value": f"**Viral Potential: {features.get('viral_potential', 0):.0f}%**\n"
                                f"Social Hype: {features.get('social_hype_score', 0):.0f}%\n"
                                f"Organic Growth: {features.get('organic_growth', 0):.0f}%",
                        "inline": True
                    },
                    {
                        "name": "💎 Holder Analysis",
                        "value": f"Holders: {features.get('holder_count', 0)}\n"
                                f"Top 10: {features.get('top_10_concentration', 0):.1f}%\n"
                                f"Fresh Wallets: {features.get('fresh_wallets', 0):.1f}%",
                        "inline": True
                    },
                    {
                        "name": "💧 Liquidity",
                        "value": f"${features.get('liquidity_usd', 0):,.0f}",
                        "inline": True
                    },
                    {
                        "name": "📈 Action Recommandee",
                        "value": f"**{price_pred.get('action', 'N/A')}**\n{price_pred.get('reason', '')}",
                        "inline": False
                    },
                    {
                        "name": "🎯 Points d'Entree/Sortie",
                        "value": f"Entry: ${price_pred.get('entry_price', 0):.8f}\n"
                                f"Exit: ${price_pred.get('exit_price', 0):.8f}\n"
                                f"Stop Loss: ${price_pred.get('stop_loss', 0):.8f}",
                        "inline": False
                    },
                    {
                        "name": "🔗 Links",
                        "value": f"[DexScreener](https://dexscreener.com/solana/{token_address}) | "
                                f"[Solscan](https://solscan.io/token/{token_address}) | "
                                f"[Birdeye](https://birdeye.so/token/{token_address})",
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Prediction AI V2 - Auto Alert System"
                }
            }

            payload = {
                "embeds": [embed],
                "username": "Prediction AI Bot"
            }

            response = await self.client.post(
                self.discord_webhook,
                json=payload
            )

            if response.status_code == 204:
                console.print("[green]Alerte Discord envoyee!")
                return True
            else:
                console.print(f"[red]Erreur Discord: {response.status_code}")
                return False

        except Exception as e:
            console.print(f"[red]Erreur send_discord_alert: {e}")
            return False

    async def send_telegram_alert(self, token_address, prediction_data, alert_score):
        """Envoie alerte Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False

        try:
            features = prediction_data.get('features', {})
            price_pred = prediction_data.get('price_prediction', {})
            category_pred = prediction_data.get('category_prediction', {})

            # Construire le message
            message = f"🚀 *ALERTE PUMP DETECTE!* Score: {alert_score}/100\n\n"
            message += f"Token: `{token_address}`\n\n"

            message += f"💰 *Prix & Potentiel*\n"
            message += f"Prix: ${price_pred.get('current_price', 0):.8f}\n"
            message += f"Market Cap: ${price_pred.get('current_mcap', 0):,.0f}\n"
            message += f"*Potentiel: {price_pred.get('potential_multiplier', 0):.1f}x*\n\n"

            message += f"📊 *Categorie*\n"
            message += f"*{category_pred.get('category', 'N/A')}* ({category_pred.get('confidence', 0):.1f}%)\n"
            message += f"Rug Risk: {category_pred.get('probabilities', {}).get('RUG', 0):.1f}%\n\n"

            message += f"🐦 *Twitter*\n"
            message += f"Mentions: {features.get('twitter_mentions', 0)}\n"
            message += f"Sentiment: {features.get('twitter_sentiment', 0):.0f}/100\n"
            message += f"Influencers: {features.get('twitter_influencers', 0)}\n\n"

            message += f"🔥 *Viral: {features.get('viral_potential', 0):.0f}%*\n\n"

            message += f"📈 *Action: {price_pred.get('action', 'N/A')}*\n"
            message += f"{price_pred.get('reason', '')}\n\n"

            message += f"🔗 [DexScreener](https://dexscreener.com/solana/{token_address})"

            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"

            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }

            response = await self.client.post(url, json=payload)

            if response.status_code == 200:
                console.print("[green]Alerte Telegram envoyee!")
                return True
            else:
                console.print(f"[red]Erreur Telegram: {response.status_code}")
                return False

        except Exception as e:
            console.print(f"[red]Erreur send_telegram_alert: {e}")
            return False

    def calculate_alert_score(self, prediction_data):
        """Calcule un score global pour l'alerte (0-100)"""
        try:
            features = prediction_data.get('features', {})
            price_pred = prediction_data.get('price_prediction', {})
            category_pred = prediction_data.get('category_prediction', {})

            score = 0

            # 1. Multiplier potential (30 points max)
            multiplier = price_pred.get('potential_multiplier', 0)
            score += min(multiplier * 3, 30)

            # 2. Viral potential (25 points max)
            viral = features.get('viral_potential', 0)
            score += viral * 0.25

            # 3. Confidence du modele (20 points max)
            confidence = category_pred.get('confidence', 0)
            score += confidence * 0.20

            # 4. Twitter sentiment (15 points max)
            sentiment = features.get('twitter_sentiment', 0)
            score += sentiment * 0.15

            # 5. Pas de rug (10 points max)
            rug_prob = category_pred.get('probabilities', {}).get('RUG', 100)
            score += (100 - rug_prob) * 0.10

            return min(int(score), 100)

        except:
            return 0

    async def process_prediction_for_alert(self, token_address, prediction_data):
        """Analyse une prediction et envoie alerte si criteres valides"""
        console.print(f"\n[cyan]Analyse alerte pour {token_address[:8]}...")

        # Check si on doit alerter
        should_alert, reason = self.should_alert(prediction_data)

        if not should_alert:
            console.print(f"[yellow]Pas d'alerte: {reason}")
            return False

        # Calculer score
        alert_score = self.calculate_alert_score(prediction_data)

        console.print(f"[bold green]ALERTE DECLENCHEE! Score: {alert_score}/100")
        console.print(f"[green]Raison: {reason}")

        # Envoyer alertes
        discord_sent = await self.send_discord_alert(token_address, prediction_data, alert_score)
        telegram_sent = await self.send_telegram_alert(token_address, prediction_data, alert_score)

        if discord_sent or telegram_sent:
            console.print("[bold green]Alertes envoyees avec succes!")
            return True
        else:
            console.print("[yellow]Aucune alerte envoyee (webhook pas configure)")
            return False

    async def close(self):
        """Cleanup"""
        await self.client.aclose()


# Test
async def main():
    alerts = SmartAlertsSystem()

    # Test avec des donnees fictives
    test_prediction = {
        'features': {
            'market_cap_usd': 50000,
            'viral_potential': 85,
            'twitter_sentiment': 75,
            'twitter_mentions': 150,
            'twitter_engagement': 5000,
            'twitter_influencers': 3,
            'social_hype_score': 80,
            'organic_growth': 70,
            'holder_count': 500,
            'top_10_concentration': 45,
            'fresh_wallets': 30,
            'liquidity_usd': 25000
        },
        'price_prediction': {
            'current_price': 0.00001234,
            'current_mcap': 50000,
            'predicted_max_price': 0.00007000,
            'potential_multiplier': 7.5,
            'is_at_top': False,
            'action': 'ACHETER',
            'reason': 'Fort potentiel viral + sentiment positif',
            'entry_price': 0.00001234,
            'exit_price': 0.00007000,
            'stop_loss': 0.00000617
        },
        'category_prediction': {
            'category': 'GEM',
            'confidence': 92.5,
            'probabilities': {
                'RUG': 5.0,
                'SAFE': 25.0,
                'GEM': 70.0
            }
        }
    }

    test_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    await alerts.process_prediction_for_alert(test_address, test_prediction)

    await alerts.close()


if __name__ == "__main__":
    asyncio.run(main())
