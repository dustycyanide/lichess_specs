---
title: Opening Explorer
category: content
status: draft
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
lichess_equivalent: lila-openingexplorer
dependencies:
  - python-chess
  - redis
  - postgresql
priority: medium
---

# Opening Explorer

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md); Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md).

## Overview

The Opening Explorer provides move statistics aggregated from millions of chess games, allowing users to research openings by seeing which moves are most commonly played and their success rates.

## Feature Summary

Three database tabs providing different perspectives on opening theory:

| Database | Source | Size | Use Case |
|----------|--------|------|----------|
| Masters | OTB games (2200+ FIDE) | 2M+ games | Classical theory |
| Lichess | Platform games | Billions | Real-world usage |
| Player | Individual user | Varies | Opponent prep |

---

## Architecture

### Lichess Implementation

- **Service**: lila-openingexplorer (Rust + RocksDB)
- **Performance**: ~12,000 requests/minute
- **Infrastructure**: 4 RAID10 disks, 128GB RAM

### Django/React Implementation

#### Backend Services

```
backend/
  <project_slug>/
    opening_explorer/
      models.py          # PositionStats, MasterGame
      services/
        aggregation.py   # Position statistics calculation
        indexing.py      # Game indexing service
      selectors/
        position_stats.py  # Query position data
      apis/
        explorer.py      # REST endpoints
```

> **Hacksoft Django Styleguide Notes**:
> - Services use keyword-only arguments after `*` (e.g., `def create_stats(*, position_key: str, database: str)`)
> - All service functions have full type annotations
> - Use `@transaction.atomic` for services that perform multiple writes
> - Call `full_clean()` before `save()` on model instances

#### Database Design

**Option A: PostgreSQL with Materialized Views**
- Store games in normalized tables
- Pre-compute position statistics via materialized views
- Refresh periodically (hourly/daily)
- Pros: Simpler stack, good for MVP
- Cons: Slower updates, storage-heavy for positions

**Option B: Redis + PostgreSQL Hybrid**
- Redis for hot position cache (top ~1M positions)
- PostgreSQL for long-tail storage
- Pros: Fast lookups, memory-efficient
- Cons: More complex architecture

**Recommended for MVP**: Option A with caching layer

#### Position Key Format

Store positions using FEN-derived keys:
```python
def position_key(fen: str) -> str:
    """Generate compact position key from FEN."""
    # Strip move counters, keep only board + turn + castling + en passant
    parts = fen.split()
    return "_".join(parts[:4])
```

---

## Data Models

### PositionStats

```python
class PositionStats(models.Model):
    position_key = models.CharField(max_length=100, primary_key=True)
    database = models.CharField(max_length=20)  # masters, lichess, player

    # Move statistics (JSONB for flexibility)
    moves = models.JSONField(default=dict)
    # Format: {"e2e4": {"white": 1000, "draws": 500, "black": 400, "avg_rating": 2100}}

    total_games = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['database', 'total_games']),
        ]
```

### MasterGame (for Masters database)

```python
class MasterGame(models.Model):
    id = models.UUIDField(primary_key=True)
    white_player = models.CharField(max_length=100)
    black_player = models.CharField(max_length=100)
    white_elo = models.IntegerField()
    black_elo = models.IntegerField()
    result = models.CharField(max_length=10)  # 1-0, 0-1, 1/2-1/2
    year = models.IntegerField()
    event = models.CharField(max_length=200)
    pgn = models.TextField()
    moves_uci = models.JSONField()  # List of UCI moves
```

---

## API Design

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/explorer/masters` | GET | Master game statistics |
| `/api/explorer/lichess` | GET | Platform game statistics |
| `/api/explorer/player/{username}` | GET | Player-specific stats |

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `fen` | string | Starting position (default: initial) |
| `play` | string | Comma-separated UCI moves |
| `speeds` | string | Filter by time control |
| `ratings` | string | Filter by rating range |
| `color` | string | Filter by color (player DB) |

### Response Format

```json
{
  "position": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3",
  "opening": {
    "eco": "B00",
    "name": "King's Pawn Opening"
  },
  "moves": [
    {
      "uci": "c7c5",
      "san": "c5",
      "white": 15234,
      "draws": 8901,
      "black": 12456,
      "averageRating": 1856
    }
  ],
  "topGames": [],
  "recentGames": []
}
```

---

## Implementation Phases

### Phase 1: Masters Database (MVP)

1. Import master games from Lichess open database
2. Index positions using python-chess
3. Build aggregation service
4. Create REST API endpoints
5. Frontend integration with chessground

### Phase 2: Platform Database

1. Index user games on completion
2. Background job for aggregation
3. Rating range filtering
4. Time control filtering

### Phase 3: Player Database

1. On-demand player indexing
2. Color filtering
3. Recent games display

---

## Frontend Components

```
frontend/
  src/
    features/
      opening-explorer/
        api/
          explorer.ts       # API client
        components/
          explorer-panel.tsx   # Main container
          move-table.tsx       # Move statistics table
          database-tabs.tsx    # Masters/Lichess/Player tabs
          filter-controls.tsx  # Rating, speed filters
        hooks/
          use-explorer-data.ts
        types/
          index.ts
```

> **Bulletproof React Styleguide Notes**:
> - Use kebab-case for file names (e.g., `explorer-panel.tsx`, not `ExplorerPanel.tsx`)
> - No barrel files (`index.ts` re-exports) - use direct imports
> - Import components directly: `import { ExplorerPanel } from '@/features/opening-explorer/components/explorer-panel'`

### Key UI Elements

- **Move Table**: Shows moves sorted by popularity with win/draw/loss bars
- **Database Selector**: Tabs for Masters, Lichess, Player databases
- **Filters**: Rating range, time controls (Lichess DB only)
- **Game Samples**: Top games and recent games for each position

---

## Opening Name Integration

Use the [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings) repository:

- TSV files mapping FEN positions to ECO codes and names
- Import as static data during deployment
- Lookup opening name by position hash

```python
class OpeningName(models.Model):
    position_key = models.CharField(max_length=100, primary_key=True)
    eco = models.CharField(max_length=5)
    name = models.CharField(max_length=200)
    pgn = models.CharField(max_length=500)  # Canonical move sequence
```

---

## Performance Considerations

### Caching Strategy

- **L1 Cache**: Django cache (Redis) for hot positions
- **L2 Cache**: Materialized views for aggregated stats
- **Cache TTL**: 1 hour for Lichess DB, 24 hours for Masters

### Query Optimization

- Index on `position_key` + `database`
- Partial indexes for high-frequency positions
- Consider read replicas for explorer queries

### Indexing Pipeline

For indexing new games:
1. Parse PGN to extract moves
2. Generate position keys for each game state
3. Update move statistics incrementally
4. Batch updates for efficiency

---

## Data Sources

### Masters Database
- Lichess provides 2M+ OTB games from FIDE 2200+ players
- Download from [database.lichess.org](https://database.lichess.org/)
- Update periodically (monthly)

### Lichess Database (for development)
- Sample datasets available for testing
- Full database is petabytes (not practical for clone)
- Index user games played on our platform instead

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `python-chess` | Move generation, FEN parsing |
| `redis` | Position caching |
| `celery` | Background indexing jobs |

---

## Success Metrics

- API response time < 200ms for cached positions
- Position coverage: All games indexed within 1 hour
- Cache hit rate > 80% for opening positions

---

## References

- [lila-openingexplorer](https://github.com/lichess-org/lila-openingexplorer)
- [chess-openings](https://github.com/lichess-org/chess-openings)
- [Lichess API Documentation](https://lichess.org/api)
