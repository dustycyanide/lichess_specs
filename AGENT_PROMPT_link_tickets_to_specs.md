# Agent Prompt: Link Lichess Tickets to Spec Documents

## Objective

Update ALL 200 tickets in `lichess_specs/lichess_tickets.json` to reference the detailed spec documents in the `lichess_specs/` folder. Each ticket should include a `spec_refs` field pointing to relevant specification documents that provide deeper context.

## Context

The `lichess_tickets.json` file contains 200 tickets organized into 10 phases. A previous agent updated ~15-20 tickets to align with Hacksoft Django and Bulletproof React patterns, but did NOT add references to the spec documents. Your job is to:

1. Go through EVERY ticket (all 200)
2. Add a `spec_refs` array field to each ticket
3. Reference the appropriate spec documents from `lichess_specs/` subdirectories

## Spec Document Inventory

### 00-overview/
- `project-overview.md` - High-level project goals and scope
- `mvp-prioritization.md` - MVP feature prioritization

### 01-architecture/
- `backend-architecture.md` - Django backend design
- `frontend-architecture.md` - React frontend design
- `database-schema.md` - Data models and relationships
- `websocket-architecture.md` - Real-time communication design
- `caching-strategy.md` - Redis caching approach

### 02-core-features/
- `game-engine.md` - Chess rules, python-chess integration
- `user-authentication.md` - Auth flows, allauth integration
- `real-time-gameplay.md` - Live game mechanics
- `rating-system.md` - Glicko-2 implementation

### 03-game-modes/
- `timed-games.md` - Bullet, blitz, rapid, classical
- `correspondence.md` - Correspondence game mechanics

### 04-training/
- `puzzles.md` - Puzzle system and rating
- `analysis-board.md` - Stockfish integration, analysis features

### 05-competitive/
- `arena-tournaments.md` - Arena tournament format
- `swiss-tournaments.md` - Swiss pairing system
- `leaderboards.md` - Ranking and leaderboard display

### 06-social/
- `teams-clubs.md` - Team creation and management
- `chat-messaging.md` - In-game and direct messaging
- `studies.md` - Collaborative study feature

### 07-content/
- `opening-explorer.md` - Opening database integration
- `tablebase.md` - Endgame tablebase queries
- `tv-broadcasts.md` - Live game spectating, broadcasts

### 08-api/
- `api-design.md` - Public API design, OAuth, rate limiting

### 09-resources/
- `data-sources.md` - External data (puzzles, openings, etc.)
- `open-source-resources.md` - Libraries and tools to use

### lichess_clones/
- Reference implementations from actual Lichess codebase (lila, scalachess, chessground, lila-ws)

## Mapping Guide: Phases to Spec Documents

Use this mapping as a starting point:

| Phase | Primary Spec Docs |
|-------|-------------------|
| phase-0 (Foundation) | `01-architecture/*`, `00-overview/*` |
| phase-1 (Chess Engine) | `02-core-features/game-engine.md`, `lichess_clones/scalachess/` |
| phase-2 (Auth & Users) | `02-core-features/user-authentication.md` |
| phase-3 (Real-time) | `01-architecture/websocket-architecture.md`, `02-core-features/real-time-gameplay.md` |
| phase-4 (Game Mechanics) | `02-core-features/real-time-gameplay.md`, `03-game-modes/*` |
| phase-5 (Analysis & Training) | `04-training/*` |
| phase-6 (Rating & Competitive) | `02-core-features/rating-system.md`, `05-competitive/*` |
| phase-7 (Social) | `06-social/*` |
| phase-8 (Content & Discovery) | `07-content/*`, `06-social/studies.md` |
| phase-9 (API & Polish) | `08-api/api-design.md`, `01-architecture/*` |

## Output Format

Add a `spec_refs` array to each ticket. Use relative paths from `lichess_specs/`:

```json
{
  "id": "LIC-21",
  "title": "Integrate python-chess library with Hacksoft service pattern",
  "description": "...",
  "spec_refs": [
    "02-core-features/game-engine.md",
    "lichess_clones/scalachess/README.md"
  ],
  ...
}
```

## Rules

1. **Every ticket MUST have spec_refs** - even if just `["00-overview/project-overview.md"]` as a fallback
2. **Be specific** - Don't just reference entire directories, reference specific .md files
3. **Multiple refs are fine** - A ticket can reference 1-4 spec documents
4. **Prioritize primary specs** - List most relevant spec first
5. **Don't modify other fields** - Only add the `spec_refs` array
6. **Use relative paths** - From the `lichess_specs/` directory root

## Validation

After updating, verify:
- All 200 tickets have a `spec_refs` field
- All referenced files actually exist
- JSON is valid (no trailing commas, proper syntax)

## Execution Strategy

Process tickets in batches by phase:
1. Phase 0: LIC-1 through LIC-20
2. Phase 1: LIC-21 through LIC-40
3. Phase 2: LIC-41 through LIC-60
4. Phase 3: LIC-61 through LIC-80
5. Phase 4: LIC-81 through LIC-100
6. Phase 5: LIC-101 through LIC-120
7. Phase 6: LIC-121 through LIC-140
8. Phase 7: LIC-141 through LIC-160
9. Phase 8: LIC-161 through LIC-180
10. Phase 9: LIC-181 through LIC-200

For each batch:
1. Read the relevant spec documents to understand their content
2. Match tickets to specs based on topic alignment
3. Update the tickets with `spec_refs`
4. Move to next batch

## Example Mappings

| Ticket | Likely spec_refs |
|--------|------------------|
| LIC-1 (Django init) | `["01-architecture/backend-architecture.md"]` |
| LIC-2 (React init) | `["01-architecture/frontend-architecture.md"]` |
| LIC-21 (python-chess) | `["02-core-features/game-engine.md", "lichess_clones/scalachess/README.md"]` |
| LIC-61 (Django Channels) | `["01-architecture/websocket-architecture.md", "02-core-features/real-time-gameplay.md"]` |
| LIC-105 (Puzzle model) | `["04-training/puzzles.md", "09-resources/data-sources.md"]` |
| LIC-121 (Glicko-2) | `["02-core-features/rating-system.md", "lichess_clones/scalachess/rating/"]` |
| LIC-125 (Tournaments) | `["05-competitive/arena-tournaments.md"]` |
| LIC-145 (Chat) | `["06-social/chat-messaging.md"]` |
| LIC-161 (Opening explorer) | `["07-content/opening-explorer.md"]` |
| LIC-181 (Public API) | `["08-api/api-design.md"]` |

## Start

Begin with Phase 0 tickets (LIC-1 through LIC-20). Read the architecture specs first to understand the overall structure, then add spec_refs to each ticket.
