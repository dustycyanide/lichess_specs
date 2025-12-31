---
title: Correspondence Chess
category: game-modes
status: draft
styleguide: hacksoft-django-styleguide
---

# Correspondence Chess

Specification for implementing asynchronous correspondence chess where players have days, not minutes, per move.

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) (services for business logic, selectors for queries). Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) (feature modules, direct imports, TanStack Query).

---

## Overview

Correspondence chess is an asynchronous game mode designed for:
- Players in different time zones
- Players who prefer thoughtful, unhurried play
- Players who cannot commit to real-time sessions
- Deep analysis without time pressure

---

## Time Control System

### Time Per Move

Unlike timed games (total time pool), correspondence uses **time per move**:

| Setting | Description |
|---------|-------------|
| 1 day | Fast correspondence |
| 2 days | Standard |
| 3 days | Relaxed (recommended) |
| 7 days | Weekly |
| 14 days | Maximum flexibility |

### Timer Behavior

1. **On opponent's move**: Your timer starts counting down
2. **On your move**: Timer resets to full allocated time
3. **On timeout**: Automatic loss (forfeit)

```
Opponent moves → Your timer starts (e.g., 3 days) →
  → You move within time → Timer resets for opponent
  → You timeout → You lose the game
```

### Key Difference from Timed Games

| Aspect | Timed Games | Correspondence |
|--------|-------------|----------------|
| Time type | Total pool | Per move |
| Units | Seconds/minutes | Days |
| Clock behavior | Decrements continuously | Resets each move |
| Increment | Added after move | Not applicable |

---

## Rules and Allowed Resources

### What's Allowed

| Resource | Permitted | Notes |
|----------|-----------|-------|
| Opening books | Yes | Physical or digital |
| Game databases | Yes | Research past games |
| Analysis boards | Yes | Move out positions |
| Note-taking | Yes | Personal analysis |

### What's Prohibited

| Resource | Permitted | Notes |
|----------|-----------|-------|
| Chess engines | **No** | Stockfish, Leela, etc. |
| Computer analysis | **No** | Engine evaluation |
| Other players' help | **No** | Asking for advice |

### Difference from ICCF

Important distinction: **ICCF (International Correspondence Chess Federation) allows engine use**, but Lichess does NOT. This is a deliberate policy choice.

**Rationale**: Lichess wants correspondence to test human skill, not engine access.

**Enforcement**: Violations result in being flagged for engine assistance, same as timed games.

---

## Vacation Mode

### Current Status

**Lichess does NOT have vacation mode for correspondence chess.**

This is a known limitation and frequent feature request.

### Workarounds

| Strategy | Description |
|----------|-------------|
| Longer time controls | Use 3+ days/move for flexibility |
| Conditional moves | Set up if-then move sequences |
| 14-day setting | Maximum buffer for extended absences |
| Ask opponent | Request they add time (not guaranteed) |

### Conditional/Premoves

Players can set conditional moves:
```
If opponent plays e5, then play Nf3
If opponent plays d5, then play d4
```

This allows automatic responses during offline periods.

---

## Multiple Concurrent Games

### Behavior

- Players can have **many correspondence games simultaneously**
- No upper limit (practically)
- Each game tracked independently
- Games appear on home page/dashboard

### Notifications

- Email notification when it's your turn (if enabled)
- Push notification on mobile
- Dashboard indicator for games awaiting your move
- Optional daily digest of pending games

---

## Game Seeking

### Creating Correspondence Games

Unlike quick pairing (not available for correspondence), players use:

1. **Custom Game**: Create open challenge with:
   - Days per move setting
   - Rated/casual option
   - Rating range restrictions
   - Color preference

2. **Direct Challenge**: Send to specific user

3. **Lobby**: Browse open correspondence seeks

### Matchmaking Considerations

- No automatic quick pairing
- Manual seek/accept process
- Rating range filtering important (avoid provisional mismatches)

---

## Data Model (Hacksoft Pattern)

### Models (Data + Validation Only)

Models contain data structure and validation, NOT business logic:

```python
# <project_slug>/games/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class CorrespondenceGame(models.Model):
    """
    Correspondence chess game with days-per-move time control.
    Business logic (timeout handling, move processing) lives in services.py
    """
    # Time control
    days_per_move = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(14)]
    )

    # Current state
    current_player = models.CharField(max_length=5)  # 'white' or 'black'
    move_deadline = models.DateTimeField()  # When current player must move

    # Game metadata
    is_rated = models.BooleanField(default=True)
    white_rating_before = models.IntegerField(null=True)
    black_rating_before = models.IntegerField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['move_deadline']),  # For timeout queries
        ]


class CorrespondenceMove(models.Model):
    """Individual move in a correspondence game."""
    game = models.ForeignKey(CorrespondenceGame, on_delete=models.CASCADE, related_name='moves')
    move_san = models.CharField(max_length=10)  # e.g., "e4", "Nf3"
    timestamp = models.DateTimeField(auto_now_add=True)
    time_remaining = models.DurationField()  # Time left when move was made


class ConditionalMove(models.Model):
    """Pre-set automatic response to opponent's move."""
    game = models.ForeignKey(CorrespondenceGame, on_delete=models.CASCADE)
    player = models.CharField(max_length=5)
    trigger_move = models.CharField(max_length=10)  # Opponent's move that triggers this
    response_move = models.CharField(max_length=10)  # Our automatic response
    active = models.BooleanField(default=True)
```

### Service (Business Logic)

All business logic lives in services:

```python
# <project_slug>/games/services.py
from django.db import transaction
from django.utils import timezone
from datetime import timedelta


@transaction.atomic
def correspondence_game_make_move(
    *,
    game: CorrespondenceGame,
    player: str,
    move_san: str,
) -> CorrespondenceGame:
    """
    Process a correspondence move and update deadline.
    """
    # Record the move
    time_remaining = game.move_deadline - timezone.now()
    CorrespondenceMove.objects.create(
        game=game,
        move_san=move_san,
        time_remaining=time_remaining
    )

    # Swap current player and reset deadline
    game.current_player = 'black' if player == 'white' else 'white'
    game.move_deadline = timezone.now() + timedelta(days=game.days_per_move)

    game.full_clean()
    game.save()
    return game


@transaction.atomic
def correspondence_game_check_timeout(*, game: CorrespondenceGame) -> CorrespondenceGame:
    """
    Check if current player has timed out and end game if so.
    Called by scheduled Celery task.
    """
    if timezone.now() > game.move_deadline:
        # End game by timeout - winner is the other player
        game.status = 'timeout'
        game.winner = 'black' if game.current_player == 'white' else 'white'
        game.full_clean()
        game.save()

        # Notify players
        _notify_game_ended(game=game, reason='timeout')

    return game
```

### Selector (Queries)

```python
# <project_slug>/games/selectors.py
from django.db.models import QuerySet
from django.utils import timezone


def correspondence_game_list_pending(*, user: User) -> QuerySet[CorrespondenceGame]:
    """Get correspondence games where it's the user's turn."""
    return CorrespondenceGame.objects.filter(
        current_player_user=user,
        status='in_progress'
    ).order_by('move_deadline')


def correspondence_game_list_timing_out(*, threshold_hours: int = 24) -> QuerySet[CorrespondenceGame]:
    """Get games with deadlines in the next N hours (for reminders)."""
    threshold = timezone.now() + timedelta(hours=threshold_hours)
    return CorrespondenceGame.objects.filter(
        status='in_progress',
        move_deadline__lt=threshold
    ).order_by('move_deadline')
```

---

## API Endpoints

### Create Correspondence Seek

```
POST /api/game/correspondence/seek
{
    "days_per_move": 3,
    "rated": true,
    "color": "random",
    "rating_range": {
        "min": 1400,
        "max": 1800
    }
}
```

### Challenge Specific User

```
POST /api/challenge/{username}
{
    "type": "correspondence",
    "days_per_move": 3,
    "rated": true,
    "color": "white"
}
```

### Make Move

```
POST /api/game/{game_id}/move
{
    "move": "e4"
}
```

Response includes new deadline:
```json
{
    "success": true,
    "move_deadline": "2025-01-03T14:30:00Z"
}
```

### Set Conditional Moves

```
POST /api/game/{game_id}/conditional
{
    "conditionals": [
        {"if": "e5", "then": "Nf3"},
        {"if": "c5", "then": "Nf3"}
    ]
}
```

### Get Pending Games

```
GET /api/correspondence/pending
```

Returns all games where it's the user's turn.

---

## Frontend Components (Bulletproof Pattern)

All components follow the [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md):
- Feature-based organization in `features/correspondence/`
- Direct imports (no barrel files)
- Kebab-case file naming
- TanStack Query for server state
- Zod schemas for API validation

### Feature Structure

```
frontend/src/features/correspondence/
├── api/
│   ├── get-pending-games.ts     # Query hook (3-part pattern)
│   ├── make-move.ts             # Mutation hook
│   └── set-conditionals.ts      # Mutation hook
├── components/
│   ├── correspondence-dashboard.tsx
│   ├── deadline-display.tsx
│   ├── conditional-move-form.tsx
│   └── game-view.tsx
├── hooks/
│   └── use-deadline-countdown.ts
└── types/
    └── correspondence.ts        # Zod schemas + types
```

### Correspondence Dashboard

```tsx
// src/features/correspondence/components/correspondence-dashboard.tsx
// ABOUTME: Lists all active correspondence games sorted by urgency
```

Requirements:
- List of all active correspondence games
- Visual indicator for games awaiting your move
- Time remaining display (days:hours)
- Sort by urgency (closest deadline first)
- Quick access to each game

### Game View (Correspondence)

```tsx
// src/features/correspondence/components/game-view.tsx
// ABOUTME: Full game view with analysis board and move confirmation
```

Requirements:
- Standard board with move history
- Prominent deadline display
- Conditional move interface
- Analysis board (allowed in correspondence)
- Move confirmation dialog (prevent misclicks)

### Deadline Display

```tsx
// src/features/correspondence/components/deadline-display.tsx
// ABOUTME: Shows time remaining with urgency-based color coding

interface DeadlineDisplayProps {
  deadline: Date;
  className?: string;
}

export function DeadlineDisplay({ deadline, className }: DeadlineDisplayProps) {
  // Format examples:
  // - "2 days 14 hours" (comfortable)
  // - "12 hours" (getting urgent)
  // - "2 hours 30 min" (warning state)
  // - "45 minutes" (critical)
}
```

Visual states:
- Green: > 24 hours
- Yellow: 4-24 hours
- Red: < 4 hours

### Conditional Move Interface

```tsx
// src/features/correspondence/components/conditional-move-form.tsx
// ABOUTME: Form to set up if-then move responses
```

Requirements:
- List current conditional moves
- Add new conditional (dropdown for opponent moves)
- Delete existing conditionals
- Indicate which conditionals matched if one fires

---

## Background Jobs (Hacksoft Pattern)

Celery tasks are thin wrappers that call services. All business logic stays in services.

### Timeout Processing Task

```python
# <project_slug>/games/tasks.py
from celery import shared_task
from <project_slug>.games.selectors import correspondence_game_list_timed_out
from <project_slug>.games.services import correspondence_game_check_timeout


@shared_task
def process_correspondence_timeouts() -> int:
    """
    Check all games for timeouts. Run every 5-15 minutes via Celery beat.
    Returns count of games ended by timeout.
    """
    # Use selector to get games past deadline
    timed_out_games = correspondence_game_list_timed_out()

    count = 0
    for game in timed_out_games:
        # Call service for each game (keeps logic in service)
        result = correspondence_game_check_timeout(game=game)
        if result.status == 'timeout':
            count += 1

    return count
```

### Reminder Notification Task

```python
# <project_slug>/games/tasks.py

@shared_task
def send_correspondence_reminders() -> int:
    """
    Send reminder notifications for games nearing deadline.
    Run every hour via Celery beat.
    """
    from <project_slug>.games.selectors import correspondence_game_list_timing_out
    from <project_slug>.notifications.services import notification_send

    # Get games with < 24 hours remaining
    urgent_games = correspondence_game_list_timing_out(threshold_hours=24)

    count = 0
    for game in urgent_games:
        notification_send(
            user=game.current_player_user,
            type='correspondence_reminder',
            data={'game_id': str(game.id), 'deadline': game.move_deadline}
        )
        count += 1

    return count
```

### Celery Beat Schedule

```python
# config/settings/base.py
CELERY_BEAT_SCHEDULE = {
    'correspondence-timeouts': {
        'task': '<project_slug>.games.tasks.process_correspondence_timeouts',
        'schedule': 300,  # Every 5 minutes
    },
    'correspondence-reminders': {
        'task': '<project_slug>.games.tasks.send_correspondence_reminders',
        'schedule': 3600,  # Every hour
    },
}
```

### Reminder Thresholds

Optional notifications at configurable thresholds:
- 24 hours remaining
- 4 hours remaining
- 1 hour remaining

---

## Implementation Priority

### Phase 1: MVP
1. Basic correspondence game creation
2. Days-per-move timer
3. Timeout handling
4. Dashboard showing pending games

### Phase 2: Full Feature
1. Conditional moves
2. Email notifications
3. Direct challenges
4. Rating range restrictions

### Phase 3: Polish
1. Reminder notifications
2. Daily digest emails
3. Advanced conditional move UI
4. Mobile push notifications

---

## Edge Cases

### Clock During Server Downtime

If server is down, clocks should be adjusted fairly:
- Track server downtime periods
- Add equivalent time to affected players
- Or pause all correspondence clocks during outage

### Abandoned Games

Games where neither player moves for extended period:
- Could auto-adjudicate after 2x time control with no moves
- Or require moderator intervention
- Track "last activity" separately from deadline

### Rating Calculation Timing

Unlike timed games (immediate), correspondence ratings:
- Could be calculated at game end
- Or use rating at move time
- Lichess uses rating at game start

---

## References

- [Lichess Forum - How Correspondence Works](https://lichess.org/forum/general-chess-discussion/how-does-correspondence-work)
- [Lichess Forum - Correspondence Timing Rules](https://lichess.org/forum/general-chess-discussion/correspondence-timing-rules)
- [Lichess Forum - Vacation Mode Discussion](https://lichess.org/forum/lichess-feedback/please-consider-adding-vacation-mode-for-correspondence-games)
- [Lichess API - Challenge Documentation](https://lichess.org/api#tag/Challenges)
