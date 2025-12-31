---
title: API Design
category: api
reference: https://lichess.org/api
styleguide: hacksoft-django-styleguide
status: draft
linear_ticket: DJA-49
---

# API Design

> RESTful API architecture with streaming support for Django/React chess platform

> **Styleguide Reference**: This API follows the [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) API patterns: function-based views wrapped in `APIView` classes, inline `InputSerializer`/`OutputSerializer`, and calls to services/selectors.

---

## Overview

This document specifies the API design for our Lichess clone, mapping Lichess's API patterns to Django REST Framework with Django Channels for real-time features.

### Design Principles

1. **REST for CRUD, WebSockets for Real-time**: Standard REST endpoints for resources; WebSockets for live game data
2. **Streaming for Large Exports**: NDJSON streaming for bulk data exports (games, puzzles)
3. **OAuth2 for Authentication**: Token-based auth with scope-based permissions
4. **Rate Limiting by Default**: Protect against abuse while enabling legitimate use

---

## Authentication

### OAuth2 with PKCE

Following Lichess's pattern, we'll implement OAuth2 with PKCE (Proof Key for Code Exchange) for third-party applications.

```python
# Django implementation: django-oauth-toolkit
OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 31536000,  # 1 year (like Lichess)
    'PKCE_REQUIRED': True,
    'PKCE_CHALLENGE_METHOD': 'S256',
    'REFRESH_TOKEN_EXPIRE_SECONDS': None,  # No refresh tokens (like Lichess)
}
```

### Personal Access Tokens

For scripts and single-user applications:

```
Authorization: Bearer {token}
```

- Generate from user settings page
- Long-lived (1 year)
- Revocable at any time
- Scoped permissions

### API Scopes

| Scope | Description |
|-------|-------------|
| `preference:read` | Read user preferences |
| `preference:write` | Write user preferences |
| `email:read` | Read user email address |
| `challenge:read` | Read incoming challenges |
| `challenge:write` | Create, accept, decline challenges |
| `study:read` | Read private studies |
| `study:write` | Create, update studies |
| `tournament:write` | Create and manage tournaments |
| `puzzle:read` | Read puzzle activity |
| `team:read` | Read private team information |
| `team:write` | Join and leave teams |
| `team:lead` | Manage team as leader |
| `follow:read` | Read followed players |
| `follow:write` | Follow and unfollow players |
| `msg:write` | Send private messages |
| `board:play` | Play games with Board API |
| `bot:play` | Play games with Bot API |

### Token Validation Endpoint

```
GET /api/token/test
Authorization: Bearer {token}

Response:
{
  "valid": true,
  "scopes": ["challenge:read", "challenge:write"],
  "user_id": "user123"
}
```

---

## API Structure

### Base URLs

```
Production:   https://api.yourchess.com
Development:  http://localhost:8000/api
WebSocket:    wss://ws.yourchess.com
```

### Response Formats

**Standard REST (JSON)**
```
Accept: application/json
Content-Type: application/json
```

**Streaming (NDJSON)**
```
Accept: application/x-ndjson
Content-Type: application/x-ndjson
```

**Game Export (PGN)**
```
Accept: application/x-chess-pgn
```

---

## Endpoint Categories

### Account & Users

#### Get Current User
```
GET /api/account
Authorization: Bearer {token}

Response:
{
  "id": "user123",
  "username": "ChessPlayer",
  "created_at": "2024-01-15T10:30:00Z",
  "ratings": {
    "bullet": {"rating": 1650, "rd": 45, "games": 523},
    "blitz": {"rating": 1580, "rd": 65, "games": 248},
    "rapid": {"rating": 1720, "rd": 80, "games": 156}
  },
  "profile": {
    "country": "US",
    "bio": "Chess enthusiast",
    "links": []
  },
  "preferences": {
    "theme": "brown",
    "piece_set": "cburnett"
  }
}
```

#### Get User Profile
```
GET /api/user/{username}

Response:
{
  "id": "user123",
  "username": "ChessPlayer",
  "online": true,
  "created_at": "2024-01-15T10:30:00Z",
  "ratings": {...},
  "count": {
    "games": 927,
    "wins": 465,
    "losses": 398,
    "draws": 64
  }
}
```

#### List Users (Batch)
```
POST /api/users
Content-Type: application/json

{
  "usernames": ["player1", "player2", "player3"]
}

Response: [User, User, User]
```

#### User Activity
```
GET /api/user/{username}/activity?max=10

Response (NDJSON stream):
{"type": "game", "game_id": "abc123", "timestamp": "2024-01-20T15:30:00Z"}
{"type": "puzzle", "puzzle_id": "xyz789", "timestamp": "2024-01-20T14:00:00Z"}
```

---

### Games

#### Get Game by ID
```
GET /api/game/{game_id}
Accept: application/json

Response:
{
  "id": "abc123",
  "rated": true,
  "variant": "standard",
  "speed": "blitz",
  "perf": "blitz",
  "created_at": "2024-01-20T15:30:00Z",
  "status": "mate",
  "players": {
    "white": {"user": {...}, "rating": 1650, "rating_diff": 8},
    "black": {"user": {...}, "rating": 1680, "rating_diff": -8}
  },
  "winner": "white",
  "moves": "e4 e5 Nf3 Nc6 Bb5 a6...",
  "clock": {"initial": 300, "increment": 3}
}
```

#### Export User Games
```
GET /api/games/user/{username}
Accept: application/x-ndjson

Query Parameters:
- max: int (default: 100)
- since: timestamp (ms)
- until: timestamp (ms)
- vs: username (filter by opponent)
- rated: boolean
- perf_type: bullet|blitz|rapid|classical|correspondence
- color: white|black
- analyzed: boolean
- ongoing: boolean

Response (NDJSON stream):
{"id":"game1","moves":"e4 e5...","result":"1-0",...}
{"id":"game2","moves":"d4 d5...","result":"0-1",...}
```

#### Export Games by IDs (Batch)
```
POST /api/games/export/_ids
Content-Type: text/plain

game_id_1,game_id_2,game_id_3

Limit: 300 games per request
```

#### Export to PGN
```
GET /api/game/{game_id}/pgn
Accept: application/x-chess-pgn

Query Parameters:
- moves: boolean (include moves)
- tags: boolean (include PGN tags)
- clocks: boolean (include clock comments)
- evals: boolean (include evaluations)
- opening: boolean (include opening name)

Response:
[Event "Rated Blitz game"]
[Site "YourChess"]
[Date "2024.01.20"]
[White "player1"]
[Black "player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 ...
```

#### Import PGN
```
POST /api/game/import
Content-Type: application/x-chess-pgn

[PGN content]

Response:
{
  "id": "imported_game_id",
  "url": "/game/imported_game_id"
}
```

---

### Challenges

#### Create Challenge
```
POST /api/challenge/{username}
Authorization: Bearer {token}

{
  "rated": true,
  "clock": {"limit": 300, "increment": 3},
  "color": "random",
  "variant": "standard"
}

Response:
{
  "id": "challenge_id",
  "status": "created",
  "challenger": {...},
  "dest_user": {...}
}
```

#### Accept Challenge
```
POST /api/challenge/{challenge_id}/accept
Authorization: Bearer {token}

Response:
{
  "game": {"id": "new_game_id", ...}
}
```

#### Decline Challenge
```
POST /api/challenge/{challenge_id}/decline
Authorization: Bearer {token}

{
  "reason": "later"  // generic|later|tooFast|tooSlow|timeControl|rated|casual|standard|variant|noBot|onlyBot
}
```

#### Create Open Challenge (Seek)
```
POST /api/challenge/open
Authorization: Bearer {token}

{
  "rated": true,
  "clock": {"limit": 300, "increment": 3},
  "rating_range": "1500-1700"
}
```

---

### Puzzles

#### Get Daily Puzzle
```
GET /api/puzzle/daily

Response:
{
  "puzzle": {
    "id": "puzzle123",
    "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
    "moves": ["f7f6", "h5f7"],
    "rating": 1523,
    "themes": ["mate", "short", "kingsideAttack"],
    "game_url": "/game/abc123#34"
  }
}
```

#### Get Random Puzzle
```
GET /api/puzzle/next
Authorization: Bearer {token}

Query Parameters:
- angle: opening|middlegame|endgame|mix
- difficulty: easiest|easier|normal|harder|hardest

Response: {puzzle object}
```

#### Submit Puzzle Solution
```
POST /api/puzzle/{puzzle_id}/complete
Authorization: Bearer {token}

{
  "win": true
}

Response:
{
  "rating_diff": 12,
  "new_rating": 1535
}
```

#### Get Puzzle Activity
```
GET /api/puzzle/activity
Authorization: Bearer {token}
Accept: application/x-ndjson

Response (NDJSON stream):
{"id":"puzzle1","win":true,"rating":1523,"date":"2024-01-20T15:00:00Z"}
{"id":"puzzle2","win":false,"rating":1650,"date":"2024-01-20T14:30:00Z"}
```

---

### Tournaments

#### List Current Tournaments
```
GET /api/tournament

Response:
{
  "created": [{tournament}],
  "started": [{tournament}],
  "finished": [{tournament}]
}
```

#### Get Tournament
```
GET /api/tournament/{tournament_id}

Response:
{
  "id": "tournament123",
  "name": "Weekly Blitz Arena",
  "clock": {"limit": 300, "increment": 0},
  "minutes": 90,
  "variant": "standard",
  "rated": true,
  "nb_players": 156,
  "status": "started",
  "starts_at": "2024-01-20T18:00:00Z",
  "standings": {...}
}
```

#### Create Tournament
```
POST /api/tournament
Authorization: Bearer {token}

{
  "name": "My Tournament",
  "clock_time": 3,
  "clock_increment": 2,
  "minutes": 60,
  "wait_minutes": 5,
  "variant": "standard",
  "rated": true,
  "berserkable": true,
  "description": "Tournament description"
}
```

#### Join Tournament
```
POST /api/tournament/{tournament_id}/join
Authorization: Bearer {token}
```

#### Stream Tournament
```
GET /api/tournament/{tournament_id}/stream
Accept: application/x-ndjson

Response (NDJSON stream):
{"type":"featured","game":{...}}
{"type":"standing","player":{...}}
```

---

### Studies

#### List User Studies
```
GET /api/study/user/{username}

Response:
[
  {
    "id": "study123",
    "name": "My Opening Repertoire",
    "chapters": 5,
    "created_at": "2024-01-15T10:00:00Z",
    "visibility": "public"
  }
]
```

#### Get Study
```
GET /api/study/{study_id}

Response:
{
  "id": "study123",
  "name": "My Opening Repertoire",
  "owner": {...},
  "chapters": [
    {"id": "ch1", "name": "Sicilian Defense", "pgn": "..."}
  ],
  "visibility": "public"
}
```

#### Export Study PGN
```
GET /api/study/{study_id}.pgn
Accept: application/x-chess-pgn
```

---

### Teams

#### Get Team
```
GET /api/team/{team_id}

Response:
{
  "id": "team123",
  "name": "Chess Club",
  "description": "...",
  "leader": {...},
  "nb_members": 156,
  "joined": true
}
```

#### Join Team
```
POST /api/team/{team_id}/join
Authorization: Bearer {token}
```

#### List Team Tournaments
```
GET /api/team/{team_id}/tournament
```

---

### Analysis

#### Cloud Evaluation
```
GET /api/cloud-eval?fen={fen}&multiPv=3

Response:
{
  "fen": "...",
  "depth": 40,
  "pvs": [
    {"moves": "e4 e5 Nf3", "cp": 35},
    {"moves": "d4 d5", "cp": 28}
  ]
}
```

#### Opening Explorer
```
GET /api/explorer/lichess?fen={fen}&speeds=blitz,rapid&ratings=1600,1800,2000

Response:
{
  "white": 45234,
  "draws": 12456,
  "black": 42890,
  "moves": [
    {"uci": "e2e4", "san": "e4", "white": 25000, "draws": 8000, "black": 22000}
  ],
  "top_games": [...]
}
```

#### Tablebase
```
GET /api/tablebase/standard?fen={fen}

Response:
{
  "category": "win",
  "dtz": 12,
  "dtm": 25,
  "moves": [
    {"uci": "e7e8q", "category": "win", "dtz": 11}
  ]
}
```

---

## Streaming API (WebSocket)

### Connection

```javascript
const ws = new WebSocket('wss://ws.yourchess.com/api/stream');
ws.send(JSON.stringify({type: 'auth', token: 'bearer_token'}));
```

### Event Stream

```
GET /api/stream/event
Authorization: Bearer {token}
Accept: application/x-ndjson

Response (NDJSON stream - keeps connection open):
{"type": "gameStart", "game": {...}}
{"type": "gameFinish", "game": {...}}
{"type": "challenge", "challenge": {...}}
{"type": "challengeDeclined", "challenge": {...}}
```

### Game Stream (Board API)

```
GET /api/board/game/stream/{game_id}
Authorization: Bearer {token}
Accept: application/x-ndjson

Response (NDJSON stream):
{"type": "gameFull", "id": "...", "state": {...}}
{"type": "gameState", "moves": "e4 e5 Nf3", "wtime": 298000, "btime": 295000}
{"type": "chatLine", "room": "player", "text": "Good game!"}
```

### Playing Moves

```
POST /api/board/game/{game_id}/move/{move}
Authorization: Bearer {token}

// move in UCI format: e2e4, e7e8q (promotion)
```

### Game Actions

```
POST /api/board/game/{game_id}/abort
POST /api/board/game/{game_id}/resign
POST /api/board/game/{game_id}/draw/yes    // offer or accept
POST /api/board/game/{game_id}/draw/no     // decline
POST /api/board/game/{game_id}/takeback/yes
POST /api/board/game/{game_id}/takeback/no
```

---

## Rate Limiting

### General Rules

1. **Sequential Requests**: One request at a time per client
2. **429 Handling**: Wait 60 seconds after receiving HTTP 429
3. **Authenticated vs Anonymous**: Authenticated requests receive higher limits

### Implementation

```python
# Django REST Framework throttling
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '300/minute',
        'burst': '10/second',
    }
}
```

### Response Headers

```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 287
X-RateLimit-Reset: 1705766400
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "not_found",
    "message": "Game not found",
    "details": {"game_id": "invalid123"}
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient scope) |
| 404 | Not Found |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

---

## Django Implementation Notes

### Hacksoft APIView Pattern

Following the Hacksoft styleguide, we use `APIView` with inline serializers and service/selector calls:

```python
# <project_slug>/games/apis.py
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from <project_slug>.games.services import game_create
from <project_slug>.games.selectors import game_get, game_list_for_user


class GameDetailApi(APIView):
    """Get a single game by ID."""

    class OutputSerializer(serializers.Serializer):
        id = serializers.CharField()
        fen = serializers.CharField()
        moves = serializers.CharField()
        status = serializers.CharField()
        white = serializers.DictField()
        black = serializers.DictField()

    def get(self, request, game_id):
        game = game_get(game_id=game_id)
        serializer = self.OutputSerializer(game)
        return Response(serializer.data)


class GameCreateApi(APIView):
    """Create a new game challenge."""

    class InputSerializer(serializers.Serializer):
        opponent_id = serializers.UUIDField()
        time_control = serializers.CharField()
        rated = serializers.BooleanField(default=True)
        color = serializers.ChoiceField(choices=['white', 'black', 'random'], default='random')

    class OutputSerializer(serializers.Serializer):
        game_id = serializers.CharField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        game = game_create(
            challenger=request.user,
            **serializer.validated_data
        )

        output = self.OutputSerializer({'game_id': str(game.id)})
        return Response(output.data, status=status.HTTP_201_CREATED)


class GameListApi(APIView):
    """List games for a user with filtering."""

    class FilterSerializer(serializers.Serializer):
        status = serializers.CharField(required=False)
        rated = serializers.BooleanField(required=False)
        perf_type = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.CharField()
        white = serializers.DictField()
        black = serializers.DictField()
        status = serializers.CharField()
        created_at = serializers.DateTimeField()

    def get(self, request, username):
        filters = self.FilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        games = game_list_for_user(
            username=username,
            **filters.validated_data
        )

        output = self.OutputSerializer(games, many=True)
        return Response(output.data)


class GamePgnExportApi(APIView):
    """Export game as PGN."""

    def get(self, request, game_id):
        from <project_slug>.games.selectors import game_get_pgn

        pgn = game_get_pgn(game_id=game_id)
        return Response(
            pgn,
            content_type='application/x-chess-pgn'
        )
```

### Streaming Responses

```python
# <project_slug>/games/apis.py
from django.http import StreamingHttpResponse
from rest_framework.views import APIView

from <project_slug>.games.selectors import game_list_for_user


class GameStreamApi(APIView):
    """Stream games for a user as NDJSON."""

    class OutputSerializer(serializers.Serializer):
        id = serializers.CharField()
        white = serializers.DictField()
        black = serializers.DictField()
        moves = serializers.CharField()
        status = serializers.CharField()

    def get(self, request, username):
        # Delegate to selector - never query models directly in APIs
        games = game_list_for_user(username=username)

        def generate():
            for game in games.iterator():
                yield json.dumps(self.OutputSerializer(game).data) + '\n'

        return StreamingHttpResponse(
            generate(),
            content_type='application/x-ndjson'
        )
```

### WebSocket Consumers

```python
class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        await self.channel_layer.group_add(
            f'game_{self.game_id}',
            self.channel_name
        )
        await self.accept()

        # Send initial game state
        game = await self.get_game()
        await self.send_json({
            'type': 'gameFull',
            'game': game
        })
```

---

## Related Documents

- [WebSocket Architecture](../01-architecture/websocket-architecture.md) - Real-time communication patterns
- [Backend Architecture](../01-architecture/backend-architecture.md) - Django structure
- [lichess_clones/RESEARCH.md](../lichess_clones/RESEARCH.md) - Lichess API research

---

*Document created: December 2025*
