---
title: Project Overview
category: overview
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
  - init-django-backend
status: draft
linear_ticket: DJA-49
---

# Lichess Clone - Project Overview

> Building a free, open-source chess platform using Django and React

## Styleguide References

This project follows these architectural patterns:

| Layer | Styleguide | Key Patterns |
|-------|------------|--------------|
| **Django Backend** | [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) | Service layer, selectors, thin APIs |
| **React Frontend** | [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) | Feature-based modules, direct imports, TanStack Query |
| **Project Setup** | [Init Django Backend](/.claude/skills/init-django-backend/SKILL.md) | cookiecutter-django, django-allauth headless |

---

## Vision

Create a Lichess-inspired chess platform that demonstrates how Django/React can power a real-time, feature-rich gaming application. This project serves as both a functional chess platform and a showcase for the django_react_shipfast template capabilities.

### Why Clone Lichess?

Lichess represents one of the most impressive achievements in open-source software:
- **Scale**: 5+ million daily games, 7.7+ billion total games
- **Efficiency**: Only 3 full-time employees, ~$577K EUR/year operating costs
- **Philosophy**: 100% free, no ads, no premium tiers, fully open-source

This makes it an ideal reference architecture for building scalable, efficient web applications.

---

## Technology Stack Mapping

### Lichess Stack → Our Stack

| Component | Lichess | Our Implementation |
|-----------|---------|-------------------|
| **Backend Language** | Scala 3 | Python (Django) |
| **Web Framework** | Play Framework | Django + Django REST Framework |
| **Real-time** | Custom WebSocket (lila-ws) | Django Channels |
| **Database** | MongoDB | PostgreSQL |
| **Cache** | Redis | Redis |
| **Chess Logic** | scalachess (Scala) | python-chess |
| **Frontend Board** | Chessground | Chessground (React wrapper) |
| **Frontend UI** | TypeScript + Snabbdom | React + TypeScript |
| **Analysis Engine** | Stockfish (Fishnet) | Stockfish.wasm (browser) |
| **Search** | Custom | Elasticsearch/PostgreSQL FTS |

---

## Core Features

### Game Engine & Chess Logic

**Reference**: `python-chess` library provides:
- Legal move generation and validation
- PGN/FEN parsing and generation
- UCI protocol for engine communication
- Syzygy tablebase support

### Real-time Gameplay

**Architecture**: Django Channels with WebSocket consumers
- Game room management
- Move synchronization
- Clock management
- Disconnect/reconnect handling
- Spectator mode

### User System

- Registration and authentication (django-allauth **headless**)
- User profiles with game history
- Rating display and progression
- Account settings and preferences
- Title verification (GM, IM, FM, etc.)

### Rating System

**Glicko-2 Implementation**:
- Separate ratings per time control
- Rating deviation tracking
- Rating confidence intervals
- Provisional rating handling

### Game Modes

| Mode | Time Control | Clock Increment |
|------|-------------|-----------------|
| **UltraBullet** | < 30s | Typically 0s |
| **Bullet** | < 3min | 0-1s |
| **Blitz** | 3-8min | 0-5s |
| **Rapid** | 8-25min | 0-10s |
| **Classical** | > 25min | Varies |
| **Correspondence** | Days per move | N/A |

### Training Features

- **Puzzles**: Tactical problems from real games
- **Practice**: Endgame and opening drills
- **Coordinates**: Board vision training
- **Analysis Board**: Free-form position analysis

### Tournament Systems

**Arena Tournaments**:
- Continuous pairing during tournament window
- Points based on streaks
- Berserk mode (half time for extra point)

**Swiss Tournaments**:
- Fixed rounds with Swiss pairing
- Tiebreakers (Buchholz, Sonneborn-Berger)

### Study & Learning

- Collaborative analysis boards
- Chapter-based organization
- Interactive lesson creation
- Public/private visibility

### Social Features

- Team/club creation and management
- Team matches and tournaments
- Chat and messaging
- Following/followers

---

## Architecture Decisions

### Database Design (PostgreSQL)

```
Core Models:
├── User (extended Django user)
├── Game
│   ├── Players (white/black FK to User)
│   ├── Moves (stored as PGN/move list)
│   ├── Clock states
│   └── Result and termination
├── Rating (per user, per variant)
├── Puzzle
├── Tournament
└── Study
```

### WebSocket Architecture

```
Django Channels:
├── GameConsumer (real-time gameplay)
├── TournamentConsumer (live standings)
├── TVConsumer (spectating top games)
└── LobbyConsumer (seek/challenge matching)
```

### Caching Strategy

**Redis layers**:
1. **Session cache**: User sessions and authentication
2. **Game cache**: Active game states (hot path)
3. **Rating cache**: Current ratings for matchmaking
4. **Leaderboard cache**: Top players, sorted sets

### API Design

RESTful API (Django REST Framework) for:
- Game history and archives
- User profiles and stats
- Puzzle database
- Tournament management

WebSocket API for:
- Live game moves
- Real-time clock sync
- Lobby/matchmaking
- Chat messages

---

## Open Source Resources

### Direct Integration

| Resource | Purpose | License |
|----------|---------|---------|
| **[Chessground](https://github.com/lichess-org/chessground)** | Board UI component | GPL-3.0 |
| **[python-chess](https://github.com/niklasf/python-chess)** | Chess logic library | GPL-3.0 |
| **[Stockfish.wasm](https://github.com/nicfab/stockfish.wasm)** | Browser analysis | GPL-3.0 |

### Data Resources

| Resource | Purpose | Size |
|----------|---------|------|
| **[Lichess Database](https://database.lichess.org/)** | Historical games | 4TB+ |
| **[Lichess Puzzles](https://database.lichess.org/#puzzles)** | Puzzle database | Millions |
| **[Opening Explorer](https://lichess.org/api#tag/Opening-Explorer)** | Opening statistics | API |

### Reference Repositories

| Repository | What to Learn |
|------------|---------------|
| **[lila](https://github.com/lichess-org/lila)** | Overall architecture |
| **[scalachess](https://github.com/lichess-org/scalachess)** | Chess logic patterns |
| **[lila-ws](https://github.com/lichess-org/lila-ws)** | WebSocket design |
| **[fishnet](https://github.com/lichess-org/fishnet)** | Distributed analysis |

---

## Success Metrics

### Technical Metrics
- **Latency**: < 100ms move propagation
- **Uptime**: 99.9% availability target
- **Concurrency**: Support 1000+ simultaneous games

### User Metrics
- Games played per day
- User retention rate
- Average session duration
- Tournament participation

---

## Related Documents

- [MVP Prioritization](./mvp-prioritization.md) - Feature phasing and priorities
- [RESEARCH.md](./RESEARCH.md) - Detailed Lichess research

---

*Document created: December 2025*
