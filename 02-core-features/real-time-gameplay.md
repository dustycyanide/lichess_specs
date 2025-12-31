---
title: Real-Time Gameplay
category: core-features
dependencies: Django Channels, WebSockets
styleguide: hacksoft-django-styleguide
lichess_equivalent: lila-ws
status: complete
---

# Real-Time Gameplay Specification

This document specifies the real-time gameplay system for our Django/React Lichess clone, using Django Channels and WebSockets.

> **Styleguide Reference**: WebSocket consumers call **services** for business logic (e.g., `game_make_move`). Consumers are thin interfaces similar to APIs. Services use keyword-only args with `*`, type annotations, `@transaction.atomic` for data integrity, and `full_clean()` before `save()`.

## Overview

Lichess uses a dedicated WebSocket server called **lila-ws** (written in Scala/Akka) to handle real-time communication:

```
lila <-> redis <-> lila-ws <-> websocket <-> client
```

Our Django implementation uses **Django Channels** with a similar architecture:

```
Django <-> Redis (Channel Layer) <-> Channels Consumer <-> WebSocket <-> Client
```

| Lichess | Our Stack |
|---------|-----------|
| lila-ws (Scala/Akka) | Django Channels |
| Redis pub/sub | Redis Channel Layer |
| Custom protocol | JSON messages |
| Snabbdom (client) | React + Chessground |

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT (React)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Chessground │  │ Game State   │  │ WebSocket Client │   │
│  │ (Board UI)  │  │ (React State)│  │                  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                                            │                 │
└────────────────────────────────────────────│─────────────────┘
                                             │ WebSocket
                                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Django Channels                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    GameConsumer                        │  │
│  │  - Handles WebSocket connections                       │  │
│  │  - Validates moves                                     │  │
│  │  - Broadcasts game state                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Redis Channel Layer                       │  │
│  │  - Game rooms (groups)                                 │  │
│  │  - Real-time pub/sub                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Django Channels Setup

### Installation

```bash
pip install channels channels-redis
```

### Configuration

```python
# settings.py
INSTALLED_APPS = [
    'daphne',  # ASGI server
    'channels',
    # ...
]

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('localhost', 6379)],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}
```

```python
# config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

django_asgi_app = get_asgi_application()

from <project_slug>.games.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

### URL Routing

```python
# <project_slug>/games/routing.py
from django.urls import re_path
from <project_slug>.games import consumers

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_id>\w+)/$', consumers.GameConsumer.as_asgi()),
]
```

## Game Consumer

### Core Implementation

```python
# <project_slug>/games/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import chess

from <project_slug>.games.services import game_make_move, game_end, game_get_clock_state


class GameConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time chess games.

    Message Types:
    - move: Player makes a move
    - resign: Player resigns
    - draw_offer: Player offers draw
    - draw_accept: Player accepts draw
    - chat: Chat message
    - ping: Keep-alive
    """

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'game_{self.game_id}'
        self.user = self.scope['user']

        # Join game room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Validate user is a player in this game
        self.game = await self.get_game()
        if not self.game:
            await self.close(code=4004)
            return

        self.player_color = await self.get_player_color()
        if self.player_color is None and not self.is_spectator_allowed():
            await self.close(code=4003)
            return

        await self.accept()

        # Send current game state
        await self.send_game_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive_json(self, content):
        msg_type = content.get('type')

        handlers = {
            'move': self.handle_move,
            'resign': self.handle_resign,
            'draw_offer': self.handle_draw_offer,
            'draw_accept': self.handle_draw_accept,
            'chat': self.handle_chat,
            'ping': self.handle_ping,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(content)

    # --- Message Handlers ---

    async def handle_move(self, content):
        """Handle a move from a player."""
        uci = content.get('uci')
        if not uci:
            await self.send_error('Missing move')
            return

        # Validate it's this player's turn
        game = await self.get_game()
        board = self.get_board(game)

        expected_color = 'white' if board.turn == chess.WHITE else 'black'
        if self.player_color != expected_color:
            await self.send_error('Not your turn')
            return

        # Validate and apply move
        try:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                await self.send_error('Illegal move')
                return

            board.push(move)

            # Update game state
            await self.update_game(game, uci, board)

            # Broadcast move to all clients
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_move',
                    'uci': uci,
                    'fen': board.fen(),
                    'san': board.san(move),
                    'player': self.player_color,
                    'clock': await self.get_clock_state(game),
                }
            )

            # Check for game end
            if board.is_game_over():
                await self.handle_game_end(board)

        except ValueError as e:
            await self.send_error(f'Invalid move: {e}')

    async def handle_resign(self, content):
        """Handle player resignation."""
        if not self.player_color:
            return

        game = await self.get_game()
        winner = 'black' if self.player_color == 'white' else 'white'

        await self.end_game(game, f'{winner}_wins', 'resignation')

    async def handle_draw_offer(self, content):
        """Handle draw offer."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'draw_offered',
                'player': self.player_color,
            }
        )

    async def handle_draw_accept(self, content):
        """Handle draw acceptance."""
        game = await self.get_game()
        await self.end_game(game, 'draw', 'agreement')

    async def handle_chat(self, content):
        """Handle chat message."""
        message = content.get('message', '').strip()[:500]  # Limit length
        if message:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'username': self.user.username,
                    'message': message,
                }
            )

    async def handle_ping(self, content):
        """Respond to keep-alive ping."""
        await self.send_json({'type': 'pong'})

    # --- Broadcast Handlers ---

    async def game_move(self, event):
        """Broadcast a move to all connected clients."""
        await self.send_json({
            'type': 'move',
            'uci': event['uci'],
            'fen': event['fen'],
            'san': event['san'],
            'player': event['player'],
            'clock': event['clock'],
        })

    async def game_end(self, event):
        """Broadcast game end to all connected clients."""
        await self.send_json({
            'type': 'gameEnd',
            'status': event['status'],
            'reason': event['reason'],
            'winner': event.get('winner'),
        })

    async def draw_offered(self, event):
        """Broadcast draw offer."""
        await self.send_json({
            'type': 'drawOffer',
            'player': event['player'],
        })

    async def chat_message(self, event):
        """Broadcast chat message."""
        await self.send_json({
            'type': 'chat',
            'username': event['username'],
            'message': event['message'],
        })

    # --- Helper Methods ---

    @database_sync_to_async
    def get_game(self):
        from <project_slug>.games.models import Game
        try:
            return Game.objects.select_related('white_player', 'black_player').get(id=self.game_id)
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def get_player_color(self):
        if self.user == self.game.white_player:
            return 'white'
        elif self.user == self.game.black_player:
            return 'black'
        return None

    def get_board(self, game):
        board = chess.Board()
        if game.moves:
            for uci in game.moves.split():
                board.push_uci(uci)
        return board

    @database_sync_to_async
    def update_game(self, game, uci, board):
        game.moves = f'{game.moves} {uci}'.strip()
        game.fen = board.fen()
        game.save(update_fields=['moves', 'fen'])

    async def send_game_state(self):
        """Send current game state to newly connected client."""
        game = await self.get_game()
        board = self.get_board(game)

        await self.send_json({
            'type': 'gameState',
            'fen': board.fen(),
            'moves': game.moves,
            'white': {'username': game.white_player.username},
            'black': {'username': game.black_player.username},
            'turn': 'white' if board.turn else 'black',
            'status': game.status,
            'clock': await self.get_clock_state(game),
        })

    async def send_error(self, message):
        await self.send_json({'type': 'error', 'message': message})

    async def handle_game_end(self, board):
        """Handle natural game end (checkmate, stalemate, etc.)."""
        game = await self.get_game()
        outcome = board.outcome()

        if outcome.winner is True:
            status = 'white_wins'
            reason = 'checkmate'
        elif outcome.winner is False:
            status = 'black_wins'
            reason = 'checkmate'
        else:
            status = 'draw'
            reason = str(outcome.termination.name).lower()

        await self.end_game(game, status, reason)

    @database_sync_to_async
    def end_game_db(self, game, status):
        game.status = status
        game.ended_at = timezone.now()
        game.save(update_fields=['status', 'ended_at'])

    async def end_game(self, game, status, reason):
        await self.end_game_db(game, status)

        # Determine winner
        winner = None
        if status == 'white_wins':
            winner = 'white'
        elif status == 'black_wins':
            winner = 'black'

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_end',
                'status': status,
                'reason': reason,
                'winner': winner,
            }
        )

    @database_sync_to_async
    def get_clock_state(self, game):
        """Get current clock state for both players."""
        # Implement based on your clock model
        return {
            'white': getattr(game, 'white_time_remaining', None),
            'black': getattr(game, 'black_time_remaining', None),
        }
```

## Game Services

Following Hacksoft pattern, business logic lives in services. Consumers call these services as thin wrappers.

```python
# <project_slug>/games/services.py
from django.db import transaction
from django.utils import timezone
import chess

from <project_slug>.games.models import Game


@transaction.atomic
def game_make_move(*, game: Game, uci: str) -> Game:
    """
    Apply a move to a game and update its state.

    Following Hacksoft pattern: keyword-only args, type annotations,
    @transaction.atomic for data integrity, full_clean() before save().
    """
    game.moves = f'{game.moves} {uci}'.strip()

    board = chess.Board()
    for move in game.moves.split():
        board.push_uci(move)

    game.fen = board.fen()
    game.full_clean()
    game.save(update_fields=['moves', 'fen'])

    return game


@transaction.atomic
def game_end(*, game: Game, status: str, reason: str) -> Game:
    """
    End a game with the given status and reason.

    Following Hacksoft pattern: keyword-only args, type annotations,
    @transaction.atomic for data integrity, full_clean() before save().
    """
    game.status = status
    game.end_reason = reason
    game.ended_at = timezone.now()
    game.full_clean()
    game.save(update_fields=['status', 'end_reason', 'ended_at'])

    return game


def game_get_clock_state(*, game: Game) -> dict:
    """
    Get current clock state for both players.

    Pure read operation - no transaction needed.
    """
    return {
        'white': getattr(game, 'white_time_remaining', None),
        'black': getattr(game, 'black_time_remaining', None),
    }
```

## Clock Management

### Server-Side Clock

```python
# <project_slug>/games/clock.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

@dataclass
class ChessClock:
    """
    Chess clock management.
    Time is stored in milliseconds for precision.
    """
    initial_time_ms: int
    increment_ms: int

    white_time_ms: int
    black_time_ms: int

    last_move_at: Optional[datetime] = None
    running_for: Optional[str] = None  # 'white' or 'black'

    @classmethod
    def from_time_control(cls, time_control: str) -> 'ChessClock':
        """Create clock from time control string like '5+3'."""
        parts = time_control.split('+')
        initial = int(parts[0]) * 60 * 1000  # minutes to ms
        increment = int(parts[1]) * 1000 if len(parts) > 1 else 0

        return cls(
            initial_time_ms=initial,
            increment_ms=increment,
            white_time_ms=initial,
            black_time_ms=initial,
        )

    def start(self, color: str):
        """Start the clock for a color."""
        self.running_for = color
        self.last_move_at = datetime.now()

    def stop(self) -> int:
        """
        Stop the clock and add increment.
        Returns time remaining for the player who just moved.
        """
        if not self.running_for or not self.last_move_at:
            return 0

        elapsed = int((datetime.now() - self.last_move_at).total_seconds() * 1000)

        if self.running_for == 'white':
            self.white_time_ms = max(0, self.white_time_ms - elapsed + self.increment_ms)
            remaining = self.white_time_ms
        else:
            self.black_time_ms = max(0, self.black_time_ms - elapsed + self.increment_ms)
            remaining = self.black_time_ms

        self.running_for = None
        self.last_move_at = None

        return remaining

    def get_times(self) -> tuple[int, int]:
        """Get current times accounting for running clock."""
        white = self.white_time_ms
        black = self.black_time_ms

        if self.running_for and self.last_move_at:
            elapsed = int((datetime.now() - self.last_move_at).total_seconds() * 1000)
            if self.running_for == 'white':
                white = max(0, white - elapsed)
            else:
                black = max(0, black - elapsed)

        return white, black

    def is_flag_fallen(self) -> Optional[str]:
        """Check if either player has run out of time."""
        white, black = self.get_times()
        if white <= 0:
            return 'white'
        if black <= 0:
            return 'black'
        return None
```

### Clock Integration in Consumer

```python
# Add to GameConsumer

async def handle_move(self, content):
    # ... existing validation ...

    # Stop clock for moving player, start for opponent
    clock = await self.get_or_create_clock()
    clock.stop()
    opponent = 'black' if self.player_color == 'white' else 'white'
    clock.start(opponent)
    await self.save_clock(clock)

    # Include clock in broadcast
    white_time, black_time = clock.get_times()

    await self.channel_layer.group_send(
        self.room_group_name,
        {
            'type': 'game_move',
            'uci': uci,
            'fen': board.fen(),
            'clock': {'white': white_time, 'black': black_time},
        }
    )
```

## Client-Side Implementation

### WebSocket Hook

```typescript
// frontend/src/hooks/useGameSocket.ts
import { useEffect, useRef, useCallback, useState } from 'react';

interface GameState {
  fen: string;
  moves: string;
  turn: 'white' | 'black';
  status: string;
  clock: { white: number; black: number };
}

interface UseGameSocketProps {
  gameId: string;
  onMove: (data: { uci: string; fen: string; san: string }) => void;
  onGameEnd: (data: { status: string; winner?: string }) => void;
}

export function useGameSocket({ gameId, onMove, onGameEnd }: UseGameSocketProps) {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [gameState, setGameState] = useState<GameState | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/game/${gameId}/`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setConnected(true);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'gameState':
          setGameState(data);
          break;
        case 'move':
          onMove(data);
          break;
        case 'gameEnd':
          onGameEnd(data);
          break;
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
    };

    // Keep-alive ping every 30 seconds
    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      ws.current?.close();
    };
  }, [gameId, onMove, onGameEnd]);

  const sendMove = useCallback((uci: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'move', uci }));
    }
  }, []);

  const resign = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'resign' }));
    }
  }, []);

  const offerDraw = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'draw_offer' }));
    }
  }, []);

  return {
    connected,
    gameState,
    sendMove,
    resign,
    offerDraw,
  };
}
```

### Game Component

```typescript
// frontend/src/features/game/components/GameBoard.tsx
import { useCallback } from 'react';
import { Chessground } from 'react-chessground';
import { useGameSocket } from '../hooks/useGameSocket';

interface GameBoardProps {
  gameId: string;
  playerColor: 'white' | 'black';
}

export function GameBoard({ gameId, playerColor }: GameBoardProps) {
  const handleMove = useCallback((data: { uci: string; fen: string }) => {
    // Update board state
  }, []);

  const handleGameEnd = useCallback((data: { status: string }) => {
    // Show game end modal
  }, []);

  const { connected, gameState, sendMove } = useGameSocket({
    gameId,
    onMove: handleMove,
    onGameEnd: handleGameEnd,
  });

  const onMove = (from: string, to: string) => {
    // Optimistic update + send to server
    sendMove(`${from}${to}`);
  };

  if (!gameState) {
    return <div>Loading...</div>;
  }

  return (
    <div className="game-board">
      <Chessground
        fen={gameState.fen}
        orientation={playerColor}
        turnColor={gameState.turn}
        movable={{
          free: false,
          color: playerColor,
          dests: new Map(), // Calculate from legal moves
        }}
        events={{
          move: onMove,
        }}
      />
      <Clock
        whiteTime={gameState.clock.white}
        blackTime={gameState.clock.black}
        activeSide={gameState.turn}
      />
    </div>
  );
}
```

## Message Protocol

### Client → Server

| Type | Payload | Description |
|------|---------|-------------|
| `move` | `{ uci: "e2e4" }` | Player makes a move |
| `resign` | `{}` | Player resigns |
| `draw_offer` | `{}` | Player offers draw |
| `draw_accept` | `{}` | Player accepts draw offer |
| `chat` | `{ message: "..." }` | Chat message |
| `ping` | `{}` | Keep-alive |

### Server → Client

| Type | Payload | Description |
|------|---------|-------------|
| `gameState` | Full game state | Initial state on connect |
| `move` | `{ uci, fen, san, clock }` | A move was made |
| `gameEnd` | `{ status, reason, winner }` | Game has ended |
| `drawOffer` | `{ player }` | Draw offer received |
| `chat` | `{ username, message }` | Chat message |
| `pong` | `{}` | Ping response |
| `error` | `{ message }` | Error occurred |

## Scaling Considerations

### Redis Channel Layer

For production, configure Redis with proper settings:

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.environ.get('REDIS_URL', 'redis://localhost:6379')],
            'capacity': 1500,
            'expiry': 10,
            'group_expiry': 86400,  # 24 hours
        },
    },
}
```

### Connection Limits

- Use nginx/haproxy for WebSocket load balancing
- Implement connection rate limiting
- Add reconnection logic on client

### Horizontal Scaling

Multiple Channels workers can run with shared Redis:

```bash
# Run multiple workers
daphne -p 8001 config.asgi:application
daphne -p 8002 config.asgi:application
```

## Sources

- [Django Channels Documentation](https://channels.readthedocs.io/)
- [lila-ws Repository](https://github.com/lichess-org/lila-ws)
- [Chessground React](https://github.com/ruilisi/react-chessground)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
