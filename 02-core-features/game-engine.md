---
title: Game Engine & Chess Logic
category: core-features
dependencies: python-chess
lichess_equivalent: scalachess
styleguide: hacksoft-django-styleguide
status: complete
---

# Game Engine & Chess Logic Specification

This document specifies how to implement chess game logic for our Django/React Lichess clone, mapping Lichess's scalachess patterns to Python equivalents.

> **Styleguide Reference**: This feature follows the [Hacksoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide) patterns. Business logic belongs in **services**, not in models or views. Models should only contain properties, validations, and simple methods. Services handle all write operations with `@transaction.atomic`, keyword-only arguments (`*`), type annotations, and `full_clean()` before `save()`.

## Overview

Lichess uses **scalachess**, a pure functional, immutable Scala library. Our Django implementation will use **python-chess**, which provides similar functionality with a Pythonic API.

| Lichess | Our Stack |
|---------|-----------|
| scalachess (Scala) | python-chess (Python) |
| scalachessjs (JS/WebWorker) | chess.js (client-side validation) |
| FEN/PGN serialization | python-chess built-in |

## python-chess Library

### Installation

```bash
pip install chess
```

### Core Concepts

python-chess provides:
- Complete chess rules implementation
- Move generation and validation
- FEN/PGN parsing and serialization
- Syzygy tablebase support
- UCI protocol for engine communication

### Key Classes

```python
import chess

# Board represents the current game state
board = chess.Board()  # Standard starting position
board = chess.Board(fen="...")  # From FEN string

# Move representation
move = chess.Move.from_uci("e2e4")
move = chess.Move(chess.E2, chess.E4)

# Move validation
if move in board.legal_moves:
    board.push(move)
```

## Move Validation

### Approach

Like scalachess, python-chess generates legal moves efficiently:

```python
import chess

board = chess.Board()

# Get all legal moves
legal_moves = list(board.legal_moves)

# Validate a specific move
move = chess.Move.from_uci("e2e4")
is_legal = move in board.legal_moves

# Apply move if legal
if is_legal:
    board.push(move)
```

### Move Format

Use UCI (Universal Chess Interface) notation for consistency with Lichess:

| Move Type | UCI Format | Example |
|-----------|------------|---------|
| Standard | `{from}{to}` | `e2e4` |
| Castling (kingside) | King movement | `e1g1` |
| Castling (queenside) | King movement | `e1c1` |
| Promotion | `{from}{to}{piece}` | `e7e8q` |

### Special Moves

#### Castling

```python
# Check castling rights
board.has_kingside_castling_rights(chess.WHITE)
board.has_queenside_castling_rights(chess.WHITE)

# Castling moves are represented as king movement
kingside = chess.Move.from_uci("e1g1")  # White O-O
queenside = chess.Move.from_uci("e1c1")  # White O-O-O
```

#### En Passant

```python
# Check if en passant is possible
if board.ep_square:
    print(f"En passant available on {chess.square_name(board.ep_square)}")

# En passant moves are in legal_moves when valid
```

#### Pawn Promotion

```python
# Promotion moves include the piece type
promo_queen = chess.Move.from_uci("e7e8q")
promo_knight = chess.Move.from_uci("e7e8n")

# Check if move is promotion
if move.promotion:
    print(f"Promoting to {chess.piece_name(move.promotion)}")
```

## Game State Representation

### FEN (Forsyth-Edwards Notation)

FEN is the standard for serializing board positions. python-chess handles this natively:

```python
# Get current FEN
fen = board.fen()
# "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"

# Load from FEN
board = chess.Board(fen)

# FEN components
board.board_fen()  # Piece placement only
board.turn         # chess.WHITE or chess.BLACK
board.castling_rights  # Bitmask of castling rights
board.ep_square    # En passant target square
board.halfmove_clock  # For 50-move rule
board.fullmove_number  # Move counter
```

### PGN (Portable Game Notation)

For complete game history with metadata:

```python
import chess.pgn
import io

# Parse PGN
pgn_string = """
[Event "Casual Game"]
[White "Player1"]
[Black "Player2"]

1. e4 e5 2. Nf3 Nc6 *
"""
game = chess.pgn.read_game(io.StringIO(pgn_string))

# Navigate moves
board = game.board()
for move in game.mainline_moves():
    board.push(move)

# Create PGN from game
game = chess.pgn.Game()
game.headers["Event"] = "Rated Game"
node = game.add_variation(chess.Move.from_uci("e2e4"))
node = node.add_variation(chess.Move.from_uci("e7e5"))
print(game)
```

## Game State Detection

### Game Termination

```python
# Check various end conditions
board.is_checkmate()
board.is_stalemate()
board.is_insufficient_material()
board.can_claim_fifty_moves()
board.can_claim_threefold_repetition()
board.is_game_over()

# Get outcome
outcome = board.outcome()
if outcome:
    print(f"Winner: {outcome.winner}")  # True=White, False=Black, None=Draw
    print(f"Termination: {outcome.termination}")
```

### Check Detection

```python
board.is_check()
board.is_into_check(move)  # Would this move leave us in check?
board.gives_check(move)    # Does this move give check?
```

## Django Integration

### Game Model

> **Note**: Following Hacksoft patterns, models contain only field definitions, properties, and simple read-only methods. All business logic (making moves, updating game status) is in services.

```python
# <project_slug>/games/models.py
from django.db import models
import chess

class Game(models.Model):
    white_player = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='games_as_white')
    black_player = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='games_as_black')

    # Current position
    fen = models.CharField(max_length=100, default=chess.STARTING_FEN)

    # Move history in UCI format
    moves = models.TextField(blank=True)  # Space-separated: "e2e4 e7e5 g1f3"

    # Game metadata
    time_control = models.CharField(max_length=20)  # "5+0", "10+5", etc.
    status = models.CharField(max_length=20, choices=[
        ('created', 'Created'),
        ('started', 'Started'),
        ('draw', 'Draw'),
        ('white_wins', 'White Wins'),
        ('black_wins', 'Black Wins'),
        ('aborted', 'Aborted'),
    ])

    created_at = models.DateTimeField(auto_now_add=True)

    # Read-only helper method (no business logic)
    def get_board(self) -> chess.Board:
        """Reconstruct board from move history."""
        board = chess.Board()
        if self.moves:
            for uci in self.moves.split():
                board.push_uci(uci)
        return board
```

### Game Services

> **Note**: Services follow Hacksoft patterns: keyword-only arguments with `*`, type annotations, `@transaction.atomic` for write operations, and `full_clean()` before `save()`.

```python
# <project_slug>/games/services.py
import chess
from typing import Optional
from django.db import transaction

from <project_slug>.games.models import Game


# ============================================================================
# Read Operations (Selectors could also be used for complex queries)
# ============================================================================

def validate_move(*, fen: str, uci: str) -> tuple[bool, Optional[str]]:
    """
    Validate a move and return the resulting FEN if legal.

    Returns:
        (is_legal, new_fen or error_message)
    """
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci)

        if move not in board.legal_moves:
            return False, "Illegal move"

        board.push(move)
        return True, board.fen()
    except ValueError as e:
        return False, str(e)


def get_legal_moves(*, fen: str) -> list[str]:
    """Return all legal moves in UCI format."""
    board = chess.Board(fen)
    return [move.uci() for move in board.legal_moves]


def get_game_status(*, fen: str) -> dict:
    """Return current game status."""
    board = chess.Board(fen)
    return {
        'is_check': board.is_check(),
        'is_checkmate': board.is_checkmate(),
        'is_stalemate': board.is_stalemate(),
        'is_game_over': board.is_game_over(),
        'turn': 'white' if board.turn else 'black',
        'legal_moves': [m.uci() for m in board.legal_moves],
    }


# ============================================================================
# Write Operations
# ============================================================================

@transaction.atomic
def game_make_move(*, game: Game, uci: str) -> Game:
    """
    Make a move in a game. Updates game state and checks for game end.

    Raises:
        ValueError: If move is illegal or invalid.
    """
    board = game.get_board()

    try:
        move = chess.Move.from_uci(uci)
    except ValueError as e:
        raise ValueError(f"Invalid UCI format: {e}")

    if move not in board.legal_moves:
        raise ValueError("Illegal move")

    board.push(move)
    game.moves = f"{game.moves} {uci}".strip()
    game.fen = board.fen()

    # Check for game end conditions
    if board.is_checkmate():
        game.status = 'white_wins' if board.turn == chess.BLACK else 'black_wins'
    elif board.is_stalemate() or board.is_insufficient_material():
        game.status = 'draw'

    game.full_clean()
    game.save()

    return game


@transaction.atomic
def game_create(
    *,
    white_player,
    black_player,
    time_control: str,
) -> Game:
    """Create a new game."""
    game = Game(
        white_player=white_player,
        black_player=black_player,
        time_control=time_control,
        status='created',
    )

    game.full_clean()
    game.save()

    return game
```

## Client-Side Validation

For responsive UI, use chess.js for client-side move validation:

```typescript
// frontend/src/utils/chess.ts
import { Chess } from 'chess.js';

export function validateMoveClient(fen: string, from: string, to: string): boolean {
  const chess = new Chess(fen);
  const move = chess.move({ from, to, promotion: 'q' }); // Auto-promote to queen
  return move !== null;
}

export function getLegalMoves(fen: string): string[] {
  const chess = new Chess(fen);
  return chess.moves({ verbose: true }).map(m => `${m.from}${m.to}`);
}
```

**Important**: Always validate moves server-side. Client-side validation is only for UI responsiveness.

## Variant Support (Future)

python-chess supports variants that can be added later:

```python
import chess.variant

# Chess960/Fischer Random
board = chess.Board.from_chess960_pos(518)

# Other variants available:
# chess.variant.CrazyhouseBoard()
# chess.variant.AtomicBoard()
# chess.variant.AntichessBoard()
# chess.variant.KingOfTheHillBoard()
# chess.variant.ThreeCheckBoard()
# chess.variant.RacingKingsBoard()
# chess.variant.HordeBoard()
```

## Performance Considerations

1. **FEN vs Move History**: Store move history for game replay, but use FEN for quick position lookups
2. **Caching**: Cache legal moves for positions that appear frequently
3. **Client Validation**: Validate on client for instant feedback, always verify server-side
4. **Board Reconstruction**: For long games, consider storing checkpoints every N moves

## Sources

- [python-chess Documentation](https://python-chess.readthedocs.io/)
- [scalachess Repository](https://github.com/lichess-org/scalachess)
- [UCI Protocol](https://www.chessprogramming.org/UCI)
- [FEN Specification](https://www.chessprogramming.org/Forsyth-Edwards_Notation)
