---
title: Backend Architecture
category: architecture
stack: Django, Django Channels, PostgreSQL, Redis
styleguide: hacksoft-django-styleguide
status: draft
---

# Backend Architecture

This document maps Lichess's Scala/Play/Akka backend patterns to Django equivalents for our chess platform implementation.

> **Styleguide Reference**: This architecture follows the [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) patterns. All business logic belongs in **Services** and **Selectors**, NOT in APIs, serializers, models, or signals.

## Lichess → Django Architecture Mapping

| Lichess (Scala) | Our Stack (Django) | Purpose |
|-----------------|-------------------|---------|
| Play Framework | Django | Web framework |
| Akka Actors | Django Channels + Celery | Async processing & concurrency |
| scalatags | Django Templates / DRF | Server-side rendering / API |
| scalachess | python-chess | Chess rules engine |
| MongoDB | PostgreSQL | Primary database |
| Redis | Redis | Pub/sub, caching, sessions |

## Application Structure

Following the Hacksoft Django Styleguide and cookiecutter-django project structure:

```
backend/
├── config/
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── local.py        # Development settings
│   │   ├── production.py   # Production settings
│   │   └── test.py         # Test settings
│   ├── urls.py             # Root URL configuration
│   ├── asgi.py             # ASGI entry point (Django Channels)
│   └── wsgi.py             # WSGI entry point
├── <project_slug>/
│   ├── users/              # Authentication, profiles, ratings
│   │   ├── models.py       # User model, Rating model
│   │   ├── services.py     # user_create, user_update, rating_update
│   │   ├── selectors.py    # user_get, user_list, rating_get
│   │   ├── apis.py         # UserCreateApi, UserDetailApi
│   │   └── tests/
│   ├── games/              # Game logic, moves, results
│   │   ├── models.py
│   │   ├── services.py     # game_create, game_make_move, game_resign
│   │   ├── selectors.py    # game_get, game_list_for_user
│   │   ├── apis.py
│   │   └── consumers.py    # GameConsumer (WebSocket)
│   ├── matchmaking/        # Lobby, pairing, seek system
│   ├── tournaments/        # Arena & Swiss tournaments
│   ├── puzzles/            # Tactical puzzles & training
│   ├── analysis/           # Stockfish integration, eval
│   ├── studies/            # Collaborative analysis boards
│   ├── teams/              # Clubs and team features
│   └── common/             # Shared utilities, exception handlers
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
└── pyproject.toml          # UV/pip configuration
```

**Note:** This structure follows cookiecutter-django conventions. The `<project_slug>` directory contains all Django apps (not a separate `apps/` directory).

## Core Design Patterns

### Service Layer (Hacksoft Pattern)

All business logic lives in services, not views or models. Services:
- Use keyword-only arguments (`*`) for explicitness
- Are type-annotated
- Call `full_clean()` before `save()` (Full Clean Pattern)
- Use `@transaction.atomic` for data integrity

```python
# <project_slug>/games/services.py
from django.db import transaction

from <project_slug>.games.models import Game
from <project_slug>.users.models import User
import chess


@transaction.atomic
def game_create(
    *,
    white: User,
    black: User,
    time_control: str,
    rated: bool = True
) -> Game:
    """Create a new game between two players."""
    board = chess.Board()

    game = Game(
        white=white,
        black=black,
        time_control=time_control,
        rated=rated,
        fen=board.fen(),
        status=Game.Status.STARTED
    )

    # Full Clean Pattern: validate before save
    game.full_clean()
    game.save()

    # Notify players via WebSocket
    game_notify_started(game=game)

    return game


@transaction.atomic
def game_make_move(
    *,
    game: Game,
    player: User,
    uci_move: str
) -> Game:
    """Process a move in an ongoing game."""
    board = chess.Board(game.fen)
    move = chess.Move.from_uci(uci_move)

    if move not in board.legal_moves:
        raise InvalidMoveError(f"Illegal move: {uci_move}")

    if not _is_player_turn(game=game, player=player):
        raise NotYourTurnError()

    board.push(move)

    game.fen = board.fen()
    game.moves = f"{game.moves} {uci_move}".strip()
    game.ply += 1

    if board.is_game_over():
        game = _finalize_game(game=game, board=board)

    game.full_clean()
    game.save()

    # Broadcast move to spectators and opponent
    game_broadcast_move(game=game, move=uci_move)

    return game
```

### Selectors for Queries

Complex queries are encapsulated in selectors:

```python
# <project_slug>/games/selectors.py
from django.db.models import QuerySet, Q

from <project_slug>.games.models import Game
from <project_slug>.users.models import User


def game_list_for_user(*, user: User, status: str | None = None) -> QuerySet[Game]:
    """Get games where user is a participant."""
    queryset = Game.objects.filter(
        Q(white=user) | Q(black=user)
    ).select_related('white', 'black')

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by('-created_at')


def game_list_live() -> QuerySet[Game]:
    """Get all currently active games for TV/spectating."""
    return Game.objects.filter(
        status=Game.Status.STARTED
    ).select_related(
        'white', 'black'
    ).order_by('-white__rating', '-created_at')[:50]
```

## Chess Logic Integration

### python-chess Library

We use [python-chess](https://python-chess.readthedocs.io/) as our chess rules engine, equivalent to Lichess's scalachess:

```python
import chess
import chess.pgn
import chess.engine

# Board representation
board = chess.Board()
board.push_san("e4")
board.push_san("e5")

# Legal move validation
move = chess.Move.from_uci("g1f3")
is_legal = move in board.legal_moves

# Game state detection
board.is_checkmate()
board.is_stalemate()
board.is_insufficient_material()
board.can_claim_draw()

# FEN import/export
fen = board.fen()
board = chess.Board(fen)

# PGN generation
game = chess.pgn.Game.from_board(board)
pgn_string = str(game)
```

### Engine Analysis (Stockfish)

For server-side analysis (similar to Lichess's fishnet):

```python
# <project_slug>/analysis/services.py
import chess.engine


async def position_analyze(
    *,
    fen: str,
    depth: int = 20,
    multipv: int = 3
) -> list[dict]:
    """Analyze a position using Stockfish."""
    transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")

    board = chess.Board(fen)
    analysis = await engine.analyse(
        board,
        chess.engine.Limit(depth=depth),
        multipv=multipv
    )

    await engine.quit()

    return [
        {
            "pv": [m.uci() for m in info.get("pv", [])],
            "score": info["score"].relative.score(mate_score=10000),
            "depth": info["depth"],
            "mate": info["score"].relative.mate()
        }
        for info in analysis
    ]
```

## Async Patterns

### Django Channels for Real-Time

Lichess uses Akka actors for concurrency. We use Django Channels:

```python
# <project_slug>/games/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'game_{self.game_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def receive_json(self, content):
        action = content.get('t')  # 'type' like Lichess protocol

        if action == 'move':
            await self.handle_move(content['d'])
        elif action == 'draw':
            await self.handle_draw_offer(content['d'])

    async def game_move(self, event):
        """Broadcast move to all connected clients."""
        await self.send_json({
            't': 'move',
            'd': event['move']
        })
```

### Celery for Background Tasks

Heavy processing (analysis, rating updates, tournament pairings):

```python
# <project_slug>/games/tasks.py
from celery import shared_task


@shared_task
def game_process_result(game_id: str) -> None:
    """Update ratings and statistics after game ends."""
    # Import inside task to avoid circular imports (Hacksoft pattern)
    from <project_slug>.games.models import Game
    from <project_slug>.users.services import rating_update

    game = Game.objects.get(id=game_id)

    rating_update(
        white=game.white,
        black=game.black,
        result=game.result,
        time_control=game.time_control
    )


@shared_task
def analysis_request(game_id: str, depth: int = 20) -> None:
    """Queue server-side analysis for a completed game."""
    from <project_slug>.analysis.services import game_analyze_full

    game_analyze_full(game_id=game_id, depth=depth)
```

## API Design

### REST Endpoints (DRF)

APIs follow the Hacksoft pattern with nested `InputSerializer` and `OutputSerializer`:

```python
# <project_slug>/games/apis.py
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from <project_slug>.games.services import game_create
from <project_slug>.games.selectors import game_list_for_user


class GameCreateApi(APIView):
    class InputSerializer(serializers.Serializer):
        opponent_id = serializers.UUIDField()
        time_control = serializers.CharField()
        rated = serializers.BooleanField(default=True)

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        game = game_create(
            white=request.user,
            black_id=serializer.validated_data['opponent_id'],
            **serializer.validated_data
        )

        return Response({'game_id': str(game.id)}, status=status.HTTP_201_CREATED)
```

## Error Handling

Custom exceptions following Hacksoft's `ApplicationError` pattern:

```python
# <project_slug>/games/exceptions.py
from <project_slug>.common.exceptions import ApplicationError

class GameError(ApplicationError):
    pass

class InvalidMoveError(GameError):
    def __init__(self, message="Invalid move"):
        super().__init__(message, extra={"code": "INVALID_MOVE"})

class NotYourTurnError(GameError):
    def __init__(self):
        super().__init__("Not your turn", extra={"code": "NOT_YOUR_TURN"})

class GameOverError(GameError):
    def __init__(self):
        super().__init__("Game is already over", extra={"code": "GAME_OVER"})
```

## Key Differences from Lichess

| Aspect | Lichess | Our Approach |
|--------|---------|--------------|
| **Concurrency** | Akka actors (message passing) | Channels consumers + Celery |
| **Database** | MongoDB (document store) | PostgreSQL (relational) |
| **Chess engine** | scalachess (Scala) | python-chess (Python) |
| **Templating** | scalatags (server-side) | React SPA (client-side) |
| **Session state** | In-memory actors | Redis + Django sessions |

## Performance Considerations

1. **Move validation**: python-chess is slower than scalachess; consider caching board states
2. **Database writes**: PostgreSQL transactions vs MongoDB's eventual consistency
3. **WebSocket scaling**: Use Redis channel layer for multi-instance deployment
4. **Engine analysis**: Queue via Celery to avoid blocking request threads
