---
title: Open Source Resources
category: resources
resources:
  - name: Chessground
    url: https://github.com/lichess-org/chessground
    description: Reusable board UI
  - name: Stockfish.wasm
    url: https://github.com/lichess-org/stockfish.wasm
    description: Browser-side analysis engine
  - name: python-chess
    url: https://github.com/niklasf/python-chess
    description: Python chess rules library
  - name: chess.js
    url: https://github.com/jhlywa/chess.js
    description: TypeScript chess logic library
status: draft
---

# Open Source Libraries & Tools

This document catalogs the open source libraries and tools we'll use to build the Lichess clone, with implementation guidance for our Django/React stack.

---

## Frontend Libraries

### Chessground (Board UI)

**Repository**: [lichess-org/chessground](https://github.com/lichess-org/chessground)
**License**: GPL-3.0

The official chess UI library from Lichess. Battle-tested with millions of daily games.

#### Why Chessground

- **Small footprint**: 10KB gzipped, zero dependencies
- **Touch-optimized**: Full mobile/tablet support
- **Feature-rich**: Premoves, predrop, SVG arrows/circles, 3D support
- **Chess variant support**: 960, atomic, crazyhouse, etc.
- **Custom DOM diffing**: Optimized performance with minimal DOM writes

#### React Integration

```bash
pnpm add @lichess-org/chessground @react-chess/chessground
```

**Recommended React wrapper**: [@react-chess/chessground](https://www.npmjs.com/package/@react-chess/chessground)

Alternative wrappers:
| Package | Notes |
|---------|-------|
| `@bezalel6/react-chessground` | Modern wrapper with move validation, themes, promotion dialogs |
| `ruilisi/react-chessground` | Includes onMove callback, randomMove functions |

#### CSS Requirements

```typescript
// In your component or global styles
import '@lichess-org/chessground/assets/chessground.base.css';
import '@lichess-org/chessground/assets/chessground.brown.css';
import '@lichess-org/chessground/assets/chessground.cburnett.css';
```

#### Basic Usage

```tsx
import { Chessground } from '@react-chess/chessground';

interface BoardProps {
  fen: string;
  orientation: 'white' | 'black';
  onMove: (from: string, to: string) => void;
}

export function ChessBoard({ fen, orientation, onMove }: BoardProps) {
  const config = {
    fen,
    orientation,
    movable: {
      free: false,
      color: orientation,
      events: {
        after: (orig: string, dest: string) => onMove(orig, dest),
      },
    },
    drawable: {
      enabled: true,
      visible: true,
    },
  };

  return <Chessground config={config} />;
}
```

---

### chess.js (Chess Logic)

**Repository**: [jhlywa/chess.js](https://github.com/jhlywa/chess.js)
**License**: BSD

TypeScript library for chess move generation and validation. Pairs with Chessground for complete frontend chess functionality.

#### Installation

```bash
pnpm add chess.js
```

#### Key Features

- Legal move generation and validation
- FEN/PGN parsing and generation
- Check, checkmate, stalemate detection
- Move history with undo support
- SAN (Standard Algebraic Notation) parsing

#### Integration with Chessground

```tsx
import { Chess } from 'chess.js';
import { Chessground } from '@react-chess/chessground';
import { useState, useCallback } from 'react';

export function InteractiveBoard() {
  const [game, setGame] = useState(new Chess());

  const handleMove = useCallback((from: string, to: string) => {
    const newGame = new Chess(game.fen());
    const move = newGame.move({ from, to, promotion: 'q' });

    if (move) {
      setGame(newGame);
      return true;
    }
    return false;
  }, [game]);

  const getLegalMoves = useCallback(() => {
    const dests = new Map();
    game.moves({ verbose: true }).forEach((move) => {
      const from = move.from;
      const to = move.to;
      if (!dests.has(from)) dests.set(from, []);
      dests.get(from).push(to);
    });
    return dests;
  }, [game]);

  return (
    <Chessground
      config={{
        fen: game.fen(),
        movable: {
          free: false,
          dests: getLegalMoves(),
          events: { after: handleMove },
        },
      }}
    />
  );
}
```

---

### Stockfish.wasm (Browser Analysis)

**Repository**: [lichess-org/stockfish.wasm](https://github.com/lichess-org/stockfish.wasm)
**License**: GPL-3.0

WebAssembly port of Stockfish for browser-side chess analysis.

#### Variants

| Package | Use Case | Size |
|---------|----------|------|
| `lichess-org/stockfish.wasm` | Multi-threaded analysis | ~150KB gzipped |
| `nmrugg/stockfish.js` | NNUE support (stronger) | ~7-75MB |
| `@chessle/chess.js-extended` | Bundled with Web Workers | Varies |

#### Browser Compatibility

| Browser | Version | Support |
|---------|---------|---------|
| Chromium | 79+ | Full |
| Firefox | 79+ | Full |
| Safari | All | Not supported (use single-threaded fallback) |

#### Required CORS Headers

Multi-threaded WASM requires special headers:

```python
# Django middleware
class StockfishCORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/static/stockfish/'):
            response['Cross-Origin-Embedder-Policy'] = 'require-corp'
            response['Cross-Origin-Opener-Policy'] = 'same-origin'
        return response
```

#### Web Worker Integration

```typescript
// stockfish.worker.ts
let stockfish: any = null;

self.onmessage = async (e) => {
  if (e.data.type === 'init') {
    stockfish = await Stockfish();
    stockfish.addMessageListener((line: string) => {
      self.postMessage({ type: 'output', line });
    });
    stockfish.postMessage('uci');
  } else if (e.data.type === 'analyze') {
    const { fen, depth } = e.data;
    stockfish.postMessage(`position fen ${fen}`);
    stockfish.postMessage(`go depth ${depth}`);
  }
};
```

```tsx
// useStockfish.ts
import { useEffect, useRef, useCallback, useState } from 'react';

interface AnalysisResult {
  bestMove: string;
  evaluation: number;
  depth: number;
  pv: string[];
}

export function useStockfish() {
  const workerRef = useRef<Worker | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    workerRef.current = new Worker(
      new URL('./stockfish.worker.ts', import.meta.url)
    );
    workerRef.current.postMessage({ type: 'init' });

    workerRef.current.onmessage = (e) => {
      if (e.data.type === 'output') {
        // Parse UCI output
        const line = e.data.line;
        if (line.startsWith('bestmove')) {
          const move = line.split(' ')[1];
          setResult((prev) => prev ? { ...prev, bestMove: move } : null);
        }
      }
    };

    return () => workerRef.current?.terminate();
  }, []);

  const analyze = useCallback((fen: string, depth = 20) => {
    workerRef.current?.postMessage({ type: 'analyze', fen, depth });
  }, []);

  return { analyze, result };
}
```

#### Performance Recommendations

1. **Lazy load** - Don't bundle with main JS; load on demand
2. **Use Web Workers** - Keep UI responsive during analysis
3. **Limit hash size** - Check `navigator.deviceMemory` before setting
4. **Fallback** - Provide single-threaded fallback for Safari

---

## Backend Libraries

### python-chess (Chess Logic)

**Repository**: [niklasf/python-chess](https://github.com/niklasf/python-chess)
**License**: GPL-3.0

Comprehensive Python library for chess programming. Handles all chess logic on the Django backend.

#### Installation

```bash
uv add chess
```

#### Core Features

- Legal move generation and validation
- Check, checkmate, stalemate detection
- Threefold/fivefold repetition tracking
- 50-move and 75-move rule support
- Pin detection with directional information
- Insufficient material recognition

#### Format Support

- **FEN**: Position representation
- **PGN**: Game notation with headers, comments, variations
- **SAN**: Standard Algebraic Notation
- **UCI**: Universal Chess Interface moves
- **EPD**: Extended Position Description

#### Chess Variants

Supports: Standard, Chess960, Suicide, Giveaway, Atomic, King of the Hill, Racing Kings, Horde, Three-check, Crazyhouse

#### Django Service Example

```python
# backend/apps/chess/services/game_logic.py
import chess
import chess.pgn
from io import StringIO


def create_game() -> dict:
    """Create a new game with starting position."""
    board = chess.Board()
    return {
        'fen': board.fen(),
        'legal_moves': [move.uci() for move in board.legal_moves],
    }


def make_move(fen: str, move_uci: str) -> dict:
    """Execute a move and return the new position."""
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)

    if move not in board.legal_moves:
        raise ValueError(f"Illegal move: {move_uci}")

    board.push(move)

    return {
        'fen': board.fen(),
        'legal_moves': [m.uci() for m in board.legal_moves],
        'is_check': board.is_check(),
        'is_checkmate': board.is_checkmate(),
        'is_stalemate': board.is_stalemate(),
        'is_game_over': board.is_game_over(),
        'outcome': _get_outcome(board),
    }


def _get_outcome(board: chess.Board) -> dict | None:
    """Get game outcome if game is over."""
    outcome = board.outcome()
    if outcome is None:
        return None

    return {
        'winner': 'white' if outcome.winner else ('black' if outcome.winner is False else None),
        'termination': outcome.termination.name,
    }


def validate_position(fen: str) -> bool:
    """Check if a FEN string represents a valid position."""
    try:
        board = chess.Board(fen)
        return board.is_valid()
    except ValueError:
        return False


def parse_pgn(pgn_text: str) -> list[dict]:
    """Parse a PGN string and return game data."""
    games = []
    pgn_io = StringIO(pgn_text)

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        games.append({
            'headers': dict(game.headers),
            'moves': [move.uci() for move in game.mainline_moves()],
            'result': game.headers.get('Result'),
        })

    return games
```

#### Engine Integration (Stockfish)

```python
# backend/apps/analysis/services/engine.py
import chess.engine
from typing import AsyncIterator
from contextlib import asynccontextmanager


@asynccontextmanager
async def get_engine(path: str = "/usr/local/bin/stockfish"):
    """Async context manager for Stockfish engine."""
    transport, engine = await chess.engine.popen_uci(path)
    try:
        yield engine
    finally:
        await engine.quit()


async def analyze_position(
    fen: str,
    depth: int = 20,
    multipv: int = 3,
) -> list[dict]:
    """Analyze a position and return top variations."""
    async with get_engine() as engine:
        board = chess.Board(fen)
        info = await engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
            multipv=multipv,
        )

        return [
            {
                'pv': [move.uci() for move in line.get('pv', [])],
                'score': _format_score(line.get('score')),
                'depth': line.get('depth'),
            }
            for line in info
        ]


def _format_score(score) -> dict:
    """Format engine score for API response."""
    if score is None:
        return {'type': 'unknown'}

    pov = score.white()
    if pov.is_mate():
        return {'type': 'mate', 'value': pov.mate()}
    return {'type': 'cp', 'value': pov.score()}
```

#### Syzygy Tablebase Probing

```python
# backend/apps/analysis/services/tablebase.py
import chess.syzygy


class TablebaseService:
    def __init__(self, path: str = "/data/syzygy"):
        self.tablebase = chess.syzygy.open_tablebase(path)

    def probe(self, fen: str) -> dict | None:
        """Probe tablebase for endgame position."""
        board = chess.Board(fen)

        # Tablebases only work for positions with ≤7 pieces
        if len(board.piece_map()) > 7:
            return None

        try:
            wdl = self.tablebase.probe_wdl(board)
            dtz = self.tablebase.probe_dtz(board)

            return {
                'wdl': wdl,  # -2 to 2 (loss to win)
                'dtz': dtz,  # Distance to zeroing move
                'result': self._wdl_to_result(wdl),
            }
        except chess.syzygy.MissingTableError:
            return None

    def _wdl_to_result(self, wdl: int) -> str:
        mapping = {
            2: 'win',
            1: 'cursed_win',  # Win but 50-move rule
            0: 'draw',
            -1: 'blessed_loss',  # Loss but 50-move rule
            -2: 'loss',
        }
        return mapping.get(wdl, 'unknown')
```

---

## Alternative Libraries

### react-chessboard

**Repository**: [react-chessboard](https://www.npmjs.com/package/react-chessboard)
**License**: MIT

Alternative React chessboard with simpler API but larger bundle size.

#### When to Consider

| Criteria | Chessground | react-chessboard |
|----------|-------------|------------------|
| Size | 10KB gzipped | Larger (react-dnd) |
| Origin | Lichess (battle-tested) | Community |
| Features | SVG arrows, premoves | Custom pieces, styles |
| Learning curve | Steeper (config-heavy) | React-native API |
| License | GPL-3.0 | MIT |

**Our choice**: Chessground for Lichess-like experience and proven reliability.

---

### cm-chessboard

**Repository**: [shaack/cm-chessboard](https://github.com/shaack/cm-chessboard)
**License**: MIT

Lightweight ES6 chessboard with SVG rendering. Good alternative if GPL-3.0 is a concern.

---

## License Compliance

| Library | License | Requirement |
|---------|---------|-------------|
| Chessground | GPL-3.0 | Source disclosure if distributed |
| python-chess | GPL-3.0 | Source disclosure if distributed |
| Stockfish.wasm | GPL-3.0 | Source disclosure if distributed |
| chess.js | BSD | Attribution |

**Note**: Since we're building a web application (not distributing software), GPL-3.0 allows us to use these libraries without open-sourcing our entire codebase. The copyleft provisions apply to distribution, not server-side use.

---

## Recommended Stack

### Frontend
```
React + @react-chess/chessground + chess.js + stockfish.wasm
```

### Backend
```
Django + python-chess + Stockfish (via UCI for deep analysis)
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
├─────────────────────────────────────────────────────────────┤
│  Chessground (UI)  ←→  chess.js (validation/display logic)  │
│         ↓                                                    │
│  stockfish.wasm (quick browser analysis via Web Worker)      │
└─────────────────────────────────────────────────────────────┘
                              ↕ WebSocket / REST
┌─────────────────────────────────────────────────────────────┐
│                         Backend                              │
├─────────────────────────────────────────────────────────────┤
│  python-chess (authoritative game state, move validation)    │
│         ↓                                                    │
│  Stockfish binary (deep analysis, game review)               │
│  Syzygy tablebases (endgame lookup)                          │
└─────────────────────────────────────────────────────────────┘
```
