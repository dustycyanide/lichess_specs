# Training Features Research

**Research Date:** December 31, 2025  
**Topic:** Lichess Puzzle System and Analysis Board

---

## Summary

Lichess provides a comprehensive training ecosystem comprising puzzles, analysis tools, and learning resources. The puzzle system is powered by over 5.4 million puzzles generated from 600 million analyzed games using Stockfish NNUE. The analysis board offers both client-side (browser WASM) and server-side (fishnet distributed computing) engine analysis. The learn section includes interactive lessons for beginners, practice positions for tactical training, and coordinate drills.

---

## Puzzle System

### Overview

Lichess hosts one of the largest open-source chess puzzle databases in the world, containing **5,423,662 puzzles** that are rated, tagged, and freely available for download.

### Puzzle Generation Process

The puzzle generation process is computationally intensive:

- **Source Data:** Analyzed 600,000,000 games from the Lichess database
- **Analysis Engine:** Re-analyzed interesting positions with Stockfish NNUE at 40 meganodes
- **Computation Time:** Generating the puzzle database took more than 100 years of CPU time
- **Automatic Tagging:** Puzzles are automatically tagged based on tactical motifs and game characteristics

### Quality Standards

Lichess applies strict quality criteria for puzzle selection:

1. **Game Source Quality:** Puzzles are sourced strictly from games where the average player rating is above 2000
2. **Solution Uniqueness:** All player moves in the solution are "only moves" - playing any other move would considerably worsen the position
3. **Mate Exception:** For mate-in-one puzzles, there can be multiple valid solutions; any checkmate move wins
4. **Position Balance:** Puzzles start from relatively balanced positions in terms of evaluation and material

### Database Format (CSV)

The puzzle database is available at [database.lichess.org](https://database.lichess.org/) in CSV format with the following fields:

| Field | Description |
|-------|-------------|
| `PuzzleId` | Unique identifier; puzzle accessible at `lichess.org/training/{PuzzleId}` |
| `FEN` | Position before opponent's move; apply first move to get player position |
| `Moves` | Solution moves in UCI format; first move is opponent's, second begins solution |
| `Rating` | Glicko-2 rating of the puzzle |
| `RatingDeviation` | Glicko-2 rating deviation |
| `Popularity` | Score from -100 (worst) to 100 (best) based on weighted user votes |
| `NbPlays` | Number of times the puzzle has been played |
| `Themes` | Comma-separated list of puzzle themes/tags |
| `GameUrl` | Link to the original game the puzzle was derived from |
| `OpeningTags` | Opening classification (only for puzzles starting before move 20) |

---

## Puzzle Rating System

### Glicko-2 Implementation

Lichess uses the Glicko-2 rating system for both players and puzzles:

- **Rating Period:** Lichess uses a modified Glicko-2 that updates ratings immediately after each attempt (not in bulk periods)
- **Fractional Periods:** 0.21436 rating periods per day, calibrated so RD goes from 60 to 110 in a year of inactivity
- **Puzzle as Opponent:** Each solve attempt is treated as a rated game between the player and the puzzle

### How Puzzle Ratings Evolve

- When you **solve** a puzzle: The puzzle loses rating, you gain rating
- When you **fail** a puzzle: The puzzle gains rating, you lose rating
- **Rating Convergence:** Puzzles played hundreds of thousands of times have highly accurate ratings

### Rating Deviation

- **Confidence Intervals:** Rating plus/minus (2 x RD) represents 95% confidence interval
- **Provisional Status:** Ratings are considered provisional when RD > 110
- **New Player Default:** Starting rating of 1500 plus/minus 1000

---

## Puzzle Themes and Categories

### Tactical Motifs

| Theme | Description |
|-------|-------------|
| **Fork** | A move where the moved piece attacks two opponent pieces at once |
| **Pin** | A piece is unable to move without revealing an attack on a higher value piece |
| **Skewer** | A high value piece is attacked, moves, allowing a lower value piece behind to be captured |
| **Discovered Attack** | Moving a piece reveals an attack from a hidden long-range piece |
| **Discovered Check** | Moving a piece reveals a check, often leading to decisive advantage |
| **Double Check** | Checking with two pieces at once from a discovered attack |
| **Deflection** | Distracting an opponent piece from its defensive duty |
| **Attraction** | An exchange or sacrifice forcing an opponent piece to a vulnerable square |
| **Interference** | Moving between two opponent pieces to leave one or both undefended |
| **X-Ray Attack** | A piece attacks or defends through an enemy piece |
| **Clearance** | A move, often with tempo, that clears a square/file/diagonal for a follow-up tactic |
| **Zugzwang** | The opponent must move but all moves worsen their position |
| **Trapped Piece** | A piece cannot escape capture due to limited moves |
| **Hanging Piece** | An opponent piece is undefended or insufficiently defended |
| **Overloaded Piece** | (Capture the Defender) Removing a piece critical to defense |
| **Intermezzo/Zwischenzug** | Playing an unexpected intermediate move before the expected move |
| **Sacrifice** | Giving up material for an advantage after a forced sequence |
| **Quiet Move** | A non-check, non-capture move that prepares an unavoidable threat |
| **Defensive Move** | A precise move needed to avoid losing material or advantage |

### Checkmate Patterns

| Theme | Description |
|-------|-------------|
| **Back Rank Mate** | Checkmate on the home rank when king is trapped by its own pieces |
| **Smothered Mate** | Knight checkmate where the king is surrounded by its own pieces |
| **Anastasia's Mate** | Knight and rook/queen trap king between board edge and friendly piece |
| **Arabian Mate** | Knight and rook trap king in a corner |
| **Boden's Mate** | Two bishops on crossing diagonals mate a king obstructed by friendly pieces |
| **Dovetail Mate** | Queen mates adjacent king whose two escape squares are blocked by friendly pieces |
| **Opera Mate** | Rook checks king while bishop defends the rook |
| **Morphy's Mate** | Bishop checks king while rook helps confine it |
| **Hook Mate** | Rook, knight, and pawn mate with enemy pawn limiting escape |
| **Corner Mate** | Rook/queen and knight confine king to corner |
| **Kill Box Mate** | Rook next to king supported by queen blocking escape squares |

### Mate Length

- **Mate in 1:** Deliver checkmate in one move
- **Mate in 2:** Deliver checkmate in two moves
- **Mate in 3:** Deliver checkmate in three moves
- **Mate in 4:** Deliver checkmate in four moves
- **Mate in 5+:** Figure out a long mating sequence

### Puzzle Length

- **One-Move Puzzle:** Only one move long
- **Short Puzzle:** Two moves to win
- **Long Puzzle:** Three moves to win
- **Very Long Puzzle:** Four moves or more to win

### Game Phases

- **Opening:** Tactics during the first phase
- **Middlegame:** Tactics during the second phase
- **Endgame:** Tactics during the last phase

### Endgame Types

- Pawn Endgame
- Knight Endgame
- Bishop Endgame
- Rook Endgame
- Queen Endgame
- Queen and Rook Endgame

### Evaluation Categories

- **Equality:** Come back from losing to secure draw or balanced position (eval <= 200cp)
- **Advantage:** Seize chance for decisive advantage (200cp <= eval <= 600cp)
- **Crushing:** Spot opponent blunder for crushing advantage (eval >= 600cp)

### Special Categories

- **Master Games:** Puzzles from games played by titled players
- **Master vs Master:** Puzzles from games between two titled players
- **Super GM Games:** Puzzles from games by the world's best players
- **Player Games:** Lookup puzzles from your own or another player's games
- **Healthy Mix:** Random variety to prepare for anything

### Theme Voting

Users can vote on puzzle themes after solving:
- Upvote/downvote themes to refine accuracy
- Votes are weighted by factors like solve success and rating comparison
- Community refinement improves theme accuracy over time

---

## Puzzle Game Modes

### Standard Puzzles

- **Adaptive Difficulty:** Puzzles matched to player's puzzle rating
- **No Time Pressure:** Solve at your own pace
- **Rating Impact:** Affects your puzzle rating via Glicko-2

### Puzzle Storm

A timed mode for rapid-fire puzzle solving:

- **Time Format:** 3 minutes starting time
- **Combo System:**
  - +3 seconds for first 5 correct moves
  - +5 seconds for next 7 moves (12 total)
  - +7 seconds for next 8 moves (20 total)
  - +10 seconds for every 10 moves after that
- **Penalty:** -10 seconds for wrong answer; combo resets
- **Progression:** Puzzles start very easy and get progressively harder
- **Training Focus:** Pattern recognition and quick calculation

### Puzzle Streak

An untimed mode for building winning streaks:

- **No Clock:** Take as long as needed
- **Progressive Difficulty:** Puzzles get harder as streak continues
- **One Life:** One wrong move ends the streak
- **Skip Token:** One skip allowed per session
- **Training Focus:** Deep calculation without time pressure

### Puzzle Racer

Multiplayer competitive puzzle solving:

- **Format:** 90 seconds, all players get same puzzles
- **Scoring:** One point per correct move (not per puzzle)
- **Combo Bonuses:**
  - +1 point after 5 correct moves
  - +2 points after 12 total moves
  - +3 points after 20 total moves
  - +4 points for every 10 moves after that
- **Mistake Penalty:** Combo resets on wrong answer
- **Lobbies:** Public matchmaking or private rooms (max 10 players)
- **Unrated:** Does not affect puzzle rating
- **Puzzle Source:** Uses Puzzle Storm puzzles, skipping every other to increase difficulty faster

---

## Analysis Board

### Overview

Lichess provides a comprehensive analysis board with both local (browser-based) and server-side engine analysis capabilities.

### Client-Side Analysis (Browser)

**Technology Stack:**
- **Engine:** Stockfish compiled to WebAssembly (WASM)
- **Repositories:**
  - [lichess-org/stockfish.wasm](https://github.com/lichess-org/stockfish.wasm) - Main WASM port
  - [lichess-org/stockfish.js](https://github.com/lichess-org/stockfish.js) - JavaScript/WASM via Emscripten
  - [lichess-org/stockfish-web](https://github.com/lichess-org/stockfish-web) - Optimized for lichess.org

**Technical Requirements:**
- File size: ~400KB (~150KB gzipped) for stockfish.js + stockfish.wasm + stockfish.worker.js
- HTTP Headers required:
  - `Cross-Origin-Embedder-Policy: require-corp`
  - `Cross-Origin-Opener-Policy: same-origin`

**Browser Compatibility:**
- **Chromium 79+:** Full multi-threaded WASM support
- **Chromium 74-78:** Threading supported but limited memory allocation (up to 2 threads, 16MB hash)
- **Older browsers:** Falls back to single-threaded WASM or ASMJS

**Multi-threaded WebAssembly (WASMX):**
- Labeled as "WASMX" (WebAssembly eXperimental)
- Uses latest WebAssembly threading proposal
- Significantly faster than single-threaded analysis

**NNUE Support:**
- Maintained via [lichess-org/stockfish-nnue.wasm](https://github.com/lichess-org/stockfish-nnue.wasm)
- Toggle between NNUE and classical evaluation available
- Network parameters loaded from file or embedded in binary

### Server-Side Analysis (Fishnet)

**What is Fishnet:**
Fishnet is a distributed computing network where volunteers donate CPU resources to analyze games for Lichess.

**How It Works:**
- Clients download analysis jobs from Lichess servers
- Analysis performed using Stockfish (or Fairy-Stockfish for variants)
- Results uploaded back to Lichess
- Faster clients get priority jobs with users actively waiting

**Technical Details:**
- **Communication:** HTTP-based (outgoing only, no firewall issues)
- **Performance Requirement:** ~2 meganodes in 6 seconds
- **Memory:** ~64 MiB RAM per CPU core
- **Platforms:** Linux, Windows, macOS (x86_64, ARM64), FreeBSD
- **License:** GPLv3+
- **Repository:** [lichess-org/fishnet](https://github.com/lichess-org/fishnet)

**Queue System:**
- **User Queue:** For faster clients; serves users actively waiting
- **System Queue:** For slower clients; background analysis
- Clients may remain idle if faster clients can handle backlog

**Fault Tolerance:**
- Clients can disconnect anytime
- Unfinished batches reassigned after timeout
- No configuration needed from volunteers

**Usage Limits:**
- ~20 games/day or 100/week for server analysis
- Local analysis has no limits

### Engine Features

**Multiple Lines:**
- Configure 1-5 analysis lines simultaneously
- Access via menu icon (three horizontal lines) in analysis board
- Each line shows alternative move sequences

**Analysis Depth:**
- **Local Analysis:** Typically reaches depth 22-27 plies
- **Server Analysis:** Limited by nodes (2,250,000 nodes for NNUE Stockfish), usually 23-27 plies
- **Infinite Analysis:** Runs until stopped or reaches 99 plies
- **Cloud Cache:** Previously analyzed positions may show deeper analysis

**Evaluation Graph:**
- Visual graph showing evaluation changes throughout game
- Current position indicated by dot on graph
- Clickable to navigate to any position
- Shows centipawn advantage for each side

### Move Annotations

**Classification Criteria:**
Moves are classified based on evaluation drop and winning chance change:

| Classification | Traditional Threshold | Modern Approach |
|----------------|----------------------|-----------------|
| Inaccuracy | -50 centipawns | Small win probability drop |
| Mistake | -100 centipawns | Moderate win probability drop |
| Blunder | -300 centipawns | Large win probability drop |

**Modern Classification Note:**
Lichess now uses winning probability changes rather than pure centipawn loss for more accurate classification. A move that drops 200cp in a clearly winning position may not be marked as a blunder if winning chances remain high.

**Average Centipawn Loss (ACPL):**
- Average difference between played moves and engine-recommended moves
- Calculated across all moves in the game
- Does not count moves on the evaluation plateau (extremely winning positions)

### Cloud Analysis

**How Cloud Works:**
- Opening positions are cached from previous deep analyses
- Shows "cloud" label beneath evaluation when using cached results
- Studies and broadcasts have full cloud evaluation access
- Regular game analysis has cloud restricted to openings

**Local vs Cloud Priority:**
- Cloud evaluations shown when available and deeper
- Local analysis takes over for novel positions
- Users can let local engine run longer to override cloud with deeper analysis

---

## Learn From Your Mistakes

### Feature Overview

An interactive learning tool that transforms game blunders into mini-puzzles:

1. Request computer analysis of your game
2. Engine highlights inaccuracies, mistakes, and blunders
3. Feature guides you through each mistake
4. Challenge to find the better move yourself

### How to Use

1. Open game in Analysis Board
2. Click "Request a Computer Analysis"
3. Wait for server analysis to complete
4. Click "Learn from your mistakes" button
5. Replay game, finding correct moves at each mistake

### Limitations

- Not available for Study chapters (only individual games)
- Engine evaluation may take longer for alternative moves
- Not every inaccuracy/mistake/blunder is included
- Cannot explore opponent's responses after your corrected move

### Best Practices

- Analyze games manually first before using engine
- Understand *why* the suggested move is better
- When confused, play the move you rejected to see engine's refutation
- Use as supplement to, not replacement for, own analysis

---

## Learn Section

### Chess Basics (lichess.org/learn)

Interactive lessons teaching fundamentals through gameplay:

**Piece Movement:**
- How each piece moves (King, Queen, Rook, Bishop, Knight, Pawn)
- Capturing mechanics
- Special moves (castling, en passant, pawn promotion)

**Fundamentals:**
- Defending your King
- Delivering checkmate
- Basic tactical patterns

**Target Audience:** Complete beginners and those teaching chess to others

### Practice Section (lichess.org/practice)

Structured lessons on specific chess concepts:

**Checkmates (7 lessons):**
- Piece Checkmates I & II (basic and challenging patterns)
- Checkmate Patterns I-IV (pattern recognition)
- Knight & Bishop Mate (interactive lesson)

**Fundamental Tactics (8 lessons):**
- Pins
- Skewers  
- Forks
- Discovered Attacks
- Double Checks
- Overloaded Pieces
- Zwischenzug (In-between moves)
- X-Ray Attacks

**Advanced Tactics (10 lessons):**
- Zugzwang
- Interference
- Greek Gift Sacrifice
- Deflection
- Attraction
- Underpromotion
- Desperado Moves
- Counter-checks
- Undermining
- Clearance

**Pawn Endgames (3 lessons):**
- Key Squares
- Opposition
- 7th-Rank Rook Pawn vs Queen

**Rook Endgames (4 lessons):**
- Lucena and Philidor positions
- Intermediate endings
- Multiple pawns scenarios
- 7th-rank pawn defense

### Coordinate Training (lichess.org/training/coordinate)

Interactive drill for learning board coordinates:

**Modes:**
- Find Square (click the named square)
- Name Square (identify clicked square)

**Options:**
- White or Black perspective
- Timed or unlimited
- Progress tracking

**Purpose:**
- Essential for reading chess notation
- Helpful for studying opening theory
- Improves board visualization
- Useful for following games and instruction

---

## Additional Resources

### Community Studies

Lichess hosts user-created studies on various topics:
- Checkmate patterns collections
- Endgame training materials
- Opening theory compilations
- Annotated famous games

### Video Content

Lichess hosts instructional videos covering:
- Board setup
- Piece movements
- Check and checkmate
- Special moves
- Basic strategy

---

## Sources

### Official Lichess Resources
- [Lichess Open Database](https://database.lichess.org/)
- [Lichess Puzzle Themes](https://lichess.org/training/themes)
- [Lichess Practice](https://lichess.org/practice)
- [Lichess Learn](https://lichess.org/learn)
- [Lichess Coordinate Training](https://lichess.org/training/coordinate)
- [Lichess Analysis Board](https://lichess.org/analysis)
- [Lichess Puzzle Storm](https://lichess.org/storm)
- [Lichess Puzzle Streak](https://lichess.org/streak)
- [Lichess Puzzle Racer](https://lichess.org/page/racer)
- [Lichess FAQ](https://lichess.org/faq)

### GitHub Repositories
- [lichess-org/fishnet](https://github.com/lichess-org/fishnet) - Distributed Stockfish analysis
- [lichess-org/stockfish.wasm](https://github.com/lichess-org/stockfish.wasm) - WebAssembly Stockfish port
- [lichess-org/stockfish.js](https://github.com/lichess-org/stockfish.js) - JavaScript/WASM Stockfish
- [lichess-org/stockfish-web](https://github.com/lichess-org/stockfish-web) - Lichess-optimized Stockfish
- [lichess-org/stockfish-nnue.wasm](https://github.com/lichess-org/stockfish-nnue.wasm) - NNUE WebAssembly port
- [niklasf/liglicko2](https://github.com/niklasf/liglicko2) - Lichess Glicko-2 implementation
- [puzzleTheme.xml](https://github.com/lichess-org/lila/blob/master/translation/source/puzzleTheme.xml) - Theme definitions

### Datasets
- [Lichess/chess-puzzles on Hugging Face](https://huggingface.co/datasets/Lichess/chess-puzzles)

### Community Discussions
- [Lichess Feedback Forum](https://lichess.org/forum/lichess-feedback)
- [Lichess General Chess Discussion](https://lichess.org/forum/general-chess-discussion)
- [Lichess Game Analysis Forum](https://lichess.org/forum/game-analysis)

### Blog Posts
- [Lichess Blog: Puzzles Update](https://lichess.org/blog/WDY6cCEAALYi5Xg2/puzzles-update)
- [Lichess Combined Puzzle-Game Database](https://mcognetta.github.io/posts/lichess-combined-puzzle-game-db/)
- [Fishnet - Lichess' distributed computing](https://blog.bustikiller.com/2025/05/16/lichess-fishnet.html)

### External Analysis
- [Lichess Puzzle Database Analysis](https://github.com/Nik-Hairie/Lichess-Puzzle-Database-Analysis)
- [Next Level Chess: Lichess 101 Guide](https://nextlevelchess.com/lichess-101-a-comprehensive-grandmaster-guide-3/)

---

The complete research document above should be saved to `/Users/dustycyanide/Documents/projects/ai/vibefaster/django_react_shipfast/lichess_specs/04-training/RESEARCH.md`.

## Key Findings Summary

1. **Puzzle System**: 5.4M+ puzzles generated from 600M games using Stockfish NNUE at 40 meganodes. Puzzles use Glicko-2 rating with immediate updates. Quality sourced from 2000+ rated players.

2. **Puzzle Themes**: 50+ themes organized by tactical motifs, checkmate patterns, game phases, endgame types, and puzzle characteristics. Community voting refines theme accuracy.

3. **Puzzle Modes**: Standard (adaptive), Storm (timed with combos), Streak (untimed with progressive difficulty), and Racer (multiplayer competition).

4. **Analysis Board**: Dual-architecture with browser WASM Stockfish (client-side) and fishnet distributed computing (server-side). Supports 1-5 lines, depths up to 99 plies, and cloud caching.

5. **Stockfish Integration**: Multiple WASM ports including NNUE support. Multi-threaded WebAssembly for performance. Requires specific HTTP headers (COOP/COEP).

6. **Learn Section**: Chess basics for beginners, 32 structured practice lessons (checkmates, tactics, endgames), and coordinate training drills.
