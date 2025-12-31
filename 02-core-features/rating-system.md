---
title: Rating System
category: core-features
algorithm: Glicko-2
styleguide: hacksoft-django-styleguide
lichess_equivalent: scalachess/rating
status: complete
---

# Rating System Specification

This document specifies the Glicko-2 rating system implementation for our Django/React Lichess clone.

> **Styleguide Reference**: Rating calculations are implemented in **services** (e.g., `rating_update_for_game`). The `Rating` model stores data only; calculation logic lives in services. Services use keyword-only args with `*`, type annotations, `@transaction.atomic` for data integrity, and `full_clean()` before `save()`.

## Overview

Lichess uses the **Glicko-2** rating system, an improvement over the original Glicko system and traditional Elo. It provides more accurate ratings by tracking rating uncertainty (deviation) and volatility.

| Lichess | Our Stack |
|---------|-----------|
| scalachess/rating (Scala) | glicko2 Python library or custom implementation |
| Separate ratings per time control | Same approach |

## Glicko-2 Fundamentals

### Three Rating Components

Unlike Elo (single number), Glicko-2 tracks three values per player:

| Component | Symbol | Description | Typical Range |
|-----------|--------|-------------|---------------|
| **Rating (r)** | μ | Skill estimate | 400-2800 |
| **Rating Deviation (RD)** | φ | Uncertainty in rating | 30-350 |
| **Volatility (σ)** | σ | Expected rating fluctuation | 0.03-0.1 |

### Key Concepts

1. **Rating Deviation (RD)**: Decreases with more games, increases over time without play
2. **Volatility**: High for players with inconsistent performance
3. **Rating Period**: Games are processed in batches (Lichess: per game for faster updates)
4. **Tau (τ)**: System constant controlling volatility changes (typically 0.3-1.2)

## Lichess Implementation Details

From the scalachess `GlickoCalculator`:

```scala
// Key parameters from Lichess
tau: Tau = Tau.default               // System constant
ratingPeriodsPerDay: RatingPeriodsPerDay = RatingPeriodsPerDay.default
colorAdvantage: ColorAdvantage = ColorAdvantage.zero  // White piece advantage
```

### Player Model

```scala
case class Player(
  glicko: Glicko,           // rating, deviation, volatility
  numberOfResults: Int,      // games played
  lastRatingPeriodEnd: Option[Instant]
)

case class Glicko(
  rating: Double,
  deviation: Double,
  volatility: Double
)
```

## Django Implementation

### Installation

```bash
pip install glicko2
```

Or implement from scratch for more control.

### Rating Model

```python
# <project_slug>/ratings/models.py
from django.db import models
from django.conf import settings

class PlayerRating(models.Model):
    """Glicko-2 rating for a specific time control."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings'
    )

    # Time control category
    time_control = models.CharField(max_length=20, choices=[
        ('ultrabullet', 'UltraBullet'),  # < 30 seconds
        ('bullet', 'Bullet'),             # < 3 minutes
        ('blitz', 'Blitz'),               # 3-8 minutes
        ('rapid', 'Rapid'),               # 8-25 minutes
        ('classical', 'Classical'),       # > 25 minutes
        ('correspondence', 'Correspondence'),
    ])

    # Glicko-2 components
    rating = models.FloatField(default=1500.0)
    deviation = models.FloatField(default=350.0)  # High uncertainty for new players
    volatility = models.FloatField(default=0.06)

    # Tracking
    games_played = models.IntegerField(default=0)
    last_game_at = models.DateTimeField(null=True, blank=True)

    # Peak rating (for display)
    peak_rating = models.FloatField(default=1500.0)

    class Meta:
        unique_together = ['user', 'time_control']
        indexes = [
            models.Index(fields=['time_control', '-rating']),  # For leaderboards
        ]

    @property
    def display_rating(self) -> int:
        """Rounded rating for display."""
        return round(self.rating)

    @property
    def is_provisional(self) -> bool:
        """Provisional if RD is high (few games)."""
        return self.deviation > 110 or self.games_played < 5
```

### Glicko-2 Calculator Service

```python
# <project_slug>/ratings/services.py
import math
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

# Glicko-2 constants
TAU = 0.5  # System constant (Lichess default)
INITIAL_RATING = 1500.0
INITIAL_RD = 350.0
INITIAL_VOLATILITY = 0.06
GLICKO2_SCALE = 173.7178  # Conversion factor

@dataclass
class Glicko2Rating:
    rating: float
    deviation: float
    volatility: float

    @classmethod
    def default(cls) -> 'Glicko2Rating':
        return cls(INITIAL_RATING, INITIAL_RD, INITIAL_VOLATILITY)

    def to_glicko2_scale(self) -> tuple[float, float]:
        """Convert to Glicko-2 internal scale."""
        mu = (self.rating - 1500) / GLICKO2_SCALE
        phi = self.deviation / GLICKO2_SCALE
        return mu, phi

    @classmethod
    def from_glicko2_scale(cls, mu: float, phi: float, sigma: float) -> 'Glicko2Rating':
        """Convert from Glicko-2 internal scale."""
        return cls(
            rating=mu * GLICKO2_SCALE + 1500,
            deviation=phi * GLICKO2_SCALE,
            volatility=sigma
        )


def calculate_new_ratings(
    *,
    white: Glicko2Rating,
    black: Glicko2Rating,
    outcome: float,  # 1.0 = white wins, 0.5 = draw, 0.0 = black wins
    white_color_advantage: float = 0.0
) -> tuple[Glicko2Rating, Glicko2Rating]:
    """
    Calculate new ratings after a game.

    Uses the Glicko-2 algorithm as implemented by Lichess.
    """
    # Convert to Glicko-2 scale
    mu_w, phi_w = white.to_glicko2_scale()
    mu_b, phi_b = black.to_glicko2_scale()
    sigma_w = white.volatility
    sigma_b = black.volatility

    # Apply color advantage
    mu_w_adj = mu_w + white_color_advantage / GLICKO2_SCALE

    # Calculate g(φ) - reduces impact of opponent's uncertainty
    def g(phi: float) -> float:
        return 1 / math.sqrt(1 + 3 * phi**2 / math.pi**2)

    # Expected score E(μ, μ_j, φ_j)
    def expected_score(mu: float, mu_j: float, phi_j: float) -> float:
        return 1 / (1 + math.exp(-g(phi_j) * (mu - mu_j)))

    # Calculate for white
    g_b = g(phi_b)
    e_w = expected_score(mu_w_adj, mu_b, phi_b)

    # Calculate for black
    g_w = g(phi_w)
    e_b = expected_score(mu_b, mu_w_adj, phi_w)

    # Variance v
    v_w = 1 / (g_b**2 * e_w * (1 - e_w))
    v_b = 1 / (g_w**2 * e_b * (1 - e_b))

    # Delta (rating change before applying volatility)
    delta_w = v_w * g_b * (outcome - e_w)
    delta_b = v_b * g_w * ((1 - outcome) - e_b)

    # New volatility (simplified - use Illinois algorithm for full implementation)
    new_sigma_w = _compute_volatility(sigma_w, phi_w, v_w, delta_w)
    new_sigma_b = _compute_volatility(sigma_b, phi_b, v_b, delta_b)

    # New deviation
    phi_star_w = math.sqrt(phi_w**2 + new_sigma_w**2)
    phi_star_b = math.sqrt(phi_b**2 + new_sigma_b**2)

    new_phi_w = 1 / math.sqrt(1/phi_star_w**2 + 1/v_w)
    new_phi_b = 1 / math.sqrt(1/phi_star_b**2 + 1/v_b)

    # New rating
    new_mu_w = mu_w + new_phi_w**2 * g_b * (outcome - e_w)
    new_mu_b = mu_b + new_phi_b**2 * g_w * ((1 - outcome) - e_b)

    return (
        Glicko2Rating.from_glicko2_scale(new_mu_w, new_phi_w, new_sigma_w),
        Glicko2Rating.from_glicko2_scale(new_mu_b, new_phi_b, new_sigma_b),
    )


def _compute_volatility(sigma: float, phi: float, v: float, delta: float) -> float:
    """
    Compute new volatility using the Illinois algorithm.
    This is Step 5 of the Glicko-2 algorithm.
    """
    a = math.log(sigma**2)
    epsilon = 0.000001

    def f(x: float) -> float:
        ex = math.exp(x)
        num = ex * (delta**2 - phi**2 - v - ex)
        denom = 2 * (phi**2 + v + ex)**2
        return num / denom - (x - a) / TAU**2

    # Illinois algorithm to find root
    A = a
    if delta**2 > phi**2 + v:
        B = math.log(delta**2 - phi**2 - v)
    else:
        k = 1
        while f(a - k * TAU) < 0:
            k += 1
        B = a - k * TAU

    fa = f(A)
    fb = f(B)

    while abs(B - A) > epsilon:
        C = A + (A - B) * fa / (fb - fa)
        fc = f(C)
        if fc * fb <= 0:
            A = B
            fa = fb
        else:
            fa /= 2
        B = C
        fb = fc

    return math.exp(A / 2)


def increase_deviation_for_inactivity(
    *,
    rating: Glicko2Rating,
    days_inactive: int,
    rating_periods_per_day: float = 0.21436
) -> Glicko2Rating:
    """
    Increase RD for players who haven't played recently.
    Lichess default: ~0.21436 rating periods per day.
    """
    if days_inactive <= 0:
        return rating

    periods = days_inactive * rating_periods_per_day
    _, phi = rating.to_glicko2_scale()
    sigma = rating.volatility

    # New deviation increases over time
    new_phi = math.sqrt(phi**2 + periods * sigma**2)

    # Cap at initial RD
    new_phi = min(new_phi, INITIAL_RD / GLICKO2_SCALE)

    return Glicko2Rating(
        rating=rating.rating,
        deviation=new_phi * GLICKO2_SCALE,
        volatility=rating.volatility
    )
```

### Rating Update Service

Following Hacksoft pattern with `@transaction.atomic` for data integrity:

```python
# <project_slug>/ratings/services.py (continued)
from django.db import transaction
from django.utils import timezone

from <project_slug>.ratings.models import PlayerRating


from <project_slug>.games.models import Game


@transaction.atomic
def rating_update_for_game(*, game: Game) -> tuple[PlayerRating, PlayerRating]:
    """
    Update ratings after a game ends.

    Following Hacksoft pattern: keyword-only args, type annotations,
    @transaction.atomic for data integrity, full_clean() before save().

    Args:
        game: Game model instance with white_player, black_player, status
    """
    time_control = categorize_time_control(time_control=game.time_control)

    # Get or create ratings
    white_rating, _ = PlayerRating.objects.get_or_create(
        user=game.white_player,
        time_control=time_control,
        defaults={'rating': 1500, 'deviation': 350, 'volatility': 0.06}
    )
    black_rating, _ = PlayerRating.objects.get_or_create(
        user=game.black_player,
        time_control=time_control,
        defaults={'rating': 1500, 'deviation': 350, 'volatility': 0.06}
    )

    # Determine outcome
    if game.status == 'white_wins':
        outcome = 1.0
    elif game.status == 'black_wins':
        outcome = 0.0
    else:  # draw
        outcome = 0.5

    # Apply inactivity RD increase
    now = timezone.now()
    if white_rating.last_game_at:
        days = (now - white_rating.last_game_at).days
        white_glicko = increase_deviation_for_inactivity(
            rating=Glicko2Rating(white_rating.rating, white_rating.deviation, white_rating.volatility),
            days_inactive=days
        )
    else:
        white_glicko = Glicko2Rating(white_rating.rating, white_rating.deviation, white_rating.volatility)

    if black_rating.last_game_at:
        days = (now - black_rating.last_game_at).days
        black_glicko = increase_deviation_for_inactivity(
            rating=Glicko2Rating(black_rating.rating, black_rating.deviation, black_rating.volatility),
            days_inactive=days
        )
    else:
        black_glicko = Glicko2Rating(black_rating.rating, black_rating.deviation, black_rating.volatility)

    # Calculate new ratings
    new_white, new_black = calculate_new_ratings(
        white=white_glicko,
        black=black_glicko,
        outcome=outcome
    )

    # Update database - full_clean() before save() per Hacksoft pattern
    white_rating.rating = new_white.rating
    white_rating.deviation = new_white.deviation
    white_rating.volatility = new_white.volatility
    white_rating.games_played += 1
    white_rating.last_game_at = now
    white_rating.peak_rating = max(white_rating.peak_rating, new_white.rating)
    white_rating.full_clean()
    white_rating.save()

    black_rating.rating = new_black.rating
    black_rating.deviation = new_black.deviation
    black_rating.volatility = new_black.volatility
    black_rating.games_played += 1
    black_rating.last_game_at = now
    black_rating.peak_rating = max(black_rating.peak_rating, new_black.rating)
    black_rating.full_clean()
    black_rating.save()

    return white_rating, black_rating


def categorize_time_control(*, time_control: str) -> str:
    """
    Categorize a time control string (e.g., "5+3") into a category.

    Time is initial_minutes + increment * 40 (estimated game length)
    """
    try:
        parts = time_control.split('+')
        initial = int(parts[0])
        increment = int(parts[1]) if len(parts) > 1 else 0
        estimated_time = initial * 60 + increment * 40  # in seconds

        if estimated_time < 30:
            return 'ultrabullet'
        elif estimated_time < 180:
            return 'bullet'
        elif estimated_time < 480:
            return 'blitz'
        elif estimated_time < 1500:
            return 'rapid'
        else:
            return 'classical'
    except (ValueError, IndexError):
        return 'rapid'  # Default
```

## Rating Display

### Confidence Interval

```python
def get_rating_range(rating: PlayerRating, confidence: float = 0.95) -> tuple[int, int]:
    """
    Get confidence interval for rating.
    95% confidence = ~2 standard deviations
    """
    z = 1.96 if confidence == 0.95 else 2.58  # 99%
    margin = z * rating.deviation
    return (
        round(rating.rating - margin),
        round(rating.rating + margin)
    )
```

### Provisional Ratings

```python
def format_rating(rating: PlayerRating) -> str:
    """Format rating for display with provisional marker."""
    if rating.is_provisional:
        return f"{rating.display_rating}?"
    return str(rating.display_rating)
```

## Time Control Categories

| Category | Estimated Time | Examples |
|----------|----------------|----------|
| UltraBullet | < 30s | 0+1 |
| Bullet | 30s - 3min | 1+0, 2+1 |
| Blitz | 3-8min | 3+0, 5+0, 3+2 |
| Rapid | 8-25min | 10+0, 15+10 |
| Classical | > 25min | 30+0, 30+20 |
| Correspondence | Days | - |

## Matchmaking Integration

Use ratings for fair matchmaking:

```python
def find_opponent(player: PlayerRating, tolerance: float = 100.0) -> Optional[User]:
    """
    Find an opponent within rating tolerance.
    Wider tolerance = faster match, less balanced
    """
    return PlayerRating.objects.filter(
        time_control=player.time_control,
        rating__gte=player.rating - tolerance,
        rating__lte=player.rating + tolerance
    ).exclude(
        user=player.user
    ).order_by('?').first()
```

## Performance Considerations

1. **Per-Game Updates**: Update ratings immediately after each game (like Lichess)
2. **Indexing**: Index `(time_control, rating)` for fast leaderboard queries
3. **Caching**: Cache leaderboards, invalidate on rating changes
4. **Inactivity**: Run periodic job to increase RD for inactive players

## Sources

- [Glicko-2 Paper (Mark Glickman)](http://www.glicko.net/glicko/glicko2.pdf)
- [scalachess/rating](https://github.com/lichess-org/scalachess/tree/master/rating)
- [Lichess Rating FAQ](https://lichess.org/faq#rating)
- [glicko2 Python Package](https://pypi.org/project/glicko2/)
