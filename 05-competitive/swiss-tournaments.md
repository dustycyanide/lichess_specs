---
title: Swiss Tournaments
category: competitive
status: spec
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
dependencies: websockets, rating-system, game-engine, teams
lichess_equivalent: lila/modules/swiss
---

# Swiss Tournaments

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md); Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md).

Swiss is a structured tournament format where all participants play the same number of games, with pairings based on current standings each round.

## Overview

Swiss tournaments on Lichess differ from Arena:
- **Round-based**: Fixed number of rounds, all players play same number of games
- **Structured pairings**: Each round pairs players with similar scores
- **No rematches**: Players can only face each other once
- **Team-required**: Must be hosted by a team (ensures player commitment)
- **Punctuality required**: Players must be present for round start

---

## Core Rules

### Team Requirement

Swiss tournaments require team membership:
- Tournaments are created and hosted by teams
- Players must be team members to participate
- Designed for clubs and official tournament settings

### Byes

When odd number of players or pairing impossible:
- **Full bye**: 1 point when pairing system can't find opponent
- **Half bye**: 0.5 points for late-joining players
- Late joiners receive a single half-point bye regardless of rounds missed

---

## Dutch Pairing System

Lichess uses the **bbpPairings** library implementing the FIDE Dutch system.

### How Dutch Pairing Works

1. **Score grouping**: Players grouped by current points (score brackets)
2. **Halving**: Each score group split into upper/lower half by starting rank (rating)
3. **Cross-pairing**: Upper half paired against lower half
4. **Color balance**: System balances white/black games

Example with 8 players in a score group:
- Upper half: Players 1, 2, 3, 4
- Lower half: Players 5, 6, 7, 8
- Pairings: 1v5, 2v6, 3v7, 4v8

### Time Complexity

```
O(n^3 * s * (d + s) * log n)
```

Where:
- n = largest player ID
- s = number of occupied score groups
- d = distinct score differences

### FIDE Absolute Constraints

These constraints **cannot** be violated:
1. Two players cannot meet more than once
2. Color difference must stay between -2 and +2
3. No player receives same color 3 times in row

### Color Balance Rules

FIDE-compliant color allocation:
- Difference between white and black games: max +2 or -2
- No player receives same color three times consecutively
- System alternates colors when possible
- May only be relaxed in final round

### Floaters

When perfect pairing within a score group isn't possible:
- **Downfloat**: Player paired with lower score group
- **Upfloat**: Opponent of downfloating player
- Algorithm minimizes number of floaters

---

## Advanced Pairing Features

### Forbidden Pairings

Tournament creators can specify player pairs who must not play each other:
- Use case: siblings, schoolmates in scholastic events
- Entered as list of username pairs
- System treats as absolute constraint

### Accelerated Pairings

Used in large tournaments to quickly separate top players:
- Top half players get 1 virtual point for pairing in rounds 1-2
- Effect: top quarter plays second quarter; third plays fourth
- Virtual points removed after accelerated rounds

**Methods:**
- US Chess Variation 28R2
- FIDE BAM (Baku Acceleration Method)

---

## Special Rules

### Early Draw Prevention

- Draws before move 30 are **not allowed**
- Prevents pre-arranged quick draws
- Cannot be bypassed via threefold repetition (must play on)

### No-Show Handling

1. Player's clock ticks, they flag, lose the game
2. System auto-withdraws player to prevent further losses
3. Player can re-join at any time
4. No-show players temporarily banned from joining new Swiss events
5. Creator can override this ban

### Late Joining

- Players can join until more than half the rounds have started
- 11-round Swiss: can join before round 6
- 12-round Swiss: can join before round 7
- Late joiners get single half-point bye

### Tournament Ending

- Ends when all scheduled rounds are complete
- OR when all possible pairings have been played
- Useful for simulating round-robin with high round count

---

## Scoring

### Standard Scoring

| Result   | Points |
|----------|--------|
| Win      | 1      |
| Draw     | 0.5    |
| Loss     | 0      |
| Full Bye | 1      |
| Half Bye | 0.5    |

### Tiebreakers

When players have equal points, tiebreakers in order:

**1. Buchholz Score:**
- Sum of opponents' scores
- Higher = played stronger opposition

**2. Sonneborn-Berger Score:**
- Sum of: scores of beaten opponents + half scores of drawn opponents
- Rewards beating stronger opponents

**3. Progressive Score:**
- Cumulative score after each round
- Rewards early wins

**4. Direct Encounter:**
- Head-to-head result if applicable

---

## Django Implementation

### Models

```python
# <project_slug>/tournaments/models.py

from decimal import Decimal
from django.db import models


class TournamentStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Scheduled'
    RUNNING = 'running', 'Running'
    FINISHED = 'finished', 'Finished'
    CANCELLED = 'cancelled', 'Cancelled'


class RoundStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAIRING = 'pairing', 'Pairing'
    PLAYING = 'playing', 'Playing'
    COMPLETE = 'complete', 'Complete'


class SwissTournament(models.Model):
    name = models.CharField(max_length=255)
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE)
    time_control = models.ForeignKey('games.TimeControl', on_delete=models.CASCADE)
    num_rounds = models.PositiveIntegerField()
    current_round = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=TournamentStatus.choices,
        default=TournamentStatus.SCHEDULED
    )
    start_time = models.DateTimeField()
    round_interval_minutes = models.PositiveIntegerField(default=5)
    min_rating = models.PositiveIntegerField(null=True, blank=True)
    max_rating = models.PositiveIntegerField(null=True, blank=True)
    no_show_ban_minutes = models.PositiveIntegerField(default=10)
    use_accelerated_pairings = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']


class SwissParticipant(models.Model):
    tournament = models.ForeignKey(
        SwissTournament,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    player = models.ForeignKey('users.User', on_delete=models.CASCADE)
    starting_rank = models.PositiveIntegerField()  # Based on initial rating
    score = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal('0'))
    buchholz = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('0'))
    sonneborn_berger = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('0'))
    progressive = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('0'))
    white_games = models.PositiveIntegerField(default=0)
    black_games = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    late_join_round = models.PositiveIntegerField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['tournament', 'player']
        ordering = ['-score', '-buchholz', '-sonneborn_berger']

    @property
    def color_difference(self) -> int:
        """Difference between white and black games played."""
        return self.white_games - self.black_games


class SwissRound(models.Model):
    tournament = models.ForeignKey(
        SwissTournament,
        on_delete=models.CASCADE,
        related_name='rounds'
    )
    round_number = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=RoundStatus.choices,
        default=RoundStatus.PENDING
    )

    class Meta:
        unique_together = ['tournament', 'round_number']
        ordering = ['round_number']


class SwissPairing(models.Model):
    round = models.ForeignKey(
        SwissRound,
        on_delete=models.CASCADE,
        related_name='pairings'
    )
    white = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='swiss_white_pairings'
    )
    black = models.ForeignKey(
        'users.User',
        null=True,
        on_delete=models.CASCADE,
        related_name='swiss_black_pairings'
    )
    game = models.OneToOneField(
        'games.Game',
        null=True,
        on_delete=models.SET_NULL
    )
    result = models.CharField(max_length=10, null=True, blank=True)
    is_bye = models.BooleanField(default=False)

    class Meta:
        unique_together = ['round', 'white']


class ForbiddenPairing(models.Model):
    """Players who cannot be paired against each other."""
    tournament = models.ForeignKey(
        SwissTournament,
        on_delete=models.CASCADE,
        related_name='forbidden_pairings'
    )
    player1 = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='+'
    )
    player2 = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='+'
    )

    class Meta:
        unique_together = ['tournament', 'player1', 'player2']
```

### Services

```python
# <project_slug>/tournaments/services/swiss.py

from decimal import Decimal
from typing import Tuple
from django.db import transaction


@transaction.atomic
def generate_pairings(*, tournament, round_number: int) -> list:
    """Generate Dutch system pairings for a round."""
    from <project_slug>.tournaments.selectors.swiss import (
        get_active_participants,
        get_previous_opponents,
        get_forbidden_pairs,
    )

    participants = list(get_active_participants(tournament=tournament))
    previous_opponents = get_previous_opponents(tournament=tournament)
    forbidden_pairs = get_forbidden_pairs(tournament=tournament)

    # Group by score
    score_groups = _group_by_score(participants)

    pairings = []
    unpaired = []

    for score in sorted(score_groups.keys(), reverse=True):
        group = unpaired + score_groups[score]
        unpaired = []

        # Sort by starting rank within group
        group.sort(key=lambda p: p.starting_rank)

        # Split into halves
        mid = len(group) // 2
        upper_half = group[:mid]
        lower_half = group[mid:]

        # Pair upper with lower
        paired, unpaired = _pair_halves(
            upper_half=upper_half,
            lower_half=lower_half,
            previous_opponents=previous_opponents,
            forbidden_pairs=forbidden_pairs,
        )
        pairings.extend(paired)

    # Handle odd player with bye
    if unpaired:
        pairings.append(_create_bye(participant=unpaired[0], round_number=round_number))

    return pairings


def _group_by_score(participants: list) -> dict:
    """Group participants by their current score."""
    groups = {}
    for p in participants:
        score = p.score
        if score not in groups:
            groups[score] = []
        groups[score].append(p)
    return groups


def _pair_halves(
    *,
    upper_half: list,
    lower_half: list,
    previous_opponents: dict,
    forbidden_pairs: set,
) -> Tuple[list, list]:
    """Pair upper half against lower half respecting constraints."""
    pairings = []
    used = set()

    for upper in upper_half:
        best_match = None
        for lower in lower_half:
            if lower.player_id in used:
                continue

            # Check constraints
            if not _can_pair(
                a=upper,
                b=lower,
                previous_opponents=previous_opponents,
                forbidden_pairs=forbidden_pairs,
            ):
                continue

            best_match = lower
            break

        if best_match:
            white, black = _assign_colors(a=upper, b=best_match)
            pairings.append({'white': white, 'black': black})
            used.add(best_match.player_id)
        else:
            # Upper couldn't be paired - becomes unpaired
            pass

    # Collect unpaired
    unpaired = [p for p in upper_half + lower_half if p.player_id not in used]
    return pairings, unpaired


def _can_pair(
    *,
    a,
    b,
    previous_opponents: dict,
    forbidden_pairs: set,
) -> bool:
    """Check if two participants can be paired."""
    # No rematches
    if b.player_id in previous_opponents.get(a.player_id, set()):
        return False

    # Check forbidden pairings
    pair_key = tuple(sorted([a.player_id, b.player_id]))
    if pair_key in forbidden_pairs:
        return False

    # Color constraints
    if abs(a.color_difference + 1) > 2 and abs(b.color_difference - 1) > 2:
        return False

    return True


def _assign_colors(*, a, b) -> Tuple:
    """Assign white/black based on color history and rules."""
    # Player with fewer white games gets white
    if a.color_difference < b.color_difference:
        return (a, b)
    elif b.color_difference < a.color_difference:
        return (b, a)

    # Higher ranked player gets white
    if a.starting_rank < b.starting_rank:
        return (a, b)
    return (b, a)


@transaction.atomic
def calculate_tiebreakers(*, tournament) -> None:
    """Recalculate all tiebreakers for all participants."""
    from <project_slug>.tournaments.models import SwissParticipant
    from <project_slug>.tournaments.selectors.swiss import get_opponents_with_results

    participants = SwissParticipant.objects.filter(tournament=tournament)

    for participant in participants:
        opponents_results = get_opponents_with_results(participant=participant)

        # Buchholz: sum of opponents' scores
        buchholz = sum(opp.score for opp, _ in opponents_results)

        # Sonneborn-Berger
        sb_score = Decimal('0')
        for opp, result in opponents_results:
            if result == 'win':
                sb_score += opp.score
            elif result == 'draw':
                sb_score += opp.score / 2

        participant.buchholz = buchholz
        participant.sonneborn_berger = sb_score
        participant.full_clean()
        participant.save(update_fields=['buchholz', 'sonneborn_berger'])


def can_player_join(*, tournament, player) -> Tuple[bool, str]:
    """Check if player can join (late join rules)."""
    if tournament.current_round == 0:
        return True, ""

    max_late_round = tournament.num_rounds // 2
    if tournament.current_round > max_late_round:
        return False, f"Cannot join after round {max_late_round}"

    # Check no-show ban
    from <project_slug>.tournaments.selectors.swiss import is_player_banned
    if is_player_banned(player=player, team=tournament.team):
        return False, "Temporarily banned from Swiss events"

    return True, ""
```

### Selectors

```python
# <project_slug>/tournaments/selectors/swiss.py

from django.db.models import QuerySet
from django.utils import timezone


def get_swiss_standings(*, tournament) -> QuerySet:
    """Get tournament standings with all tiebreakers."""
    from <project_slug>.tournaments.models import SwissParticipant

    return (
        SwissParticipant.objects
        .filter(tournament=tournament)
        .select_related('player')
        .order_by('-score', '-buchholz', '-sonneborn_berger', '-progressive')
    )


def get_active_participants(*, tournament) -> QuerySet:
    """Get participants eligible for pairing."""
    from <project_slug>.tournaments.models import SwissParticipant

    return (
        SwissParticipant.objects
        .filter(tournament=tournament, is_active=True)
        .select_related('player')
    )


def get_previous_opponents(*, tournament) -> dict:
    """Get mapping of player_id -> set of opponent_ids."""
    from <project_slug>.tournaments.models import SwissPairing

    pairings = SwissPairing.objects.filter(
        round__tournament=tournament,
        is_bye=False,
    ).values_list('white_id', 'black_id')

    opponents = {}
    for white_id, black_id in pairings:
        opponents.setdefault(white_id, set()).add(black_id)
        opponents.setdefault(black_id, set()).add(white_id)

    return opponents


def get_forbidden_pairs(*, tournament) -> set:
    """Get set of (player1_id, player2_id) tuples that cannot be paired."""
    from <project_slug>.tournaments.models import ForbiddenPairing

    forbidden = ForbiddenPairing.objects.filter(
        tournament=tournament
    ).values_list('player1_id', 'player2_id')

    return {tuple(sorted([p1, p2])) for p1, p2 in forbidden}


def get_opponents_with_results(*, participant) -> list:
    """Get list of (opponent_participant, result) tuples."""
    from <project_slug>.tournaments.models import SwissPairing, SwissParticipant

    results = []
    player_id = participant.player_id

    pairings = SwissPairing.objects.filter(
        round__tournament=participant.tournament,
        is_bye=False,
    ).filter(
        models.Q(white_id=player_id) | models.Q(black_id=player_id)
    )

    for pairing in pairings:
        if pairing.white_id == player_id:
            opp_id = pairing.black_id
            result = 'win' if pairing.result == '1-0' else ('draw' if pairing.result == '1/2' else 'loss')
        else:
            opp_id = pairing.white_id
            result = 'win' if pairing.result == '0-1' else ('draw' if pairing.result == '1/2' else 'loss')

        opp = SwissParticipant.objects.get(
            tournament=participant.tournament,
            player_id=opp_id
        )
        results.append((opp, result))

    return results


def is_player_banned(*, player, team) -> bool:
    """Check if player is temporarily banned from Swiss events."""
    # Implementation would check recent no-shows
    return False
```

### API Endpoints

```
GET  /api/tournaments/swiss/                     # List Swiss tournaments
POST /api/tournaments/swiss/                     # Create tournament (team leaders)
GET  /api/tournaments/swiss/{id}/                # Tournament details
POST /api/tournaments/swiss/{id}/join/           # Join tournament
POST /api/tournaments/swiss/{id}/withdraw/       # Withdraw
GET  /api/tournaments/swiss/{id}/standings/      # Current standings
GET  /api/tournaments/swiss/{id}/rounds/         # All rounds with pairings
GET  /api/tournaments/swiss/{id}/rounds/{n}/     # Specific round pairings
GET  /api/tournaments/swiss/{id}/export/trf/     # TRF export
WS   /ws/tournaments/swiss/{id}/                 # Real-time updates
```

### WebSocket Events

```python
# Outbound events (server → client)
{
    "type": "round_start",
    "round": 3,
    "pairings": [
        {"white": "player1", "black": "player2", "game_id": "abc123"},
        {"white": "player3", "black": null, "is_bye": true}
    ]
}

{
    "type": "game_result",
    "round": 3,
    "white": "player1",
    "black": "player2",
    "result": "1-0"
}

{
    "type": "standings_update",
    "standings": [
        {"player": "player1", "score": 3.0, "buchholz": 7.5, "rank": 1}
    ]
}

{
    "type": "tournament_end",
    "final_standings": [...]
}
```

---

## React Components

> **Note**: Following Bulletproof React conventions:
> - No barrel files (index.ts) - use direct imports
> - Kebab-case file names
> - Feature-based organization

```
src/features/tournaments/
├── components/
│   ├── swiss-lobby.tsx           # Main tournament view
│   ├── swiss-standings.tsx       # Standings with tiebreakers
│   ├── swiss-round-view.tsx      # Round pairings display
│   ├── swiss-pairing-card.tsx    # Individual pairing
│   ├── round-countdown.tsx       # Time to next round
│   └── trf-export-button.tsx     # Export to TRF format
├── hooks/
│   ├── use-swiss-tournament.ts   # Tournament state
│   └── use-swiss-pairings.ts     # Pairing state per round
└── api/
    └── swiss-api.ts              # API calls
```

**Import example**:
```typescript
// Correct: Direct import
import { SwissLobby } from '@/features/tournaments/components/swiss-lobby';
import { useSwissTournament } from '@/features/tournaments/hooks/use-swiss-tournament';
```

---

## TRF Export Format

Tournament Report File format for FIDE reporting:

```
012 Tournament Name
022 City
032 Federation
042 Start Date
052 End Date
062 Number of Players
072 Number of Rated Players
082 Number of Teams
092 Type (SWISS)
102 Chief Arbiter
...
001 001 Player1Name    1234  USA  1800  1.0  +W002  -B003  =W004
001 002 Player2Name    5678  USA  1750  2.0  -B001  +W004  +B003
```

### Lichess TRF Notes

- Player names in lowercase
- Byes exported as "H" (half-point) or "U" (unpaired)
- Withdrawals exported as "-" (SwissChess expects "0000 - Z")
- Sorted by starting rank number

---

## MVP Scope

### Phase 1: Core Swiss
- Tournament creation (team-hosted)
- Basic Dutch pairing algorithm
- Standard scoring
- Round scheduling
- Player join/withdraw

### Phase 2: Enhanced Features
- Full color balancing
- Buchholz tiebreaker
- Late join handling
- No-show auto-withdrawal

### Phase 3: Advanced
- TRF export
- Sonneborn-Berger tiebreaker
- Custom round intervals
- Rating restrictions
- Forbidden pairings

### Phase 4: Professional
- Accelerated pairings
- Manual pairing corrections
- Progressive tiebreaker
- FIDE-rated tournament support

---

## Sources

- [Lichess Swiss Tournaments](https://lichess.org/swiss)
- [FIDE Dutch System Handbook](https://handbook.fide.com/chapter/C0403)
- [FIDE Swiss Rules](https://handbook.fide.com/chapter/C0403Till2025)
- [Lichess Forum - Swiss Tournaments](https://lichess.org/forum/general-chess-discussion/about-swiss-tournaments)
- [Lichess Forum - Forbidden Pairings](https://lichess.org/forum/lichess-feedback/forbidden-pairings-in-swiss-tournaments)
- [bbpPairings Library](https://github.com/BieremaBoyzProgramming/bbpPairings)
- [Lichess lila/modules/swiss](https://github.com/lichess-org/lila/tree/master/modules/swiss)
