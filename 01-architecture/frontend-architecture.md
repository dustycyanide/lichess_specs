---
title: Frontend Architecture
category: architecture
stack: React, Chessground, TypeScript
styleguide: bulletproof-react-styleguide
status: draft
---

# Frontend Architecture

This document maps Lichess's Snabbdom-based frontend to React equivalents, following the **Bulletproof React Styleguide** patterns.

> **Styleguide Reference**: This architecture follows the [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md). Key principles: feature-based organization, **direct imports (no barrel files)**, TanStack Query for server state, and provider pattern for swappable implementations.

## Lichess → React Architecture Mapping

| Lichess | Our Stack | Purpose |
|---------|-----------|---------|
| Snabbdom | React 18 | UI library / Virtual DOM |
| TypeScript | TypeScript | Type safety |
| Chessground | react-chessground | Chess board component |
| Sass/SCSS | Tailwind CSS | Styling |
| pnpm workspaces | pnpm | Package management |
| Server-side render (scalatags) | Client-side SPA | Rendering strategy |

## Application Structure

Following Bulletproof React patterns:

```
frontend/
├── src/
│   ├── app/                    # App-level config, providers, routes
│   │   ├── routes/             # Route definitions
│   │   ├── provider.tsx        # App providers (auth, theme, etc.)
│   │   └── main.tsx            # Entry point
│   │
│   ├── components/             # Shared UI components
│   │   ├── ui/                 # Primitive UI (buttons, inputs)
│   │   └── layouts/            # Page layouts
│   │
│   ├── features/               # Feature-based modules
│   │   ├── game/               # Live game playing
│   │   ├── lobby/              # Matchmaking & seeks
│   │   ├── analysis/           # Analysis board
│   │   ├── puzzles/            # Tactical training
│   │   ├── tournaments/        # Tournament UI
│   │   ├── study/              # Collaborative studies
│   │   └── user/               # Profiles & settings
│   │
│   ├── hooks/                  # Shared React hooks
│   ├── lib/                    # Third-party wrappers
│   ├── stores/                 # Global state (Zustand)
│   ├── types/                  # Shared TypeScript types
│   └── utils/                  # Utility functions
│
├── public/
└── package.json
```

## Core Components

### Chessground Integration

[Chessground](https://github.com/lichess-org/chessground) is Lichess's official board component. We use the React wrapper:

```tsx
// src/features/game/components/Board.tsx
import { Chessground } from 'react-chessground'
import 'react-chessground/dist/styles/chessground.css'
import { useMemo } from 'react'
import type { Key } from 'chessground/types'

interface BoardProps {
  fen: string
  orientation: 'white' | 'black'
  lastMove?: [Key, Key]
  turnColor: 'white' | 'black'
  movable?: {
    free: boolean
    dests: Map<Key, Key[]>
  }
  onMove?: (from: Key, to: Key) => void
  viewOnly?: boolean
}

export function Board({
  fen,
  orientation,
  lastMove,
  turnColor,
  movable,
  onMove,
  viewOnly = false
}: BoardProps) {
  const config = useMemo(() => ({
    fen,
    orientation,
    lastMove,
    turnColor,
    viewOnly,
    movable: movable ?? { free: false },
    events: {
      move: onMove
    },
    animation: {
      enabled: true,
      duration: 200
    },
    highlight: {
      lastMove: true,
      check: true
    }
  }), [fen, orientation, lastMove, turnColor, movable, onMove, viewOnly])

  return (
    <div className="board-container aspect-square w-full max-w-[600px]">
      <Chessground config={config} />
    </div>
  )
}
```

### Legal Moves Calculation

Client-side move validation using chess.js:

```tsx
// src/features/game/hooks/useLegalMoves.ts
import { useMemo } from 'react'
import { Chess } from 'chess.js'
import type { Key } from 'chessground/types'

export function useLegalMoves(fen: string): Map<Key, Key[]> {
  return useMemo(() => {
    const chess = new Chess(fen)
    const dests = new Map<Key, Key[]>()

    chess.moves({ verbose: true }).forEach(move => {
      const from = move.from as Key
      const to = move.to as Key

      if (!dests.has(from)) {
        dests.set(from, [])
      }
      dests.get(from)!.push(to)
    })

    return dests
  }, [fen])
}
```

## Feature Module Pattern

Each feature is self-contained with its own components, hooks, and API layer.

> **IMPORTANT**: No barrel files (`index.ts` with re-exports). Use direct imports for optimal tree-shaking.

```
features/game/
├── api/                         # TanStack Query hooks (three-part pattern)
│   ├── get-game.ts             # Query hook: schema + fetcher + hook
│   ├── create-game.ts          # Mutation hook with cache invalidation
│   └── make-move.ts
├── components/                  # Feature-specific components (kebab-case)
│   ├── game-board.tsx
│   ├── chess-clock.tsx
│   ├── move-list.tsx
│   └── game-controls.tsx
├── hooks/                       # Feature-specific hooks
│   ├── use-game.ts
│   ├── use-game-socket.ts
│   └── use-legal-moves.ts
├── stores/                      # Feature-specific Zustand stores
│   └── game-store.ts
└── types/                       # Feature-specific Zod schemas + types
    └── game.ts                  # NOT index.ts - direct imports only
```

**Import Pattern:**
```typescript
// ✅ CORRECT: Direct imports
import { GameBoard } from '@/features/game/components/game-board';
import { useGame } from '@/features/game/api/get-game';
import { type Game, gameSchema } from '@/features/game/types/game';

// ❌ WRONG: Barrel file imports
import { GameBoard, useGame } from '@/features/game';
```

### Example Feature: Live Game

```tsx
// src/features/game/components/LiveGame.tsx
import { useParams } from 'react-router-dom'
import { Board } from './Board'
import { Clock } from './Clock'
import { MoveList } from './MoveList'
import { useGame } from '../hooks/useGame'
import { useGameSocket } from '../hooks/useGameSocket'
import { useLegalMoves } from '../hooks/useLegalMoves'

export function LiveGame() {
  const { gameId } = useParams<{ gameId: string }>()
  const { game, makeMove } = useGame(gameId!)
  const { connected } = useGameSocket(gameId!)
  const legalMoves = useLegalMoves(game?.fen ?? '')

  if (!game) return <div>Loading...</div>

  const isMyTurn = game.turnColor === game.myColor

  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <Clock
          time={game.opponentClock}
          active={!isMyTurn && game.status === 'started'}
        />

        <Board
          fen={game.fen}
          orientation={game.myColor}
          lastMove={game.lastMove}
          turnColor={game.turnColor}
          movable={isMyTurn ? { free: false, dests: legalMoves } : undefined}
          onMove={(from, to) => makeMove(`${from}${to}`)}
        />

        <Clock
          time={game.myClock}
          active={isMyTurn && game.status === 'started'}
        />
      </div>

      <MoveList moves={game.moves} currentPly={game.ply} />
    </div>
  )
}
```

## State Management

### Zustand for Global State

```tsx
// src/features/game/stores/game-store.ts
import { create } from 'zustand'
import type { Game, Move } from '../types'

interface GameState {
  game: Game | null
  setGame: (game: Game) => void
  applyMove: (move: Move) => void
  reset: () => void
}

export const useGameStore = create<GameState>((set) => ({
  game: null,

  setGame: (game) => set({ game }),

  applyMove: (move) => set((state) => {
    if (!state.game) return state

    return {
      game: {
        ...state.game,
        fen: move.fen,
        moves: [...state.game.moves, move],
        ply: state.game.ply + 1,
        lastMove: [move.from, move.to],
        turnColor: state.game.turnColor === 'white' ? 'black' : 'white'
      }
    }
  }),

  reset: () => set({ game: null })
}))
```

### TanStack Query for Server State (Three-Part Pattern)

Every API operation follows the **three-part pattern**: Zod schema → Fetcher function → Query/Mutation hook.

```tsx
// src/features/game/api/get-game.ts
import { useQuery, queryOptions } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/lib/api-client';

// 1. Zod Schema (runtime validation + type inference)
export const gameSchema = z.object({
  id: z.string(),
  fen: z.string(),
  moves: z.string(),
  status: z.enum(['created', 'started', 'finished']),
  white: z.object({ id: z.string(), username: z.string(), rating: z.number() }),
  black: z.object({ id: z.string(), username: z.string(), rating: z.number() }),
  clock: z.object({ white: z.number(), black: z.number() }).optional(),
});

export type Game = z.infer<typeof gameSchema>;

// 2. Fetcher function
export const getGame = async (gameId: string): Promise<Game> => {
  const response = await api.get(`/games/${gameId}`);
  return gameSchema.parse(response);
};

// 3. Query options (for prefetching and cache key consistency)
export const getGameQueryOptions = (gameId: string) => {
  return queryOptions({
    queryKey: ['games', gameId],
    queryFn: () => getGame(gameId),
  });
};

// 4. Hook
export const useGame = (gameId: string) => {
  return useQuery(getGameQueryOptions(gameId));
};
```

```tsx
// src/features/game/api/make-move.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/lib/api-client';
import { getGameQueryOptions } from './get-game';

const makeMoveInputSchema = z.object({
  uci: z.string().min(4).max(5),  // e.g., "e2e4" or "e7e8q"
});

export const makeMove = async (gameId: string, input: z.infer<typeof makeMoveInputSchema>) => {
  return await api.post(`/games/${gameId}/move`, input);
};

export const useMakeMove = (gameId: string, mutationConfig = {}) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (uci: string) => makeMove(gameId, { uci }),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getGameQueryOptions(gameId).queryKey,
      });
      mutationConfig.onSuccess?.(...args);
    },
  });
};
```

## WebSocket Integration

### Custom Hook for Game WebSocket

```tsx
// src/features/game/hooks/useGameSocket.ts
import { useEffect, useRef, useCallback } from 'react'
import { useGameStore } from '../stores/game-store'

interface GameMessage {
  t: string  // type
  d?: any    // data
}

export function useGameSocket(gameId: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const { applyMove, setGame } = useGameStore()

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/game/${gameId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const msg: GameMessage = JSON.parse(event.data)

      switch (msg.t) {
        case 'move':
          applyMove(msg.d)
          break
        case 'end':
          setGame({ ...useGameStore.getState().game!, status: msg.d.status })
          break
        case 'clock':
          // Update clocks
          break
      }
    }

    return () => ws.close()
  }, [gameId, applyMove, setGame])

  const sendMove = useCallback((uci: string) => {
    wsRef.current?.send(JSON.stringify({ t: 'move', d: { uci } }))
  }, [])

  return { sendMove, connected: wsRef.current?.readyState === WebSocket.OPEN }
}
```

## Shared Components

### Chess Clock

```tsx
// src/features/game/components/Clock.tsx
import { useEffect, useState } from 'react'
import { cn } from '@/utils/cn'

interface ClockProps {
  time: number  // milliseconds
  active: boolean
  className?: string
}

export function Clock({ time, active, className }: ClockProps) {
  const [displayTime, setDisplayTime] = useState(time)

  useEffect(() => {
    setDisplayTime(time)
  }, [time])

  useEffect(() => {
    if (!active) return

    const interval = setInterval(() => {
      setDisplayTime(t => Math.max(0, t - 100))
    }, 100)

    return () => clearInterval(interval)
  }, [active])

  const minutes = Math.floor(displayTime / 60000)
  const seconds = Math.floor((displayTime % 60000) / 1000)
  const tenths = Math.floor((displayTime % 1000) / 100)

  const isLow = displayTime < 20000

  return (
    <div className={cn(
      'font-mono text-2xl px-4 py-2 rounded',
      active ? 'bg-green-600 text-white' : 'bg-gray-200',
      isLow && active && 'bg-red-600',
      className
    )}>
      {minutes}:{seconds.toString().padStart(2, '0')}
      {isLow && `.${tenths}`}
    </div>
  )
}
```

### Move List

```tsx
// src/features/game/components/MoveList.tsx
import { cn } from '@/utils/cn'
import type { Move } from '../types'

interface MoveListProps {
  moves: Move[]
  currentPly: number
  onMoveClick?: (ply: number) => void
}

export function MoveList({ moves, currentPly, onMoveClick }: MoveListProps) {
  const pairs = []
  for (let i = 0; i < moves.length; i += 2) {
    pairs.push({
      number: Math.floor(i / 2) + 1,
      white: moves[i],
      black: moves[i + 1]
    })
  }

  return (
    <div className="w-64 h-96 overflow-y-auto bg-gray-50 rounded p-2">
      {pairs.map((pair) => (
        <div key={pair.number} className="flex gap-2 text-sm">
          <span className="w-8 text-gray-500">{pair.number}.</span>
          <span
            className={cn(
              'w-16 cursor-pointer hover:bg-blue-100 px-1 rounded',
              pair.white.ply === currentPly && 'bg-blue-200'
            )}
            onClick={() => onMoveClick?.(pair.white.ply)}
          >
            {pair.white.san}
          </span>
          {pair.black && (
            <span
              className={cn(
                'w-16 cursor-pointer hover:bg-blue-100 px-1 rounded',
                pair.black.ply === currentPly && 'bg-blue-200'
              )}
              onClick={() => onMoveClick?.(pair.black.ply)}
            >
              {pair.black.san}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `react-chessground` | Lichess board component wrapper |
| `chess.js` | Client-side chess logic |
| `@tanstack/react-query` | Server state management |
| `zustand` | Client state management |
| `react-router-dom` | Routing |
| `tailwindcss` | Styling |

## Browser Engine Analysis

For client-side analysis, use Stockfish WASM:

```tsx
// src/features/analysis/hooks/useStockfish.ts
import { useState, useEffect, useCallback } from 'react'

export function useStockfish() {
  const [engine, setEngine] = useState<Worker | null>(null)
  const [evaluation, setEvaluation] = useState<number | null>(null)
  const [bestMove, setBestMove] = useState<string | null>(null)

  useEffect(() => {
    const worker = new Worker('/stockfish.js')

    worker.onmessage = (e) => {
      const line = e.data as string

      if (line.startsWith('info') && line.includes('score cp')) {
        const match = line.match(/score cp (-?\d+)/)
        if (match) setEvaluation(parseInt(match[1]) / 100)
      }

      if (line.startsWith('bestmove')) {
        const match = line.match(/bestmove (\w+)/)
        if (match) setBestMove(match[1])
      }
    }

    worker.postMessage('uci')
    worker.postMessage('isready')
    setEngine(worker)

    return () => worker.terminate()
  }, [])

  const analyze = useCallback((fen: string, depth = 20) => {
    if (!engine) return
    engine.postMessage(`position fen ${fen}`)
    engine.postMessage(`go depth ${depth}`)
  }, [engine])

  return { analyze, evaluation, bestMove }
}
```

## Key Differences from Lichess

| Aspect | Lichess | Our Approach |
|--------|---------|--------------|
| **UI Library** | Snabbdom (lightweight VDOM) | React (full-featured) |
| **Rendering** | Server-side + hydration | Client-side SPA |
| **State** | Custom state management | Zustand + React Query |
| **Bundling** | Custom build system | Vite |
| **Board** | Chessground (direct) | react-chessground (wrapper) |
