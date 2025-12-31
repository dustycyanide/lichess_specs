---
title: Lichess Clone Specification Documents
linear_ticket: DJA-49
status: draft
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
  - init-django-backend
---

# Lichess Clone Specs

Specification documents for building a Lichess clone with Django/React.

## Styleguides Applied

These specs follow the project's established patterns:

### Backend: Hacksoft Django Styleguide
- **Service Layer**: Business logic in `services.py`, not views or models
- **Selectors**: Query logic in `selectors.py` for read operations
- **Full Clean Pattern**: Always `full_clean()` before `save()`
- **Transaction Boundaries**: `@transaction.atomic` on service methods
- **Keyword-Only Arguments**: `def service_action(*, param: Type)` pattern
- **Type Annotations**: All services and selectors are typed

See: `/.claude/skills/hacksoft-django-styleguide/SKILL.md`

### Frontend: Bulletproof React Styleguide
- **Feature-Based Organization**: Code organized by feature, not file type
- **Direct Imports Only**: No barrel files (`index.ts` re-exports)
- **Three-Part API Pattern**: Zod schema → Fetcher → TanStack Query hook
- **State Management**: Zustand for client state, TanStack Query for server state
- **File Naming**: kebab-case for all files

See: `/.claude/skills/bulletproof-react-styleguide/SKILL.md`

### Project Setup: cookiecutter-django
- **Directory Structure**: `backend/<project_slug>/` (not `backend/apps/`)
- **Settings**: `config/settings/{base,local,production}.py`
- **Authentication**: django-allauth headless for React SPA

See: `/.claude/skills/init-django-backend/SKILL.md`

## Linear Integration

This repo contains 200 tickets organized into 10 phases, synced to Linear.

- `lichess_tickets.json` - All 200 tickets with phase/priority metadata
- `linear_ticket_mapping.json` - Maps local ticket IDs to Linear issue IDs

## Document Structure

```
lichess_specs/
├── 00-overview/           # Project overview, MVP prioritization
├── 01-architecture/       # System architecture specs
│   ├── backend-architecture.md
│   ├── frontend-architecture.md
│   ├── database-schema.md
│   ├── websocket-architecture.md
│   └── caching-strategy.md
├── 02-core-features/      # Core game functionality
│   ├── game-engine.md
│   ├── rating-system.md
│   ├── real-time-gameplay.md
│   └── user-authentication.md
├── 03-game-modes/         # Game mode variants
│   ├── timed-games.md
│   └── correspondence.md
├── 04-training/           # Training features
│   ├── puzzles.md
│   └── analysis-board.md
├── 05-competitive/        # Tournament features
│   ├── arena-tournaments.md
│   ├── swiss-tournaments.md
│   └── leaderboards.md
├── 06-social/             # Social features
│   ├── teams-clubs.md
│   └── chat-messaging.md
├── 07-content/            # Content management
│   ├── opening-explorer.md
│   └── endgame-tablebase.md
├── 08-api/                # API design
│   └── api-design.md
└── 09-resources/          # Reference materials
    └── lichess-research.md
```

## Pattern Examples

### Django Service Pattern
```python
# <project_slug>/games/services.py
@transaction.atomic
def game_create(*, white: User, black: User, time_control: str) -> Game:
    game = Game(white=white, black=black, time_control=time_control)
    game.full_clean()
    game.save()
    return game
```

### React API Pattern
```typescript
// src/features/game/api/get-game.ts
// 1. Schema
export const gameSchema = z.object({ id: z.string(), ... });
// 2. Fetcher
export const getGame = async (id: string) => api.get(`/games/${id}`);
// 3. Hook
export const useGame = (id: string) => useQuery(getGameQueryOptions(id));
```
