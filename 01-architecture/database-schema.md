---
title: Database Schema Design
category: architecture
stack: PostgreSQL
styleguide: hacksoft-django-styleguide
status: draft
---

# Database Schema Design

This document maps Lichess's MongoDB document model to a PostgreSQL relational schema for our Django implementation.

> **Styleguide Reference**: Models follow the [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md). Models are kept **thin** (data structure + simple properties/validators only). All business logic lives in **Services**, not in model methods or `save()` overrides.

## Lichess → PostgreSQL Mapping Strategy

| Lichess (MongoDB) | Our Approach (PostgreSQL) |
|-------------------|---------------------------|
| Document embedding | Foreign keys + joins |
| Flexible schemas | Strict migrations |
| BSON fields | JSONB for flexible data |
| ObjectId | UUID primary keys |
| Denormalization | Normalized + materialized views |

## Core Models

### Users & Authentication

```python
# <project_slug>/users/models.py
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)

    # Profile
    bio = models.TextField(blank=True, max_length=400)
    country = models.CharField(max_length=2, blank=True)  # ISO 3166-1 alpha-2
    flair = models.CharField(max_length=50, blank=True)  # emoji/icon

    # Account status
    is_active = models.BooleanField(default=True)
    is_patron = models.BooleanField(default=False)  # Lichess Patron equivalent
    is_verified = models.BooleanField(default=False)  # Title verification

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    seen_at = models.DateTimeField(auto_now=True)

    # Play preferences (JSONB for flexibility)
    preferences = models.JSONField(default=dict)
    # Example: {"blindMode": false, "autoQueen": true, "premove": true}

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']


class Title(models.TextChoices):
    """FIDE and Lichess titles"""
    GM = 'GM', 'Grandmaster'
    IM = 'IM', 'International Master'
    FM = 'FM', 'FIDE Master'
    CM = 'CM', 'Candidate Master'
    NM = 'NM', 'National Master'
    WGM = 'WGM', 'Woman Grandmaster'
    WIM = 'WIM', 'Woman International Master'
    WFM = 'WFM', 'Woman FIDE Master'
    WCM = 'WCM', 'Woman Candidate Master'
    LM = 'LM', 'Lichess Master'
    BOT = 'BOT', 'Bot'


class UserTitle(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='title_record')
    title = models.CharField(max_length=4, choices=Title.choices)
    verified_at = models.DateTimeField(auto_now_add=True)
```

### Rating System (Glicko-2)

```python
# <project_slug>/users/models.py (continued)

class TimeControl(models.TextChoices):
    ULTRABULLET = 'ultraBullet', 'UltraBullet'
    BULLET = 'bullet', 'Bullet'
    BLITZ = 'blitz', 'Blitz'
    RAPID = 'rapid', 'Rapid'
    CLASSICAL = 'classical', 'Classical'
    CORRESPONDENCE = 'correspondence', 'Correspondence'


class Rating(models.Model):
    """
    Glicko-2 rating per user per time control.
    Equivalent to Lichess's perf stats.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    time_control = models.CharField(max_length=20, choices=TimeControl.choices)

    # Glicko-2 values
    rating = models.IntegerField(default=1500)
    deviation = models.FloatField(default=350.0)  # RD
    volatility = models.FloatField(default=0.06)  # σ

    # Stats
    games_count = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)

    # Provisional flag (RD > 110)
    is_provisional = models.BooleanField(default=True)

    # Peak rating tracking
    peak_rating = models.IntegerField(default=1500)
    peak_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'time_control']
        indexes = [
            models.Index(fields=['time_control', '-rating']),
        ]
```

### Games

```python
# <project_slug>/games/models.py
import uuid
from django.db import models
from <project_slug>.users.models import User, TimeControl

class GameStatus(models.TextChoices):
    CREATED = 'created', 'Created'
    STARTED = 'started', 'Started'
    ABORTED = 'aborted', 'Aborted'
    MATE = 'mate', 'Checkmate'
    RESIGN = 'resign', 'Resignation'
    STALEMATE = 'stalemate', 'Stalemate'
    TIMEOUT = 'timeout', 'Timeout'
    DRAW = 'draw', 'Draw'
    OUT_OF_TIME = 'outoftime', 'Out of Time'
    CHEAT = 'cheat', 'Cheat Detected'
    NO_START = 'noStart', 'No Start'
    UNKNOWN_FINISH = 'unknownFinish', 'Unknown'
    VARIANT_END = 'variantEnd', 'Variant End'


class GameResult(models.TextChoices):
    WHITE_WINS = '1-0', 'White wins'
    BLACK_WINS = '0-1', 'Black wins'
    DRAW = '1/2-1/2', 'Draw'
    ONGOING = '*', 'Ongoing'


class Game(models.Model):
    """
    Core game model. Equivalent to Lichess's Game document.
    """
    id = models.CharField(max_length=8, primary_key=True)  # Short ID like Lichess

    # Players
    white = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='games_as_white')
    black = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='games_as_black')

    # Ratings at game start (snapshot for history)
    white_rating = models.IntegerField(null=True)
    black_rating = models.IntegerField(null=True)
    white_rating_diff = models.IntegerField(null=True)  # +/- after game
    black_rating_diff = models.IntegerField(null=True)

    # Game state
    status = models.CharField(max_length=20, choices=GameStatus.choices, default=GameStatus.CREATED)
    result = models.CharField(max_length=10, choices=GameResult.choices, default=GameResult.ONGOING)
    winner = models.CharField(max_length=5, blank=True)  # 'white', 'black', or ''

    # Time control
    time_control = models.CharField(max_length=20, choices=TimeControl.choices)
    initial_time = models.IntegerField()  # seconds
    increment = models.IntegerField(default=0)  # seconds

    # Game data
    fen = models.CharField(max_length=100, default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    moves = models.TextField(blank=True)  # Space-separated UCI moves
    pgn = models.TextField(blank=True)

    # Flags
    rated = models.BooleanField(default=True)
    variant = models.CharField(max_length=20, default='standard')

    # Clocks (stored in centiseconds like Lichess)
    white_clock = models.IntegerField(null=True)  # remaining time in centiseconds
    black_clock = models.IntegerField(null=True)
    clock_history = models.JSONField(default=list)  # [[w_time, b_time], ...]

    # Metadata
    ply = models.IntegerField(default=0)  # half-moves played
    last_move_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)

    # Analysis (populated after game)
    analysis = models.JSONField(null=True, blank=True)
    # Example: [{"eval": 0.3, "best": "e2e4"}, {"eval": -0.1}, ...]

    class Meta:
        indexes = [
            models.Index(fields=['white', '-created_at']),
            models.Index(fields=['black', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['time_control', '-created_at']),
        ]

    # NOTE: No save() override per Hacksoft pattern
    # ID generation happens in the service layer:
    #
    # def game_create(...) -> Game:
    #     game = Game(id=_generate_game_id(), ...)
    #     game.full_clean()
    #     game.save()
    #     return game


# <project_slug>/games/services.py (ID generation helper)
def _generate_game_id() -> str:
    """Generate 8-char alphanumeric ID like Lichess."""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))
```

### Puzzles

```python
# <project_slug>/puzzles/models.py
import uuid
from django.db import models
from <project_slug>.users.models import User

class Puzzle(models.Model):
    """
    Tactical puzzle. Lichess has 4M+ puzzles from their database.
    """
    id = models.CharField(max_length=5, primary_key=True)  # Like Lichess puzzle IDs

    # Position
    fen = models.CharField(max_length=100)
    moves = models.CharField(max_length=200)  # Solution moves (space-separated UCI)

    # Metadata
    rating = models.IntegerField(db_index=True)
    rating_deviation = models.IntegerField(default=75)
    popularity = models.IntegerField(default=0)  # Vote score
    plays = models.IntegerField(default=0)

    # Classification
    themes = models.JSONField(default=list)
    # Example: ["middlegame", "short", "fork", "master"]

    opening_tags = models.JSONField(default=list, blank=True)
    # Example: ["Italian_Game", "Giuoco_Piano"]

    # Source game (optional)
    game_url = models.URLField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['rating']),
        ]


class PuzzleAttempt(models.Model):
    """Track user puzzle attempts for rating and history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puzzle_attempts')
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    solved = models.BooleanField()
    time_spent = models.IntegerField()  # milliseconds
    rating_before = models.IntegerField()
    rating_after = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
```

### Tournaments

```python
# <project_slug>/tournaments/models.py
import uuid
from django.db import models
from <project_slug>.users.models import User, TimeControl

class TournamentType(models.TextChoices):
    ARENA = 'arena', 'Arena'
    SWISS = 'swiss', 'Swiss'


class Tournament(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Type and settings
    type = models.CharField(max_length=10, choices=TournamentType.choices)
    time_control = models.CharField(max_length=20, choices=TimeControl.choices)
    initial_time = models.IntegerField()
    increment = models.IntegerField(default=0)

    # Schedule
    starts_at = models.DateTimeField()
    duration_minutes = models.IntegerField()  # For arena
    rounds = models.IntegerField(null=True)  # For Swiss

    # Entry requirements
    min_rating = models.IntegerField(null=True)
    max_rating = models.IntegerField(null=True)
    is_rated = models.BooleanField(default=True)

    # Status
    status = models.CharField(max_length=20, default='created')
    # created, started, finished

    # Organizer
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    team = models.ForeignKey('teams.Team', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class TournamentPlayer(models.Model):
    """Player participation in a tournament."""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='players')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Score
    score = models.FloatField(default=0)  # Arena: points, Swiss: match points
    tie_break = models.FloatField(default=0)  # Buchholz, performance, etc.

    # Stats
    games_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    performance = models.IntegerField(null=True)

    # Fire/berserk (Arena)
    fire = models.IntegerField(default=0)  # Win streak bonus
    berserk_count = models.IntegerField(default=0)

    # Rank (updated during tournament)
    rank = models.IntegerField(null=True)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['tournament', 'user']
        indexes = [
            models.Index(fields=['tournament', '-score', 'tie_break']),
        ]
```

### Teams / Clubs

```python
# <project_slug>/teams/models.py
import uuid
from django.db import models
from <project_slug>.users.models import User

class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    description = models.TextField(blank=True, max_length=2000)

    # Settings
    is_open = models.BooleanField(default=True)  # Anyone can join
    password = models.CharField(max_length=60, blank=True)  # For private teams

    # Leader
    leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='led_teams')

    # Stats (denormalized for performance)
    member_count = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)


class TeamMember(models.Model):
    class Role(models.TextChoices):
        MEMBER = 'member', 'Member'
        ADMIN = 'admin', 'Admin'
        LEADER = 'leader', 'Leader'

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['team', 'user']
```

### Studies

```python
# <project_slug>/studies/models.py
import uuid
from django.db import models
from <project_slug>.users.models import User

class Study(models.Model):
    """
    Collaborative analysis/lesson board.
    Lichess's study feature stores chapters with move trees.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    # Owner
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_studies')

    # Visibility
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        UNLISTED = 'unlisted', 'Unlisted'
        PRIVATE = 'private', 'Private'

    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)

    # Settings
    cloneable = models.BooleanField(default=True)
    chat = models.BooleanField(default=True)
    computer = models.BooleanField(default=True)

    # Stats
    likes = models.IntegerField(default=0)
    views = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Chapter(models.Model):
    """A chapter within a study, containing a move tree."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='chapters')

    name = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    # Initial position
    fen = models.CharField(max_length=100, default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    orientation = models.CharField(max_length=5, default='white')

    # Move tree stored as JSONB
    # Lichess uses a custom tree format; we can use a simplified version
    tree = models.JSONField(default=dict)
    # Example: {
    #   "fen": "...",
    #   "children": [
    #     {"move": "e4", "fen": "...", "comment": "Best move!", "children": [...]}
    #   ]
    # }

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
```

## Database Indexes Strategy

```python
# Recommended indexes beyond model definitions

# For leaderboards
CREATE INDEX users_rating_bullet_idx ON users_rating (rating DESC) WHERE time_control = 'bullet';
CREATE INDEX users_rating_blitz_idx ON users_rating (rating DESC) WHERE time_control = 'blitz';

# For game search
CREATE INDEX games_players_idx ON games_game USING GIN ((ARRAY[white_id, black_id]));

# For full-text search on usernames
CREATE INDEX users_username_trgm_idx ON users_user USING GIN (username gin_trgm_ops);
```

## Key Design Decisions

### Short Game IDs

Like Lichess, we use 8-character alphanumeric IDs for games (not UUIDs). This makes URLs cleaner and is sufficient for uniqueness.

### Clock History as JSONB

Storing clock times per move as JSONB array allows efficient storage while supporting replay functionality.

### Move Storage

Moves stored as space-separated UCI strings (e.g., `"e2e4 e7e5 g1f3"`) is compact and easily parsed. PGN generated on-demand.

### Analysis as JSONB

Per-move engine evaluations stored as JSONB array, populated asynchronously after game completion.

### Denormalized Stats

Some stats (like `Team.member_count`) are denormalized for read performance. Per Hacksoft styleguide, these are updated via **services** (not signals) or periodic Celery tasks:

```python
# <project_slug>/teams/services.py
from django.db import transaction
from <project_slug>.teams.models import Team, TeamMember


@transaction.atomic
def team_member_add(*, team: Team, user: User) -> TeamMember:
    """Add a member to a team and update denormalized count."""
    member = TeamMember(team=team, user=user)
    member.full_clean()
    member.save()

    # Update denormalized count in same transaction
    team.member_count = team.members.count()
    team.save(update_fields=['member_count'])

    return member
```

## Migration from MongoDB Mindset

| MongoDB Pattern | PostgreSQL Equivalent |
|-----------------|----------------------|
| Embedded documents | Separate tables with FK |
| Array of subdocs | JSONB or junction table |
| Schemaless flexibility | JSONB columns for dynamic fields |
| ObjectId references | UUID or integer FK |
| `$lookup` aggregation | SQL JOINs |
| TTL indexes | `pg_cron` + delete jobs |
