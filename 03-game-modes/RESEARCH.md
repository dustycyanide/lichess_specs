# Game Modes Research

## Time Control Categories

### Overview

Lichess classifies games based on **estimated game duration**, calculated using the formula:

```
Estimated Duration = (initial time in seconds) + 40 × (increment in seconds)
```

The multiplier of 40 represents an estimated number of moves in a typical game.

### Category Boundaries

| Category | Estimated Duration | Example Time Controls |
|----------|-------------------|----------------------|
| **UltraBullet** | ≤ 29 seconds | 1/4+0 (15 sec), 1/2+0 (HyperBullet) |
| **Bullet** | ≤ 179 seconds | 1+0, 2+1, 1+1 |
| **Blitz** | ≤ 479 seconds | 3+0, 3+2, 5+0, 5+3 |
| **Rapid** | ≤ 1,499 seconds | 10+0, 15+10, 10+5 |
| **Classical** | ≥ 1,500 seconds | 30+0, 30+20 |
| **Correspondence** | Days per move | 1-14 days/move |

### Calculation Examples

- **5+3 Blitz**: 5x60 + 40x3 = 300 + 120 = 420 seconds (Blitz)
- **10+0 Rapid**: 10x60 + 40x0 = 600 seconds (Rapid)
- **15+10 Rapid**: 15x60 + 40x10 = 900 + 400 = 1,300 seconds (Rapid)
- **1+0 Bullet**: 1x60 + 40x0 = 60 seconds (Bullet)

### Differences from FIDE Definitions

Lichess time control categories differ from FIDE's official definitions:

| Category | FIDE Definition | Lichess Definition |
|----------|-----------------|-------------------|
| Bullet | < 3 min/player | ≤ 179 sec estimated |
| Blitz | < 15 min/player | ≤ 479 sec estimated |
| Rapid | 15-60 min/player | ≤ 1,499 sec estimated |
| Classical | > 60 min/player | ≥ 1,500 sec estimated |

Lichess explicitly states that online chess has different needs than over-the-board (OTB) chess, justifying their custom definitions.

---

## Clock Mechanics

### Fischer Increment (Used by Lichess)

Lichess uses **Fischer increment** (also called "bonus" or "Fischer time"):

- A specified amount of time is added to the player's clock **after each move**
- Time is added regardless of how long the move took
- The player's total time can increase above the initial time
- First used in the 1992 Fischer-Spassky match
- Now the most common increment system worldwide

**Example**: In a 5+3 game, after each move, 3 seconds are added to your clock.

### Bronstein Delay (Not Used by Lichess)

- Time is added after each move, but **only up to the amount of time spent**
- Your clock can never increase above what it was at the start of your turn
- If the delay is 5 seconds and you move in 3 seconds, only 3 seconds are added

**Example**: With a 5-second Bronstein delay, if you have 10 seconds, spend 3 seconds on your move, you end with 10 seconds (not 12).

### Simple Delay / US Delay (Not Used by Lichess)

- The clock waits for the delay period before counting down
- If you move within the delay period, no time is subtracted
- Common in the United States for OTB play
- Mathematically equivalent to Bronstein delay

### Why Lichess Uses Fischer Increment

- Most widely used system internationally
- Simple to understand: same amount added every move
- Prevents "flagging" (winning purely on time in won positions)
- Allows time to be accumulated for complex positions

---

## Correspondence Chess

### Overview

Correspondence chess is an asynchronous form of chess where players have days, not minutes, to make moves.

### Time Control Options

- Players can set **1 to 14 days per move**
- Common options: 1 day, 2 days, 3 days, 7 days, 14 days
- Each move resets the timer to the full allocated time

### How Timing Works

1. When your opponent moves, your timer starts
2. You have the specified number of days to make your move
3. If you move, your timer resets for the next turn
4. If you run out of time before moving, you lose on time

### Rules and Allowed Resources

| Resource | Allowed? |
|----------|----------|
| Opening books | Yes |
| Databases | Yes |
| Chess engines | **No** |
| Other players' help | **No** |

**Important**: Unlike ICCF (International Correspondence Chess Federation), Lichess **prohibits engine use** in correspondence games. Violations result in being flagged for engine assistance.

### Vacation Mode

**Lichess does not have vacation mode for correspondence chess.**

Workarounds suggested by the community:
1. Use longer time controls (e.g., 3+ days/move) for flexibility
2. Set conditional premoves before going offline
3. Use the maximum 14-day setting
4. Ask opponents to manually add time (not guaranteed)

### Multiple Games

- Players can have multiple correspondence games running simultaneously
- Games appear on the home page
- Notifications sent when it's your turn

---

## Game Matching and Seeking

### Quick Pairing System

Quick Pairing is Lichess's primary matchmaking system:

- Click one of 11 preset time control buttons (e.g., "5+3 Blitz")
- System automatically matches you with a similar-rated opponent
- Games are **always rated**
- Uses a pool-based matching system (abstracted from users)
- Rating range expands over time if no match is found

### Lobby System

The Lobby shows custom game seeks:

- Games created via "Custom" or "Create a Game" appear here
- Players can filter lobby games by:
  - Rating range
  - Time control
  - Variant
- Click the gear icon in the lobby to set filters
- Filters are stored in browser local storage

### Quick Pairing vs Lobby

| Feature | Quick Pairing | Lobby |
|---------|--------------|-------|
| Game type | Always rated | Rated or casual |
| Time controls | Preset only | Custom allowed |
| Matching | Automatic | Manual selection |
| Rating range | Auto-expanding | User-defined |
| Visibility | Hidden (pool) | Public seeks |

### Seek Graph

- Visual representation of available game seeks
- Shows rating and time control of seekers
- Available on web version (not mobile app)

### Rating Restrictions

- Players can set maximum rating difference for opponents
- Games outside your specified range won't be visible
- Quick pairing respects rating proximity

---

## Casual vs Rated Games

### Key Differences

| Aspect | Rated Games | Casual Games |
|--------|-------------|--------------|
| Rating impact | Yes | No |
| Matchmaking | Rating-based | Less precise |
| Cheat detection | **Automated** | **Manual only** |
| Leaderboard eligibility | Yes | No |

### Cheat Detection

**Rated games**: Full automated anti-cheat detection active

**Casual games**: "The cheat detection is pretty much turned off for casual games." This is because:
- Training games may involve engines
- Games with friends may be experimental
- Less competitive stakes

Players can still report cheating in casual games, but moderators are less likely to act without obvious evidence.

### When to Play Rated

- When you want accurate matchmaking
- When you want cheat protection
- For tournaments with prizes
- To establish your skill level

### When to Play Casual

- Testing new openings/strategies
- Playing with friends of different skill levels
- Teaching/training purposes
- When you don't want rating pressure

---

## Rematch System

### How Rematches Work

1. After a game ends, the rematch button appears
2. Clicking it sends a rematch offer to your opponent
3. The button disappears when your opponent leaves the game
4. A green indicator turning red shows they've left

### Color Alternation

**Key rule**: Using the rematch button **swaps colors** between games.

- If you played White, you'll play Black in the rematch
- This ensures fairness across multiple games
- Applies to all rematches in the same variant

### Accepting Rematches

**Web**:
- Rematch button appears next to the board after game ends
- Button blinks/wiggles to draw attention
- Click to accept

**Mobile App**:
- Bottom-left menu icon glows blue
- Open the menu to find accept/decline options

### Anti-Sandbagging Protection

- Rematch may be disabled after very short games
- Prevents manipulation (e.g., abort then rematch to keep preferred color)

### Limitations

- Rematch offer only visible if you're online when it's sent
- Correspondence game rematches can be missed if offline
- Multi-device usage can cause rematch to appear on wrong device

---

## Provisional Ratings

### What the Question Mark (?) Means

A rating with a "?" is **provisional**, indicating uncertainty.

### Causes

1. Player hasn't completed enough rated games in that category
2. Player hasn't played recently (ratings can become provisional again after ~1 year of inactivity)

### Technical Details

- Uses Glicko-2 rating system
- "?" appears when rating deviation > 110
- Rating deviation measures confidence in the rating
- Lower deviation = more stable rating

### How Provisional Ratings Behave

- Large rating changes after wins/losses
- Typically stabilizes after ~12 games
- New accounts start at 1500 rating

### Avoiding Provisional Opponents

Players can filter lobby games to avoid provisional-rated opponents through rating range restrictions.

---

## Sources

- [Lichess FAQ - Time Controls](https://lichess.org/faq)
- [Lichess Forum - Time Control Classification](https://lichess.org/forum/lichess-feedback/classification-of-time-controls)
- [Lichess Forum - Quick Pairing vs Lobby](https://lichess.org/forum/general-chess-discussion/quick-pairing-vs-lobby)
- [Lichess Forum - How Correspondence Works](https://lichess.org/forum/general-chess-discussion/how-does-correspondence-work)
- [Lichess Forum - Correspondence Timing Rules](https://lichess.org/forum/general-chess-discussion/correspondence-timing-rules)
- [Lichess Forum - Vacation Mode Discussion](https://lichess.org/forum/lichess-feedback/please-consider-adding-vacation-mode-for-correspondence-games)
- [Lichess Forum - Rated vs Casual](https://lichess.org/forum/general-chess-discussion/whats-difference-between-rated-and-casual-games)
- [Lichess Forum - Cheat Detection in Casual](https://lichess.org/forum/general-chess-discussion/cheat-detection-in-casual-games)
- [Lichess Forum - Rematch System](https://lichess.org/forum/general-chess-discussion/how-do-you-offer-a-rematch-to-your-opponent)
- [Lichess Forum - Provisional Ratings](https://lichess.org/forum/lichess-feedback/explanation-provisional-rating)
- [Wikipedia - Chess Clock](https://en.wikipedia.org/wiki/Chess_clock)
- [Wikipedia - Time Control](https://en.wikipedia.org/wiki/Time_control)
- [Lichess API Documentation](https://lichess.org/api)
- [Lichess API GitHub](https://github.com/lichess-org/api)

---

**Note**: I do not have file writing capabilities in this environment. The above content should be written to `/Users/dustycyanide/Documents/projects/ai/vibefaster/django_react_shipfast/lichess_specs/03-game-modes/RESEARCH.md`.

The research covers all requested topics:
- Time control categories with exact boundaries (UltraBullet through Classical)
- Clock mechanics (Fischer increment vs Bronstein delay vs Simple delay)
- Correspondence chess (time per move, rules, no vacation mode)
- Game seeking/matching (Quick Pairing pools vs Lobby system)
- Casual vs Rated games (including cheat detection differences)
- Rematch system (color swapping, how to accept, anti-sandbagging)
