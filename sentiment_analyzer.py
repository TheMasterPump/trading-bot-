"""
SENTIMENT ANALYZER - Analyse Twitter/Telegram pour prédire les pumps
Détecte le hype AVANT le pump avec analyse de sentiment
"""
import asyncio
import httpx
import re
from datetime import datetime, timedelta
from rich.console import Console
import os
from dotenv import load_dotenv

load_dotenv()

console = Console()

class SentimentAnalyzer:
    """Analyse le sentiment social pour améliorer les prédictions"""

    def __init__(self):
        # Clés API (depuis .env)
        self.twitter_bearer = os.getenv('TWITTER_BEARER_TOKEN', '')
        self.client = httpx.AsyncClient(timeout=30.0)

    async def analyze_twitter(self, token_address, token_name=None, token_symbol=None):
        """Analyse Twitter pour le token - cherche ticker ET contract"""
        try:
            # Construire query: chercher ticker OU contract
            search_parts = []

            # Ajouter ticker avec $ (ex: $PREDICT)
            if token_symbol:
                search_parts.append(f"${token_symbol}")

            # Ajouter contract address (8 premiers caractères)
            search_parts.append(token_address[:8])

            # Combiner avec OR pour chercher les deux
            search_query = " OR ".join(search_parts)

            console.print(f"[cyan]Searching Twitter for: {search_query}")

            # Si on a le bearer token Twitter
            if self.twitter_bearer:
                return await self._twitter_api_search(search_query)
            else:
                # Fallback: estimation basique
                return self._estimate_twitter_sentiment()

        except Exception as e:
            console.print(f"[yellow]Twitter analysis failed: {e}")
            return self._estimate_twitter_sentiment()

    async def _twitter_api_search(self, query):
        """Recherche Twitter avec API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.twitter_bearer}'
            }

            # Rechercher les tweets récents (dernières 24h)
            url = 'https://api.twitter.com/2/tweets/search/recent'
            params = {
                'query': query,
                'max_results': 100,
                'tweet.fields': 'created_at,public_metrics'
            }

            response = await self.client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])

                if not tweets:
                    return {
                        'mention_count': 0,
                        'engagement_score': 0,
                        'sentiment_score': 0,
                        'trend_score': 0,
                        'influencer_mentions': 0
                    }

                # Calculer les métriques
                mention_count = len(tweets)

                total_likes = sum(t.get('public_metrics', {}).get('like_count', 0) for t in tweets)
                total_retweets = sum(t.get('public_metrics', {}).get('retweet_count', 0) for t in tweets)
                total_replies = sum(t.get('public_metrics', {}).get('reply_count', 0) for t in tweets)

                engagement_score = total_likes + (total_retweets * 2) + total_replies

                # Analyser le sentiment (simple: ratio positif/négatif keywords)
                positive_words = ['moon', 'gem', 'bullish', 'pump', 'buy', 'huge', 'amazing', '🚀', '💎', '🔥']
                negative_words = ['scam', 'rug', 'dump', 'sell', 'fake', 'careful', 'beware', '⚠️']

                positive_count = 0
                negative_count = 0

                for tweet in tweets:
                    text = tweet.get('text', '').lower()
                    positive_count += sum(1 for word in positive_words if word in text)
                    negative_count += sum(1 for word in negative_words if word in text)

                if (positive_count + negative_count) > 0:
                    sentiment_score = (positive_count - negative_count) / (positive_count + negative_count) * 100
                else:
                    sentiment_score = 0

                # Score de tendance (croissance des mentions)
                trend_score = min(mention_count / 10, 100)  # Normaliser

                return {
                    'mention_count': mention_count,
                    'engagement_score': engagement_score,
                    'sentiment_score': sentiment_score,
                    'trend_score': trend_score,
                    'influencer_mentions': self._count_influencer_tweets(tweets)
                }

        except Exception as e:
            console.print(f"[yellow]Twitter API error: {e}")
            return self._estimate_twitter_sentiment()

    def _estimate_twitter_sentiment(self):
        """Estimation par défaut quand pas d'API"""
        return {
            'mention_count': 0,
            'engagement_score': 0,
            'sentiment_score': 0,
            'trend_score': 0,
            'influencer_mentions': 0
        }

    def _count_influencer_tweets(self, tweets):
        """Compte les tweets d'influenceurs (>10k followers)"""
        # Simplification: on estime basé sur l'engagement
        influencers = 0
        for tweet in tweets:
            likes = tweet.get('public_metrics', {}).get('like_count', 0)
            retweets = tweet.get('public_metrics', {}).get('retweet_count', 0)

            # Si beaucoup d'engagement = probablement un influenceur
            if likes > 100 or retweets > 50:
                influencers += 1

        return influencers

    async def analyze_telegram(self, token_metadata):
        """Analyse Telegram pour le token"""
        try:
            # Récupérer le lien Telegram depuis les métadonnées
            telegram_link = token_metadata.get('telegram', '')

            if not telegram_link:
                return self._estimate_telegram_activity()

            # Extraire le nom du groupe
            telegram_group = self._extract_telegram_group(telegram_link)

            if telegram_group:
                # Analyser l'activité du groupe
                return await self._analyze_telegram_group(telegram_group)
            else:
                return self._estimate_telegram_activity()

        except Exception as e:
            console.print(f"[yellow]Telegram analysis failed: {e}")
            return self._estimate_telegram_activity()

    def _extract_telegram_group(self, link):
        """Extrait le nom du groupe Telegram"""
        match = re.search(r't\.me/([^/\?]+)', link)
        if match:
            return match.group(1)
        return None

    async def _analyze_telegram_group(self, group_name):
        """Analyse un groupe Telegram (via API publique ou estimation)"""
        # Note: Telegram API nécessite un bot token
        # Pour l'instant, on fait une estimation basique

        return {
            'member_count': 0,  # Nécessite API bot
            'message_rate': 0,  # Messages par heure
            'activity_score': 0,
            'has_telegram': 1  # Au moins ils ont un Telegram
        }

    def _estimate_telegram_activity(self):
        """Estimation par défaut"""
        return {
            'member_count': 0,
            'message_rate': 0,
            'activity_score': 0,
            'has_telegram': 0
        }

    def calculate_sentiment_features(self, twitter_data, telegram_data):
        """Calcule les features de sentiment pour le ML - Focus sur Twitter"""
        return {
            # Twitter (PRINCIPAL)
            'twitter_mentions': twitter_data['mention_count'],
            'twitter_engagement': twitter_data['engagement_score'],
            'twitter_sentiment': twitter_data['sentiment_score'],
            'twitter_trend': twitter_data['trend_score'],
            'twitter_influencers': twitter_data['influencer_mentions'],

            # Telegram (minimal - juste présence)
            'telegram_members': 0,  # Pas important
            'telegram_activity': 0,  # Pas important
            'has_telegram': telegram_data['has_telegram'],  # Juste si existe

            # Scores combinés (basés principalement sur Twitter)
            'social_hype_score': self._calculate_hype_score(twitter_data, telegram_data),
            'viral_potential': self._calculate_viral_potential(twitter_data, telegram_data),
            'organic_growth': self._calculate_organic_score(twitter_data, telegram_data)
        }

    def _calculate_hype_score(self, twitter, telegram):
        """Score de hype global (0-100) - Basé à 100% sur Twitter"""
        twitter_score = min(
            (twitter['mention_count'] / 10) * 50 +
            (twitter['engagement_score'] / 1000) * 30 +
            (twitter['trend_score'] / 100) * 20,
            100
        )

        # Bonus si Telegram existe (+5 points max)
        telegram_bonus = 5 if telegram['has_telegram'] else 0

        return min(twitter_score + telegram_bonus, 100)

    def _calculate_viral_potential(self, twitter, telegram):
        """Potentiel viral (croissance rapide)"""
        viral_score = 0

        # Beaucoup de mentions = viral
        if twitter['mention_count'] > 50:
            viral_score += 40
        elif twitter['mention_count'] > 20:
            viral_score += 20

        # Influenceurs = viral
        viral_score += min(twitter['influencer_mentions'] * 20, 40)

        # Sentiment positif = viral
        if twitter['sentiment_score'] > 50:
            viral_score += 20

        return min(viral_score, 100)

    def _calculate_organic_score(self, twitter, telegram):
        """Score de croissance organique vs manipulée"""
        # Croissance organique a:
        # - Engagement distribué (pas juste quelques gros tweets)
        # - Sentiment modérément positif (pas extrême)
        # - Présence Telegram

        organic = 50  # Base

        # Telegram présent = +20 organic
        if telegram['has_telegram']:
            organic += 20

        # Sentiment modéré = organic
        if 20 < twitter['sentiment_score'] < 80:
            organic += 15
        elif twitter['sentiment_score'] > 90:
            organic -= 20  # Trop positif = suspect

        # Engagement équilibré
        if twitter['mention_count'] > 0:
            avg_engagement = twitter['engagement_score'] / twitter['mention_count']
            if 10 < avg_engagement < 100:
                organic += 15
            elif avg_engagement > 500:
                organic -= 20  # Trop d'engagement = suspect

        return max(0, min(organic, 100))

    async def analyze_token(self, token_address, token_metadata=None):
        """Analyse complète d'un token"""
        console.print(f"\n[cyan]Analyse de sentiment pour {token_address[:8]}...")

        # Analyser Twitter (avec ticker et contract)
        token_name = token_metadata.get('name') if token_metadata else None
        token_symbol = token_metadata.get('symbol') if token_metadata else None
        twitter_data = await self.analyze_twitter(token_address, token_name, token_symbol)

        # Analyser Telegram
        telegram_data = await self.analyze_telegram(token_metadata if token_metadata else {})

        # Calculer les features
        features = self.calculate_sentiment_features(twitter_data, telegram_data)

        # Afficher résumé
        console.print(f"\n[bold yellow]Résultats Sentiment:")
        console.print(f"[cyan]Twitter Mentions: {twitter_data['mention_count']}")
        console.print(f"[cyan]Engagement: {twitter_data['engagement_score']}")
        console.print(f"[cyan]Sentiment: {twitter_data['sentiment_score']:.1f}")
        console.print(f"[cyan]Hype Score: {features['social_hype_score']:.1f}/100")
        console.print(f"[cyan]Viral Potential: {features['viral_potential']:.1f}/100")
        console.print(f"[cyan]Organic Growth: {features['organic_growth']:.1f}/100")

        return features

    async def close(self):
        """Ferme les connexions"""
        await self.client.aclose()


# Test
async def main():
    analyzer = SentimentAnalyzer()

    # Test avec un token
    test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    test_metadata = {
        'name': 'USDC',
        'telegram': 'https://t.me/example'
    }

    features = await analyzer.analyze_token(test_token, test_metadata)

    console.print("\n[bold green]Features de sentiment:")
    for key, value in features.items():
        console.print(f"[white]{key}: {value}")

    await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())
