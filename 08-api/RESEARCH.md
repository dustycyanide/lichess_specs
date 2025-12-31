# Lichess API Research

## Overview

This document provides comprehensive research on the Lichess API structure, endpoints, and patterns for integration with our chess application.

---

## API Overview

### REST vs Streaming (NDJSON)

The Lichess API uses a hybrid approach combining traditional REST endpoints with streaming NDJSON (Newline Delimited JSON) endpoints for real-time data.

**REST Endpoints:**
- Standard HTTP request/response pattern
- Return complete JSON responses
- Used for single-item retrievals, mutations, and bounded collections

**Streaming NDJSON Endpoints:**
- Return `application/x-ndjson` content type
- One JSON object per line, continuously streamed
- No fixed content-length - streams stay open until event completion
- Used for real-time game moves, ongoing events, and large data exports
- Client must handle incremental line-by-line parsing

**Base URLs:**
- Production: `https://lichess.org`
- Development: `https://lichess.dev` or `http://localhost:8080`
- Opening Explorer: `explorer.lichess.ovh`
- Tablebase: `tablebase.lichess.ovh`

---

## Authentication (OAuth2)

### Authentication Methods

Lichess supports three authentication approaches:

#### 1. Personal Access Tokens

Simple authentication for personal scripts and single-user applications.

- Generate at: `https://lichess.org/account/oauth/token`
- Include in requests via Authorization header:
  ```
  Authorization: Bearer {your-token}
  ```
- Long-lived tokens (approximately one year)
- Can be revoked at any time from account settings

**Security Best Practices:**
- Store tokens in environment variables
- Never hardcode tokens in applications
- Never share tokens in public repositories
- Revoke immediately if compromised

#### 2. OAuth 2.0 with PKCE

Full OAuth flow for multi-user applications requiring "Login with Lichess" functionality.

**Key Characteristics:**
- Authorization code flow with PKCE (Proof Key for Code Exchange)
- Only accepted code challenge method: `S256` (SHA-256)
- Supports unregistered and public clients (no client secret required)
- Access tokens are long-lived (approximately one year)
- Refresh tokens are NOT supported
- Token format: `^[A-Za-z0-9_]+$` (alphanumeric + underscore, up to 512 characters)

**OAuth Flow:**
1. Redirect user to Lichess authorization page with PKCE challenge
2. User authenticates and grants permissions
3. Lichess redirects back with authorization code
4. Exchange code + verifier for access token
5. Use access token in Authorization header

#### 3. Anonymous Access

Public endpoints that don't require authentication can be accessed without tokens. These typically have lower rate limits.

### API Scopes

Applications must request only the scopes they need:

| Scope | Description |
|-------|-------------|
| `preference:read` | Read user preferences |
| `preference:write` | Write user preferences |
| `email:read` | Read user email address |
| `challenge:read` | Read incoming challenges |
| `challenge:write` | Create, accept, decline challenges |
| `challenge:bulk` | Create, delete, query bulk pairings |
| `study:read` | Read private studies and broadcasts |
| `study:write` | Create, update studies and broadcasts |
| `tournament:write` | Create and manage tournaments |
| `puzzle:read` | Read puzzle activity |
| `team:read` | Read private team information |
| `team:write` | Join and leave teams |
| `team:lead` | Manage team as leader |
| `follow:read` | Read followed players |
| `follow:write` | Follow and unfollow players |
| `msg:write` | Send private messages |
| `board:play` | Play games with Board API |
| `bot:play` | Play games with Bot API |

### Testing Authentication

Verify token validity using the test endpoint:
```bash
curl -H "Authorization: Bearer {your-token}" https://lichess.org/api/token/test
```

Successful response includes the token's accessible scopes.

---

## Rate Limiting

### Core Rules

1. **Sequential Requests**: Only make one request at a time
2. **429 Response Handling**: If HTTP 429 is received, wait a full minute before resuming

### Rate Limit Behavior

- Authenticated requests receive higher rate limits than anonymous requests
- Rate limits use a complex array of separate factors for DDOS protection
- Exact thresholds are variable and not publicly specified
- Limits vary by endpoint type and authentication status

### Best Practices

- Implement exponential backoff for 429 responses
- Use streaming endpoints for large data exports instead of pagination
- Cache responses where appropriate
- Batch requests when possible (e.g., POST multiple game IDs)

---

## Endpoint Categories

The Lichess API is organized into the following major categories:

### Account & Users

- **Account**: Current user profile, preferences, settings
- **Users**: User profiles, ratings, activity, online status
- **Relations**: Following/followers management

### Games

- **Export**: Download games in PGN or JSON format
- **Import**: Upload PGN games
- **Streaming**: Real-time game updates via NDJSON
- **Bookmarks**: Saved game management
- **TV**: Current featured games by category

### Puzzles

- **Daily Puzzle**: Get the daily puzzle
- **Puzzle Activity**: User's puzzle history (streamed as NDJSON)
- **Puzzle Dashboard**: Performance statistics
- **Themed Batches**: Puzzles by theme/difficulty
- **Storm/Racer**: Speed puzzle modes

### Tournaments

- **Arena Tournaments**: Lichess Arena format with continuous pairing
- **Swiss Tournaments**: Traditional Swiss system
- **Simuls**: Simultaneous exhibitions

### Broadcasts

- **Tournament Management**: Create/edit broadcast events
- **Round Management**: Individual broadcast rounds
- **PGN Sync**: Automatic PGN updates from URLs
- **Manual Push**: Direct PGN submission via API

### Teams

- **Team Info**: Team details and membership
- **Join/Leave**: Membership management
- **Tournaments**: Team-specific tournaments
- **Messaging**: Team communication

### Studies

- **Collaborative Analysis**: Shared analysis boards
- **PGN Import/Export**: Study content management
- **Chapter Management**: Study organization

### Other Categories

- **Challenges**: Send and receive game challenges
- **Messaging**: Private player communication
- **Analysis**: Cloud evaluation database
- **Opening Explorer**: Opening statistics
- **Tablebase**: Endgame tablebase lookups
- **FIDE**: FIDE player and federation data

---

## Streaming API

### How Streaming Works

Streaming endpoints maintain an open HTTP connection and emit NDJSON data as events occur:

```
{"type":"gameStart","game":{"id":"abc123",...}}
{"type":"move","game":{"id":"abc123","fen":"..."}}
{"type":"gameFinish","game":{"id":"abc123",...}}
```

The connection remains open until:
- The event completes (e.g., game ends)
- The client disconnects
- Server timeout occurs

### Key Streaming Endpoints

**Game Streams:**
- `/api/stream/event` - User's incoming events (challenges, game starts)
- `/api/bot/game/stream/{gameId}` - Stream a specific game (Bot API)
- `/api/board/game/stream/{gameId}` - Stream a specific game (Board API)
- `/api/games/user/{username}` - Stream user's games

**Multi-Game Streams:**
- `/api/stream/games-by-users` - Stream games between specified users
- `/api/stream/games/{streamId}` - Stream from game ID list (500 anonymous, 1000 authenticated)

**Event Streams:**
- `/api/broadcast/{broadcastRoundId}` - Broadcast round updates
- `/api/tv/channels` - Current TV games

### Client Implementation Notes

- Set appropriate timeout (or no timeout) for streaming connections
- Parse response line-by-line, not as complete JSON
- Handle connection drops with reconnection logic
- Use `withCurrentGames` flag to get initial state on connect

---

## Bot API

### Overview

The Bot API enables engine-powered accounts to play on Lichess.

### Requirements

- Account must be upgraded to Bot status via `/api/bot/account/upgrade`
- Once upgraded, account CANNOT be used for human play
- OAuth2 authentication required with `bot:play` scope

### Capabilities

- Receive, create, accept, or decline challenges
- Stream game state and events
- Play moves
- Chat in game
- Resign and abort games
- Engine assistance is explicitly ALLOWED

### Restrictions

- Cannot play UltraBullet (1/4+0) due to request frequency
- 0+1 and 1/2+0 time controls are permitted
- Must follow Lichess TOS (no sandbagging, boosting, constant aborting)
- Recommended: Play casual games only during testing

### Key Endpoints

- `POST /api/bot/account/upgrade` - Upgrade account to bot
- `GET /api/bot/game/stream/{gameId}` - Stream game state
- `POST /api/bot/game/{gameId}/move/{move}` - Play a move
- `POST /api/bot/game/{gameId}/chat` - Send chat message
- `POST /api/bot/game/{gameId}/abort` - Abort game
- `POST /api/bot/game/{gameId}/resign` - Resign game

---

## Board API

### Overview

The Board API enables third-party clients and physical boards to play on Lichess using normal user accounts.

### Requirements

- OAuth2 authentication with `board:play` scope
- Compatible with regular Lichess accounts (not Bot accounts)

### Capabilities

- Stream incoming chess moves
- Play chess moves
- Read and write in player/spectator chats
- Receive, create, accept, or decline challenges
- Abort and resign games

### Restrictions

- **Engine assistance is FORBIDDEN**
- Time controls limited to:
  - Rapid (10-15 minutes)
  - Classical (30+ minutes)
  - Correspondence
  - Blitz (3-8 minutes) - only for direct challenges, AI games, and bulk pairing

### Key Endpoints

- `GET /api/board/game/stream/{gameId}` - Stream game state
- `POST /api/board/game/{gameId}/move/{move}` - Play a move
- `POST /api/board/game/{gameId}/chat` - Send chat message
- `POST /api/board/game/{gameId}/abort` - Abort game
- `POST /api/board/game/{gameId}/resign` - Resign game

### External Engine API (Alpha)

Lichess also provides an External Engine API for analysis features:
- Engines run as external services (outside browser or different machine)
- Provide analysis on pages like the analysis board
- Subject to change as it's in alpha

---

## Export Formats

### PGN (Portable Game Notation)

Standard chess notation format, widely compatible with chess software.

**Request with Accept header:**
```
Accept: application/x-chess-pgn
```

**Available options:**
- `moves` - Include moves (default: true)
- `tags` - Include PGN tags
- `clocks` - Include clock comments
- `evals` - Include analysis evaluation comments
- `opening` - Include opening name
- `pgn_in_json` - Include full PGN within JSON response

### JSON

Structured data format for programmatic access.

**Request with Accept header:**
```
Accept: application/json
```

**Note:** If not specified, some endpoints default to PGN. Use the `Accept` header rather than `Content-Type` to request JSON.

### NDJSON (Newline Delimited JSON)

Streaming format for real-time or bulk data.

**Content type:**
```
application/x-ndjson
```

One JSON object per line, streamed incrementally.

### TRF Format

Tournament Report File format for Swiss tournament results export.

### Batch Export

Export multiple games via POST:
```bash
curl -X POST https://lichess.org/games/export/_ids \
  --data 'TJxUmbWK,4OtIh2oh,ILwozzRZ' \
  -o games.pgn
```

Limit: 300 games per POST request.

---

## Pagination

### Streaming-Based Pagination

Lichess primarily uses streaming instead of traditional pagination:

- Collection endpoints return generators/streams
- Client processes data incrementally as it arrives
- No page numbers or cursors needed
- More efficient for large datasets

### Parameters for Bounded Requests

When limiting results:

| Parameter | Description |
|-----------|-------------|
| `max` | Maximum number of items to return |
| `since` | Unix timestamp - only items after this time |
| `until` | Unix timestamp - only items before this time |
| `sort` | Sort order (typically `dateAsc` or `dateDesc`) |

### Example: User Games Export

```
GET /api/games/user/{username}?max=100&since=1609459200000&rated=true
```

Parameters:
- `max` - Maximum games to return
- `since` / `until` - Time bounds (Unix milliseconds)
- `vs` - Filter by opponent
- `rated` - Only rated games
- `perfType` - Filter by game type (bullet, blitz, rapid, etc.)
- `color` - Filter by color played
- `analyzed` - Only computer-analyzed games
- `ongoing` - Include ongoing games
- `finished` - Include finished games

---

## Additional Resources

### Official Documentation
- API Documentation: https://lichess.org/api
- GitHub Repository: https://github.com/lichess-org/api
- API Tips: https://lichess.org/page/api-tips

### Client Libraries
- Python: `berserk` (general API), `python-lichess`
- Async Python: `lichess_python_SDK`
- Rust: `lichess-api`
- .NET: `LichessApi`
- PHP: `lichess-php-sdk`

### Example Applications
- Lichess API Demo App (OAuth2 + gameplay)
- Lichess API UI App (OAuth2 + endpoint forms)
- Lichess Bot (Python bot implementation)
- CLI Chess (command-line client)

### Database Downloads
- Puzzle database (public domain): https://database.lichess.org
- Game database exports available monthly

### Support
- Discord: #lichess-api-support channel
- Lichess encourages requesting new endpoints rather than web scraping

---

## Sources

- [Lichess.org API Docs](https://lichess.org/api)
- [GitHub - lichess-org/api](https://github.com/lichess-org/api)
- [API Tips - lichess.org](https://lichess.org/page/api-tips)
- [Authentication - DeepWiki](https://deepwiki.com/lichess-org/api/3-authentication)
- [Broadcast System - DeepWiki](https://deepwiki.com/lichess-org/api/7-broadcast-system)
- [Lichess API YAML Spec](https://github.com/lichess-org/api/blob/master/doc/specs/lichess-api.yaml)
- [Python Lichess Documentation](https://python-lichess.readthedocs.io/)
- [Lichess API Wrapper Documentation](https://lichess-api.readthedocs.io/)
