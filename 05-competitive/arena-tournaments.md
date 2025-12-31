---
title: Arena Tournaments
category: competitive
status: spec
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
dependencies: websockets, rating-system, game-engine
lichess_equivalent: lila/modules/tournament
---

# Arena Tournaments

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md); Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md).

Arena is the primary tournament format on Lichess, designed for continuous play over a set duration with dynamic scoring.

## Overview

Arena tournaments differ from traditional chess tournaments:
- **Duration-based**: Run for a fixed time (1 hour, 2 hours, 24-hour marathons)
- **Continuous play**: Players join/leave freely during the tournament
- **Immediate pairing**: After finishing a game, players are instantly re-paired
- **No fixed rounds**: Unlike Swiss, no predetermined number of rounds
- **Open participation**: Anyone can join (some may have rating restrictions)

---

## Scoring System

### Base Points

| Result | Normal | On Streak | With Berserk | Berserk + Streak |
|--------|--------|-----------|--------------|------------------|
| Win    | 2      | 4         | 3            | 5                |
| Draw   | 1      | 2         | 1            | 2                |
| Loss   | 0      | 0         | 0            | 0                |

### Berserk Mode

Players can sacrifice half their clock time for an extra tournament point on a win.

**Rules:**
- Requires at least 7 moves to be played for the bonus to apply
- Cancels increment (except 1+2 format which becomes 1+0)
- Not available in zero-increment games (0+1, 0+2)
- Strategic risk/reward tradeoff

### Winning Streaks (Fire)

Consecutive wins trigger double points:
- Streak activates after 2 consecutive wins
- All subsequent wins earn double points
- Streak continues until the player fails to win
- Draws during a streak still award streak-enhanced points (2 instead of 1)

### Draw Restrictions

To prevent farming and quick draws:
- Draws within first 10 moves award no points
- Consecutive draws: only first draw awards points (unless 30+ moves)
- Draw streaks can only be broken by wins, not losses

---

## Pairing Algorithm

Arena matchmaking uses a **minimum weight matching algorithm** based on Edmonds' Blossom algorithm.

### Pairing Formula

The edge weight (pair score) between players a and b:

```
pairScore(a, b) = abs(a.rank - b.rank) * rankFactor(a, b) + abs(a.rating - b.rating)^2
```

### Rank Factor Formula

```
rankFactor = 300 + 1700 * (maxRank - min(a.rank, b.rank)) / maxRank
```

This creates dynamic weighting where:
- **Top-ranked players**: ~2000 weight (prioritizing good pairings at top)
- **Bottom-ranked players**: ~300 weight (looser pairing constraints)

### Pairing Behavior

1. **Tournament Start**: Players paired by rating (no scores yet)
2. **During Tournament**: Players paired by current ranking
3. **Rematch Avoidance**: Tracks last opponents to prevent immediate rematches
4. **Color Balance**: Tracks color history to alternate white/black
5. **Wait Time**: Pairing range extends as player waits longer

### Implementation Tiers

From Lichess `PairingSystem.scala`:
1. **Initial pairings**: Simple sequential with random color
2. **Best pairings**: AntmaPairing algorithm for up to 100 players
3. **Proximity pairings**: For overflow players beyond 100

---

## Performance Rating (Tiebreaker)

### Formula

Tournament Performance Rating (TPR) breaks ties when players have identical points:

```
TPR = Average_Opponent_Rating + (Points_Ratio - 0.5) * 1000
```

### Per-Game Calculation

| Result | Performance Delta |
|--------|-------------------|
| Win    | opponent_rating + 500 |
| Draw   | opponent_rating |
| Loss   | opponent_rating - 500 |

The mean of all per-game performance ratings determines the tiebreaker.

### Alternative Expression

```
PERF = RO - 500 + 1000 * RATIO
```

Where RO = average opponent rating, RATIO = points / total possible points

---

## Tournament Lifecycle

### Pre-Tournament
1. Tournament created with time control, duration, start time
2. Players can register in advance
3. Optional: rating restrictions, team restrictions

### During Tournament
1. **Start countdown**: Tournament starts at scheduled time
2. **First move countdown**: ~15-30 seconds to make first move or forfeit
3. **Pairing loop**: Complete game → return to lobby → immediate re-pair
4. **Live leaderboard**: Rankings update in real-time
5. **Pause/Withdraw**: Players can pause (with cooldown) or leave

### Tournament End
1. When countdown reaches zero, rankings freeze
2. Games in progress finish but don't affect final standings
3. Tiebreaker: Tournament performance rating

---

## Shield Tournaments

Monthly Arena events where winners receive unique profile trophies.

### Mechanics

- Winner receives unique shield trophy on their profile
- Trophy held for one month until next Shield tournament
- Must defend in next month's event or lose trophy

### Available Shield Types

**Standard Time Controls:**
- Bullet, SuperBlitz, Blitz, Rapid, Classical
- HyperBullet, UltraBullet

**Variants:**
- Chess960, Crazyhouse, King of the Hill
- Racing Kings, Antichess, Atomic, Horde, Three-check

---

## Team Battles

Arena-format tournaments where teams compete against each other.

### Key Mechanics

- **Inter-team pairing only**: Never paired with teammates
- **Top N scoring**: Only top N player scores count for team
- **N = configurable**: Creator sets number of "leaders"
- **Protection**: Lower-rated players cannot hurt team score

### Team Scoring

```
Team Score = Sum of top N individual player scores
```

### Tiebreaker

Average performance rating of team leaders (higher wins).

---

## Marathon Tournaments

24-hour continuous Arena tournaments with seasonal themes.

### Time Controls by Season

| Season | Time Control |
|--------|-------------|
| Spring | 2+0 or 5+0  |
| Summer | varies      |
| Autumn | 3+2         |
| Winter | 5+3         |

### Trophies

- Top 500 receive unique marathon trophy
- Points threshold varies (e.g., 185-217 for top 500)

---

## Django Implementation

### Models

```python
# <project_slug>/tournaments/models.py

from django.db import models


class TournamentStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Scheduled'
    RUNNING = 'running', 'Running'
    FINISHED = 'finished', 'Finished'
    CANCELLED = 'cancelled', 'Cancelled'


class ArenaTournament(models.Model):
    name = models.CharField(max_length=255)
    time_control = models.ForeignKey('games.TimeControl', on_delete=models.CASCADE)
    duration_minutes = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=TournamentStatus.choices,
        default=TournamentStatus.SCHEDULED
    )
    min_rating = models.PositiveIntegerField(null=True, blank=True)
    max_rating = models.PositiveIntegerField(null=True, blank=True)
    team = models.ForeignKey(
        'teams.Team',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    is_shield = models.BooleanField(default=False)
    is_marathon = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']


class ArenaParticipant(models.Model):
    tournament = models.ForeignKey(
        ArenaTournament,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    player = models.ForeignKey('users.User', on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    performance_sum = models.IntegerField(default=0)
    games_played = models.PositiveIntegerField(default=0)
    streak = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    last_opponent = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    last_color = models.CharField(max_length=5, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['tournament', 'player']
        ordering = ['-score', '-performance_sum']

    @property
    def performance(self) -> int:
        if self.games_played == 0:
            return 0
        return self.performance_sum // self.games_played

    @property
    def on_streak(self) -> bool:
        return self.streak >= 2


class ArenaGame(models.Model):
    tournament = models.ForeignKey(
        ArenaTournament,
        on_delete=models.CASCADE,
        related_name='arena_games'
    )
    game = models.OneToOneField('games.Game', on_delete=models.CASCADE)
    white_participant = models.ForeignKey(
        ArenaParticipant,
        on_delete=models.CASCADE,
        related_name='white_games'
    )
    black_participant = models.ForeignKey(
        ArenaParticipant,
        on_delete=models.CASCADE,
        related_name='black_games'
    )
    white_berserk = models.BooleanField(default=False)
    black_berserk = models.BooleanField(default=False)
    white_score = models.PositiveIntegerField(default=0)
    black_score = models.PositiveIntegerField(default=0)
    counted = models.BooleanField(default=True)
```

### Services

```python
# <project_slug>/tournaments/services/arena.py

from django.db import transaction
from django.utils import timezone


def calculate_game_score(
    *,
    result: str,
    on_streak: bool,
    berserked: bool,
    moves_played: int = 10,
) -> int:
    """Calculate points for a single arena game."""
    base_scores = {'win': 2, 'draw': 1, 'loss': 0}
    base = base_scores[result]

    if base == 0:
        return 0

    if on_streak:
        base *= 2

    if berserked and result == 'win' and moves_played >= 7:
        base += 1

    return base


def calculate_performance_delta(
    *,
    result: str,
    opponent_rating: int,
) -> int:
    """Calculate performance rating contribution for a single game."""
    deltas = {'win': 500, 'draw': 0, 'loss': -500}
    return opponent_rating + deltas[result]


@transaction.atomic
def update_participant_after_game(
    *,
    participant,
    result: str,
    opponent_rating: int,
    berserked: bool,
    moves_played: int,
) -> int:
    """Update participant stats after a game. Returns points earned."""
    score = calculate_game_score(
        result=result,
        on_streak=participant.on_streak,
        berserked=berserked,
        moves_played=moves_played,
    )

    if result == 'win':
        participant.streak += 1
    else:
        participant.streak = 0

    participant.score += score
    participant.games_played += 1
    participant.performance_sum += calculate_performance_delta(
        result=result,
        opponent_rating=opponent_rating,
    )

    participant.full_clean()
    participant.save(update_fields=[
        'score', 'streak', 'games_played', 'performance_sum'
    ])

    return score


def calculate_pair_score(
    *,
    a,
    b,
    max_rank: int,
) -> float:
    """
    Calculate pairing weight between two players.
    Lower score = better pairing.
    """
    a_rank = get_participant_rank(participant=a)
    b_rank = get_participant_rank(participant=b)

    min_rank = min(a_rank, b_rank)
    rank_factor = 300 + 1700 * (max_rank - min_rank) / max_rank

    rank_diff = abs(a_rank - b_rank)
    rating_diff = abs(a.player.rating - b.player.rating)

    return rank_diff * rank_factor + (rating_diff ** 2)


def can_pair(*, a, b) -> bool:
    """Check if two participants can be paired."""
    if a.last_opponent_id == b.player_id:
        return False
    if b.last_opponent_id == a.player_id:
        return False
    if not a.is_active or a.is_paused:
        return False
    if not b.is_active or b.is_paused:
        return False
    return True
```

### Selectors

```python
# <project_slug>/tournaments/selectors/arena.py

from django.db.models import QuerySet


def get_arena_standings(*, tournament) -> QuerySet:
    """Get tournament standings ordered by score and performance."""
    from <project_slug>.tournaments.models import ArenaParticipant

    return (
        ArenaParticipant.objects
        .filter(tournament=tournament)
        .select_related('player')
        .order_by('-score', '-performance_sum', 'joined_at')
    )


def get_active_participants(*, tournament) -> QuerySet:
    """Get participants ready to be paired."""
    from <project_slug>.tournaments.models import ArenaParticipant

    return (
        ArenaParticipant.objects
        .filter(
            tournament=tournament,
            is_active=True,
            is_paused=False,
        )
        .select_related('player')
    )


def get_participant_rank(*, participant) -> int:
    """Get current rank of a participant (1-indexed)."""
    from <project_slug>.tournaments.models import ArenaParticipant

    return (
        ArenaParticipant.objects
        .filter(
            tournament=participant.tournament,
            score__gt=participant.score,
        )
        .count() + 1
    )
```

### API Endpoints

```
GET  /api/tournaments/arena/                    # List arena tournaments
POST /api/tournaments/arena/                    # Create tournament
GET  /api/tournaments/arena/{id}/               # Tournament details
POST /api/tournaments/arena/{id}/join/          # Join tournament
POST /api/tournaments/arena/{id}/withdraw/      # Leave tournament
POST /api/tournaments/arena/{id}/pause/         # Pause participation
GET  /api/tournaments/arena/{id}/standings/     # Live standings
GET  /api/tournaments/arena/{id}/games/         # Recent games
WS   /ws/tournaments/arena/{id}/                # Real-time updates
```

### WebSocket Events

```python
# Outbound events (server → client)
{
    "type": "standings_update",
    "standings": [
        {"player_id": 1, "username": "player1", "score": 24, "rank": 1, "streak": 3}
    ]
}

{
    "type": "pairing",
    "game_id": "abc123",
    "color": "white",
    "opponent": {"id": 2, "username": "opponent", "rating": 1800}
}

{
    "type": "game_result",
    "game_id": "abc123",
    "your_score": 4,
    "opponent_score": 0,
    "new_total": 28
}

{
    "type": "tournament_end",
    "final_standings": [...]
}

# Inbound events (client → server)
{"type": "ready"}    # Player ready for next game
{"type": "berserk"}  # Activate berserk for current game
{"type": "pause"}    # Pause participation
```

---

## React Components

> **Note**: Following Bulletproof React conventions:
> - No barrel files (index.ts) - use direct imports
> - Kebab-case file names (e.g., `arena-lobby.tsx`)
> - Feature-based organization

```
src/features/tournaments/
├── components/
│   ├── arena-lobby.tsx            # Main tournament view
│   ├── arena-standings.tsx        # Live leaderboard
│   ├── arena-game-wrapper.tsx     # In-tournament game wrapper
│   ├── berserk-button.tsx         # Berserk activation
│   ├── streak-indicator.tsx       # Fire/streak display
│   ├── tournament-clock.tsx       # Time remaining
│   ├── participant-row.tsx        # Single standings row
│   └── pairing-notification.tsx   # New game notification
├── hooks/
│   ├── use-arena-tournament.ts    # Tournament state
│   ├── use-arena-pairing.ts       # Pairing logic
│   └── use-arena-websocket.ts     # WebSocket connection
└── api/
    └── arena-api.ts               # API calls
```

**Import example** (direct imports, no barrel files):
```typescript
// Correct: Direct import
import { ArenaLobby } from '@/features/tournaments/components/arena-lobby';
import { useArenaTournament } from '@/features/tournaments/hooks/use-arena-tournament';

// Incorrect: Barrel file import (do not use)
// import { ArenaLobby } from '@/features/tournaments';
```

---

## MVP Scope

### Phase 1: Core Arena
- Basic tournament creation with time controls
- Player join/withdraw
- Immediate pairing (simplified algorithm)
- Standard scoring (no berserk)
- Live standings via WebSocket

### Phase 2: Enhanced Features
- Berserk mode
- Streak tracking with visual indicators
- Draw restrictions
- Tournament performance tiebreaker
- Pause functionality

### Phase 3: Advanced
- Team-restricted tournaments
- Rating-restricted tournaments
- Optimal pairing algorithm (Blossom)
- Arena shields (titles for winners)

### Phase 4: Special Events
- Team battles
- Marathon tournaments (24hr)
- Shield tournaments with trophies

---

## Sources

- [Lichess Arena Tournament FAQ](https://lichess.org/tournament/help)
- [Lichess Forum - Scoring in Arena Tournament](https://lichess.org/forum/general-chess-discussion/scoring-in-arena-tournament)
- [Lichess Forum - Arena Pairing Algorithm](https://lichess.org/forum/general-chess-discussion/high-level-descriptiion-of-the-matchmaking-algorithm)
- [Lichess Forum - Performance Rating](https://lichess.org/forum/general-chess-discussion/how-is-performance-calculated-in-tournaments-)
- [Lichess GitHub - PairingSystem.scala](https://github.com/lichess-org/lila/blob/master/modules/tournament/src/main/arena/PairingSystem.scala)
- [Lichess Team Battle FAQ](https://lichess.org/page/team-battle-faq)
