---
title: Competitive Features Research
category: competitive
status: research
last_updated: 2025-12-31
---

# Lichess Competitive Features Research

This document contains comprehensive research on Lichess's competitive features including tournaments, leaderboards, and special events.

---

## Arena Format

Arena tournaments are Lichess's primary tournament format, designed for continuous play over a set duration.

### Core Mechanics

- **Duration-based**: Tournaments run for a set time limit (e.g., 1 hour, 2 hours, 24 hours for marathons)
- **Continuous play**: Players can join and leave at any time during the tournament
- **Immediate pairing**: After finishing a game, players return to the lobby and are paired with someone close to their ranking
- **No fixed rounds**: Unlike Swiss, there's no predetermined number of rounds
- **Open participation**: Anyone can join official arenas (some may have rating restrictions)

### Key Features

1. **Berserk Mode**: Players can sacrifice half their clock time for an extra tournament point on a win
   - Requires at least 7 moves to be played
   - Cancels increment (except 1+2 format which becomes 1+0)
   - Not available in zero-increment games (0+1, 0+2)

2. **Winning Streaks (Fire/Flame)**: Consecutive wins trigger double points
   - Streak starts after 2 consecutive wins
   - Continues until the player fails to win
   - Draws during streak still get streak bonus (2 points instead of 1)

3. **Draw Restrictions**:
   - Draws within the first 10 moves award no points
   - Consecutive draws only award points for the first draw (or draws lasting 30+ moves)
   - Draw streaks can only be broken by wins, not losses

Source: [Arena Tournament FAQ](https://lichess.org/tournament/help)

---

## Arena Scoring

### Points Table

| Result | Normal | On Streak | With Berserk | Berserk + Streak |
|--------|--------|-----------|--------------|------------------|
| Win    | 2      | 4         | 3            | 5                |
| Draw   | 1      | 2         | 1            | 2                |
| Loss   | 0      | 0         | 0            | 0                |

### Additional Scoring Rules

- **First move countdown**: Failing to make the first move within ~15-30 seconds forfeits the game
- **Tournament end**: When the countdown reaches zero, rankings are frozen; games in progress finish but don't count
- **Tiebreaker**: Tournament performance rating breaks ties when players have identical points

Source: [Lichess Forum - Scoring in Arena Tournament](https://lichess.org/forum/general-chess-discussion/scoring-in-arena-tournament)

---

## Arena Pairing Algorithm

### Algorithm Overview

Arena matchmaking uses a **minimum weight matching algorithm** based on Edmonds' Blossom algorithm from graph theory.

### Pairing Formula

The edge weight (pair score) between players a and b is calculated as:

```
pairScore(a, b) = abs(a.rank - b.rank) * rankFactor(a, b) + abs(a.rating - b.rating)^2
```

### Rank Factor Formula

```
rankFactor = 300 + 1700 * (maxRank - min(a.rank, b.rank)) / maxRank
```

This creates dynamic weighting where:
- Top-ranked players receive ~2000 weight (prioritizing good pairings at top)
- Bottom-ranked players receive ~300 weight (looser pairing constraints)
- Higher-ranked players get better pairing quality

### Pairing Behavior

1. **Tournament Start**: Players paired by rating (no scores yet)
2. **During Tournament**: Players paired by current ranking
3. **Rematch Avoidance**: System tracks last opponents to prevent immediate rematches
4. **Color Balance**: Tracks color history to alternate white/black
5. **Wait Time**: Pairing range extends as player waits longer

### Implementation Details

From `modules/tournament/src/main/arena/PairingSystem.scala`:
- Uses tiered strategy:
  1. **Initial pairings**: Simple sequential with random color
  2. **Best pairings**: AntmaPairing algorithm for up to 100 players
  3. **Proximity pairings**: For overflow players beyond 100

Source: [Lichess GitHub - PairingSystem.scala](https://github.com/lichess-org/lila/blob/master/modules/tournament/src/main/arena/PairingSystem.scala)

---

## Performance Rating (Tiebreaker)

### Formula

Tournament Performance Rating (TPR) is calculated as:

```
TPR = Average_Opponent_Rating + (Points_Ratio - 0.5) * 1000
```

Or per-game basis:
- **Win**: opponent rating + 500
- **Draw**: opponent rating
- **Loss**: opponent rating - 500

The mean of all per-game performance ratings determines the tiebreaker.

### Alternative Expression

```
PERF = RO - 500 + 1000 * RATIO
```

Where:
- RO = average opponent rating
- RATIO = points achieved / total points possible

Source: [Lichess Forum - Performance Calculation](https://lichess.org/forum/general-chess-discussion/how-is-performance-calculated-in-tournaments-)

---

## Shield Tournaments

### Overview

Shield tournaments are monthly Arena events where winners receive unique profile trophies.

### Mechanics

- Winner receives a unique shield trophy on their profile
- Trophy held for one month until next Shield tournament
- Must defend in next month's event or lose trophy
- Creates ongoing competitive narrative

### Available Shield Types

**Standard Time Controls:**
- Bullet, SuperBlitz, Blitz, Rapid, Classical
- HyperBullet, UltraBullet

**Variants:**
- Chess960, Crazyhouse, King of the Hill
- Racing Kings, Antichess, Atomic, Horde, Three-check

Source: [Lichess Forum - Shield Arena](https://lichess.org/forum/general-chess-discussion/what-is-shield-arena)

---

## Team Battles

### Overview

Team Battles are Arena-format tournaments where teams compete against each other.

### Key Mechanics

- **Inter-team pairing only**: Players only paired with opponents from other teams (never teammates)
- **Top N scoring**: Only top N player scores count for team total
- **N = configurable**: Tournament creator sets number of "leaders"
- **Protection**: Lower-rated players cannot hurt team score

### Team Scoring

```
Team Score = Sum of top N individual player scores
```

Where N = number of configured "leaders" per team

### Tiebreaker

When teams have equal points:
- Average performance rating of team leaders
- Higher average performance wins

Source: [Team Battle FAQ](https://lichess.org/page/team-battle-faq)

---

## Swiss Format

### Core Rules

- **Round-based**: Fixed number of rounds, all players play same number of games
- **No rematches**: Players can only face each other once
- **Team-required**: Must be hosted by a team (ensures player commitment)

### Scoring

| Result | Points |
|--------|--------|
| Win    | 1      |
| Draw   | 0.5    |
| Loss   | 0      |
| Bye    | 1      |

### Dutch Pairing Algorithm

Lichess uses the **bbpPairings** library implementing the FIDE Dutch system.

#### How Dutch Pairing Works

1. Players grouped by current score (score brackets)
2. Each group split in half by starting rank (rating)
3. Upper half paired with lower half
4. Player 1 vs Player 5, Player 2 vs Player 6, etc.

#### Time Complexity

```
O(n^3 * s * (d + s) * log n)
```

Where:
- n = largest player ID
- s = number of occupied score groups
- d = distinct score differences

### FIDE Absolute Constraints

1. Two players cannot meet more than once
2. Color difference must stay between -2 and +2
3. No player gets same color 3 times in row

### Floaters

- **Downfloat**: Player paired with lower score group
- **Upfloat**: Opponent of downfloating player
- Algorithm minimizes number of floaters

### Forbidden Pairings

Tournament creators can specify player pairs who must not play each other:
- Use case: siblings, schoolmates in scholastic events
- Entered as list of username pairs

### Accelerated Pairings

Used in large tournaments:
- Top half players get 1 virtual point for pairing in rounds 1-2
- Effect: top quarter plays second quarter; third plays fourth
- Methods: US Chess Variation 28R2, FIDE BAM (Baku Acceleration Method)

Source: [FIDE Dutch System Handbook](https://handbook.fide.com/chapter/C0403)

---

## Swiss Special Rules

### Early Draw Prevention

- Draws not allowed before move 30
- Prevents pre-arranged quick draws
- Cannot be bypassed via threefold repetition (must play on)

### Late Joining

- Players can join until more than half the rounds started
- 11-round Swiss: join before round 6
- 12-round Swiss: join before round 7
- Late joiners receive single 0.5 point bye

### No-Show Handling

1. Player's clock ticks, they flag, lose the game
2. System auto-withdraws player to prevent further losses
3. Player can rejoin at any time
4. No-show players temporarily banned from joining new Swiss events
5. Creator can override this ban

### Tiebreakers

**Buchholz Score:**
- Sum of opponents' scores

**Sonneborn-Berger Score:**
- Sum of: scores of beaten opponents + half scores of drawn opponents

Source: [Lichess Swiss](https://lichess.org/swiss)

---

## Swiss TRF Export Format

Tournament Report File format for FIDE reporting:

```
012 Tournament Name
022 City
032 Federation
042 Start Date
052 End Date
062 Number of Players
072 Number of Rated Players
082 Number of Teams
092 Type (SWISS)
102 Chief Arbiter
...
001 001 Player1Name    1234  USA  1800  1.0  +W002  -B003  =W004
001 002 Player2Name    5678  USA  1750  2.0  -B001  +W004  +B003
```

### Lichess TRF Notes

- Player names in lowercase
- Byes exported as "H" or "U"
- Withdrawals exported as "-" (SwissChess expects "0000 - Z")
- Sorted by starting rank number

Source: [FIDE TRF Format](https://handbook.fide.com/chapter/TRFFormat)

---

## Leaderboards

### Rating Leaderboard Requirements

To appear on a variant/time control leaderboard:
1. At least **30 rated games** in that category
2. Played a rated game **within last week**
3. Rating deviation **< 75** (standard chess)
4. Rating deviation **< 65** (variants)

### Rationale

- Week requirement prevents inactive accounts from populating boards
- 30 games ensures established rating
- RD threshold ensures rating confidence

### Provisional Rating Thresholds

- **RD < 230**: Provisional rating displayed (shows "?")
- **RD < 110**: Established rating (no "?")
- Takes approximately 10-20 games depending on opponent RDs

Source: [Lichess Forum - Leaderboard Requirements](https://lichess.org/forum/general-chess-discussion/leaderboard-requirements)

---

## Trophy System

### Leaderboard Trophies

- **Top 100, Top 50, Top 10, Champion** positions
- Trophy retained while player maintains position
- Removed if no rated game in 2 weeks for that variant

### Marathon Trophies

- **Top 500, Top 100, Top 50, Top 10, Winner**
- Blue globe trophy for top 500
- Unique trophies for marathon achievements

### Shield Trophies

- Winner holds unique shield trophy
- Must defend monthly

### Tournament Leaderboard Categories

- **Time-based**: Yearly, Monthly, Weekly, Daily winners
- **Marathon**: Seasonal winners (Spring, Summer, Autumn, Winter)

Source: [Lichess Forum - All Trophies](https://lichess.org/forum/general-chess-discussion/all-the-trophies-in-lichess)

---

## Special Events

### Titled Arena

**Requirements:**
- Verified titled account (GM, IM, FM, NM, CM, etc.)
- Title verification via FIDE or national federation

**Warm-up Arena:**
- Open to all players
- Minimum 20 rated games in time control
- Chess960: minimum 10 rated games

**Format:**
- Standard arena rules
- Usually Bullet (1+0) or Blitz (3+0)

**Prizes:**
- $500 / $250 / $125 / $75 / $50 for top 5

**Schedule:**
- Monthly occurrence with variations (Bullet, Blitz, Chess960)

### Marathon Tournaments

**Duration:** 24 hours of continuous play

**Time Controls by Season:**
- Spring: 2+0 or 5+0
- Summer: varies
- Autumn: 3+2
- Winter: 5+3

**Scoring:**
- Standard arena scoring (2/1/0)
- Streaks and berserk apply
- Performance rating tiebreaker

**Trophies:**
- Top 500 receive unique trophy
- Points threshold varies (e.g., 185-217 for top 500)

### Simultaneous Exhibitions (Simuls)

**Concept:**
- One host plays multiple opponents simultaneously
- Mirrors real-world simul format

**Rules:**
- Always casual (unrated)
- No rematches, takebacks, or time additions
- All games start when simul begins
- Ends when all games complete

**Hosting Requirements:**
- Public visibility: >2400 rating OR titled player
- Anyone can host privately with shareable URL
- Minimum 2 participants to start

**Features:**
- Auto-switch to board with least clock time
- Host can accept/reject join requests
- Multiple variants supported (standard + 8 variants)
- Flexible time controls (Blitz, Rapid, Classical)

Source: [Lichess Simul](https://lichess.org/simul)

---

## Rating System (Glicko-2)

### Implementation

- Uses Glicko-2 (improvement over Glicko-1)
- Starting rating: 1500
- Starting RD (rating deviation): 1000
- 95% confidence: rating between 500 and 2500

### Lichess Adaptations

**Immediate Calculation:**
- Ratings calculated after every game (not in periods)
- Formula modification: `sqrt(phi^2 + t * sigma^2)`
- Where t = time since last update / rating period

**Color Consideration:**
- Slightly more points awarded for results with black pieces

**Rating Stability:**
- Median player stays near 1500
- No significant drift over time

Source: [Lichess Rating Systems](https://lichess.org/page/rating-systems)

---

## Source Code References

### Main Repository

- [lichess-org/lila](https://github.com/lichess-org/lila) - Main codebase (Scala 3)

### Key Arena Files

- `modules/tournament/src/main/arena/PairingSystem.scala`
- `modules/tournament/src/main/TournamentApi.scala`
- `modules/tournament/src/main/Scoring.scala`

### Swiss Pairing

- Uses [bbpPairings](https://github.com/BieremaBoyzProgramming/bbpPairings) library
- [cyanfish/bbpPairings](https://github.com/cyanfish/bbpPairings) - Fast Swiss fork for large tournaments

### Leaderboard

- `modules/user/src/main/Ranking.scala`

---

## Sources

### Official Lichess Documentation
- [Arena Tournament FAQ](https://lichess.org/tournament/help?system=arena)
- [Swiss Tournaments](https://lichess.org/swiss)
- [Team Battle FAQ](https://lichess.org/page/team-battle-faq)
- [Rating Systems](https://lichess.org/page/rating-systems)
- [Simul Page](https://lichess.org/simul)
- [Tournament Leaderboard](https://lichess.org/tournament/leaderboard)
- [FAQ](https://lichess.org/faq)

### Lichess Forum Discussions
- [High Level Description of Matchmaking Algorithm](https://lichess.org/forum/general-chess-discussion/high-level-descriptiion-of-the-matchmaking-algorithm)
- [Arena Pairing Deeper Understanding](https://lichess.org/forum/lichess-feedback/arena-paring-deeper-understanding-request)
- [Performance Rating Calculation](https://lichess.org/forum/general-chess-discussion/how-is-performance-calculated-in-tournaments-)
- [Leaderboard Requirements](https://lichess.org/forum/general-chess-discussion/leaderboard-requirements)
- [Shield Arena](https://lichess.org/forum/general-chess-discussion/what-is-shield-arena)
- [All Trophies](https://lichess.org/forum/general-chess-discussion/all-the-trophies-in-lichess)
- [Forbidden Pairings](https://lichess.org/forum/lichess-feedback/forbidden-pairings-in-swiss-tournaments)

### GitHub Repositories
- [lichess-org/lila](https://github.com/lichess-org/lila)
- [BieremaBoyzProgramming/bbpPairings](https://github.com/BieremaBoyzProgramming/bbpPairings)

### FIDE Documentation
- [FIDE Dutch System Handbook](https://handbook.fide.com/chapter/C0403)
- [Swiss Rules](https://handbook.fide.com/chapter/C0403Till2025)
- [TRF Format](https://handbook.fide.com/chapter/TRFFormat)
