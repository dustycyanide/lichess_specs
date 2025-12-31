---
title: Timed Game Modes
category: game-modes
modes: [bullet, blitz, rapid, classical]
status: draft
styleguide: hacksoft-django-styleguide
---

# Timed Game Modes

Specification for implementing real-time timed chess games (UltraBullet through Classical).

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) (services for business logic, selectors for queries). Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) (feature modules, direct imports, TanStack Query).

---

## Overview

Timed games are the core gameplay mode where both players have a shared time constraint. Games are classified by **estimated duration**, not just initial time.

---

## Time Control Categories

### Classification Formula

```
Estimated Duration = (initial_time_seconds) + 40 × (increment_seconds)
```

The multiplier of 40 represents an estimated number of moves in a typical game.

### Category Boundaries

| Category | Max Estimated Duration | Common Time Controls |
|----------|----------------------|---------------------|
| **UltraBullet** | ≤ 29 seconds | 1/4+0, 1/2+0 |
| **Bullet** | ≤ 179 seconds | 1+0, 2+1, 1+1 |
| **Blitz** | ≤ 479 seconds | 3+0, 3+2, 5+0, 5+3 |
| **Rapid** | ≤ 1,499 seconds | 10+0, 15+10, 10+5 |
| **Classical** | ≥ 1,500 seconds | 30+0, 30+20 |

### Implementation Notes

- These differ from FIDE definitions (intentionally - online chess has different needs)
- Each category has its own separate rating
- Category determines matchmaking pool
- Category affects anti-cheat sensitivity thresholds

---

## Clock Mechanics

### Fischer Increment (Primary System)

Lichess uses **Fischer increment** exclusively:

- Time is added **after each move completes**
- Time is added regardless of how long the move took
- Player's clock can exceed initial time
- Simple rule: same amount added every move

**Example**: 5+3 game
- Start with 5 minutes
- After move 1: time remaining + 3 seconds
- Clock can grow above 5 minutes if moves are fast

### Clock Implementation Requirements

```python
# Pseudo-code for clock update
def process_move(game, player, move_timestamp):
    time_spent = move_timestamp - player.last_move_timestamp
    player.time_remaining -= time_spent

    if player.time_remaining <= 0:
        return GameResult.TIMEOUT_LOSS

    # Add increment AFTER the move
    player.time_remaining += game.increment_seconds
    player.last_move_timestamp = move_timestamp
```

### Clock Precision

- Store time in **milliseconds** internally
- Display to user in seconds (with decimal for < 10 seconds)
- Network latency compensation required (see Real-Time Gameplay spec)

---

## Matchmaking System

### Quick Pairing (Primary)

Quick Pairing is the primary matchmaking for rated games:

| Aspect | Behavior |
|--------|----------|
| Game type | Always rated |
| Time controls | Preset buttons only |
| Matching | Automatic, rating-based |
| Rating range | Auto-expands over time |
| Visibility | Pool is hidden from users |

**Preset Time Controls** (11 buttons):
- UltraBullet: 1/4+0
- Bullet: 1+0, 2+1
- Blitz: 3+0, 3+2, 5+0, 5+3
- Rapid: 10+0, 15+10
- Classical: 30+0

### Lobby System (Secondary)

The Lobby shows custom game seeks:

| Aspect | Behavior |
|--------|----------|
| Game type | Rated or casual |
| Time controls | Custom allowed |
| Matching | Manual selection |
| Rating range | User-defined filter |
| Visibility | Public seeks visible |

**Lobby Features**:
- Filter by rating range
- Filter by time control category
- Filter by variant
- Filters stored in browser localStorage
- Seek graph visualization (optional)

### Rating Restrictions

- Players can set maximum rating difference
- Games outside specified range not visible
- Quick pairing respects rating proximity

---

## Rated vs Casual Games

### Key Differences

| Aspect | Rated | Casual |
|--------|-------|--------|
| Rating impact | Yes | No |
| Matchmaking | Rating-based | Less precise |
| Anti-cheat | **Full automated** | **Manual only** |
| Leaderboards | Eligible | No |

### Anti-Cheat Implications

**Rated games**: Full automated detection active

**Casual games**: Detection largely disabled because:
- Training games may involve engines
- Friends may be experimenting
- Lower competitive stakes

Players can still report cheating in casual games, but requires obvious evidence.

---

## Rematch System

### Color Alternation Rule

Using rematch **swaps colors** between games:
- White player becomes Black
- Black player becomes White
- Ensures fairness in multi-game sessions

### Rematch Flow

```
Game Ends → Rematch Button Appears →
  → Player A clicks → Offer sent to Player B →
    → Player B accepts → New game starts (colors swapped)
    → Player B leaves → Button disappears
```

### Anti-Sandbagging Protection

- Rematch may be disabled after very short games
- Prevents manipulation to keep preferred color
- Prevents abort-then-rematch exploits

---

## Provisional Ratings

### Rating Deviation Indicator

A "?" next to rating indicates provisional status.

**Causes**:
1. Not enough rated games in category (< ~12 games)
2. Long inactivity (~1 year without playing)

### Glicko-2 System

| Parameter | Meaning |
|-----------|---------|
| Rating | Skill estimate |
| Rating Deviation (RD) | Confidence in rating |
| Volatility | Expected fluctuation |

- "?" appears when RD > 110
- New accounts start at 1500 rating
- Provisional ratings change more dramatically
- Stabilizes after ~12 games

---

## Data Model (Hacksoft Pattern)

### Model (Data + Validation Only)

Models contain data structure and validation, NOT business logic:

```python
# <project_slug>/games/models.py
from django.db import models
from django.core.validators import MinValueValidator

class TimeControlCategory(models.TextChoices):
    ULTRABULLET = 'ultrabullet', 'UltraBullet'
    BULLET = 'bullet', 'Bullet'
    BLITZ = 'blitz', 'Blitz'
    RAPID = 'rapid', 'Rapid'
    CLASSICAL = 'classical', 'Classical'


class TimedGame(models.Model):
    """
    Model for real-time timed chess games.
    Business logic (clock updates, move processing) lives in services.py
    """
    # Time control settings
    initial_time_seconds = models.IntegerField(validators=[MinValueValidator(1)])
    increment_seconds = models.IntegerField(default=0)
    time_control_category = models.CharField(
        max_length=20,
        choices=TimeControlCategory.choices
    )

    # Clock state (in milliseconds for precision)
    white_time_remaining_ms = models.IntegerField()
    black_time_remaining_ms = models.IntegerField()

    # Game metadata
    is_rated = models.BooleanField(default=True)
    white_rating_before = models.IntegerField(null=True)
    black_rating_before = models.IntegerField(null=True)

    # Computed property (OK in models - no side effects)
    @property
    def estimated_duration_seconds(self) -> int:
        return self.initial_time_seconds + (40 * self.increment_seconds)
```

### Service (Business Logic)

Clock updates and move processing live in services:

```python
# <project_slug>/games/services.py
from django.db import transaction
from datetime import datetime


@transaction.atomic
def timed_game_process_move(
    *,
    game: TimedGame,
    player_color: str,
    move_timestamp: datetime,
    last_move_timestamp: datetime,
) -> TimedGame:
    """
    Process a move and update clock times.
    Returns updated game or raises TimeoutError.
    """
    time_spent_ms = int((move_timestamp - last_move_timestamp).total_seconds() * 1000)

    if player_color == 'white':
        game.white_time_remaining_ms -= time_spent_ms
        if game.white_time_remaining_ms <= 0:
            raise TimeoutError("White has run out of time")
        game.white_time_remaining_ms += game.increment_seconds * 1000
    else:
        game.black_time_remaining_ms -= time_spent_ms
        if game.black_time_remaining_ms <= 0:
            raise TimeoutError("Black has run out of time")
        game.black_time_remaining_ms += game.increment_seconds * 1000

    game.full_clean()
    game.save()
    return game
```

### Time Control Presets

```python
TIME_CONTROL_PRESETS = {
    'ultrabullet': [
        {'initial': 15, 'increment': 0, 'name': '1/4+0'},
        {'initial': 30, 'increment': 0, 'name': '1/2+0'},
    ],
    'bullet': [
        {'initial': 60, 'increment': 0, 'name': '1+0'},
        {'initial': 120, 'increment': 1, 'name': '2+1'},
    ],
    'blitz': [
        {'initial': 180, 'increment': 0, 'name': '3+0'},
        {'initial': 180, 'increment': 2, 'name': '3+2'},
        {'initial': 300, 'increment': 0, 'name': '5+0'},
        {'initial': 300, 'increment': 3, 'name': '5+3'},
    ],
    'rapid': [
        {'initial': 600, 'increment': 0, 'name': '10+0'},
        {'initial': 900, 'increment': 10, 'name': '15+10'},
    ],
    'classical': [
        {'initial': 1800, 'increment': 0, 'name': '30+0'},
        {'initial': 1800, 'increment': 20, 'name': '30+20'},
    ],
}
```

---

## API Endpoints

### Create Game Seek

```
POST /api/game/seek
{
    "initial_time": 300,
    "increment": 3,
    "rated": true,
    "color": "random"  // "white", "black", or "random"
}
```

### Quick Pairing

```
POST /api/game/quick-pair
{
    "preset": "5+3"  // One of the preset time controls
}
```

### Accept Rematch

```
POST /api/game/{game_id}/rematch
```

---

## Frontend Components (Bulletproof Pattern)

All components follow the [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md):
- Feature-based organization in `features/game/`
- Direct imports (no barrel files)
- Kebab-case file naming
- TanStack Query for server state
- Zod schemas for API validation

### Feature Structure

```
frontend/src/features/game/
├── api/
│   ├── get-game.ts          # Query hook (3-part pattern)
│   ├── create-seek.ts       # Mutation hook
│   └── accept-seek.ts       # Mutation hook
├── components/
│   ├── chess-clock.tsx      # Clock display
│   ├── quick-pairing.tsx    # Quick pairing panel
│   └── lobby-view.tsx       # Lobby table
├── hooks/
│   └── use-clock-timer.ts   # Clock countdown logic
└── types/
    └── game.ts              # Zod schemas + types
```

### Clock Display Component

```tsx
// src/features/game/components/chess-clock.tsx
// ABOUTME: Displays chess clock with countdown and visual warnings

interface ChessClockProps {
  timeMs: number;
  active: boolean;
  className?: string;
}

export function ChessClock({ timeMs, active, className }: ChessClockProps) {
  // Component implementation...
}
```

Requirements:
- Show minutes:seconds format (5:00, 4:32)
- Show deciseconds when < 10 seconds (9.4, 3.2)
- Visual warning at low time (< 30 seconds)
- Critical warning at very low time (< 10 seconds)
- Smooth countdown animation

### Quick Pairing Panel

```tsx
// src/features/game/components/quick-pairing.tsx
// ABOUTME: Grid of preset time control buttons for quick matchmaking
```

Requirements:
- 11 preset buttons in grid layout
- Show player's rating for each category
- Indicate provisional ratings with "?"
- Show active seek status
- Cancel seek functionality

### Lobby View

```tsx
// src/features/game/components/lobby-view.tsx
// ABOUTME: Table of available game seeks with filtering
```

Requirements:
- Table of available seeks
- Filter controls (rating range, time control, variant)
- Seek graph (optional visualization)
- Click to accept functionality
- Real-time updates via WebSocket

---

## Implementation Priority

### Phase 1: MVP
1. Fischer increment clock mechanics
2. Category classification (bullet/blitz/rapid)
3. Quick pairing for 3-4 popular presets
4. Basic rated game support

### Phase 2: Full Feature
1. All time control categories
2. Full lobby system
3. Rematch functionality
4. Casual game support

### Phase 3: Polish
1. Provisional rating display
2. Rating restrictions
3. Seek graph visualization
4. Advanced filters

---

## References

- [Lichess FAQ - Time Controls](https://lichess.org/faq)
- [Glicko-2 Rating System](http://www.glicko.net/glicko/glicko2.pdf)
- [Lichess API - Game Documentation](https://lichess.org/api#tag/Games)
