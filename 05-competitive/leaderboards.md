---
title: Leaderboards
category: competitive
status: spec
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
dependencies: rating-system, user-authentication
lichess_equivalent: lila/modules/user/src/main/Ranking.scala
---

# Leaderboards

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md); Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md).

Leaderboards display top-rated players across different time controls and variants, with trophy systems for achievements.

## Overview

Leaderboards serve multiple purposes:
- **Competition**: Showcase top players in each category
- **Engagement**: Motivate players to maintain activity
- **Discovery**: Help players find strong opponents
- **Recognition**: Award trophies for achievements

---

## Rating Leaderboard Requirements

### Eligibility Criteria

To appear on a leaderboard, a player must meet **all** of the following:

| Requirement | Standard Chess | Variants |
|-------------|----------------|----------|
| Minimum rated games | 30 | 30 |
| Recent activity | Game within last 7 days | Game within last 7 days |
| Rating deviation (RD) | < 75 | < 65 |

### Rationale

- **30 games**: Ensures established, reliable rating
- **7-day activity**: Prevents inactive accounts from populating boards
- **RD threshold**: Ensures high confidence in rating accuracy

### Provisional Rating Thresholds

| RD Range | Status | Display |
|----------|--------|---------|
| RD ≥ 230 | New player | Hidden rating |
| 110 ≤ RD < 230 | Provisional | Rating with "?" |
| RD < 110 | Established | Full rating |

Takes approximately 10-20 games to establish rating, depending on opponent RDs.

---

## Leaderboard Categories

### Time Control Leaderboards

| Category | Time Control |
|----------|--------------|
| UltraBullet | < 30 seconds |
| Bullet | 30s - 3 min |
| Blitz | 3-8 min |
| Rapid | 8-25 min |
| Classical | > 25 min |

### Variant Leaderboards

- Chess960 (Fischer Random)
- Crazyhouse
- King of the Hill
- Three-check
- Antichess
- Atomic
- Horde
- Racing Kings

---

## Trophy System

### Leaderboard Position Trophies

| Position | Trophy | Retention Rule |
|----------|--------|----------------|
| #1 (Champion) | Gold crown | While maintaining position |
| Top 10 | Silver crown | While in top 10 |
| Top 50 | Bronze crown | While in top 50 |
| Top 100 | Ribbon | While in top 100 |

Trophies are **removed** if no rated game in that category within 2 weeks.

### Tournament Trophies

**Time-Based Tournament Leaders:**
- Yearly champion
- Monthly champion
- Weekly champion
- Daily champion

**Marathon Trophies:**
- Top 500: Blue globe trophy
- Top 100: Silver marathon trophy
- Top 50: Gold marathon trophy
- Top 10: Diamond marathon trophy
- Winner: Unique marathon crown

**Shield Trophies:**
- Winner holds unique shield trophy
- Must defend monthly or lose trophy
- One shield per time control/variant

---

## Django Implementation

### Models

```python
# <project_slug>/rankings/models.py

from django.db import models


class LeaderboardCategory(models.TextChoices):
    ULTRABULLET = 'ultrabullet', 'UltraBullet'
    BULLET = 'bullet', 'Bullet'
    BLITZ = 'blitz', 'Blitz'
    RAPID = 'rapid', 'Rapid'
    CLASSICAL = 'classical', 'Classical'
    CHESS960 = 'chess960', 'Chess960'
    CRAZYHOUSE = 'crazyhouse', 'Crazyhouse'
    KINGOFTHEHILL = 'kingofthehill', 'King of the Hill'
    THREECHECK = 'threecheck', 'Three-check'
    ANTICHESS = 'antichess', 'Antichess'
    ATOMIC = 'atomic', 'Atomic'
    HORDE = 'horde', 'Horde'
    RACINGKINGS = 'racingkings', 'Racing Kings'


class LeaderboardEntry(models.Model):
    """
    Cached leaderboard position for a player.
    Updated periodically via background task.
    """
    player = models.ForeignKey('users.User', on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=LeaderboardCategory.choices)
    rank = models.PositiveIntegerField()
    rating = models.PositiveIntegerField()
    rating_deviation = models.FloatField()
    games_played = models.PositiveIntegerField()
    last_game_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['player', 'category']
        indexes = [
            models.Index(fields=['category', 'rank']),
            models.Index(fields=['category', '-rating']),
        ]


class TrophyType(models.TextChoices):
    CHAMPION = 'champion', 'Champion (#1)'
    TOP_10 = 'top10', 'Top 10'
    TOP_50 = 'top50', 'Top 50'
    TOP_100 = 'top100', 'Top 100'
    MARATHON_WINNER = 'marathon_winner', 'Marathon Winner'
    MARATHON_TOP_10 = 'marathon_top10', 'Marathon Top 10'
    MARATHON_TOP_50 = 'marathon_top50', 'Marathon Top 50'
    MARATHON_TOP_100 = 'marathon_top100', 'Marathon Top 100'
    MARATHON_TOP_500 = 'marathon_top500', 'Marathon Top 500'
    SHIELD = 'shield', 'Shield Holder'


class Trophy(models.Model):
    """Player trophy/achievement."""
    player = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='trophies'
    )
    trophy_type = models.CharField(max_length=20, choices=TrophyType.choices)
    category = models.CharField(
        max_length=20,
        choices=LeaderboardCategory.choices,
        null=True,
        blank=True
    )
    tournament = models.ForeignKey(
        'tournaments.ArenaTournament',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    awarded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['player', 'is_active']),
            models.Index(fields=['trophy_type', 'category']),
        ]
```

### Services

```python
# <project_slug>/rankings/services.py

from datetime import timedelta
from django.db import transaction
from django.utils import timezone


# Leaderboard requirements
MIN_GAMES_STANDARD = 30
MIN_GAMES_VARIANT = 30
MAX_RD_STANDARD = 75
MAX_RD_VARIANT = 65
ACTIVITY_WINDOW_DAYS = 7
TROPHY_EXPIRY_DAYS = 14


@transaction.atomic
def leaderboard_rebuild(*, category: str) -> int:
    """
    Rebuild leaderboard for a category.
    Returns number of entries created.
    """
    from <project_slug>.rankings.models import LeaderboardEntry, LeaderboardCategory
    from <project_slug>.rankings.selectors import get_eligible_players

    # Clear existing entries for this category
    LeaderboardEntry.objects.filter(category=category).delete()

    # Get eligible players sorted by rating
    players = get_eligible_players(category=category)

    entries = []
    for rank, player_data in enumerate(players, start=1):
        entry = LeaderboardEntry(
            player_id=player_data['player_id'],
            category=category,
            rank=rank,
            rating=player_data['rating'],
            rating_deviation=player_data['rd'],
            games_played=player_data['games'],
            last_game_at=player_data['last_game_at'],
        )
        entries.append(entry)

    LeaderboardEntry.objects.bulk_create(entries)

    # Update trophies based on new rankings
    trophies_update_for_category(category=category)

    return len(entries)


@transaction.atomic
def trophies_update_for_category(*, category: str) -> None:
    """Update trophies for leaderboard positions."""
    from <project_slug>.rankings.models import LeaderboardEntry, Trophy, TrophyType

    entries = LeaderboardEntry.objects.filter(category=category).order_by('rank')[:100]

    # Deactivate old position trophies for this category
    Trophy.objects.filter(
        category=category,
        trophy_type__in=[
            TrophyType.CHAMPION,
            TrophyType.TOP_10,
            TrophyType.TOP_50,
            TrophyType.TOP_100,
        ],
        is_active=True,
    ).update(is_active=False)

    # Award new trophies
    for entry in entries:
        if entry.rank == 1:
            trophy_type = TrophyType.CHAMPION
        elif entry.rank <= 10:
            trophy_type = TrophyType.TOP_10
        elif entry.rank <= 50:
            trophy_type = TrophyType.TOP_50
        else:
            trophy_type = TrophyType.TOP_100

        trophy, created = Trophy.objects.get_or_create(
            player_id=entry.player_id,
            trophy_type=trophy_type,
            category=category,
            defaults={
                'is_active': True,
                'expires_at': timezone.now() + timedelta(days=TROPHY_EXPIRY_DAYS),
            }
        )
        if not created:
            trophy.is_active = True
            trophy.expires_at = timezone.now() + timedelta(days=TROPHY_EXPIRY_DAYS)
            trophy.full_clean()
            trophy.save(update_fields=['is_active', 'expires_at'])


@transaction.atomic
def trophy_award_for_tournament(
    *,
    tournament,
    player,
    position: int,
) -> Trophy:
    """Award trophy for tournament placement."""
    from <project_slug>.rankings.models import Trophy, TrophyType

    if tournament.is_marathon:
        if position == 1:
            trophy_type = TrophyType.MARATHON_WINNER
        elif position <= 10:
            trophy_type = TrophyType.MARATHON_TOP_10
        elif position <= 50:
            trophy_type = TrophyType.MARATHON_TOP_50
        elif position <= 100:
            trophy_type = TrophyType.MARATHON_TOP_100
        elif position <= 500:
            trophy_type = TrophyType.MARATHON_TOP_500
        else:
            return None
    elif tournament.is_shield:
        if position == 1:
            trophy_type = TrophyType.SHIELD
        else:
            return None
    else:
        return None

    trophy = Trophy(
        player=player,
        trophy_type=trophy_type,
        tournament=tournament,
        is_active=True,
    )

    if tournament.is_shield:
        # Shield expires after one month (next shield tournament)
        trophy.expires_at = timezone.now() + timedelta(days=32)

    trophy.full_clean()
    trophy.save()
    return trophy


def trophies_expire_inactive() -> int:
    """
    Expire trophies for players who haven't played recently.
    Run as periodic task.
    Returns number of trophies expired.
    """
    from <project_slug>.rankings.models import Trophy

    expired = Trophy.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now(),
    ).update(is_active=False)

    return expired
```

### Selectors

```python
# <project_slug>/rankings/selectors.py

from datetime import timedelta
from django.db.models import QuerySet
from django.utils import timezone


def get_eligible_players(*, category: str) -> list:
    """
    Get players eligible for leaderboard in a category.
    Returns list of dicts with player_id, rating, rd, games, last_game_at.
    """
    from <project_slug>.ratings.models import PlayerRating
    from <project_slug>.rankings.services import (
        MIN_GAMES_STANDARD,
        MAX_RD_STANDARD,
        MAX_RD_VARIANT,
        ACTIVITY_WINDOW_DAYS,
    )

    # Determine RD threshold based on category
    is_variant = category in [
        'chess960', 'crazyhouse', 'kingofthehill',
        'threecheck', 'antichess', 'atomic', 'horde', 'racingkings'
    ]
    max_rd = MAX_RD_VARIANT if is_variant else MAX_RD_STANDARD

    activity_cutoff = timezone.now() - timedelta(days=ACTIVITY_WINDOW_DAYS)

    eligible = (
        PlayerRating.objects
        .filter(
            time_control=category,
            games_played__gte=MIN_GAMES_STANDARD,
            deviation__lt=max_rd,
            last_game_at__gte=activity_cutoff,
        )
        .select_related('user')
        .order_by('-rating')
        .values('user_id', 'rating', 'deviation', 'games_played', 'last_game_at')
    )

    return [
        {
            'player_id': e['user_id'],
            'rating': e['rating'],
            'rd': e['deviation'],
            'games': e['games_played'],
            'last_game_at': e['last_game_at'],
        }
        for e in eligible
    ]


def get_leaderboard(*, category: str, limit: int = 100) -> QuerySet:
    """Get leaderboard entries for a category."""
    from <project_slug>.rankings.models import LeaderboardEntry

    return (
        LeaderboardEntry.objects
        .filter(category=category)
        .select_related('player')
        .order_by('rank')[:limit]
    )


def get_player_trophies(*, player) -> QuerySet:
    """Get active trophies for a player."""
    from <project_slug>.rankings.models import Trophy

    return (
        Trophy.objects
        .filter(player=player, is_active=True)
        .select_related('tournament')
        .order_by('-awarded_at')
    )


def get_player_rank(*, player, category: str) -> int | None:
    """Get player's current rank in a category, or None if not on leaderboard."""
    from <project_slug>.rankings.models import LeaderboardEntry

    try:
        entry = LeaderboardEntry.objects.get(player=player, category=category)
        return entry.rank
    except LeaderboardEntry.DoesNotExist:
        return None
```

### API Endpoints

```
GET  /api/leaderboard/                          # List all categories
GET  /api/leaderboard/{category}/               # Get leaderboard for category
GET  /api/leaderboard/{category}/top/{n}/       # Get top N players
GET  /api/users/{username}/rank/                # Get user's ranks across categories
GET  /api/users/{username}/trophies/            # Get user's trophies
```

### Background Tasks

```python
# <project_slug>/rankings/tasks.py

from celery import shared_task


@shared_task
def rebuild_all_leaderboards():
    """Rebuild all leaderboards. Run every 5 minutes."""
    from <project_slug>.rankings.models import LeaderboardCategory
    from <project_slug>.rankings.services import leaderboard_rebuild

    for category in LeaderboardCategory.values:
        leaderboard_rebuild(category=category)


@shared_task
def expire_inactive_trophies():
    """Expire trophies for inactive players. Run hourly."""
    from <project_slug>.rankings.services import trophies_expire_inactive

    trophies_expire_inactive()
```

---

## React Components

> **Note**: Following Bulletproof React conventions:
> - No barrel files (index.ts) - use direct imports
> - Kebab-case file names
> - Feature-based organization

```
src/features/leaderboards/
├── components/
│   ├── leaderboard-page.tsx        # Main leaderboard view
│   ├── leaderboard-table.tsx       # Ranked player table
│   ├── leaderboard-row.tsx         # Single player row
│   ├── category-tabs.tsx           # Time control/variant tabs
│   ├── trophy-display.tsx          # Trophy icon component
│   └── player-rank-badge.tsx       # Rank indicator badge
├── hooks/
│   ├── use-leaderboard.ts          # Leaderboard data fetching
│   └── use-player-trophies.ts      # Trophy fetching
├── api/
│   ├── get-leaderboard.ts          # Leaderboard query
│   └── get-player-trophies.ts      # Trophies query
└── types/
    └── index.ts                    # Leaderboard types
```

### API Hooks (TanStack Query Pattern)

```typescript
// src/features/leaderboards/api/get-leaderboard.ts

import { useQuery, queryOptions } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/lib/api-client';

// Schema
const leaderboardEntrySchema = z.object({
  rank: z.number(),
  player: z.object({
    id: z.string(),
    username: z.string(),
    title: z.string().nullable(),
  }),
  rating: z.number(),
  gamesPlayed: z.number(),
});

export type LeaderboardEntry = z.infer<typeof leaderboardEntrySchema>;

// Fetcher
export const getLeaderboard = async (category: string): Promise<LeaderboardEntry[]> => {
  const response = await api.get(`/leaderboard/${category}/`);
  return z.array(leaderboardEntrySchema).parse(response.data);
};

// Query options
export const getLeaderboardQueryOptions = (category: string) => {
  return queryOptions({
    queryKey: ['leaderboard', category],
    queryFn: () => getLeaderboard(category),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Hook
export const useLeaderboard = (category: string) => {
  return useQuery(getLeaderboardQueryOptions(category));
};
```

**Import example**:
```typescript
// Correct: Direct import
import { useLeaderboard } from '@/features/leaderboards/api/get-leaderboard';
import { LeaderboardTable } from '@/features/leaderboards/components/leaderboard-table';
```

---

## Caching Strategy

### Redis Cache Structure

```
leaderboard:{category}:top100     # Cached top 100 entries (5 min TTL)
leaderboard:{category}:updated_at # Last rebuild timestamp
player:{id}:ranks                 # Player's ranks across categories
player:{id}:trophies              # Player's active trophies
```

### Cache Invalidation

- **Leaderboard rebuild**: Every 5 minutes via background task
- **Trophy changes**: Invalidate player's trophy cache
- **Game completion**: Invalidate player's rank cache if near threshold

---

## MVP Scope

### Phase 1: Core Leaderboards
- Rating leaderboards for major time controls (bullet, blitz, rapid)
- Basic eligibility criteria (games played, recent activity)
- Top 100 display per category

### Phase 2: Trophies
- Leaderboard position trophies (Champion, Top 10, Top 50, Top 100)
- Trophy display on user profiles
- Trophy expiration for inactivity

### Phase 3: Extended
- Variant leaderboards
- Marathon trophies
- Shield trophies
- Tournament leaderboard (best performers)

### Phase 4: Advanced
- Weekly/monthly/yearly leaderboards
- Country leaderboards
- Historical rankings

---

## Sources

- [Lichess Forum - Leaderboard Requirements](https://lichess.org/forum/general-chess-discussion/leaderboard-requirements)
- [Lichess Forum - All Trophies](https://lichess.org/forum/general-chess-discussion/all-the-trophies-in-lichess)
- [Lichess Tournament Leaderboard](https://lichess.org/tournament/leaderboard)
- [Lichess GitHub - Ranking.scala](https://github.com/lichess-org/lila/blob/master/modules/user/src/main/Ranking.scala)
