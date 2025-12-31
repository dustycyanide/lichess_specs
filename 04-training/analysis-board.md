---
title: Analysis Board
category: training
dependencies: Stockfish.wasm, Chessground
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
status: draft
lichess_equivalent: lichess.org/analysis
---

# Analysis Board

> Interactive chess position analysis with browser-based Stockfish engine

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) - services for writes, selectors for reads, explicit `<project_slug>/` imports. Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) - analysis feature in `features/analysis/` with direct imports, no barrel files, kebab-case filenames.

---

## Overview

The analysis board provides free-form position analysis using Stockfish running entirely in the browser via WebAssembly. Users can explore positions, analyze games, and study openings without server-side computation. The board integrates with Chessground for visualization and supports features like multiple analysis lines, evaluation graphs, and move annotations.

### Architecture Decision: Client-Side Only

Unlike Lichess (which offers both client-side WASM and server-side Fishnet analysis), we will use **browser-based analysis only** for MVP. This simplifies architecture and eliminates server compute costs while still providing powerful analysis capabilities.

---

## Technology Stack

### Stockfish.wasm

Browser-based Stockfish compiled to WebAssembly.

| Component | Size | Purpose |
|-----------|------|---------|
| stockfish.js | ~50KB | JavaScript loader |
| stockfish.wasm | ~350KB | WASM binary |
| stockfish.worker.js | ~5KB | Web Worker wrapper |
| **Total** | ~400KB (~150KB gzipped) | Full engine |

**Repositories**:
- [lichess-org/stockfish.wasm](https://github.com/lichess-org/stockfish.wasm) - Main WASM port
- [lichess-org/stockfish.js](https://github.com/lichess-org/stockfish.js) - Emscripten build
- [lichess-org/stockfish-nnue.wasm](https://github.com/lichess-org/stockfish-nnue.wasm) - NNUE support

### Required HTTP Headers

Multi-threaded WASM requires specific security headers:

```
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Opener-Policy: same-origin
```

### Browser Compatibility

| Browser | Support Level |
|---------|--------------|
| Chromium 79+ | Full multi-threaded WASM |
| Chromium 74-78 | Limited threading (2 threads, 16MB hash) |
| Firefox 79+ | Full multi-threaded WASM |
| Safari 15.2+ | Single-threaded WASM |
| Older browsers | Falls back to ASMJS |

---

## Features

### Engine Analysis

**Multiple Lines**:
- Configure 1-5 analysis lines simultaneously
- Each line shows principal variation (PV)
- Lines ranked by evaluation score

**Analysis Depth**:
- Typical browser depth: 22-27 plies
- Infinite mode: Runs until stopped or 99 plies
- Depth display shows current search progress

**Evaluation Display**:
- Centipawn score (e.g., +1.25 means White is ahead by 1.25 pawns)
- Mate-in-N notation for forced checkmates
- Evaluation from perspective of side to move

### Move Annotations

Moves are classified based on evaluation change:

| Classification | Criteria | Symbol |
|----------------|----------|--------|
| Brilliant | Best move in complex position | !! |
| Great | Strong move finding only good option | ! |
| Best | Engine's top choice | (none) |
| Good | Close to best | (none) |
| Inaccuracy | -50 to -100 centipawn loss | ?! |
| Mistake | -100 to -300 centipawn loss | ? |
| Blunder | > -300 centipawn loss | ?? |

**Modern Classification**: Use winning probability changes rather than pure centipawn loss. A 200cp drop in a winning position may not be a blunder if winning chances remain high.

### Evaluation Graph

Visual representation of game flow:
- X-axis: Move number
- Y-axis: Evaluation (White positive, Black negative)
- Clickable to navigate to any position
- Current position highlighted

### Position Setup

- Load from FEN string
- Load from PGN
- Set up position manually (drag pieces)
- Clear board / starting position buttons
- Side to move toggle
- Castling rights checkboxes
- En passant square selection

---

## Data Model

### Analysis Session

```python
# <project_slug>/analysis/models.py

from django.db import models

from <project_slug>.users.models import User


class AnalysisSession(models.Model):
    """Saved analysis session for registered users."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, blank=True)

    # Position
    initial_fen = models.CharField(max_length=100)
    current_fen = models.CharField(max_length=100)
    pgn = models.TextField(blank=True)  # Move history

    # Analysis data (cached engine output)
    analysis_cache = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]


class GameAnalysis(models.Model):
    """Analysis results for a completed game."""

    game = models.OneToOneField('games.Game', on_delete=models.CASCADE)

    # Per-move evaluations
    evaluations = models.JSONField()  # [{ply: 1, eval: 0.3, best_move: "e2e4"}, ...]

    # Summary statistics
    white_acpl = models.FloatField(null=True)  # Average centipawn loss
    black_acpl = models.FloatField(null=True)
    white_inaccuracies = models.PositiveSmallIntegerField(default=0)
    white_mistakes = models.PositiveSmallIntegerField(default=0)
    white_blunders = models.PositiveSmallIntegerField(default=0)
    black_inaccuracies = models.PositiveSmallIntegerField(default=0)
    black_mistakes = models.PositiveSmallIntegerField(default=0)
    black_blunders = models.PositiveSmallIntegerField(default=0)

    analyzed_at = models.DateTimeField(auto_now_add=True)
```

---

## Frontend Implementation

### Component Structure

```
src/features/analysis/
├── api/
│   └── analysisApi.ts         # Save/load sessions
├── components/
│   ├── AnalysisBoard.tsx      # Main board with engine integration
│   ├── EngineLines.tsx        # PV display (1-5 lines)
│   ├── EvalBar.tsx            # Vertical evaluation bar
│   ├── EvalGraph.tsx          # Game evaluation chart
│   ├── MoveList.tsx           # Navigable move tree
│   ├── PositionSetup.tsx      # FEN/PGN input, manual setup
│   ├── EngineSettings.tsx     # Depth, lines, NNUE toggle
│   └── MoveAnnotation.tsx     # Inaccuracy/mistake/blunder markers
├── hooks/
│   ├── useStockfish.ts        # Engine communication
│   ├── useAnalysis.ts         # Position state management
│   └── useEvalGraph.ts        # Graph data computation
├── workers/
│   └── stockfish.worker.ts    # Web Worker wrapper
└── pages/
    └── AnalysisPage.tsx       # Main analysis page
```

### Stockfish Integration

```typescript
// hooks/useStockfish.ts

interface EngineState {
  isReady: boolean;
  isSearching: boolean;
  depth: number;
  evaluation: number | null;  // centipawns, null for mate
  mateIn: number | null;      // moves to mate
  lines: PrincipalVariation[];
}

interface PrincipalVariation {
  moves: string[];      // UCI moves
  evaluation: number;
  mateIn: number | null;
  depth: number;
}

interface UseStockfishOptions {
  numLines?: number;     // 1-5, default 1
  useNnue?: boolean;     // default true
}

export function useStockfish(options: UseStockfishOptions = {}) {
  const [state, setState] = useState<EngineState>(initialState);
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => {
    // Initialize Stockfish Web Worker
    const worker = new Worker('/stockfish/stockfish.worker.js');

    worker.onmessage = (e) => {
      const line = e.data;

      if (line === 'uciok') {
        // Engine ready, configure options
        worker.postMessage(`setoption name MultiPV value ${options.numLines ?? 1}`);
        worker.postMessage('isready');
      } else if (line === 'readyok') {
        setState(s => ({ ...s, isReady: true }));
      } else if (line.startsWith('info depth')) {
        // Parse search info
        const parsed = parseInfoLine(line);
        setState(s => updateFromInfo(s, parsed));
      }
    };

    worker.postMessage('uci');
    workerRef.current = worker;

    return () => worker.terminate();
  }, [options.numLines]);

  const analyze = useCallback((fen: string) => {
    if (!workerRef.current) return;
    workerRef.current.postMessage('stop');
    workerRef.current.postMessage(`position fen ${fen}`);
    workerRef.current.postMessage('go infinite');
    setState(s => ({ ...s, isSearching: true }));
  }, []);

  const stop = useCallback(() => {
    workerRef.current?.postMessage('stop');
    setState(s => ({ ...s, isSearching: false }));
  }, []);

  return { ...state, analyze, stop };
}
```

### UCI Protocol Parsing

```typescript
// utils/uciParser.ts

interface UciInfo {
  depth: number;
  seldepth: number;
  multipv: number;
  score: { cp?: number; mate?: number };
  nodes: number;
  nps: number;
  pv: string[];
}

export function parseInfoLine(line: string): UciInfo | null {
  if (!line.startsWith('info depth')) return null;

  const tokens = line.split(' ');
  const info: Partial<UciInfo> = {};

  for (let i = 0; i < tokens.length; i++) {
    switch (tokens[i]) {
      case 'depth':
        info.depth = parseInt(tokens[++i]);
        break;
      case 'seldepth':
        info.seldepth = parseInt(tokens[++i]);
        break;
      case 'multipv':
        info.multipv = parseInt(tokens[++i]);
        break;
      case 'score':
        if (tokens[++i] === 'cp') {
          info.score = { cp: parseInt(tokens[++i]) };
        } else if (tokens[i] === 'mate') {
          info.score = { mate: parseInt(tokens[++i]) };
        }
        break;
      case 'nodes':
        info.nodes = parseInt(tokens[++i]);
        break;
      case 'nps':
        info.nps = parseInt(tokens[++i]);
        break;
      case 'pv':
        info.pv = tokens.slice(i + 1);
        i = tokens.length;  // Exit loop
        break;
    }
  }

  return info as UciInfo;
}
```

### Evaluation Bar Component

```typescript
// components/EvalBar.tsx

interface EvalBarProps {
  evaluation: number | null;  // centipawns
  mateIn: number | null;
  orientation: 'white' | 'black';
}

export function EvalBar({ evaluation, mateIn, orientation }: EvalBarProps) {
  // Convert evaluation to percentage (0-100, 50 = equal)
  const getPercentage = () => {
    if (mateIn !== null) {
      return mateIn > 0 ? 100 : 0;
    }
    if (evaluation === null) return 50;

    // Sigmoid-like scaling: ±400cp maps to ~10-90%
    const scaled = 50 + 50 * (2 / (1 + Math.exp(-0.004 * evaluation)) - 1);
    return Math.max(0, Math.min(100, scaled));
  };

  const percentage = getPercentage();
  const whiteHeight = orientation === 'white' ? percentage : 100 - percentage;

  return (
    <div className="eval-bar">
      <div className="eval-bar-white" style={{ height: `${whiteHeight}%` }} />
      <div className="eval-bar-black" style={{ height: `${100 - whiteHeight}%` }} />
      <div className="eval-bar-label">
        {formatEvaluation(evaluation, mateIn)}
      </div>
    </div>
  );
}

function formatEvaluation(cp: number | null, mate: number | null): string {
  if (mate !== null) {
    return mate > 0 ? `M${mate}` : `M${-mate}`;
  }
  if (cp === null) return '0.00';
  const sign = cp >= 0 ? '+' : '';
  return `${sign}${(cp / 100).toFixed(2)}`;
}
```

---

## "Learn From Your Mistakes" Feature

Interactive mode that converts game mistakes into puzzles.

### Flow

1. Load completed game into analysis board
2. User clicks "Learn from your mistakes"
3. System identifies inaccuracies, mistakes, and blunders
4. For each mistake:
   - Position is presented before the error
   - User must find the correct move
   - Engine shows why their original move was bad

### Implementation

```typescript
// hooks/useLearnFromMistakes.ts

interface Mistake {
  ply: number;
  fen: string;
  playedMove: string;
  bestMove: string;
  evalBefore: number;
  evalAfter: number;
  classification: 'inaccuracy' | 'mistake' | 'blunder';
}

export function useLearnFromMistakes(gameAnalysis: GameAnalysis) {
  const mistakes = useMemo(() => {
    return gameAnalysis.evaluations
      .filter(e => e.classification)
      .map(e => ({
        ply: e.ply,
        fen: e.fen,
        playedMove: e.played,
        bestMove: e.best_move,
        evalBefore: e.eval_before,
        evalAfter: e.eval_after,
        classification: e.classification,
      }));
  }, [gameAnalysis]);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  const currentMistake = mistakes[currentIndex];

  const checkMove = (move: string): boolean => {
    return move === currentMistake.bestMove;
  };

  const nextMistake = () => {
    if (currentIndex < mistakes.length - 1) {
      setCurrentIndex(i => i + 1);
    } else {
      setIsComplete(true);
    }
  };

  return {
    mistakes,
    currentMistake,
    currentIndex,
    total: mistakes.length,
    isComplete,
    checkMove,
    nextMistake,
  };
}
```

---

## Django Backend (Minimal)

Analysis is client-side only, so backend handles only session persistence.

### Services

```python
# <project_slug>/analysis/services.py

from <project_slug>.analysis.models import AnalysisSession, GameAnalysis
from <project_slug>.users.models import User


def save_analysis_session(
    *,
    user: User,
    initial_fen: str,
    current_fen: str,
    pgn: str = '',
    title: str = '',
    analysis_cache: dict = None,
) -> AnalysisSession:
    """Save or update an analysis session."""
    return AnalysisSession.objects.create(
        user=user,
        initial_fen=initial_fen,
        current_fen=current_fen,
        pgn=pgn,
        title=title,
        analysis_cache=analysis_cache or {},
    )


def analyze_game(*, game) -> GameAnalysis:
    """
    Analyze a completed game.

    Note: For MVP, this triggers client-side analysis.
    The frontend sends results back for storage.
    """
    analysis, created = GameAnalysis.objects.get_or_create(game=game)
    return analysis
```

### Selectors

```python
# <project_slug>/analysis/selectors.py

from django.db.models import QuerySet

from <project_slug>.analysis.models import AnalysisSession, GameAnalysis
from <project_slug>.users.models import User


def get_user_analysis_sessions(*, user: User) -> QuerySet[AnalysisSession]:
    """Get user's saved analysis sessions."""
    return AnalysisSession.objects.filter(user=user).order_by('-updated_at')


def get_game_analysis(*, game) -> GameAnalysis | None:
    """Get analysis for a completed game."""
    return GameAnalysis.objects.filter(game=game).first()
```

### API Endpoints

```python
# <project_slug>/analysis/apis.py

from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from <project_slug>.analysis.models import AnalysisSession, GameAnalysis
from <project_slug>.analysis.selectors import get_user_analysis_sessions, get_game_analysis
from <project_slug>.analysis.services import save_analysis_session
from <project_slug>.games.models import Game


class AnalysisSessionListApi(APIView):
    """List and create analysis sessions."""

    class InputSerializer(serializers.Serializer):
        initial_fen = serializers.CharField(max_length=100)
        current_fen = serializers.CharField(max_length=100)
        pgn = serializers.CharField(required=False, allow_blank=True, default='')
        title = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
        analysis_cache = serializers.JSONField(required=False, default=dict)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        title = serializers.CharField()
        initial_fen = serializers.CharField()
        current_fen = serializers.CharField()
        pgn = serializers.CharField()
        created_at = serializers.DateTimeField()
        updated_at = serializers.DateTimeField()

    def get(self, request):
        sessions = get_user_analysis_sessions(user=request.user)
        return Response(self.OutputSerializer(sessions, many=True).data)

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = save_analysis_session(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(self.OutputSerializer(session).data, status=status.HTTP_201_CREATED)


class GameAnalysisApi(APIView):
    """Get or store game analysis."""

    class InputSerializer(serializers.Serializer):
        evaluations = serializers.JSONField()
        white_acpl = serializers.FloatField(allow_null=True, required=False)
        black_acpl = serializers.FloatField(allow_null=True, required=False)
        white_inaccuracies = serializers.IntegerField(min_value=0, default=0)
        white_mistakes = serializers.IntegerField(min_value=0, default=0)
        white_blunders = serializers.IntegerField(min_value=0, default=0)
        black_inaccuracies = serializers.IntegerField(min_value=0, default=0)
        black_mistakes = serializers.IntegerField(min_value=0, default=0)
        black_blunders = serializers.IntegerField(min_value=0, default=0)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        evaluations = serializers.JSONField()
        white_acpl = serializers.FloatField()
        black_acpl = serializers.FloatField()
        white_inaccuracies = serializers.IntegerField()
        white_mistakes = serializers.IntegerField()
        white_blunders = serializers.IntegerField()
        black_inaccuracies = serializers.IntegerField()
        black_mistakes = serializers.IntegerField()
        black_blunders = serializers.IntegerField()
        analyzed_at = serializers.DateTimeField()

    def get(self, request, game_id):
        game = get_object_or_404(Game, id=game_id)
        analysis = get_game_analysis(game=game)

        if not analysis:
            return Response({'detail': 'Not analyzed'}, status=status.HTTP_404_NOT_FOUND)

        return Response(self.OutputSerializer(analysis).data)

    def post(self, request, game_id):
        """Store client-computed analysis results."""
        game = get_object_or_404(Game, id=game_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        analysis, _ = GameAnalysis.objects.update_or_create(
            game=game,
            defaults=serializer.validated_data,
        )

        return Response(self.OutputSerializer(analysis).data)
```

---

## Practice Section (Future)

Structured lessons from Lichess Practice:

### Checkmates (7 lessons)
- Piece Checkmates I & II
- Checkmate Patterns I-IV
- Knight & Bishop Mate

### Fundamental Tactics (8 lessons)
- Pins, Skewers, Forks
- Discovered Attacks, Double Checks
- Overloaded Pieces, Zwischenzug, X-Ray

### Advanced Tactics (10 lessons)
- Zugzwang, Interference, Greek Gift
- Deflection, Attraction, Underpromotion
- Desperado, Counter-checks, Undermining, Clearance

### Endgames (7 lessons)
- Pawn: Key Squares, Opposition, Rook Pawn vs Queen
- Rook: Lucena, Philidor, Multiple Pawns, 7th Rank Defense

---

## Coordinate Training (Future)

Board visualization drills:

- **Find Square**: Click the named square
- **Name Square**: Identify clicked square
- White/Black perspective toggle
- Timed and untimed modes
- Progress tracking

---

## Related Documents

- [RESEARCH.md](./RESEARCH.md) - Detailed Lichess training feature research
- [Puzzles](./puzzles.md) - Tactical puzzle system
- [Real-Time Gameplay](../02-core-features/real-time-gameplay.md) - WebSocket architecture

---

*Document created: December 2025*
