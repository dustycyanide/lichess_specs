---
title: Caching Strategy
category: architecture
stack: Redis
styleguide: hacksoft-django-styleguide
status: draft
---

# Caching Strategy

This document outlines Redis caching patterns for the chess platform, mapping Lichess's caching approach to Django.

> **Styleguide Reference**: Cache invalidation logic belongs in **services** (Hacksoft pattern). Models should not handle caching directly.

## Redis Usage Overview

Lichess uses Redis for multiple purposes. We follow the same pattern:

| Use Case | Lichess | Our Approach |
|----------|---------|--------------|
| Channel layer | Redis pub/sub | Django Channels + Redis |
| Session storage | Redis | Django sessions + Redis |
| Cache | Redis | django-redis |
| Rate limiting | Redis | django-ratelimit + Redis |
| Leaderboards | Redis sorted sets | Redis sorted sets |
| Online presence | Redis sets | Redis sets with TTL |
| Game state | In-memory actors | Redis hashes |

## Django Cache Configuration

```python
# config/settings/base.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
        "KEY_PREFIX": "chess",
    },
    # Separate cache for sessions (different DB)
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "session",
    },
}

# Use Redis for sessions
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "sessions"
```

## Caching Patterns

### 1. User Ratings Cache

Ratings are frequently accessed but rarely change:

```python
# <project_slug>/users/selectors.py
from django.core.cache import cache
from <project_slug>.users.models import Rating, User

RATING_CACHE_TTL = 300  # 5 minutes

def user_get_ratings(*, user: User) -> dict[str, int]:
    """Get all ratings for a user, with caching."""
    cache_key = f"user:{user.id}:ratings"

    ratings = cache.get(cache_key)
    if ratings is not None:
        return ratings

    ratings = {
        r.time_control: r.rating
        for r in Rating.objects.filter(user=user)
    }

    cache.set(cache_key, ratings, RATING_CACHE_TTL)
    return ratings


def user_invalidate_ratings_cache(*, user: User) -> None:
    """Invalidate ratings cache after a game."""
    cache.delete(f"user:{user.id}:ratings")
```

### 2. Leaderboards with Sorted Sets

Redis sorted sets are perfect for leaderboards:

```python
# <project_slug>/users/leaderboard.py
from django_redis import get_redis_connection
from <project_slug>.users.models import User, TimeControl

redis = get_redis_connection("default")

LEADERBOARD_KEY = "leaderboard:{time_control}"


def leaderboard_update(
    *,
    user: User,
    time_control: str,
    rating: int
) -> None:
    """Update user's position in leaderboard."""
    key = LEADERBOARD_KEY.format(time_control=time_control)
    redis.zadd(key, {str(user.id): rating})


def leaderboard_get_top(
    *,
    time_control: str,
    limit: int = 100
) -> list[dict]:
    """Get top players for a time control."""
    key = LEADERBOARD_KEY.format(time_control=time_control)

    # Get top players with scores (ratings)
    results = redis.zrevrange(key, 0, limit - 1, withscores=True)

    user_ids = [uuid for uuid, _ in results]
    users = {
        str(u.id): u
        for u in User.objects.filter(id__in=user_ids)
    }

    return [
        {
            "rank": idx + 1,
            "user": users[user_id].username,
            "rating": int(rating),
        }
        for idx, (user_id, rating) in enumerate(results)
        if user_id in users
    ]


def leaderboard_get_rank(
    *,
    user: User,
    time_control: str
) -> int | None:
    """Get user's rank in a leaderboard (1-indexed)."""
    key = LEADERBOARD_KEY.format(time_control=time_control)
    rank = redis.zrevrank(key, str(user.id))
    return rank + 1 if rank is not None else None
```

### 3. Online Users Tracking

Track who's online using Redis sets with TTL:

```python
# <project_slug>/users/presence.py
from django_redis import get_redis_connection
from datetime import timedelta

redis = get_redis_connection("default")

ONLINE_KEY = "online:users"
ONLINE_TTL = 60  # Consider offline after 60 seconds


def presence_mark_online(*, user_id: str) -> None:
    """Mark user as online with automatic expiry."""
    redis.zadd(ONLINE_KEY, {user_id: time.time()})


def presence_mark_offline(*, user_id: str) -> None:
    """Explicitly mark user as offline."""
    redis.zrem(ONLINE_KEY, user_id)


def presence_get_online_count() -> int:
    """Get count of online users."""
    cutoff = time.time() - ONLINE_TTL
    # Remove stale entries
    redis.zremrangebyscore(ONLINE_KEY, 0, cutoff)
    return redis.zcard(ONLINE_KEY)


def presence_is_online(*, user_id: str) -> bool:
    """Check if a specific user is online."""
    score = redis.zscore(ONLINE_KEY, user_id)
    if score is None:
        return False
    return (time.time() - score) < ONLINE_TTL


def presence_get_online_friends(*, user_id: str, friend_ids: list[str]) -> list[str]:
    """Get which friends are currently online."""
    cutoff = time.time() - ONLINE_TTL
    online = []

    for fid in friend_ids:
        score = redis.zscore(ONLINE_KEY, fid)
        if score and (time.time() - score) < ONLINE_TTL:
            online.append(fid)

    return online
```

### 4. Game State Cache

Cache active game state for fast WebSocket access:

```python
# <project_slug>/games/cache.py
from django_redis import get_redis_connection
import json

redis = get_redis_connection("default")

GAME_KEY = "game:{game_id}:state"
GAME_TTL = 3600 * 24  # 24 hours


def game_cache_set(*, game_id: str, state: dict) -> None:
    """Cache current game state."""
    key = GAME_KEY.format(game_id=game_id)
    redis.hset(key, mapping={
        "fen": state["fen"],
        "moves": state["moves"],
        "wc": str(state["white_clock"]),
        "bc": str(state["black_clock"]),
        "status": state["status"],
        "ply": str(state["ply"]),
    })
    redis.expire(key, GAME_TTL)


def game_cache_get(*, game_id: str) -> dict | None:
    """Get cached game state."""
    key = GAME_KEY.format(game_id=game_id)
    data = redis.hgetall(key)

    if not data:
        return None

    return {
        "fen": data[b"fen"].decode(),
        "moves": data[b"moves"].decode(),
        "white_clock": int(data[b"wc"]),
        "black_clock": int(data[b"bc"]),
        "status": data[b"status"].decode(),
        "ply": int(data[b"ply"]),
    }


def game_cache_update_move(
    *,
    game_id: str,
    fen: str,
    move: str,
    white_clock: int,
    black_clock: int,
    ply: int
) -> None:
    """Update cached game state after a move."""
    key = GAME_KEY.format(game_id=game_id)

    # Append move to existing moves
    current_moves = redis.hget(key, "moves")
    if current_moves:
        new_moves = f"{current_moves.decode()} {move}".strip()
    else:
        new_moves = move

    redis.hset(key, mapping={
        "fen": fen,
        "moves": new_moves,
        "wc": str(white_clock),
        "bc": str(black_clock),
        "ply": str(ply),
    })


def game_cache_delete(*, game_id: str) -> None:
    """Remove game from cache (when finished)."""
    key = GAME_KEY.format(game_id=game_id)
    redis.delete(key)
```

### 5. Rate Limiting

Protect APIs from abuse:

```python
# <project_slug>/common/ratelimit.py
from django_redis import get_redis_connection
import time

redis = get_redis_connection("default")


def is_rate_limited(
    *,
    key: str,
    limit: int,
    window: int  # seconds
) -> bool:
    """
    Check if action is rate limited using sliding window.

    Args:
        key: Unique identifier (e.g., "api:user:123:move")
        limit: Max requests allowed
        window: Time window in seconds
    """
    now = time.time()
    window_start = now - window

    pipe = redis.pipeline()

    # Remove old entries
    pipe.zremrangebyscore(key, 0, window_start)

    # Count current entries
    pipe.zcard(key)

    # Add new entry
    pipe.zadd(key, {str(now): now})

    # Set expiry
    pipe.expire(key, window)

    results = pipe.execute()
    current_count = results[1]

    return current_count >= limit


# Usage in views
def check_move_rate_limit(*, user_id: str) -> bool:
    """Allow max 60 moves per minute (1 per second average)."""
    return is_rate_limited(
        key=f"ratelimit:move:{user_id}",
        limit=60,
        window=60
    )
```

### 6. Puzzle Queue / Daily Puzzle

Cache puzzle selections:

```python
# <project_slug>/puzzles/cache.py
from django.core.cache import cache
from <project_slug>.puzzles.models import Puzzle
import random

DAILY_PUZZLE_KEY = "puzzle:daily:{date}"
USER_PUZZLE_QUEUE_KEY = "puzzle:queue:{user_id}"


def puzzle_get_daily() -> Puzzle:
    """Get today's daily puzzle (same for all users)."""
    from datetime import date
    today = date.today().isoformat()
    cache_key = DAILY_PUZZLE_KEY.format(date=today)

    puzzle_id = cache.get(cache_key)
    if puzzle_id:
        return Puzzle.objects.get(id=puzzle_id)

    # Select a popular puzzle in the 1400-1600 range
    puzzle = Puzzle.objects.filter(
        rating__gte=1400,
        rating__lte=1600,
        popularity__gte=50
    ).order_by('?').first()

    if puzzle:
        cache.set(cache_key, puzzle.id, timeout=86400)  # 24 hours

    return puzzle


def puzzle_get_for_user(*, user_id: str, user_rating: int) -> list[str]:
    """Get queued puzzles for a user based on their rating."""
    cache_key = USER_PUZZLE_QUEUE_KEY.format(user_id=user_id)

    queue = cache.get(cache_key)
    if queue and len(queue) > 0:
        return queue

    # Generate new queue of puzzle IDs
    rating_min = max(500, user_rating - 200)
    rating_max = min(3000, user_rating + 200)

    puzzles = list(
        Puzzle.objects.filter(
            rating__gte=rating_min,
            rating__lte=rating_max
        ).values_list('id', flat=True)[:100]
    )
    random.shuffle(puzzles)

    cache.set(cache_key, puzzles, timeout=3600)  # 1 hour
    return puzzles
```

### 7. Opening Explorer Cache

Cache opening statistics:

```python
# <project_slug>/analysis/cache.py
from django.core.cache import cache
import hashlib

OPENING_CACHE_TTL = 3600 * 24  # 24 hours


def opening_get_stats(*, fen: str, speeds: list[str], ratings: list[int]) -> dict | None:
    """Get cached opening statistics for a position."""
    cache_key = _opening_cache_key(fen, speeds, ratings)
    return cache.get(cache_key)


def opening_set_stats(
    *,
    fen: str,
    speeds: list[str],
    ratings: list[int],
    stats: dict
) -> None:
    """Cache opening statistics."""
    cache_key = _opening_cache_key(fen, speeds, ratings)
    cache.set(cache_key, stats, OPENING_CACHE_TTL)


def _opening_cache_key(fen: str, speeds: list[str], ratings: list[int]) -> str:
    """Generate cache key for opening stats."""
    params = f"{fen}:{','.join(sorted(speeds))}:{','.join(map(str, sorted(ratings)))}"
    hash_val = hashlib.md5(params.encode()).hexdigest()[:12]
    return f"opening:{hash_val}"
```

## Cache Invalidation Patterns

### Signal-Based Invalidation

```python
# <project_slug>/users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from <project_slug>.users.models import Rating
from <project_slug>.users.selectors import user_invalidate_ratings_cache
from <project_slug>.users.leaderboard import leaderboard_update


@receiver(post_save, sender=Rating)
def on_rating_updated(sender, instance, **kwargs):
    """Invalidate caches when rating changes."""
    user_invalidate_ratings_cache(user=instance.user)

    leaderboard_update(
        user=instance.user,
        time_control=instance.time_control,
        rating=instance.rating
    )
```

### Cache-Aside Pattern

```python
def get_user_profile(user_id: str) -> dict:
    """Get user profile with cache-aside pattern."""
    cache_key = f"user:{user_id}:profile"

    # Try cache first
    profile = cache.get(cache_key)
    if profile is not None:
        return profile

    # Cache miss - load from DB
    user = User.objects.get(id=user_id)
    profile = {
        "username": user.username,
        "rating": user_get_ratings(user=user),
        "country": user.country,
        # ... other fields
    }

    # Store in cache
    cache.set(cache_key, profile, timeout=300)

    return profile
```

## Monitoring & Metrics

```python
# <project_slug>/common/cache_stats.py
from django_redis import get_redis_connection

def get_cache_stats() -> dict:
    """Get Redis cache statistics."""
    redis = get_redis_connection("default")
    info = redis.info()

    return {
        "used_memory": info["used_memory_human"],
        "connected_clients": info["connected_clients"],
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0),
        "hit_rate": (
            info.get("keyspace_hits", 0) /
            max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
        ),
    }
```

## Key Design Decisions

### Separate Redis Databases

Use different Redis databases (or separate instances) for:
- **DB 0**: Application cache
- **DB 1**: Sessions
- **DB 2**: Celery broker
- **DB 3**: Channel layer

### TTL Strategy

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| User ratings | 5 min | Frequently accessed, rarely changes |
| Game state | 24 hours | Active games need fast access |
| Leaderboards | No expiry | Sorted sets, continuously updated |
| Online presence | 60 sec | Stale detection |
| Opening stats | 24 hours | Expensive to compute |
| Daily puzzle | 24 hours | Changes daily |

### Memory Management

```python
# In production settings
CACHES = {
    "default": {
        # ...
        "OPTIONS": {
            # Evict least recently used when memory is full
            "MAX_ENTRIES": 10000,
        }
    }
}
```

For Redis server, configure maxmemory policy:
```
maxmemory 2gb
maxmemory-policy allkeys-lru
```
