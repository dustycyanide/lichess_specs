---
title: Tablebase Integration
category: content
status: draft
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
lichess_equivalent: lila-tablebase
dependencies:
  - python-chess
  - syzygy-tables
priority: low
---

# Tablebase Integration

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md); Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md).

## Overview

Tablebase integration provides perfect endgame play analysis for positions with 7 or fewer pieces. Users can see the theoretical result and optimal moves for any supported endgame position.

## Feature Summary

| Aspect | Details |
|--------|---------|
| Technology | Syzygy Tablebases |
| Coverage | Up to 7 pieces (including kings) |
| Variants | Standard, Atomic, Antichess |
| Data Size | ~18.4 TB (7-piece) |

---

## Syzygy Tablebase Background

### What Are Tablebases?

Tablebases are precomputed databases containing the theoretical result and distance to mate/conversion for every possible position with a given number of pieces.

### Syzygy Specifics

- **Developer**: Ronald de Man (6-piece, 2013), Bojun Guo (7-piece, 2018)
- **7-piece positions**: 423,836,835,667,331 unique legal positions
- **Compression**: Reduced from 140 TB to 18.4 TB through efficient encoding

### Table Types

| Type | Purpose | Size | Usage |
|------|---------|------|-------|
| WDL | Win/Draw/Loss | Smaller | SSD-optimized, used during search |
| DTZ | Distance to Zero | Larger | Shows moves to reset 50-move counter |
| DTM | Distance to Mate | Largest | Optional, shows exact mate distance |

---

## Architecture

### Lichess Implementation

- **Service**: lila-tablebase (Rust + shakmaty-syzygy)
- **Average Request**: 23 WDL probes + 70 DTZ probes
- **Bottleneck**: Disk I/O

### Django/React Implementation Options

#### Option A: Self-Hosted (Full Control)

```
backend/
  <project_slug>/
    tablebase/
      services/
        probe.py         # Syzygy probing service
        cache.py         # Result caching
      apis/
        tablebase.py     # REST endpoints
```

> **Hacksoft Django Styleguide Notes**:
> - Services use keyword-only arguments after `*` (e.g., `def probe_position(*, fen: str, variant: str = "standard")`)
> - All service functions have full type annotations
> - Use `@transaction.atomic` for services that perform multiple writes
> - Call `full_clean()` before `save()` on model instances

**Requirements:**
- 7-piece tables: ~18.4 TB storage
- Fast SSD storage (NVMe recommended)
- Significant disk I/O capacity

**Pros**: No external dependencies, full control
**Cons**: Massive storage requirements, infrastructure cost

#### Option B: Proxy to Lichess API (Recommended for MVP)

```python
# services/tablebase.py
import httpx

LICHESS_TABLEBASE_URL = "https://tablebase.lichess.ovh"

async def probe_position(fen: str, variant: str = "standard") -> dict:
    """Proxy tablebase request to Lichess API."""
    async with httpx.AsyncClient() as client:
        # Replace spaces with underscores in FEN
        safe_fen = fen.replace(" ", "_")
        response = await client.get(
            f"{LICHESS_TABLEBASE_URL}/{variant}",
            params={"fen": safe_fen}
        )
        return response.json()
```

**Pros**: No storage requirements, immediate availability
**Cons**: External dependency, rate limits apply

#### Option C: Hybrid (6-piece Local, 7-piece Remote)

- Host 6-piece tables locally (~150 GB)
- Proxy 7-piece requests to Lichess
- Best balance of independence and practicality

**Recommended for production**: Option C

---

## API Design

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tablebase/standard` | GET | Standard chess position |
| `/api/tablebase/atomic` | GET | Atomic chess position |
| `/api/tablebase/antichess` | GET | Antichess position |
| `/api/tablebase/mainline` | GET | DTZ mainline sequence |

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `fen` | string | Position in FEN format (use _ for spaces) |

### Response Format

```json
{
  "category": "win",
  "dtz": 15,
  "dtm": 23,
  "checkmate": false,
  "stalemate": false,
  "moves": [
    {
      "uci": "e5e6",
      "san": "Ke6",
      "category": "win",
      "dtz": -14,
      "dtm": -22
    },
    {
      "uci": "e5d5",
      "san": "Kd5",
      "category": "draw",
      "dtz": 0,
      "dtm": null
    }
  ]
}
```

### Response Categories

| Category | Meaning |
|----------|---------|
| `win` | Winning position |
| `loss` | Losing position |
| `draw` | Drawn position |
| `cursed-win` | Would win but 50-move rule prevents |
| `blessed-loss` | Would lose but 50-move rule saves |
| `maybe-win` | Exact result unknown (DTZ rounding) |
| `maybe-loss` | Exact result unknown (DTZ rounding) |
| `unknown` | Position not in tablebase |

### Error Responses

| Code | Meaning |
|------|---------|
| 400 | Invalid FEN position |
| 404 | Position not in tablebase (>7 pieces) |
| 429 | Rate limit exceeded |

---

## Data Models

### TablebaseCache (optional, for caching results)

```python
class TablebaseCache(models.Model):
    fen_key = models.CharField(max_length=100, primary_key=True)
    variant = models.CharField(max_length=20, default="standard")
    category = models.CharField(max_length=20)
    dtz = models.IntegerField(null=True)
    dtm = models.IntegerField(null=True)
    moves_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['variant', 'created_at']),
        ]
```

---

## Frontend Integration

### Analysis Board Integration

The tablebase should integrate with the analysis board:

```
frontend/
  src/
    features/
      analysis/
        components/
          tablebase-panel.tsx    # Tablebase results display
          tablebase-moves.tsx    # Move list with evaluations
        hooks/
          use-tablebase.ts       # Fetch tablebase data
        api/
          tablebase.ts           # API client
```

> **Bulletproof React Styleguide Notes**:
> - Use kebab-case for file names (e.g., `tablebase-panel.tsx`, not `TablebasePanel.tsx`)
> - No barrel files (`index.ts` re-exports) - use direct imports
> - Import components directly: `import { TablebasePanel } from '@/features/analysis/components/tablebase-panel'`

### UI Components

**TablebasePanel**
- Shows current position evaluation (Win/Draw/Loss)
- Displays DTZ/DTM when available
- Color-coded move list (green=win, yellow=draw, red=loss)

**Integration Points**
- Auto-query when position has <=7 pieces
- Show "Tablebase" indicator in analysis
- Override engine eval with tablebase result

---

## Implementation Phases

### Phase 1: Lichess Proxy (MVP)

1. Create proxy service to Lichess tablebase API
2. Add caching layer (Redis) for common positions
3. Integrate with analysis board UI
4. Handle rate limiting gracefully

### Phase 2: Local 6-Piece Tables

1. Download and deploy 6-piece Syzygy tables (~150 GB)
2. Integrate python-chess syzygy probing
3. Fall back to Lichess for 7-piece positions

### Phase 3: Full 7-Piece Hosting (Optional)

1. Provision 20+ TB storage infrastructure
2. Download and deploy 7-piece tables
3. Remove external dependency

---

## Using python-chess for Probing

```python
import chess
import chess.syzygy

# Initialize tablebase (once at startup)
tablebase = chess.syzygy.Tablebase()
tablebase.add_directory("/path/to/syzygy/wdl")
tablebase.add_directory("/path/to/syzygy/dtz")

def probe_wdl(fen: str) -> int:
    """Probe WDL result. Returns -2 to 2."""
    board = chess.Board(fen)
    try:
        return tablebase.probe_wdl(board)
    except KeyError:
        return None  # Position not in tablebase

def probe_dtz(fen: str) -> int:
    """Probe DTZ result."""
    board = chess.Board(fen)
    try:
        return tablebase.probe_dtz(board)
    except KeyError:
        return None
```

### WDL Values

| Value | Meaning |
|-------|---------|
| 2 | Win (unconditional) |
| 1 | Cursed win (win, but 50-move blocks) |
| 0 | Draw |
| -1 | Blessed loss (loss, but 50-move saves) |
| -2 | Loss (unconditional) |

---

## Performance Considerations

### Caching Strategy

- Cache all tablebase results in Redis
- Positions are deterministic - cache indefinitely
- Key format: `tablebase:{variant}:{fen_normalized}`

### Rate Limiting (if proxying)

- Implement client-side rate limiting
- Queue requests during high traffic
- Show "calculating" state to users

### Disk I/O Optimization (if self-hosting)

- Use NVMe SSDs for table storage
- Configure kernel for large file reads
- Consider memory-mapped file access

---

## Storage Requirements

| Table Set | Size | Notes |
|-----------|------|-------|
| 3-4 piece | ~100 MB | Included with python-chess |
| 5 piece | ~1 GB | Easy to host |
| 6 piece | ~150 GB | Practical for most setups |
| 7 piece | ~18.4 TB | Requires significant infrastructure |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `python-chess` | Board representation, Syzygy probing |
| `httpx` | Async HTTP client (for Lichess proxy) |
| `redis` | Result caching |

---

## Success Metrics

- Response time < 500ms for cached positions
- Cache hit rate > 90% (many positions repeat)
- 100% accuracy (tablebases are provably correct)

---

## References

- [lila-tablebase](https://github.com/lichess-org/lila-tablebase)
- [shakmaty-syzygy](https://crates.io/crates/shakmaty-syzygy)
- [Syzygy-tables.info](https://syzygy-tables.info/)
- [python-chess Syzygy docs](https://python-chess.readthedocs.io/en/latest/syzygy.html)
- [Chessprogramming Syzygy](https://www.chessprogramming.org/Syzygy_Bases)
