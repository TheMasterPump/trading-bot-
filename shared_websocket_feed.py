"""
SHARED WEBSOCKET FEED - 1 connexion PumpFun pour TOUS les utilisateurs
Résout le problème de 200+ connexions simultanées
"""
import asyncio
import json
import websockets
from datetime import datetime
from typing import Set, Callable
import threading


class SharedTokenFeed:
    """
    Feed partagé de tokens depuis PumpFun
    1 seule connexion WebSocket pour tous les bots
    """

    def __init__(self, redis_client=None):
        self.ws = None
        self.redis = redis_client
        self.subscribers: Set[Callable] = set()
        self.is_running = False
        self.reconnect_delay = 5

        # Stats
        self.tokens_received = 0
        self.uptime_start = None

    def subscribe(self, callback: Callable):
        """Ajoute un bot qui veut recevoir les tokens"""
        self.subscribers.add(callback)
        print(f"[FEED] Bot subscribed. Total subscribers: {len(self.subscribers)}")

    def unsubscribe(self, callback: Callable):
        """Retire un bot"""
        self.subscribers.discard(callback)
        print(f"[FEED] Bot unsubscribed. Total subscribers: {len(self.subscribers)}")

    async def broadcast_token(self, token_data: dict):
        """Envoie les données à tous les bots subscribers"""
        self.tokens_received += 1

        # Option 1: Broadcast direct (fast)
        for callback in self.subscribers:
            try:
                # Call callback in non-blocking way
                asyncio.create_task(callback(token_data))
            except Exception as e:
                print(f"[ERROR] Callback failed: {e}")

        # Option 2: Broadcast via Redis (si configuré)
        if self.redis:
            try:
                self.redis.publish('pumpfun_tokens', json.dumps(token_data))
            except Exception as e:
                print(f"[ERROR] Redis broadcast failed: {e}")

    async def connect(self):
        """Connexion au WebSocket PumpFun"""
        url = "wss://pumpportal.fun/api/data"

        try:
            print(f"[FEED] Connecting to {url}...")
            self.ws = await websockets.connect(url)
            print(f"[FEED] Connected successfully!")

            # Subscribe to new tokens
            subscribe_message = {
                "method": "subscribeNewToken"
            }
            await self.ws.send(json.dumps(subscribe_message))
            print(f"[FEED] Subscribed to new tokens")

            return True

        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    async def listen(self):
        """Écoute les tokens et broadcast à tous les bots"""
        self.is_running = True
        self.uptime_start = datetime.now()

        while self.is_running:
            try:
                # Connexion
                connected = await self.connect()
                if not connected:
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                # Écoute
                print(f"[FEED] Listening for tokens... ({len(self.subscribers)} subscribers)")

                async for message in self.ws:
                    try:
                        data = json.loads(message)

                        # Broadcast à tous les bots
                        await self.broadcast_token(data)

                        # Log toutes les 100 tokens
                        if self.tokens_received % 100 == 0:
                            print(f"[FEED] {self.tokens_received} tokens processed | {len(self.subscribers)} active bots")

                    except json.JSONDecodeError:
                        print(f"[ERROR] Invalid JSON: {message[:100]}")
                    except Exception as e:
                        print(f"[ERROR] Message processing failed: {e}")

            except websockets.exceptions.ConnectionClosed:
                print(f"[FEED] Connection closed. Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)

            except Exception as e:
                print(f"[ERROR] Feed crashed: {e}")
                await asyncio.sleep(self.reconnect_delay)

    def stop(self):
        """Arrête le feed"""
        self.is_running = False
        print(f"[FEED] Stopping... ({self.tokens_received} tokens processed)")

    def get_stats(self):
        """Stats du feed"""
        uptime = (datetime.now() - self.uptime_start).total_seconds() if self.uptime_start else 0
        return {
            'is_running': self.is_running,
            'subscribers': len(self.subscribers),
            'tokens_received': self.tokens_received,
            'uptime_seconds': uptime,
            'tokens_per_minute': (self.tokens_received / uptime * 60) if uptime > 0 else 0
        }


# Instance globale (singleton)
_shared_feed = None
_feed_thread = None
_feed_loop = None


def get_shared_feed(redis_client=None) -> SharedTokenFeed:
    """Récupère l'instance globale du feed"""
    global _shared_feed

    if _shared_feed is None:
        _shared_feed = SharedTokenFeed(redis_client)

    return _shared_feed


def start_shared_feed_background(redis_client=None):
    """Démarre le feed dans un thread séparé"""
    global _feed_thread, _feed_loop

    if _feed_thread and _feed_thread.is_alive():
        print("[FEED] Already running")
        return

    def run_feed():
        global _feed_loop
        _feed_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_feed_loop)

        feed = get_shared_feed(redis_client)

        try:
            _feed_loop.run_until_complete(feed.listen())
        except KeyboardInterrupt:
            print("[FEED] Interrupted")
        finally:
            _feed_loop.close()

    _feed_thread = threading.Thread(target=run_feed, daemon=True)
    _feed_thread.start()

    print("[FEED] Started in background thread")


def stop_shared_feed():
    """Arrête le feed"""
    global _shared_feed

    if _shared_feed:
        _shared_feed.stop()


if __name__ == "__main__":
    # Test
    print("Testing Shared Feed...")

    async def test_callback(token):
        print(f"Received token: {token.get('mint', 'unknown')}")

    feed = get_shared_feed()
    feed.subscribe(test_callback)

    asyncio.run(feed.listen())
