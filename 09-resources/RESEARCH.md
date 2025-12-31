# Open Source Resources for Lichess Clone

This document provides comprehensive research on available libraries, tools, and data sources for building a Lichess-style chess application.

---

## Table of Contents

1. [Chessground](#chessground)
2. [python-chess](#python-chess)
3. [Stockfish.wasm](#stockfishwasm)
4. [Lichess Game Database](#lichess-game-database)
5. [Puzzle Database](#puzzle-database)
6. [Tablebases](#tablebases)
7. [Alternative Libraries](#alternative-libraries)
8. [Integration Considerations](#integration-considerations)

---

## Chessground

**Repository**: [lichess-org/chessground](https://github.com/lichess-org/chessground)

Chessground is the official chess UI library developed for lichess.org. It provides a mobile-friendly, performant chessboard component with no chess logic built-in.

### Key Features

- **TypeScript implementation** with strong typing
- **Small footprint**: 10KB gzipped (31KB unzipped), zero dependencies
- **Custom DOM diffing** for optimized performance and minimal DOM writes
- **SVG drawing** support for circles, arrows, and custom shapes
- **Touch-optimized** with full mobile/tablet support via Cordova
- **FEN import/export** for position representation
- **Chess variant support** (960, atomic, etc.)
- **3D piece and board support**
- **Premove and predrop** capabilities

### Installation

```bash
npm install --save @lichess-org/chessground
```

### Basic Usage

```javascript
import { Chessground } from '@lichess-org/chessground';

const config = {
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  orientation: 'white',
  movable: {
    free: false,
    color: 'white',
  },
};

const ground = Chessground(document.getElementById('board'), config);
```

### React Wrappers

Several React wrappers are available:

| Package | Notes |
|---------|-------|
| [@react-chess/chessground](https://www.npmjs.com/package/@react-chess/chessground) | Most popular, actively maintained |
| [ruilisi/react-chessground](https://github.com/ruilisi/react-chessground) | Includes onMove callback, randomMove functions |
| [@bezalel6/react-chessground](https://www.npmjs.com/package/@bezalel6/react-chessground) | Modern wrapper with move validation, themes, promotion dialogs |

### Framework Support

- **Vue.js**: vitogit/vue-chessboard, qwerty084/vue3-chessboard
- **Angular**: topce/ngx-chessground
- **Svelte**: Multiple versions for Svelte 3, 4, and 5

### CSS Requirements

```css
@import '@lichess-org/chessground/assets/chessground.base.css';
@import '@lichess-org/chessground/assets/chessground.brown.css';
@import '@lichess-org/chessground/assets/chessground.cburnett.css';
```

### License

**GPL-3.0** - Requires source code disclosure if distributed.

---

## python-chess

**Repository**: [niklasf/python-chess](https://github.com/niklasf/python-chess)

python-chess is a comprehensive Python library for chess programming. It handles move generation, validation, and all chess logic on the backend.

### Key Features

#### Core Functionality
- Legal move generation and validation
- Making and unmaking moves
- Check, checkmate, and stalemate detection
- Insufficient material recognition
- Threefold/fivefold repetition tracking
- 50-move and 75-move rule support
- Pin detection with directional information

#### Format Support
- **FEN parsing/generation** (including Shredder FEN)
- **PGN reading/writing** with headers, comments, variations
- **SAN (Standard Algebraic Notation)** parsing
- **EPD (Extended Position Description)** support
- **UCI move notation**

#### Chess Variants
Supports: Standard, Chess960, Suicide, Giveaway, Atomic, King of the Hill, Racing Kings, Horde, Three-check, Crazyhouse

#### Advanced Features
- **Polyglot opening book** reading
- **Syzygy tablebase** probing (DTZ, WDL)
- **Gaviota tablebase** probing (DTM, WDL)
- **UCI/XBoard engine communication** (asyncio-based)
- **mypy type annotations**
- **Jupyter/IPython integration** with SVG board rendering

### Installation

```bash
pip install chess
```

### Basic Usage

```python
import chess

board = chess.Board()
print(board.legal_moves)

# Make a move
board.push_san("e4")
board.push_san("e5")

# Check game state
print(board.is_checkmate())
print(board.is_stalemate())
print(board.fen())
```

### UCI Engine Integration

```python
import chess.engine

engine = chess.engine.SimpleEngine.popen_uci("/path/to/stockfish")
board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

result = engine.play(board, chess.engine.Limit(time=2.0))
print(result.move)

engine.quit()
```

### Syzygy Tablebase Probing

```python
import chess.syzygy

with chess.syzygy.open_tablebase("/path/to/syzygy") as tablebase:
    board = chess.Board("8/2K5/4B3/3N4/8/8/4k3/8 w - - 0 1")
    print(tablebase.probe_dtz(board))
    print(tablebase.probe_wdl(board))
```

### Performance Notes

- Pure Python implementation (not the fastest for intensive computation)
- For high-performance scenarios, consider rust-based alternatives or C extensions
- Asyncio-based engine communication prevents blocking

### License

**GPL-3.0**

---

## Stockfish.wasm

**Repository**: [lichess-org/stockfish.wasm](https://github.com/lichess-org/stockfish.wasm)

Stockfish.wasm is a WebAssembly port of the Stockfish chess engine, enabling browser-based chess analysis with multi-threading support.

### Variants Available

| Package | Description | Size |
|---------|-------------|------|
| [lichess-org/stockfish.wasm](https://github.com/lichess-org/stockfish.wasm) | Lichess's WASM port, multi-threaded | ~150KB gzipped |
| [nmrugg/stockfish.js](https://github.com/nmrugg/stockfish.js) | Chess.com's version, includes NNUE | ~7-75MB |
| [fairy-stockfish.wasm](https://github.com/fairy-stockfish/fairy-stockfish.wasm) | Variant support (Xiangqi, Shogi, etc.) | Varies |

### lichess-org/stockfish.wasm Features

- **Multi-threaded** via WebAssembly threading proposal
- **Up to 32 concurrent threads**
- **Configurable hash table** (max 1024 MB)
- **UCI protocol support**
- **Web Worker integration**

### Browser Compatibility

| Browser | Version | Support |
|---------|---------|---------|
| Chromium | 79+ | Full |
| Chromium | 74-78 | Limited (16MB max memory) |
| Firefox | 79+ | Full |
| Firefox | 71-78 | Requires manual flags |
| Safari | All | Not supported (use single-threaded stockfish.js) |

### Required CORS Headers

```http
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Opener-Policy: same-origin
```

### Installation & Usage

Serve these files from the same directory:
- `stockfish.js`
- `stockfish.wasm`
- `stockfish.worker.js`

```html
<script src="stockfish.js"></script>
<script>
  Stockfish().then((sf) => {
    sf.addMessageListener((line) => console.log(line));
    sf.postMessage("uci");
    sf.postMessage("position fen rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1");
    sf.postMessage("go depth 20");
  });
</script>
```

### npm Installation

```bash
npm install stockfish.wasm
# or for Chess.com's version with NNUE
npm install stockfish
```

### Limitations

- **No NNUE support** in lichess-org version (use nmrugg/stockfish.js for NNUE)
- **No Syzygy tablebase access**
- **Maximum 32 threads**
- Can hang on UCI protocol misuse

### Modern Alternative: @chessle/chess.js-extended

```bash
npm install @chessle/chess.js-extended
```

Bundles Stockfish for in-browser analysis with Web Workers and WebAssembly.

### License

**GPL-3.0**

---

## Lichess Game Database

**Website**: [database.lichess.org](https://database.lichess.org/)

Lichess provides free access to over 7.2 billion standard rated games plus variants.

### Database Statistics

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
[WhiteTitle "BOT"]  ; Computer players
[BlackTitle "BOT"]
[Variant "Antichess"]  ; Variant games
[%eval 2.35]  ; Stockfish evaluation (centipawns)
[%eval #-4]   ; Mate in 4
[%clk 0:10:00]  ; Clock times (games from 2017+)
```

### Decompression

```bash
# Unix (fastest)
pzstd -d lichess_db_standard_rated_2024-01.pgn.zst

# Streaming to Python
zstdcat lichess_db_standard_rated_2024-01.pgn.zst | python process_games.py
```

### Partial Downloads

ZStandard archives are partially decompressable - you can cancel downloads mid-stream and still decompress what you have.

### Lichess Elite Database

**Website**: [database.nikonoel.fr](https://database.nikonoel.fr/)

Filtered database containing only games:
- 2400+ rated players vs 2200+ rated opponents
- From Dec 2021: 2500+ vs 2300+
- Excludes bullet games

### License

**Creative Commons CC0** - No restrictions on use.

---

## Puzzle Database

**Download**: [database.lichess.org/#puzzles](https://database.lichess.org/#puzzles)

### Statistics

- **Total puzzles**: 5,600,086+
- **Format**: CSV (compressed with ZStandard)
- **Size**: ~250MB compressed
- **Last updated**: Monthly

### CSV Schema

```csv
PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags
```

| Field | Description |
|-------|-------------|
| PuzzleId | Unique identifier |
| FEN | Starting position |
| Moves | Solution in UCI format (e.g., e2e4 e7e5) |
| Rating | Puzzle difficulty rating |
| RatingDeviation | Rating uncertainty |
| Popularity | Score from -100 to 100 (upvotes - downvotes) |
| NbPlays | Number of attempts |
| Themes | Comma-separated tags (e.g., "fork,middlegame") |
| GameUrl | Source game on Lichess |
| OpeningTags | Opening name (only for puzzles before move 20) |

### Download

```bash
wget https://database.lichess.org/lichess_db_puzzle.csv.zst
pzstd -d lichess_db_puzzle.csv.zst
```

### Combined Puzzle-Game Database

For puzzles with full game context:
- **Repository**: [mcognetta/lichess-combined-puzzle-game-db](https://github.com/mcognetta/lichess-combined-puzzle-game-db)
- **Format**: bzip2 compressed NDJSON
- **Contains**: 2.9M puzzles with complete game data

### License

**Creative Commons CC0**

---

## Tablebases

### Syzygy Tablebases

The standard endgame tablebases used by modern chess engines.

#### Overview

- **Coverage**: Perfect play for up to 7 pieces
- **Metrics**: WDL (Win/Draw/Loss) and DTZ (Distance to Zeroing)
- **50-move rule**: Both with and without

#### Download Sources

| Source | URL | Notes |
|--------|-----|-------|
| Lichess Mirror | tablebase.sesse.net | HTTP download |
| Massimiliano Goi | chess.massimilianogoi.com | 3-6 piece sets |
| Official Torrents | syzygy-tables.info | 6-7 piece sets |

#### File Sizes

| Pieces | WDL Size | DTZ Size |
|--------|----------|----------|
| 3-5 | 378 MB | 561 MB |
| 6 | 68.2 GB | 81.9 GB |
| 7 | ~8 TB | ~10 TB |

### Lichess Tablebase API

**Endpoint**: `https://tablebase.lichess.ovh`

```bash
# Standard query
curl "http://tablebase.lichess.ovh/standard?fen=4k3/6KP/8/8/8/8/7p/8%20w%20-%20-%200%201"

# Mainline (best moves)
curl "http://tablebase.lichess.ovh/standard/mainline?fen=4k3/6KP/8/8/8/8/7p/8_w_-_-_0_1"
```

#### Rate Limiting

- Subject to Lichess API rate limits
- ~130 requests before throttling
- For bulk queries, download tables and probe locally

### Local Probing

#### Python (with python-chess)

```python
import chess.syzygy

tablebase = chess.syzygy.open_tablebase("/path/to/syzygy")
board = chess.Board("8/2K5/4B3/3N4/8/8/4k3/8 w - - 0 1")

wdl = tablebase.probe_wdl(board)  # -2 to 2
dtz = tablebase.probe_dtz(board)  # Distance to zeroing move
```

#### Online Interface

**Website**: [syzygy-tables.info](https://syzygy-tables.info/)

Interactive tablebase browser and API.

### Storage Recommendations

- **WDL tables**: Keep on SSD for search performance
- **DTZ tables**: Can be on HDD (accessed less frequently)
- **7-piece**: May be counterproductive with NNUE engines due to disk I/O overhead

### License

**Public Domain**

---

## Alternative Libraries

### Frontend Libraries

#### chess.js

**Repository**: [jhlywa/chess.js](https://github.com/jhlywa/chess.js)

TypeScript library for chess logic (no UI).

```bash
npm install chess.js
```

**Features**:
- Move generation/validation
- FEN/PGN parsing
- Check/checkmate/stalemate detection
- Move history
- Undo support

```javascript
import { Chess } from 'chess.js';

const chess = new Chess();
chess.move('e4');
chess.move('e5');
console.log(chess.ascii());
console.log(chess.fen());
```

**Commonly paired with**: chessground, react-chessboard, chessboard.js

---

#### cm-chessboard

**Repository**: [shaack/cm-chessboard](https://github.com/shaack/cm-chessboard)

Lightweight ES6 chessboard with SVG rendering.

```bash
npm install cm-chessboard
```

**Features**:
- Zero dependencies
- SVG rendering
- Extension system (markers, arrows, accessibility)
- Multiple piece sets
- Primary/secondary click handling

**Extensions**:
- Markers Extension
- Arrows Extension
- PromotionDialog Extension
- Accessibility Extension

---

#### react-chessboard

**Repository**: [react-chessboard](https://www.npmjs.com/package/react-chessboard)

Modern React chessboard component.

```bash
npm install react-chessboard
```

**Features**:
- Custom square styles
- Custom piece renderers
- Premove support
- react-dnd based drag and drop
- Responsive design

```jsx
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';

function App() {
  const [game, setGame] = useState(new Chess());

  function onDrop(sourceSquare, targetSquare) {
    const move = game.move({
      from: sourceSquare,
      to: targetSquare,
      promotion: 'q',
    });
    if (move === null) return false;
    setGame(new Chess(game.fen()));
    return true;
  }

  return <Chessboard position={game.fen()} onPieceDrop={onDrop} />;
}
```

---

#### chessboard.js

**Repository**: [oakmac/chessboardjs](https://github.com/oakmac/chessboardjs)

Classic JavaScript chessboard (jQuery-based).

```bash
npm install @chrisoakman/chessboardjs
```

**Note**: Older library, consider react-chessboard or cm-chessboard for modern projects.

---

### Backend Libraries

#### rust-chess / shakmaty

For high-performance backends:
- [jordanbray/chess](https://github.com/jordanbray/chess) - Rust chess library
- [niklasf/shakmaty](https://github.com/niklasf/shakmaty) - Rust library (powers lichess tablebase server)

---

## Integration Considerations

### Recommended Stack

#### Frontend
```
React + @react-chess/chessground + chess.js
     or
React + react-chessboard + chess.js
```

#### Backend
```
Django + python-chess + Stockfish (via UCI)
```

#### Browser Analysis
```
stockfish.wasm (lichess-org) or stockfish.js (nmrugg/NNUE)
```

### Architecture Decisions

#### Chessground vs react-chessboard

| Criteria | Chessground | react-chessboard |
|----------|-------------|------------------|
| Size | 10KB gzipped | Larger (react-dnd) |
| Origin | Lichess (battle-tested) | Community |
| Features | SVG arrows, premoves | Custom pieces, styles |
| Learning curve | Steeper (config-heavy) | React-native API |
| License | GPL-3.0 | MIT |

**Recommendation**: Use Chessground for Lichess-like experience; react-chessboard for simpler React integration.

#### Stockfish Integration

| Approach | Pros | Cons |
|----------|------|------|
| Browser WASM | No server load, instant | CORS headers, browser limits |
| Server-side | Full strength, NNUE | Server resources, latency |
| Hybrid | Best of both | Complexity |

**Recommendation**:
- Quick analysis: Browser WASM
- Deep analysis: Server-side Stockfish
- Mobile: Server-side (battery/performance)

#### Database Usage

| Use Case | Source |
|----------|--------|
| Opening explorer | Lichess game database |
| Training puzzles | Puzzle CSV database |
| Position analysis | Stockfish evaluations JSON |
| Endgame training | Syzygy tablebases |

### CORS Configuration (for Stockfish.wasm)

```python
# Django middleware or nginx config
CORS_HEADERS = {
    'Cross-Origin-Embedder-Policy': 'require-corp',
    'Cross-Origin-Opener-Policy': 'same-origin',
}
```

### Licensing Summary

| Library | License | Commercial Use |
|---------|---------|----------------|
| Chessground | GPL-3.0 | Yes (with source disclosure) |
| python-chess | GPL-3.0 | Yes (with source disclosure) |
| Stockfish.wasm | GPL-3.0 | Yes (with source disclosure) |
| chess.js | BSD | Yes |
| cm-chessboard | MIT | Yes |
| react-chessboard | MIT | Yes |
| Lichess Database | CC0 | Yes (unrestricted) |
| Syzygy | Public Domain | Yes |

### Performance Tips

1. **Lazy load Stockfish WASM** - Don't bundle with main JS
2. **Stream database downloads** - Use zstdcat for on-the-fly processing
3. **Cache tablebase queries** - API rate limits apply
4. **Use Web Workers** - Keep UI responsive during analysis
5. **Limit hash table size** - Check `navigator.deviceMemory`

---

## References

- [Lichess Open Database](https://database.lichess.org/)
- [Lichess API Documentation](https://lichess.org/api)
- [Chessground Repository](https://github.com/lichess-org/chessground)
- [python-chess Documentation](https://python-chess.readthedocs.io/)
- [Syzygy Tables Info](https://syzygy-tables.info/)
- [chess.js Documentation](https://github.com/jhlywa/chess.js)
- [Stockfish.wasm Repository](https://github.com/lichess-org/stockfish.wasm)
- [Lichess Elite Database](https://database.nikonoel.fr/)
