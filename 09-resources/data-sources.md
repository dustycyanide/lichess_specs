---
title: Data Sources
category: resources
sources:
  - name: Lichess Game Database
    url: https://database.lichess.org/
    description: 7.2B+ rated games in PGN format
  - name: Puzzle Database
    url: https://database.lichess.org/#puzzles
    description: 5.6M+ puzzles with ratings and themes
  - name: Syzygy Tablebases
    url: https://syzygy-tables.info/
    description: Perfect endgame play for ≤7 pieces
  - name: Lichess Elite Database
    url: https://database.nikonoel.fr/
    description: Filtered high-rated games
status: draft
---

# Data Sources

This document covers the open data resources available for building chess features: game databases, puzzles, and endgame tablebases.

---

## Lichess Game Database

**Website**: [database.lichess.org](https://database.lichess.org/)
**License**: Creative Commons CC0 (Public Domain)

The largest freely available chess game database with over 7.2 billion rated games.

### Statistics

| Category | Count | Format |
|----------|-------|--------|
| Standard Games | 7,227,402,778+ | PGN |
| Antichess | 33.8M | PGN |
| Atomic | 26.1M | PGN |
| Chess960 | 26M | PGN |
| Crazyhouse | 27.7M | PGN |
| Horde | 6.6M | PGN |
| King of the Hill | 7.6M | PGN |
| Racing Kings | 5.8M | PGN |
| Three-check | 9.5M | PGN |

### File Format

- **Compression**: ZStandard (.zst)
- **Game format**: PGN (Portable Game Notation)
- **Organization**: Monthly files (not cumulative)
- **Size**: ~20GB compressed per month, ~7.1x larger uncompressed

### Special PGN Tags

```pgn
[WhiteTitle "BOT"]     ; Computer players
[BlackTitle "BOT"]
[Variant "Antichess"]  ; Variant games
[%eval 2.35]           ; Stockfish evaluation (centipawns)
[%eval #-4]            ; Mate in 4
[%clk 0:10:00]         ; Clock times (games from 2017+)
```

### Downloading and Processing

#### Decompression

```bash
# Fast parallel decompression (Unix)
pzstd -d lichess_db_standard_rated_2024-01.pgn.zst

# Streaming to Python (memory-efficient)
zstdcat lichess_db_standard_rated_2024-01.pgn.zst | python process_games.py
```

ZStandard archives are partially decompressable - you can cancel downloads mid-stream and still decompress what you have.

#### Django Management Command for Import

```python
# backend/apps/games/management/commands/import_lichess_games.py
import chess.pgn
import zstandard as zstd
from django.core.management.base import BaseCommand
from apps.games.models import Game


class Command(BaseCommand):
    help = 'Import games from Lichess database'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)
        parser.add_argument('--limit', type=int, default=None)

    def handle(self, *args, **options):
        file_path = options['file_path']
        limit = options['limit']
        count = 0

        with open(file_path, 'rb') as fh:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(fh) as reader:
                text_stream = io.TextIOWrapper(reader, encoding='utf-8')

                while True:
                    if limit and count >= limit:
                        break

                    game = chess.pgn.read_game(text_stream)
                    if game is None:
                        break

                    self._import_game(game)
                    count += 1

                    if count % 10000 == 0:
                        self.stdout.write(f'Imported {count} games')

        self.stdout.write(self.style.SUCCESS(f'Imported {count} games'))

    def _import_game(self, pgn_game):
        headers = pgn_game.headers

        Game.objects.create(
            lichess_id=self._extract_lichess_id(headers.get('Site', '')),
            white_player=headers.get('White'),
            black_player=headers.get('Black'),
            white_elo=int(headers.get('WhiteElo', 0)) or None,
            black_elo=int(headers.get('BlackElo', 0)) or None,
            result=headers.get('Result'),
            time_control=headers.get('TimeControl'),
            eco=headers.get('ECO'),
            opening=headers.get('Opening'),
            moves=[move.uci() for move in pgn_game.mainline_moves()],
            pgn=str(pgn_game),
        )

    def _extract_lichess_id(self, site_url: str) -> str | None:
        # Extract game ID from URL like https://lichess.org/abcd1234
        if 'lichess.org/' in site_url:
            return site_url.split('/')[-1]
        return None
```

### Lichess Elite Database

**Website**: [database.nikonoel.fr](https://database.nikonoel.fr/)

Filtered database containing only high-rated games:
- **Before Dec 2021**: 2400+ rated players vs 2200+ rated opponents
- **After Dec 2021**: 2500+ rated players vs 2300+ rated opponents
- Excludes bullet games

Useful for opening preparation and training data for stronger play patterns.

---

## Puzzle Database

**Download**: [database.lichess.org/#puzzles](https://database.lichess.org/#puzzles)
**License**: Creative Commons CC0 (Public Domain)

### Statistics

- **Total puzzles**: 5,600,086+
- **Format**: CSV (compressed with ZStandard)
- **Size**: ~250MB compressed
- **Updates**: Monthly

### CSV Schema

```csv
PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags
```

| Field | Description | Example |
|-------|-------------|---------|
| PuzzleId | Unique identifier | `09QS8` |
| FEN | Starting position | `r1bqkbnr/pppp1ppp/...` |
| Moves | Solution in UCI format | `e2e4 e7e5 g1f3` |
| Rating | Puzzle difficulty rating | `1500` |
| RatingDeviation | Rating uncertainty | `75` |
| Popularity | Score from -100 to 100 | `85` |
| NbPlays | Number of attempts | `12543` |
| Themes | Comma-separated tags | `fork,middlegame,short` |
| GameUrl | Source game on Lichess | `https://lichess.org/abc123` |
| OpeningTags | Opening name (before move 20) | `Italian_Game` |

### Puzzle Themes

Common themes for filtering/categorization:

| Theme | Description |
|-------|-------------|
| `fork` | Attacking two pieces at once |
| `pin` | Restricting piece movement |
| `skewer` | Attack through a piece |
| `discoveredAttack` | Moving piece reveals attack |
| `sacrifice` | Giving up material for advantage |
| `mateIn1`, `mateIn2`, etc. | Checkmate patterns |
| `endgame` | Endgame positions |
| `opening` | Opening traps/tactics |

### Django Model and Import

```python
# backend/apps/puzzles/models.py
from django.db import models


class Puzzle(models.Model):
    lichess_id = models.CharField(max_length=10, unique=True, db_index=True)
    fen = models.CharField(max_length=100)
    moves = models.JSONField()  # List of UCI moves
    rating = models.IntegerField(db_index=True)
    rating_deviation = models.IntegerField()
    popularity = models.IntegerField(db_index=True)
    nb_plays = models.IntegerField()
    themes = models.JSONField()  # List of theme strings
    game_url = models.URLField(blank=True)
    opening_tags = models.CharField(max_length=100, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['rating', 'popularity']),
            models.Index(fields=['themes'], name='puzzle_themes_gin',
                        opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return f"Puzzle {self.lichess_id} (Rating: {self.rating})"
```

```python
# backend/apps/puzzles/management/commands/import_puzzles.py
import csv
import zstandard as zstd
from django.core.management.base import BaseCommand
from apps.puzzles.models import Puzzle


class Command(BaseCommand):
    help = 'Import puzzles from Lichess puzzle database'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)
        parser.add_argument('--batch-size', type=int, default=5000)

    def handle(self, *args, **options):
        file_path = options['file_path']
        batch_size = options['batch_size']
        batch = []
        count = 0

        with open(file_path, 'rb') as fh:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(fh) as reader:
                text_stream = io.TextIOWrapper(reader, encoding='utf-8')
                csv_reader = csv.DictReader(text_stream)

                for row in csv_reader:
                    puzzle = Puzzle(
                        lichess_id=row['PuzzleId'],
                        fen=row['FEN'],
                        moves=row['Moves'].split(),
                        rating=int(row['Rating']),
                        rating_deviation=int(row['RatingDeviation']),
                        popularity=int(row['Popularity']),
                        nb_plays=int(row['NbPlays']),
                        themes=row['Themes'].split(',') if row['Themes'] else [],
                        game_url=row['GameUrl'],
                        opening_tags=row.get('OpeningTags', ''),
                    )
                    batch.append(puzzle)

                    if len(batch) >= batch_size:
                        Puzzle.objects.bulk_create(batch, ignore_conflicts=True)
                        count += len(batch)
                        batch = []
                        self.stdout.write(f'Imported {count} puzzles')

                if batch:
                    Puzzle.objects.bulk_create(batch, ignore_conflicts=True)
                    count += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Imported {count} puzzles'))
```

### Puzzle Service

```python
# backend/apps/puzzles/services/puzzle_service.py
from apps.puzzles.models import Puzzle
from django.db.models import Q
import random


def get_puzzle_for_rating(
    target_rating: int,
    rating_range: int = 100,
    themes: list[str] | None = None,
) -> Puzzle | None:
    """Get a random puzzle appropriate for the user's rating."""
    queryset = Puzzle.objects.filter(
        rating__gte=target_rating - rating_range,
        rating__lte=target_rating + rating_range,
        popularity__gte=0,  # Filter out disliked puzzles
    )

    if themes:
        # Filter by any matching theme
        theme_q = Q()
        for theme in themes:
            theme_q |= Q(themes__contains=[theme])
        queryset = queryset.filter(theme_q)

    # Get random puzzle efficiently
    count = queryset.count()
    if count == 0:
        return None

    random_index = random.randint(0, count - 1)
    return queryset[random_index]


def check_puzzle_solution(puzzle: Puzzle, moves: list[str]) -> dict:
    """Check if the provided moves solve the puzzle."""
    solution = puzzle.moves

    # First move is the opponent's move that sets up the puzzle
    # Solution starts from index 1
    player_solution = solution[1::2]  # Every other move starting from index 1

    correct_so_far = True
    for i, move in enumerate(moves):
        if i >= len(player_solution):
            break
        if move != player_solution[i]:
            correct_so_far = False
            break

    is_complete = len(moves) >= len(player_solution) and correct_so_far

    return {
        'correct': correct_so_far,
        'complete': is_complete,
        'expected_move': player_solution[len(moves)] if len(moves) < len(player_solution) else None,
        'opponent_response': solution[len(moves) * 2] if len(moves) * 2 < len(solution) else None,
    }
```

---

## Syzygy Tablebases

**Website**: [syzygy-tables.info](https://syzygy-tables.info/)
**License**: Public Domain

Perfect endgame play databases for positions with up to 7 pieces.

### Overview

- **Coverage**: Perfect play for up to 7 pieces
- **Metrics**: WDL (Win/Draw/Loss) and DTZ (Distance to Zeroing move)
- **50-move rule**: Available both with and without

### Storage Requirements

| Pieces | WDL Size | DTZ Size | Total |
|--------|----------|----------|-------|
| 3-5 | 378 MB | 561 MB | ~1 GB |
| 6 | 68.2 GB | 81.9 GB | ~150 GB |
| 7 | ~8 TB | ~10 TB | ~18 TB |

**Recommendation**:
- **MVP**: 3-5 piece tables (~1 GB)
- **Production**: 3-6 piece tables (~150 GB SSD)
- **Full**: Only if you have dedicated storage

### Download Sources

| Source | URL | Notes |
|--------|-----|-------|
| Lichess Mirror | tablebase.sesse.net | HTTP download |
| Massimiliano Goi | chess.massimilianogoi.com | 3-6 piece sets |
| Official Torrents | syzygy-tables.info | 6-7 piece sets |

### Download Script

```bash
#!/bin/bash
# download_syzygy.sh - Download 3-5 piece tablebases

TABLEBASE_DIR="/data/syzygy"
mkdir -p "$TABLEBASE_DIR"

# 3-4-5 piece tables (small, essential)
wget -r -np -nH --cut-dirs=1 -P "$TABLEBASE_DIR" \
  http://tablebase.sesse.net/syzygy/3-4-5/

echo "Downloaded 3-5 piece tablebases to $TABLEBASE_DIR"
```

### Lichess Tablebase API

For quick lookups without local storage, use the Lichess API:

**Endpoint**: `https://tablebase.lichess.ovh`

```python
# backend/apps/analysis/services/tablebase_api.py
import httpx
from functools import lru_cache


class TablebaseAPIService:
    BASE_URL = "https://tablebase.lichess.ovh"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def probe(self, fen: str) -> dict | None:
        """Query Lichess tablebase API for endgame position."""
        # URL-encode the FEN (spaces become underscores for path)
        encoded_fen = fen.replace(' ', '_')

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/standard",
                params={'fen': fen}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None

    async def get_mainline(self, fen: str) -> list[dict] | None:
        """Get the optimal move sequence from this position."""
        encoded_fen = fen.replace(' ', '_')

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/standard/mainline",
                params={'fen': fen}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None
```

#### API Response Format

```json
{
  "checkmate": false,
  "stalemate": false,
  "insufficient_material": false,
  "wdl": 2,
  "dtz": 15,
  "dtm": null,
  "moves": [
    {"uci": "e1d2", "san": "Kd2", "wdl": -2, "dtz": -14},
    {"uci": "e1f2", "san": "Kf2", "wdl": -2, "dtz": -14}
  ]
}
```

#### Rate Limiting

- ~130 requests before throttling begins
- For bulk queries, download tables and probe locally

### Local Probing with python-chess

```python
# backend/apps/analysis/services/tablebase_local.py
import chess.syzygy
from django.conf import settings


class LocalTablebaseService:
    """Local Syzygy tablebase probing using python-chess."""

    def __init__(self, path: str = None):
        path = path or settings.SYZYGY_PATH
        self.tablebase = chess.syzygy.open_tablebase(path)

    def probe(self, fen: str) -> dict | None:
        """Probe local tablebase for endgame position."""
        board = chess.Board(fen)

        # Check piece count (tablebases only work for ≤7 pieces)
        piece_count = len(board.piece_map())
        if piece_count > 7:
            return None

        try:
            wdl = self.tablebase.probe_wdl(board)
            dtz = self.tablebase.probe_dtz(board)

            return {
                'wdl': wdl,
                'dtz': dtz,
                'result': self._wdl_to_result(wdl),
                'piece_count': piece_count,
            }
        except chess.syzygy.MissingTableError:
            return None

    def get_best_move(self, fen: str) -> str | None:
        """Get the tablebase-optimal move for a position."""
        board = chess.Board(fen)

        if len(board.piece_map()) > 7:
            return None

        best_move = None
        best_dtz = None

        for move in board.legal_moves:
            board.push(move)
            try:
                dtz = -self.tablebase.probe_dtz(board)
                if best_dtz is None or self._is_better(dtz, best_dtz):
                    best_dtz = dtz
                    best_move = move
            except chess.syzygy.MissingTableError:
                pass
            board.pop()

        return best_move.uci() if best_move else None

    def _is_better(self, dtz1: int, dtz2: int) -> bool:
        """Compare DTZ values (lower absolute value is better for winning)."""
        # Positive DTZ = winning, negative = losing
        if dtz1 > 0 and dtz2 > 0:
            return dtz1 < dtz2  # Faster win
        if dtz1 < 0 and dtz2 < 0:
            return dtz1 > dtz2  # Slower loss
        return dtz1 > dtz2  # Win beats loss

    def _wdl_to_result(self, wdl: int) -> str:
        mapping = {
            2: 'win',
            1: 'cursed_win',
            0: 'draw',
            -1: 'blessed_loss',
            -2: 'loss',
        }
        return mapping.get(wdl, 'unknown')
```

### Hybrid Approach (Recommended)

```python
# backend/apps/analysis/services/tablebase.py
from apps.analysis.services.tablebase_local import LocalTablebaseService
from apps.analysis.services.tablebase_api import TablebaseAPIService
from django.conf import settings


class TablebaseService:
    """Hybrid tablebase service: local probing with API fallback."""

    def __init__(self):
        self.local = None
        self.api = TablebaseAPIService()

        if settings.SYZYGY_PATH:
            try:
                self.local = LocalTablebaseService(settings.SYZYGY_PATH)
            except Exception:
                pass  # Fall back to API only

    async def probe(self, fen: str) -> dict | None:
        """Probe tablebase, preferring local, falling back to API."""
        # Try local first (faster, no rate limits)
        if self.local:
            result = self.local.probe(fen)
            if result:
                result['source'] = 'local'
                return result

        # Fall back to API
        result = await self.api.probe(fen)
        if result:
            result['source'] = 'api'
        return result
```

### Storage Recommendations

| Storage Type | Use For | Notes |
|--------------|---------|-------|
| SSD | WDL tables | Accessed during search |
| HDD | DTZ tables | Accessed less frequently |
| API | 7-piece queries | Too large to store locally |

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Import Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Lichess Database (.zst)  →  Django Management Command       │
│         ↓                           ↓                        │
│  zstdcat (streaming)        bulk_create to PostgreSQL        │
│                                                              │
│  Puzzle CSV (.zst)         →  Django Management Command      │
│         ↓                           ↓                        │
│  CSV streaming              bulk_create with themes index    │
│                                                              │
│  Syzygy Tables             →  python-chess syzygy module     │
│         ↓                           ↓                        │
│  Local files (/data/syzygy)   probe_wdl / probe_dtz         │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Runtime Usage                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Opening Explorer  →  Query games by position (FEN prefix)   │
│                                                              │
│  Puzzle Training   →  Random puzzle by rating + themes       │
│                                                              │
│  Endgame Training  →  Tablebase probing for positions ≤7 pc  │
│                                                              │
│  Game Analysis     →  Stockfish + tablebase for endgames     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Django Settings

```python
# backend/config/settings/base.py

# Chess data paths
SYZYGY_PATH = env('SYZYGY_PATH', default='/data/syzygy')
LICHESS_DATA_PATH = env('LICHESS_DATA_PATH', default='/data/lichess')

# Tablebase API fallback
TABLEBASE_API_URL = 'https://tablebase.lichess.ovh'
TABLEBASE_API_TIMEOUT = 10  # seconds
```

---

## Required Python Packages

```toml
# pyproject.toml
[project]
dependencies = [
    "chess>=1.10.0",        # python-chess
    "zstandard>=0.22.0",    # ZStandard decompression
    "httpx>=0.27.0",        # Async HTTP for tablebase API
]
```

```bash
uv add chess zstandard httpx
```
