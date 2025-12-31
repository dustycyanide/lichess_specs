---
title: Lichess Technical Architecture Research
category: architecture
status: research
last_updated: 2025-12-31
---

# Lichess Technical Architecture Research

This document contains comprehensive research findings on Lichess's technical architecture, gathered from official documentation, GitHub repositories, and community resources.

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Repository Structure](#repository-structure)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Database Design](#database-design)
6. [Caching & Redis](#caching--redis)
7. [WebSocket Layer](#websocket-layer)
8. [Key Patterns](#key-patterns)

---

## Technology Stack

### Backend

| Technology | Purpose |
|------------|---------|
| **Scala 3** | Primary backend language |
| **Play 2.8 Framework** | Web application framework |
| **Akka** | Actor-based concurrency, streams, event bus |
| **scalatags** | Server-side HTML templating |
| **MongoDB 4.2 - 7.x** | Primary database (4.7+ billion games) |
| **Redis** | Message broker, pub/sub communication |
| **Elasticsearch** | Search indexing |
| **nginx** | Reverse proxy |

### Frontend

| Technology | Purpose |
|------------|---------|
| **TypeScript** | Primary frontend language |
| **Snabbdom** | Virtual DOM library (replaced Mithril.js) |
| **Sass/SCSS** | CSS preprocessing |
| **pnpm** | Package management (workspace-based) |

### Browser Support
- Firefox 115+
- Chrome/Chromium 112+
- Edge 109+
- Opera 91+
- Safari 13.1+

### Development Requirements
- JDK >= 21
- MongoDB (4.2 <= mongo <= 7.x)
- Redis
- Node.js (version specified in `.node-version`)
- pnpm

---

## Repository Structure

Lichess is composed of multiple repositories, each with specific responsibilities:

### Core Repositories

| Repository | Language | Purpose |
|------------|----------|---------|
| **[lila](https://github.com/lichess-org/lila)** | Scala | Main backend and frontend - "Lichess in Scala" |
| **[scalachess](https://github.com/lichess-org/scalachess)** | Scala | Chess rules engine - immutable, functional, side-effect free |
| **[chessground](https://github.com/lichess-org/chessground)** | TypeScript | Chess board UI component (10KB gzipped) |
| **[lila-ws](https://github.com/lichess-org/lila-ws)** | Scala | WebSocket server for real-time communication |
| **[fishnet](https://github.com/lichess-org/fishnet)** | Rust/Python | Distributed Stockfish analysis |

### Supporting Services

| Repository | Purpose |
|------------|---------|
| **lila-search** | Search functionality |
| **lila-tablebase** | Endgame lookup tables |
| **lila-fishnet** | AI "Play with Computer" functionality |
| **Kaladin/Irwin** | Machine learning cheat detection |

### Lila Project Structure

