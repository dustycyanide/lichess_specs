---
title: WebSocket Architecture
category: architecture
stack: Django Channels, Redis
styleguide: hacksoft-django-styleguide
status: draft
---

# WebSocket Architecture

This document maps Lichess's lila-ws WebSocket server architecture to Django Channels for real-time game communication.

> **Styleguide Reference**: Consumers follow [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) patterns—business logic in services, consumers are thin wrappers that delegate to services.

## Lichess → Django Channels Mapping

| Lichess (lila-ws) | Our Approach |
|-------------------|--------------|
| Akka HTTP WebSocket | Django Channels |
| Akka Actors | Channels Consumers |
| Redis pub/sub | Redis Channel Layer |
| Custom binary protocol | JSON over WebSocket |
| lila ↔ lila-ws communication | Channels group messaging |

## Architecture Overview

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Browser   │────▶│  Django Channels │────▶│    Redis    │
│  WebSocket  │◀────│    (ASGI)        │◀────│ Channel Layer│
└─────────────┘     └──────────────────┘     └─────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Django Views    │
                    │  (HTTP/REST)     │
                    └──────────────────┘
```

## ASGI Configuration

```python
# config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

django_asgi_app = get_asgi_application()

from <project_slug>.games.routing import websocket_urlpatterns as game_ws
from <project_slug>.lobby.routing import websocket_urlpatterns as lobby_ws
from <project_slug>.tournaments.routing import websocket_urlpatterns as tournament_ws

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                game_ws + lobby_ws + tournament_ws
            )
        )
    ),
})
```

## Channel Layer Configuration

```python
# config/settings/base.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.environ.get("REDIS_HOST", "localhost"), 6379)],
            "capacity": 1500,  # Max messages per channel
            "expiry": 10,  # Message expiry in seconds
        },
    },
}
```

## WebSocket URL Routing

```python
# <project_slug>/games/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_id>\w{8})$', consumers.GameConsumer.as_asgi()),
]

# <project_slug>/lobby/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/lobby$', consumers.LobbyConsumer.as_asgi()),
    re_path(r'ws/seek$', consumers.SeekConsumer.as_asgi()),
]

# <project_slug>/tournaments/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/tournament/(?P<tournament_id>[\w-]+)$', consumers.TournamentConsumer.as_asgi()),
]
```

## Message Protocol

Following Lichess's message format with `t` (type) and `d` (data):

```python
# <project_slug>/common/websocket.py
from dataclasses import dataclass
from typing import Any
import json

@dataclass
class WSMessage:
    """WebSocket message following Lichess protocol."""
    t: str  # message type
    d: Any = None  # message data

    def to_json(self) -> str:
        msg = {"t": self.t}
        if self.d is not None:
            msg["d"] = self.d
        return json.dumps(msg)

    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        parsed = json.loads(data)
        return cls(t=parsed.get("t", ""), d=parsed.get("d"))
```

### Message Types

```python
# <project_slug>/games/constants.py

class GameMessageType:
    # Client → Server
    MOVE = "move"           # Player makes a move
    DRAW_YES = "draw-yes"   # Accept draw offer
    DRAW_NO = "draw-no"     # Decline draw offer
    DRAW_OFFER = "draw-offer"  # Offer a draw
    RESIGN = "resign"       # Resign the game
    TAKEBACK_YES = "takeback-yes"
    TAKEBACK_NO = "takeback-no"
    TAKEBACK_OFFER = "takeback"
    FLAG = "flag"           # Claim opponent timeout
    BERSERK = "berserk"     # Arena berserk

    # Server → Client
    MOVE_MADE = "move"      # Move was played
    END = "end"             # Game ended
    CLOCK = "clock"         # Clock update
    CROWD = "crowd"         # Spectator count
    GONE = "gone"           # Opponent disconnected
    BACK = "back"           # Opponent reconnected
    DRAW_OFFERED = "drawOffer"
    TAKEBACK_OFFERED = "takebackOffer"
```

## Game Consumer

```python
# <project_slug>/games/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from <project_slug>.games.models import Game
from <project_slug>.games.services import game_make_move, game_resign, game_offer_draw
from .constants import GameMessageType
import logging

logger = logging.getLogger(__name__)


class GameConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for live game communication.
    Handles moves, clock sync, draw offers, resignation.
    """

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group = f'game_{self.game_id}'
        self.user = self.scope.get('user')

        # Join game room
        await self.channel_layer.group_add(
            self.game_group,
            self.channel_name
        )

        # Validate game exists
        game = await self.get_game()
        if not game:
            await self.close(code=4004)
            return

        await self.accept()

        # Send current game state
        await self.send_json({
            "t": "full",
            "d": await self.serialize_game(game)
        })

        # Notify others of new spectator/player
        await self.broadcast_crowd()

    async def disconnect(self, close_code):
        # Leave game room
        await self.channel_layer.group_discard(
            self.game_group,
            self.channel_name
        )

        # Notify if player disconnected
        if self.user and self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.game_group,
                {
                    "type": "player_gone",
                    "user_id": str(self.user.id),
                }
            )

    async def receive_json(self, content):
        """Handle incoming WebSocket messages."""
        msg_type = content.get('t')
        data = content.get('d', {})

        handler = {
            GameMessageType.MOVE: self.handle_move,
            GameMessageType.RESIGN: self.handle_resign,
            GameMessageType.DRAW_OFFER: self.handle_draw_offer,
            GameMessageType.DRAW_YES: self.handle_draw_accept,
            GameMessageType.DRAW_NO: self.handle_draw_decline,
            GameMessageType.FLAG: self.handle_flag,
        }.get(msg_type)

        if handler:
            try:
                await handler(data)
            except Exception as e:
                logger.exception(f"Error handling {msg_type}: {e}")
                await self.send_json({"t": "error", "d": str(e)})

    async def handle_move(self, data):
        """Process a move from a player."""
        uci = data.get('u')  # UCI move like "e2e4"
        if not uci:
            return

        game = await self.get_game()

        # Validate it's this user's turn
        if not await self.is_player_turn(game):
            await self.send_json({"t": "error", "d": "Not your turn"})
            return

        # Make the move (service handles validation)
        try:
            updated_game = await database_sync_to_async(game_make_move)(
                game=game,
                player=self.user,
                uci_move=uci
            )
        except Exception as e:
            await self.send_json({"t": "error", "d": str(e)})
            return

        # Broadcast move to all connected clients
        await self.channel_layer.group_send(
            self.game_group,
            {
                "type": "game_move",
                "uci": uci,
                "fen": updated_game.fen,
                "ply": updated_game.ply,
                "wc": updated_game.white_clock,
                "bc": updated_game.black_clock,
                "status": updated_game.status,
            }
        )

        # If game ended, send end message
        if updated_game.status != 'started':
            await self.channel_layer.group_send(
                self.game_group,
                {
                    "type": "game_end",
                    "status": updated_game.status,
                    "winner": updated_game.winner,
                }
            )

    async def handle_resign(self, data):
        """Handle player resignation."""
        game = await self.get_game()

        if not await self.is_player(game):
            return

        updated_game = await database_sync_to_async(game_resign)(
            game=game,
            player=self.user
        )

        await self.channel_layer.group_send(
            self.game_group,
            {
                "type": "game_end",
                "status": "resign",
                "winner": "black" if self.user == game.white else "white",
            }
        )

    async def handle_draw_offer(self, data):
        """Handle draw offer from a player."""
        game = await self.get_game()

        if not await self.is_player(game):
            return

        await self.channel_layer.group_send(
            self.game_group,
            {
                "type": "draw_offered",
                "by": str(self.user.id),
            }
        )

    async def handle_draw_accept(self, data):
        """Handle draw acceptance."""
        game = await self.get_game()

        updated_game = await database_sync_to_async(game_offer_draw)(
            game=game,
            player=self.user,
            accept=True
        )

        if updated_game.status == 'draw':
            await self.channel_layer.group_send(
                self.game_group,
                {
                    "type": "game_end",
                    "status": "draw",
                    "winner": "",
                }
            )

    async def handle_draw_decline(self, data):
        """Handle draw decline."""
        await self.channel_layer.group_send(
            self.game_group,
            {
                "type": "draw_declined",
            }
        )

    async def handle_flag(self, data):
        """Handle timeout claim."""
        game = await self.get_game()
        # Check if opponent is actually out of time
        # Implementation depends on clock management strategy

    # ─────────────────────────────────────────────
    # Group message handlers (called by channel_layer)
    # ─────────────────────────────────────────────

    async def game_move(self, event):
        """Broadcast move to client."""
        await self.send_json({
            "t": "move",
            "d": {
                "uci": event["uci"],
                "fen": event["fen"],
                "ply": event["ply"],
                "wc": event["wc"],
                "bc": event["bc"],
            }
        })

    async def game_end(self, event):
        """Broadcast game end to client."""
        await self.send_json({
            "t": "end",
            "d": {
                "status": event["status"],
                "winner": event["winner"],
            }
        })

    async def draw_offered(self, event):
        """Notify of draw offer."""
        await self.send_json({
            "t": "drawOffer",
            "d": {"by": event["by"]}
        })

    async def draw_declined(self, event):
        """Notify draw was declined."""
        await self.send_json({"t": "drawNo"})

    async def player_gone(self, event):
        """Notify player disconnected."""
        await self.send_json({
            "t": "gone",
            "d": {"userId": event["user_id"]}
        })

    async def crowd_update(self, event):
        """Update spectator count."""
        await self.send_json({
            "t": "crowd",
            "d": event["count"]
        })

    # ─────────────────────────────────────────────
    # Helper methods
    # ─────────────────────────────────────────────

    @database_sync_to_async
    def get_game(self):
        try:
            return Game.objects.select_related('white', 'black').get(id=self.game_id)
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def is_player(self, game):
        if not self.user or not self.user.is_authenticated:
            return False
        return self.user in (game.white, game.black)

    @database_sync_to_async
    def is_player_turn(self, game):
        if not self.user or not self.user.is_authenticated:
            return False
        if game.ply % 2 == 0:  # White's turn
            return self.user == game.white
        return self.user == game.black

    @database_sync_to_async
    def serialize_game(self, game):
        return {
            "id": game.id,
            "fen": game.fen,
            "moves": game.moves,
            "status": game.status,
            "white": {"id": str(game.white.id), "name": game.white.username} if game.white else None,
            "black": {"id": str(game.black.id), "name": game.black.username} if game.black else None,
            "wc": game.white_clock,
            "bc": game.black_clock,
            "ply": game.ply,
        }

    async def broadcast_crowd(self):
        """Send current spectator count to all clients."""
        # In production, track connections per game in Redis
        await self.channel_layer.group_send(
            self.game_group,
            {"type": "crowd_update", "count": 1}
        )
```

## Lobby Consumer

```python
# <project_slug>/lobby/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async


class LobbyConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-time lobby showing current seeks and live games.
    """

    async def connect(self):
        self.user = self.scope.get('user')

        await self.channel_layer.group_add("lobby", self.channel_name)
        await self.accept()

        # Send current lobby state
        await self.send_lobby_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("lobby", self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get('t')

        if msg_type == "seek":
            await self.create_seek(content.get('d', {}))
        elif msg_type == "cancel":
            await self.cancel_seek(content.get('d', {}))

    async def create_seek(self, data):
        """Create a new game seek."""
        if not self.user or not self.user.is_authenticated:
            await self.send_json({"t": "error", "d": "Must be logged in"})
            return

        # Create seek in database
        seek = await self.create_seek_in_db(data)

        # Broadcast new seek to lobby
        await self.channel_layer.group_send(
            "lobby",
            {
                "type": "seek_created",
                "seek": await self.serialize_seek(seek),
            }
        )

    async def cancel_seek(self, data):
        """Cancel an existing seek."""
        seek_id = data.get('id')
        await self.delete_seek_in_db(seek_id)

        await self.channel_layer.group_send(
            "lobby",
            {
                "type": "seek_removed",
                "id": seek_id,
            }
        )

    # Group handlers
    async def seek_created(self, event):
        await self.send_json({
            "t": "seek",
            "d": event["seek"]
        })

    async def seek_removed(self, event):
        await self.send_json({
            "t": "seekRemove",
            "d": {"id": event["id"]}
        })

    async def game_started(self, event):
        """Notify player their seek was accepted."""
        await self.send_json({
            "t": "redirect",
            "d": {"url": f"/game/{event['game_id']}"}
        })

    async def send_lobby_state(self):
        """Send current seeks to newly connected client."""
        seeks = await self.get_active_seeks()
        await self.send_json({
            "t": "seeks",
            "d": seeks
        })

    @database_sync_to_async
    def get_active_seeks(self):
        from <project_slug>.lobby.models import Seek
        return [
            {
                "id": str(s.id),
                "user": s.user.username,
                "rating": s.user_rating,
                "time": s.initial_time,
                "increment": s.increment,
                "rated": s.rated,
            }
            for s in Seek.objects.select_related('user').filter(active=True)[:50]
        ]
```

## Clock Synchronization

Lichess sends clock updates with each move. We do the same:

```python
# <project_slug>/games/clock.py
from datetime import datetime, timezone
from typing import Tuple


class GameClock:
    """
    Manages chess clock state.
    Times stored in centiseconds (like Lichess).
    """

    def __init__(
        self,
        white_time: int,
        black_time: int,
        increment: int,
        white_to_move: bool = True,
        last_move_at: datetime | None = None
    ):
        self.white_time = white_time  # centiseconds
        self.black_time = black_time
        self.increment = increment * 100  # convert to centiseconds
        self.white_to_move = white_to_move
        self.last_move_at = last_move_at

    def make_move(self) -> Tuple[int, int]:
        """
        Process a move: deduct elapsed time, add increment.
        Returns (white_time, black_time) after the move.
        """
        now = datetime.now(timezone.utc)

        if self.last_move_at:
            elapsed = int((now - self.last_move_at).total_seconds() * 100)

            if self.white_to_move:
                self.white_time = max(0, self.white_time - elapsed + self.increment)
            else:
                self.black_time = max(0, self.black_time - elapsed + self.increment)

        self.white_to_move = not self.white_to_move
        self.last_move_at = now

        return (self.white_time, self.black_time)

    def is_flag(self) -> str | None:
        """Check if either player has flagged (run out of time)."""
        if self.white_time <= 0:
            return "white"
        if self.black_time <= 0:
            return "black"
        return None
```

## Scaling Considerations

### Multiple Server Instances

With Redis channel layer, multiple Django instances share WebSocket connections:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│  Django 1   │────▶│             │
│  (LB + WS)  │────▶│  Django 2   │────▶│    Redis    │
│             │────▶│  Django 3   │────▶│             │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Connection Tracking

Track active connections per game for spectator counts:

```python
# Using Redis directly for connection tracking
import redis

redis_client = redis.Redis()

async def track_connection(game_id: str, channel_name: str):
    redis_client.sadd(f"game:{game_id}:connections", channel_name)
    redis_client.expire(f"game:{game_id}:connections", 3600)

async def untrack_connection(game_id: str, channel_name: str):
    redis_client.srem(f"game:{game_id}:connections", channel_name)

async def get_spectator_count(game_id: str) -> int:
    return redis_client.scard(f"game:{game_id}:connections")
```

### Heartbeat / Keep-Alive

```python
# In consumer
async def connect(self):
    # ... existing connect logic ...

    # Start heartbeat task
    self.heartbeat_task = asyncio.create_task(self.heartbeat())

async def heartbeat(self):
    """Send periodic ping to detect dead connections."""
    while True:
        await asyncio.sleep(30)
        try:
            await self.send_json({"t": "ping"})
        except:
            break

async def disconnect(self, close_code):
    if hasattr(self, 'heartbeat_task'):
        self.heartbeat_task.cancel()
    # ... rest of disconnect ...
```

## Key Differences from Lichess

| Aspect | Lichess (lila-ws) | Our Approach |
|--------|-------------------|--------------|
| **Server** | Dedicated Scala service | Django Channels (integrated) |
| **Protocol** | Binary + JSON | JSON only |
| **Actor model** | Akka actors per game | Consumer instances |
| **Scaling** | Custom sharding | Redis channel layer |
| **Clock sync** | Server authoritative | Server authoritative |
