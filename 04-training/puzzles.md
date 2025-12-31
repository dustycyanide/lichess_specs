---
title: Puzzles & Tactics Training
category: training
status: draft
dependencies: python-chess, Glicko-2
lichess_equivalent: lichess.org/training
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
---

# Puzzles & Tactics Training

> Tactical puzzles generated from real games, with adaptive difficulty and multiple game modes

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) - services for writes, selectors for reads, explicit `<project_slug>/` imports. Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) - no barrel files, direct imports, kebab-case filenames.

---

## Overview

The puzzle system provides tactical training through problems extracted from real games. Puzzles are rated using Glicko-2 (same as players), enabling adaptive difficulty matching. Multiple game modes support different training objectives: accuracy (Standard), speed (Storm), consistency (Streak), and competition (Racer).

### Lichess Reference

Lichess hosts 5.4M+ puzzles generated from 600M analyzed games using Stockfish NNUE at 40 meganodes—over 100 CPU-years of computation. We will leverage the [Lichess Puzzle Database](https://database.lichess.org/#puzzles) rather than generating our own.

---

## Data Model

### Puzzle Model

```python
class Puzzle(models.Model):
    """Tactical puzzle extracted from a real game."""

    # Identification
    lichess_id = models.CharField(max_length=10, unique=True, db_index=True)

    # Position
    fen = models.CharField(max_length=100)  # Position before opponent's move
    moves = models.CharField(max_length=200)  # UCI moves; first is opponent's, rest is solution

    # Rating (Glicko-2)
    rating = models.IntegerField(db_index=True)
    rating_deviation = models.IntegerField()

    # Metadata
    popularity = models.SmallIntegerField()  # -100 to 100
    play_count = models.PositiveIntegerField(default=0)

    # Source
    game_url = models.URLField(blank=True)
    opening_tags = models.CharField(max_length=100, blank=True)  # Only for puzzles before move 20

    class Meta:
        indexes = [
            models.Index(fields=['rating', 'popularity']),
        ]


class PuzzleTheme(models.Model):
    """Tactical or positional theme tag."""

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=[
        ('tactical', 'Tactical Motif'),
        ('mate', 'Checkmate Pattern'),
        ('phase', 'Game Phase'),
        ('endgame', 'Endgame Type'),
        ('length', 'Puzzle Length'),
        ('evaluation', 'Evaluation Category'),
        ('special', 'Special Category'),
    ])


class PuzzleThemeAssignment(models.Model):
    """Many-to-many with vote tracking for theme accuracy."""

    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name='theme_assignments')
    theme = models.ForeignKey(PuzzleTheme, on_delete=models.CASCADE)
    confidence = models.FloatField(default=1.0)  # Based on community votes

    class Meta:
        unique_together = ['puzzle', 'theme']
```

### User Puzzle Progress

```python
class UserPuzzleRating(models.Model):
    """User's puzzle rating (separate from game ratings)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=1500)
    rating_deviation = models.IntegerField(default=350)
    volatility = models.FloatField(default=0.06)

    # Statistics
    puzzles_solved = models.PositiveIntegerField(default=0)
    puzzles_failed = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)

    # Game mode records
    storm_best = models.PositiveIntegerField(default=0)
    streak_best = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['-rating']),  # For leaderboards
        ]


class PuzzleAttempt(models.Model):
    """Record of a puzzle solve attempt."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    solved = models.BooleanField()
    time_taken_ms = models.PositiveIntegerField()
    rating_before = models.IntegerField()
    rating_after = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
```

---

## Puzzle Themes

### Tactical Motifs

| Theme | Description |
|-------|-------------|
| **Fork** | One piece attacks two opponent pieces simultaneously |
| **Pin** | A piece cannot move without exposing a higher-value piece |
| **Skewer** | High-value piece is attacked, moves, exposing capture of piece behind |
| **Discovered Attack** | Moving a piece reveals attack from hidden long-range piece |
| **Deflection** | Distracting a piece from its defensive duty |
| **Attraction** | Forcing an opponent piece to a vulnerable square |
| **Interference** | Blocking communication between opponent pieces |
| **X-Ray Attack** | Attacking/defending through an enemy piece |
| **Clearance** | Clearing a square/file/diagonal for a follow-up tactic |
| **Zugzwang** | Opponent must move but all moves worsen position |
| **Trapped Piece** | A piece cannot escape capture |
| **Overloaded Piece** | Removing a piece critical to defense |
| **Zwischenzug** | Unexpected intermediate move before expected continuation |
| **Sacrifice** | Giving up material for advantage after forced sequence |
| **Quiet Move** | Non-check, non-capture that prepares unavoidable threat |

### Checkmate Patterns

| Pattern | Description |
|---------|-------------|
| **Back Rank Mate** | King trapped on home rank by own pieces |
| **Smothered Mate** | Knight checkmate with king surrounded by own pieces |
| **Anastasia's Mate** | Knight + rook/queen trap king between edge and friendly piece |
| **Arabian Mate** | Knight + rook trap king in corner |
| **Boden's Mate** | Two bishops on crossing diagonals |
| **Opera Mate** | Rook + bishop coordinate |

### Puzzle Categories

- **By Length**: One-move, Short (2), Long (3), Very Long (4+)
- **By Mate Depth**: Mate in 1/2/3/4/5+
- **By Game Phase**: Opening, Middlegame, Endgame
- **By Evaluation**: Equality (≤200cp), Advantage (200-600cp), Crushing (≥600cp)

---

## Game Modes

### Standard Puzzles

Adaptive difficulty matching puzzles to user rating.

**Flow**:
1. Fetch puzzle within ±200 rating of user
2. Display position (opponent's move plays automatically)
3. User plays solution moves
4. All moves must be correct (any wrong move = fail)
5. Update ratings using Glicko-2

**Rating Updates**:
- Solve → User gains rating, puzzle loses rating
- Fail → User loses rating, puzzle gains rating
- Rating change magnitude depends on rating difference

### Puzzle Storm

Timed mode for pattern recognition training.

| Metric | Value |
|--------|-------|
| Starting Time | 3 minutes |
| Wrong Answer Penalty | -10 seconds, combo resets |

**Combo Bonuses**:
| Streak | Time Bonus |
|--------|------------|
| 1-5 | +3 seconds per correct |
| 6-12 | +5 seconds per correct |
| 13-20 | +7 seconds per correct |
| 21+ | +10 seconds per 10 moves |

**Puzzle Selection**: Start easy, progressively harder. Unrated.

### Puzzle Streak

Untimed mode for deep calculation.

- **No Clock**: Take as long as needed
- **Progressive Difficulty**: Puzzles get harder with streak
- **One Life**: Single wrong move ends streak
- **Skip Token**: One skip per session
- **Unrated**: Does not affect puzzle rating

### Puzzle Racer

Multiplayer competitive puzzle solving.

| Metric | Value |
|--------|-------|
| Duration | 90 seconds |
| Scoring | 1 point per correct move |
| Max Players | 10 per room |

**Combo Bonuses**:
| Streak | Bonus Points |
|--------|--------------|
| 5 moves | +1 |
| 12 moves | +2 |
| 20 moves | +3 |
| Every 10 after | +4 |

---

## Django Implementation

### Services

Services handle write operations with `@transaction.atomic` for data integrity:

```python
# <project_slug>/puzzles/services.py
from django.db import transaction

from <project_slug>.puzzles.models import Puzzle, PuzzleAttempt, UserPuzzleRating
from <project_slug>.users.models import User


@transaction.atomic
def puzzle_attempt_record(
    *,
    user: User,
    puzzle: Puzzle,
    solved: bool,
    time_taken_ms: int,
) -> PuzzleAttempt:
    """Record puzzle attempt and update ratings (Glicko-2)."""
    user_rating = user.puzzle_rating
    rating_before = user_rating.rating

    # Calculate Glicko-2 rating update
    new_user_rating, new_puzzle_rating = calculate_glicko2_update(
        player_rating=user_rating.rating,
        player_rd=user_rating.rating_deviation,
        opponent_rating=puzzle.rating,
        opponent_rd=puzzle.rating_deviation,
        score=1.0 if solved else 0.0,
    )

    # Update user rating
    user_rating.rating = new_user_rating
    if solved:
        user_rating.puzzles_solved += 1
        user_rating.current_streak += 1
        user_rating.best_streak = max(user_rating.best_streak, user_rating.current_streak)
    else:
        user_rating.puzzles_failed += 1
        user_rating.current_streak = 0
    user_rating.full_clean()
    user_rating.save()

    # Update puzzle rating
    puzzle.rating = new_puzzle_rating
    puzzle.play_count += 1
    puzzle.full_clean()
    puzzle.save(update_fields=['rating', 'play_count'])

    # Create attempt record
    attempt = PuzzleAttempt(
        user=user,
        puzzle=puzzle,
        solved=solved,
        time_taken_ms=time_taken_ms,
        rating_before=rating_before,
        rating_after=new_user_rating,
    )
    attempt.full_clean()
    attempt.save()

    return attempt
```

### Selectors

Selectors handle read operations (queries):

```python
# <project_slug>/puzzles/selectors.py
from django.db.models import QuerySet

from <project_slug>.puzzles.models import Puzzle, PuzzleAttempt, UserPuzzleRating
from <project_slug>.users.models import User


def puzzle_get_next(*, user: User, themes: list[str] | None = None) -> Puzzle | None:
    """Select a puzzle matching user's rating and optional theme filters."""
    user_rating = user.puzzle_rating.rating

    queryset = Puzzle.objects.filter(
        rating__gte=user_rating - 200,
        rating__lte=user_rating + 200,
        popularity__gte=0,
    )

    if themes:
        queryset = queryset.filter(
            theme_assignments__theme__name__in=themes
        ).distinct()

    return queryset.order_by('?').first()


def puzzle_leaderboard_list(*, limit: int = 100) -> QuerySet[UserPuzzleRating]:
    """Get top puzzle solvers by rating."""
    return UserPuzzleRating.objects.select_related('user').order_by('-rating')[:limit]


def puzzle_storm_leaderboard_list(*, limit: int = 100) -> QuerySet[UserPuzzleRating]:
    """Get top Puzzle Storm scores."""
    return UserPuzzleRating.objects.select_related('user').filter(
        storm_best__gt=0
    ).order_by('-storm_best')[:limit]


def puzzle_attempt_list_for_user(*, user: User, limit: int = 50) -> QuerySet[PuzzleAttempt]:
    """Get recent puzzle attempts for a user."""
    return PuzzleAttempt.objects.filter(user=user).select_related('puzzle').order_by('-created_at')[:limit]


def puzzle_list_by_theme(*, theme: str, rating_range: tuple[int, int] | None = None) -> QuerySet[Puzzle]:
    """Get puzzles filtered by theme and optional rating range."""
    queryset = Puzzle.objects.filter(theme_assignments__theme__name=theme)

    if rating_range:
        min_rating, max_rating = rating_range
        queryset = queryset.filter(rating__gte=min_rating, rating__lte=max_rating)

    return queryset.order_by('-popularity')
```

### API Endpoints

APIs use nested `InputSerializer`/`OutputSerializer` classes and call services/selectors:

```python
# <project_slug>/puzzles/apis.py
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from <project_slug>.puzzles.models import Puzzle
from <project_slug>.puzzles.selectors import puzzle_get_next
from <project_slug>.puzzles.services import puzzle_attempt_record


class PuzzleNextApi(APIView):
    """Get next puzzle for user."""

    class OutputSerializer(serializers.Serializer):
        lichess_id = serializers.CharField()
        fen = serializers.CharField()
        moves = serializers.CharField()
        rating = serializers.IntegerField()
        themes = serializers.ListField(child=serializers.CharField())

    def get(self, request):
        themes = request.query_params.getlist('themes')
        puzzle = puzzle_get_next(user=request.user, themes=themes or None)

        if not puzzle:
            return Response({'error': 'No puzzle available'}, status=status.HTTP_404_NOT_FOUND)

        return Response(self.OutputSerializer(puzzle).data)


class PuzzleAttemptCreateApi(APIView):
    """Record puzzle attempt."""

    class InputSerializer(serializers.Serializer):
        solved = serializers.BooleanField()
        time_taken_ms = serializers.IntegerField(min_value=0)

    class OutputSerializer(serializers.Serializer):
        rating_before = serializers.IntegerField()
        rating_after = serializers.IntegerField()
        rating_diff = serializers.SerializerMethodField()

        def get_rating_diff(self, obj):
            return obj.rating_after - obj.rating_before

    def post(self, request, puzzle_id):
        puzzle = get_object_or_404(Puzzle, lichess_id=puzzle_id)

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attempt = puzzle_attempt_record(
            user=request.user,
            puzzle=puzzle,
            **serializer.validated_data,
        )

        return Response(self.OutputSerializer(attempt).data, status=status.HTTP_201_CREATED)
```

---

## Frontend Components

### React Component Structure (Bulletproof Pattern)

> **IMPORTANT**: No barrel files (`index.ts`). Use direct imports. File names in kebab-case.

```
src/features/puzzles/
├── api/                            # TanStack Query hooks (three-part pattern)
│   ├── get-next-puzzle.ts          # Query: schema + fetcher + hook
│   └── create-puzzle-attempt.ts    # Mutation: schema + fetcher + hook
├── components/                      # Feature-scoped components (kebab-case)
│   ├── puzzle-board.tsx            # Chessground integration
│   ├── puzzle-controls.tsx         # Hint, retry, next buttons
│   ├── puzzle-rating.tsx           # Rating display with change
│   ├── theme-selector.tsx          # Theme filter dropdown
│   ├── storm-timer.tsx             # Countdown with combo display
│   └── streak-counter.tsx          # Current/best streak
├── hooks/                           # Feature-specific hooks
│   ├── use-puzzle.ts               # Puzzle state management
│   └── use-storm-game.ts           # Storm mode logic
├── types/                           # Zod schemas + TypeScript types
│   └── puzzle.ts                   # NOT index.ts
└── routes/                          # Route components
    ├── puzzle-page.tsx             # Standard puzzle mode
    ├── storm-page.tsx              # Puzzle Storm
    ├── streak-page.tsx             # Puzzle Streak
    └── racer-page.tsx              # Multiplayer racer
```

**Import Pattern:**
```typescript
// ✅ CORRECT: Direct imports
import { PuzzleBoard } from '@/features/puzzles/components/puzzle-board';
import { useNextPuzzle } from '@/features/puzzles/api/get-next-puzzle';
import { puzzleSchema, type Puzzle } from '@/features/puzzles/types/puzzle';
```

### Puzzle State Machine

```typescript
type PuzzleState =
  | 'loading'
  | 'playing'        // Waiting for user move
  | 'opponent_move'  // Animating opponent response
  | 'correct'        // Move was correct, continue or complete
  | 'failed'         // Wrong move
  | 'complete';      // Puzzle solved

interface PuzzleContext {
  puzzle: Puzzle;
  currentFen: string;
  moveIndex: number;
  state: PuzzleState;
  userRatingBefore: number;
  userRatingAfter: number | null;
}
```

---

## Data Import

### Lichess Puzzle CSV Format

| Field | Type | Description |
|-------|------|-------------|
| PuzzleId | string | Unique identifier |
| FEN | string | Position before opponent's move |
| Moves | string | UCI moves (first is opponent's) |
| Rating | int | Glicko-2 rating |
| RatingDeviation | int | Rating confidence |
| Popularity | int | -100 to 100 |
| NbPlays | int | Play count |
| Themes | string | Comma-separated theme names |
| GameUrl | string | Source game URL |
| OpeningTags | string | Opening classification |

### Import Command

```python
# puzzles/management/commands/import_puzzles.py

class Command(BaseCommand):
    def handle(self, *args, **options):
        csv_path = options['csv_path']

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            puzzles = []

            for row in reader:
                puzzles.append(Puzzle(
                    lichess_id=row['PuzzleId'],
                    fen=row['FEN'],
                    moves=row['Moves'],
                    rating=int(row['Rating']),
                    rating_deviation=int(row['RatingDeviation']),
                    popularity=int(row['Popularity']),
                    play_count=int(row['NbPlays']),
                    game_url=row['GameUrl'],
                    opening_tags=row['OpeningTags'],
                ))

                if len(puzzles) >= 10000:
                    Puzzle.objects.bulk_create(puzzles, ignore_conflicts=True)
                    puzzles = []

            if puzzles:
                Puzzle.objects.bulk_create(puzzles, ignore_conflicts=True)
```

---

## Related Documents

- [RESEARCH.md](./RESEARCH.md) - Detailed Lichess training feature research
- [Analysis Board](./analysis-board.md) - Engine analysis integration
- [Rating System](../02-core-features/rating-system.md) - Glicko-2 implementation details

---

*Document created: December 2025*
