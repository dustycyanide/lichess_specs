---
title: Competitive Features Research
category: competitive
status: research
last_updated: 2025-12-31
---

# Lichess Competitive Features Research

This document contains comprehensive research on Lichess's competitive features including tournaments, leaderboards, and special events.

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
   - Not available in zero-increment games

2. **Winning Streaks (Fire/Flame)**: Consecutive wins trigger double points
   - Streak starts after 2 consecutive wins
   - Continues until the player fails to win

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

- **First move countdown**: Failing to make the first move within the countdown forfeits the game
- **Tournament end**: When the countdown reaches zero, rankings are frozen; games in progress finish but don't count
- **Tiebreaker**: Tournament performance (rating-based calculation) breaks ties when players have identical points

Source: [Lichess Forum - Scoring in Arena Tournament](https://lichess.org/forum/general-chess-discussion/scoring-in-arena-tournament)

---

## Arena Pairing

### Algorithm Overview

Arena matchmaking uses a **minimum weight matching algorithm** based on graph theory (Blossom algorithm).

### Pairing Formula

The edge weight between players a and b is calculated as:

