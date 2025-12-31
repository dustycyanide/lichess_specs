---
title: TV & Broadcasts
category: content
status: draft
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
lichess_equivalent: lila (tv, relay modules)
dependencies:
  - django-channels
  - redis
  - celery
priority: low
---

# TV & Broadcasts

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md); Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md).

## Overview

This feature set includes three components:
1. **Lichess TV**: Live showcase of ongoing games
2. **Broadcasts**: Live relay of OTB (over-the-board) tournaments
3. **Blog System**: User-generated chess content

---

## Lichess TV

### Feature Summary

TV displays live games from the platform, automatically selecting and featuring the "best" games across different categories.

### Channel Structure

| Channel Type | Examples |
|--------------|----------|
| Time Controls | Bullet, Blitz, Rapid, Classical, Correspondence |
| Variants | Chess960, Crazyhouse, Atomic, Horde, King of the Hill, Racing Kings, Three-Check, Antichess |

Each channel displays the highest-rated game currently being played in that category.

### Featured Game Selection Algorithm

**Primary Factors (in order of priority):**
1. Average ELO rating of both players
2. Clock/time control settings
3. Game recency (slight preference for new games)

**Algorithm Behavior:**
- Remains on same game when possible ("sticky")
- Switches only when rating difference is significant
- Attempts to follow rematches
- ~5 second delay when switching games

### Tournament Featured Games

For tournaments, selection uses:
- `RankedPairing` to rank ongoing pairings
- Compares `bestRank.value` to current featured game
- Switches when candidate has better rank

---

## Django/React Implementation: TV

### Backend Architecture

```
backend/
  <project_slug>/
    tv/
      models.py
      services/
        featured_game.py    # Game selection algorithm
        channel_manager.py  # Channel state management
      consumers/
        tv_consumer.py      # WebSocket consumer
      apis/
        channels.py         # REST endpoints
```

> **Hacksoft Django Styleguide Notes**:
> - Services use keyword-only arguments after `*` (e.g., `def select_featured_game(*, channel: TVChannel, active_games: QuerySet)`)
> - All service functions have full type annotations
> - Use `@transaction.atomic` for services that perform multiple writes
> - Call `full_clean()` before `save()` on model instances

### Data Models

```python
class TVChannel(models.Model):
    """Represents a TV channel."""
    slug = models.SlugField(primary_key=True)  # e.g., "bullet", "blitz"
    name = models.CharField(max_length=50)
    channel_type = models.CharField(max_length=20)  # time_control, variant

    # Currently featured game
    featured_game = models.ForeignKey(
        'games.Game',
        null=True,
        on_delete=models.SET_NULL,
        related_name='tv_features'
    )
    featured_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['slug']


class TVAppearance(models.Model):
    """Track user TV time for profile stats."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE)
    channel = models.ForeignKey(TVChannel, on_delete=models.CASCADE)
    duration_seconds = models.IntegerField(default=0)
    appeared_at = models.DateTimeField(auto_now_add=True)

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        # Add custom validation here if needed

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### Featured Game Selection Service

```python
# services/featured_game.py
from typing import Optional
from django.db.models import QuerySet
from <project_slug>.games.models import Game

class FeaturedGameSelector:
    # Minimum rating difference to switch games
    SWITCH_THRESHOLD = 100

    def select_featured_game(
        self,
        *,
        channel: TVChannel,
        active_games: QuerySet[Game]
    ) -> Optional[Game]:
        """Select the best game to feature on a channel."""
        if not active_games.exists():
            return None

        # Score each game
        candidates = []
        for game in active_games:
            score = self._calculate_score(game, channel)
            candidates.append((game, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        best_game, best_score = candidates[0]

        # Sticky behavior: only switch if significantly better
        if channel.featured_game_id:
            current_score = self._calculate_score(
                channel.featured_game, channel
            )
            if best_score - current_score < self.SWITCH_THRESHOLD:
                return channel.featured_game

        return best_game

    def _calculate_score(self, game: Game, channel: TVChannel) -> int:
        """Calculate feature score for a game."""
        # Average rating is primary factor
        avg_rating = (game.white_rating + game.black_rating) // 2

        # Slight bonus for recently started games
        recency_bonus = 0
        if game.started_at:
            age_minutes = (timezone.now() - game.started_at).seconds // 60
            if age_minutes < 5:
                recency_bonus = 50

        return avg_rating + recency_bonus
```

### WebSocket Consumer

```python
# consumers/tv_consumer.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class TVConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.channel_slug = self.scope['url_route']['kwargs']['channel']
        self.group_name = f'tv_{self.channel_slug}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # Send current featured game
        await self.send_featured_game()

    async def tv_game_update(self, event):
        """Handle game move updates."""
        await self.send_json(event['data'])

    async def tv_game_switch(self, event):
        """Handle featured game switch."""
        await self.send_json({
            'type': 'switch',
            'game': event['game_data']
        })
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tv/channels` | GET | List all TV channels |
| `/api/tv/channels/{slug}` | GET | Get channel with current game |
| `/api/tv/channels/{slug}/stream` | WS | Stream game updates |

---

## Broadcasts & Relays

### Feature Summary

Broadcasts enable live streaming of OTB chess events. They function as auto-updating studies that pull moves from external PGN sources.

### Core Concepts

| Concept | Description |
|---------|-------------|
| Tournament | Container for multiple rounds |
| Round | Single round with multiple games |
| Game Source | PGN URL or Broadcaster App |
| Delay | Optional delay up to 60 minutes |

### Game Source Options

1. **Broadcaster App**: Desktop app monitoring PGN folder
2. **Single PGN URL**: Periodic fetch from hosted file
3. **Multiple PGN URLs**: Combined sources
4. **LiveChessCloud**: DGT board integration
5. **Platform Games**: By game ID or username

---

## Django/React Implementation: Broadcasts

### Backend Architecture

```
backend/
  <project_slug>/
    broadcasts/
      models.py
      services/
        pgn_fetcher.py      # Fetch and parse PGN sources
        relay_engine.py     # Push updates to viewers
        broadcaster_api.py  # Handle Broadcaster App uploads
      consumers/
        broadcast_consumer.py  # WebSocket for live updates
      tasks/
        fetch_pgn.py        # Celery tasks for periodic fetch
      apis/
        broadcasts.py       # CRUD endpoints
```

> **Hacksoft Django Styleguide Notes**:
> - Services use keyword-only arguments after `*` (e.g., `def fetch_round(*, round: BroadcastRound)`)
> - All service functions have full type annotations
> - Use `@transaction.atomic` for services that perform multiple writes
> - Call `full_clean()` before `save()` on model instances

### Data Models

```python
class BroadcastTournament(models.Model):
    """Container for a broadcast event."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    # Event details
    location = models.CharField(max_length=200, blank=True)
    time_control = models.CharField(max_length=50, blank=True)
    official_url = models.URLField(blank=True)

    # Settings
    timezone = models.CharField(max_length=50, default='UTC')
    is_official = models.BooleanField(default=False)  # Lichess-promoted

    # Ownership
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class BroadcastRound(models.Model):
    """A round within a broadcast tournament."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tournament = models.ForeignKey(
        BroadcastTournament,
        on_delete=models.CASCADE,
        related_name='rounds'
    )
    name = models.CharField(max_length=100)

    # Scheduling
    starts_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)

    # Source configuration
    source_type = models.CharField(max_length=20)  # url, broadcaster, lichess
    source_url = models.URLField(blank=True)

    # Settings
    delay_seconds = models.IntegerField(default=0)  # max 3600 (60 min)

    # Connection timing
    last_fetch_at = models.DateTimeField(null=True)
    last_sync_at = models.DateTimeField(null=True)


class BroadcastGame(models.Model):
    """A game within a broadcast round."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    round = models.ForeignKey(
        BroadcastRound,
        on_delete=models.CASCADE,
        related_name='games'
    )

    # Players
    white_name = models.CharField(max_length=100)
    black_name = models.CharField(max_length=100)
    white_title = models.CharField(max_length=10, blank=True)
    black_title = models.CharField(max_length=10, blank=True)
    white_rating = models.IntegerField(null=True)
    black_rating = models.IntegerField(null=True)

    # Game state
    pgn = models.TextField(blank=True)
    fen = models.CharField(max_length=100, blank=True)
    moves = models.JSONField(default=list)  # UCI moves
    result = models.CharField(max_length=10, blank=True)  # 1-0, 0-1, 1/2-1/2, *

    # Metadata
    board_number = models.IntegerField(default=1)

    class Meta:
        ordering = ['board_number']
```

### PGN Fetcher Service

```python
# services/pgn_fetcher.py
import httpx
import chess.pgn
from io import StringIO

class PGNFetcher:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_round(self, *, round: BroadcastRound) -> list[dict]:
        """Fetch and parse games from round source."""
        if round.source_type != 'url':
            return []

        response = await self.client.get(round.source_url)
        response.raise_for_status()

        return self._parse_pgn(response.text)

    def _parse_pgn(self, pgn_text: str) -> list[dict]:
        """Parse PGN text into game dictionaries."""
        games = []
        pgn_io = StringIO(pgn_text)

        while True:
            game = chess.pgn.read_game(pgn_io)
            if game is None:
                break

            games.append({
                'white_name': game.headers.get('White', 'Unknown'),
                'black_name': game.headers.get('Black', 'Unknown'),
                'white_rating': self._parse_rating(game.headers.get('WhiteElo')),
                'black_rating': self._parse_rating(game.headers.get('BlackElo')),
                'result': game.headers.get('Result', '*'),
                'pgn': str(game),
                'moves': [m.uci() for m in game.mainline_moves()],
                'fen': game.board().fen(),
            })

        return games

    def _parse_rating(self, rating_str: str) -> Optional[int]:
        try:
            return int(rating_str)
        except (TypeError, ValueError):
            return None
```

### Celery Task for Periodic Fetch

```python
# tasks/fetch_pgn.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def fetch_active_broadcasts():
    """Fetch updates for all active broadcasts."""
    now = timezone.now()

    # Rounds that should be active
    active_rounds = BroadcastRound.objects.filter(
        starts_at__lte=now + timedelta(hours=1),
        finished_at__isnull=True
    )

    for round in active_rounds:
        fetch_round_updates.delay(str(round.id))

@shared_task
def fetch_round_updates(round_id: str):
    """Fetch and process updates for a single round."""
    from .services.pgn_fetcher import PGNFetcher
    from .services.relay_engine import RelayEngine

    round = BroadcastRound.objects.get(id=round_id)
    fetcher = PGNFetcher()
    relay = RelayEngine()

    games = fetcher.fetch_round(round)
    relay.process_updates(round, games)
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/broadcasts` | GET | List broadcasts |
| `/api/broadcasts` | POST | Create broadcast |
| `/api/broadcasts/{id}` | GET | Get broadcast details |
| `/api/broadcasts/{id}/rounds` | GET | List rounds |
| `/api/broadcasts/{id}/rounds/{round_id}` | GET | Get round with games |
| `/api/broadcasts/{id}/rounds/{round_id}/pgn` | GET | Download PGN |
| `/api/broadcasts/{id}/rounds/{round_id}/push` | POST | Broadcaster App upload |

---

## Blog System

### Feature Summary

Community blog system for user-generated chess content.

### Content Guidelines

**Requirements:**
- Title image required
- Author must be 15+ years old
- Accurate content tags

**Prohibited:**
- Clickbait titles/images
- Copyrighted content without permission
- AI-generated content (discouraged)

### Embedding Support

| Content Type | How to Embed |
|--------------|--------------|
| Games | Paste game URL (supports move anchors) |
| Studies | Direct URL embedding |
| Images | Recommended: Unsplash, Creative Commons, Pixabay |

---

## Django/React Implementation: Blog

### Backend Architecture

```
backend/
  <project_slug>/
    blog/
      models.py
      services/
        content_parser.py   # Parse markdown, embed games
        moderation.py       # Content moderation
      apis/
        posts.py           # CRUD endpoints
```

> **Hacksoft Django Styleguide Notes**:
> - Services use keyword-only arguments after `*` (e.g., `def create_post(*, author: User, title: str, content: str)`)
> - All service functions have full type annotations
> - Use `@transaction.atomic` for services that perform multiple writes
> - Call `full_clean()` before `save()` on model instances

### Data Models

```python
class BlogPost(models.Model):
    """User blog post."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    author = models.ForeignKey('users.User', on_delete=models.CASCADE)

    # Content
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content_markdown = models.TextField()
    content_html = models.TextField(blank=True)  # Rendered

    # Media
    cover_image = models.URLField()

    # Metadata
    tags = models.JSONField(default=list)

    # Status
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moderation
    is_approved = models.BooleanField(default=True)

    class Meta:
        ordering = ['-published_at']
```

---

## Frontend Components

### TV Components

```
frontend/
  src/
    features/
      tv/
        components/
          tv-page.tsx          # Main TV page
          channel-selector.tsx  # Channel tabs
          featured-game.tsx     # Current game display
          mini-board.tsx        # Small board preview
        hooks/
          use-tv-stream.ts       # WebSocket hook
```

> **Bulletproof React Styleguide Notes**:
> - Use kebab-case for file names (e.g., `tv-page.tsx`, not `TVPage.tsx`)
> - No barrel files (`index.ts` re-exports) - use direct imports
> - Import components directly: `import { TVPage } from '@/features/tv/components/tv-page'`

### Broadcast Components

```
frontend/
  src/
    features/
      broadcasts/
        components/
          broadcast-list.tsx     # Tournament list
          broadcast-page.tsx     # Tournament view
          round-view.tsx         # Round with game list
          broadcast-game.tsx     # Single game display
          multi-board.tsx        # Multiple games view
        hooks/
          use-broadcast-stream.ts
```

> **Bulletproof React Styleguide Notes**:
> - Use kebab-case for file names (e.g., `broadcast-list.tsx`, not `BroadcastList.tsx`)
> - No barrel files (`index.ts` re-exports) - use direct imports
> - Import components directly: `import { BroadcastList } from '@/features/broadcasts/components/broadcast-list'`

### Blog Components

```
frontend/
  src/
    features/
      blog/
        components/
          blog-list.tsx         # Post list
          blog-post.tsx         # Single post view
          blog-editor.tsx       # Markdown editor
          game-embed.tsx        # Embedded game viewer
```

> **Bulletproof React Styleguide Notes**:
> - Use kebab-case for file names (e.g., `blog-list.tsx`, not `BlogList.tsx`)
> - No barrel files (`index.ts` re-exports) - use direct imports
> - Import components directly: `import { BlogList } from '@/features/blog/components/blog-list'`

---

## Implementation Phases

### Phase 1: TV (MVP)

1. Implement channel model and selection algorithm
2. WebSocket streaming of featured games
3. Basic TV page with channel switching
4. Integration with game module

### Phase 2: Broadcasts

1. Tournament and round models
2. PGN fetcher service
3. Celery tasks for periodic updates
4. Broadcast viewer UI

### Phase 3: Blog

1. Blog post model and CRUD
2. Markdown rendering with game embedding
3. Basic moderation workflow
4. Blog listing and reading pages

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `django-channels` | WebSocket support for live updates |
| `celery` | Background tasks for PGN fetching |
| `redis` | Channel layer, task broker |
| `python-chess` | PGN parsing |
| `markdown` | Blog content rendering |
| `httpx` | Async HTTP for PGN fetching |

---

## Success Metrics

### TV
- Featured game updates within 1 second of move
- Channel switch latency < 500ms
- User "Time on TV" tracking accurate

### Broadcasts
- PGN fetch interval: 5-30 seconds (configurable)
- Move relay latency < 10 seconds from source
- Support 100+ concurrent viewers per round

### Blog
- Post rendering < 200ms
- Game embed loading < 500ms

---

## References

- [Lichess Broadcast Help](https://lichess.org/broadcast/help)
- [Lichess Broadcaster App](https://lichess.org/broadcast/app)
- [broadcaster GitHub](https://github.com/lichess-org/broadcaster)
- [lila GitHub (TV module)](https://github.com/lichess-org/lila)
- [Blog Tips](https://lichess.org/page/blog-tips)
