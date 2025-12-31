---
title: Core Features Research
category: core-features
research_date: 2025-12-31
status: complete
---

# Lichess Core Features Research

This document contains research findings on Lichess's core features: chess engine, real-time gameplay, authentication, and rating system. These findings inform the implementation of our Django/React clone.

## Table of Contents

1. [Chess Rules Engine (scalachess)](#chess-rules-engine-scalachess)
2. [Move Validation](#move-validation)
3. [Game State Representation](#game-state-representation)
4. [Real-time Protocol](#real-time-protocol)
5. [Clock Management](#clock-management)
6. [Authentication](#authentication)
7. [Rating System (Glicko-2)](#rating-system-glicko-2)
8. [Sources](#sources)

---

## Chess Rules Engine (scalachess)

### Overview

Lichess uses **scalachess**, a Chess API written in Scala that is "entirely functional, immutable, and free of side effects." This pure functional approach provides critical advantages for concurrent game processing and testing reliability.

**Repository**: https://github.com/lichess-org/scalachess

### Architecture

The scalachess library is organized into modular components:

| Module | Purpose |
|--------|---------|
| `core` | Main chess logic implementation |
| `bench` | Performance benchmarking suite (JMH-based) |
| `rating` | Rating calculation modules |
| `tiebreak` | Tournament tiebreak calculations |
| `playJson` | JSON serialization support |
| `test-kit` | Testing utilities |

### Key Characteristics

- **Language**: Scala 3 (99.9% of codebase)
- **Build System**: SBT
- **License**: MIT (open source)
- **Commits**: 4,540+ commits demonstrating active maintenance
- **Releases**: 35+ published versions

### JavaScript Port (scalachessjs)

For client-side use, scalachess has been compiled to JavaScript via Scala.js:

- Runs in a **web worker** (non-blocking)
- **Completely stateless** - send complete game position in each request
- Supports FEN or PGN input
- Powers the Lichess mobile application
- Supports multiple chess variants: Chess 960, King of the Hill, Three-check, Antichess, Atomic, Horde, Racing Kings, Crazyhouse

---

## Move Validation

### Approach: Pseudo-Legal vs Legal Moves

Chess engines typically use one of two approaches:

1. **Pseudo-Legal Move Generation**: Pieces obey normal movement rules but are not checked to see if they leave the king in check. Legality is verified only when needed.

2. **Legal Move Generation**: Only legal moves are generated, requiring extra validation for pins, especially when en passant is involved.

Most engines, including scalachess, generate **pseudo-legal moves** and defer legality checks for performance reasons. During search with good move ordering, often only a few moves need legality verification before abandoning a node.

### Move Format

Lichess uses **UCI (Universal Chess Interface)** long algebraic notation:

| Move Type | UCI Format | Example |
|-----------|------------|---------|
| Standard move | `{from}{to}` | `e2e4` |
| Castling (kingside) | King's movement | `e1g1` |
| Castling (queenside) | King's movement | `e1c1` |
| Promotion | `{from}{to}{piece}` | `e7e8q` |
| Null move | `0000` | Engine only |

### Special Move Validation

#### Castling Requirements

Castling is permitted only if:
- Neither the king nor rook has previously moved
- Squares between king and rook are vacant
- King is not in check
- King does not cross or land on an attacked square

Two types:
- **Kingside (O-O)**: King to g1/g8, Rook to f1/f8
- **Queenside (O-O-O)**: King to c1/c8, Rook to d1/d8

#### En Passant

Requirements:
- Capturing pawn must be on 5th rank (White) or 4th rank (Black)
- Target pawn must have just advanced two squares
- Capture must be made immediately on the next move

#### Pawn Promotion

When a pawn reaches the 8th rank (White) or 1st rank (Black):
- Must promote to Queen, Rook, Bishop, or Knight
- Not limited to previously captured pieces
- Queen is most common choice

---

## Game State Representation

### FEN (Forsyth-Edwards Notation)

FEN describes a single static board position. A valid FEN string has six space-separated fields:

