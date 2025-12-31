---
title: Studies
category: social
status: draft
styleguides:
  - hacksoft-django-styleguide
  - bulletproof-react-styleguide
dependencies:
  - user-authentication
  - websocket-architecture
  - game-engine
lichess_equivalent: lila/modules/study
---

# Studies

> Collaborative analysis feature for creating, analyzing, and sharing chess positions and games.

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) with business logic in **Services**. Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) with **direct imports** (no barrel files).

---

## Overview

Studies are Lichess's collaborative analysis feature, enabling users to:
- Create annotated game analyses
- Organize content into chapters (up to 64 per study)
- Collaborate in real-time with other users
- Share analysis with teams or publicly

---

## Core Features

### Analysis Capabilities
- Free-form position setup and analysis
- Real-time collaborative editing
- Stockfish integration for computer analysis
- Opening book and tablebase access
- Drawing tools (arrows, circles)
- PGN import/export

### Content Organization
- Studies contain multiple chapters (max 64)
- Each chapter represents a distinct analysis
- Chapters can be reordered
- Clone studies to duplicate content

---

## Study Visibility

| Level | Behavior |
|-------|----------|
| **Public** | Visible to everyone, listed in study searches |
| **Unlisted** | Accessible only via direct link |
| **Invite-only** | Only invited members can view |

**Note:** Individual chapters cannot have different privacy settings than the parent study.

---

## Member Roles

| Role | Capabilities |
|------|--------------|
| **Owner** | Full control, can delete study |
| **Contributor** | Can edit content, make variations |
| **Spectator** | View-only access (for invite-only studies) |

### Contributor Permissions

**CAN:**
- Use the share button
- Turn on Stockfish analysis
- Use opening book/tablebase
- Practice with computer
- Draw arrows and circles associated with moves
- Make variations

**CANNOT:**
- Use annotation glyphs
- Request computer analysis (server-side)
- Change study settings
- Delete chapters

---

## Real-Time Collaboration

### Sync Mode
- **Sync Enabled**: All viewers see the same position in real-time
- **Sync Disabled**: Each viewer browses independently
- Users can toggle their sync status with SYNC button
- Green checkmark indicates sync with leader

### Record Mode
- **REC On** (green checkmark): Your moves and annotations are saved
- **REC Off**: Browsing mode, changes not saved
- Arrows/circles only visible to synced viewers when in record mode

---

## Chapter Management

### Creating Chapters
Chapters can be created via:
- Empty board
- Starting position
- PGN import
- Game URL import

### Chapter Operations
- Reorder chapters via drag-and-drop
- Export individual chapters or entire study to PGN
- Move chapters between studies (via export/import)

### Chapter Limits
- Maximum 64 chapters per study
- No individual chapter privacy settings

---

## Study Sharing

### Inviting Members
1. Open study
2. Click "Members" tab (next to "Chapters")
3. Below your username, click "Add members"
4. Type usernames to invite

### Sharing with Teams
1. Set study visibility to "Unlisted"
2. Copy the study link
3. Use team messaging to send link to members
4. Anyone with link can view (not edit unless invited)

### PGN Tags and Topics
- Studies can be tagged with topics for organization
- Access via "PGN tags" panel below the board
- Multiple topics can be assigned
- Helps with discoverability in study search

---

## Database Schema

### Django Models

```python
# <project_slug>/studies/models.py
import uuid

from django.db import models


class Study(models.Model):
    """Study entity for collaborative analysis"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(max_length=2000, blank=True)

    # Visibility
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        UNLISTED = 'unlisted', 'Unlisted'
        INVITE_ONLY = 'invite', 'Invite Only'

    visibility = models.CharField(
        max_length=15,
        choices=Visibility.choices,
        default=Visibility.PUBLIC
    )

    # Ownership
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='owned_studies'
    )

    # Settings
    allow_cloning = models.BooleanField(default=True)
    computer_analysis = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    chapter_count = models.PositiveIntegerField(default=0)
    member_count = models.PositiveIntegerField(default=0)

    # Stats
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['visibility', '-updated_at']),
            models.Index(fields=['-like_count']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(chapter_count__lte=64),
                name='max_64_chapters'
            )
        ]


class StudyChapter(models.Model):
    """Chapter within a study"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='chapters')
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    # Content
    initial_fen = models.CharField(max_length=100, default='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
    pgn = models.TextField(blank=True)  # Full PGN with variations and comments
    orientation = models.CharField(max_length=5, default='white')  # 'white' or 'black'

    # Source (if imported)
    source_game_id = models.UUIDField(null=True, blank=True)
    source_url = models.URLField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['study', 'order']),
        ]


class StudyMember(models.Model):
    """Membership in a study"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='study_memberships')

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        CONTRIBUTOR = 'contributor', 'Contributor'
        SPECTATOR = 'spectator', 'Spectator'

    role = models.CharField(max_length=15, choices=Role.choices, default=Role.SPECTATOR)
    invited_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='study_invites_sent'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['study', 'user']


class StudyTopic(models.Model):
    """Topic/tag for study organization"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    study_count = models.PositiveIntegerField(default=0)


class StudyTopicAssignment(models.Model):
    """Many-to-many relationship between studies and topics"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='topic_assignments')
    topic = models.ForeignKey(StudyTopic, on_delete=models.CASCADE, related_name='study_assignments')

    class Meta:
        unique_together = ['study', 'topic']


class StudyAnnotation(models.Model):
    """Move annotation within a chapter"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    chapter = models.ForeignKey(StudyChapter, on_delete=models.CASCADE, related_name='annotations')
    ply = models.PositiveIntegerField()  # Half-move number
    move_san = models.CharField(max_length=10)  # e.g., "Nf3", "O-O"

    # Annotation content
    comment = models.TextField(max_length=2000, blank=True)
    nag = models.CharField(max_length=10, blank=True)  # Numeric Annotation Glyph

    # Drawing shapes (stored as JSON)
    shapes = models.JSONField(default=list)  # [{"brush": "green", "orig": "e2", "dest": "e4"}]

    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='study_annotations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['chapter', 'ply']),
        ]


class StudyLike(models.Model):
    """User like on a study"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='study_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['study', 'user']
```

---

## API Endpoints

### REST API (Django REST Framework)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/studies/` | List studies (with search, filters) |
| POST | `/api/studies/` | Create new study |
| GET | `/api/studies/{id}/` | Get study details |
| PATCH | `/api/studies/{id}/` | Update study settings |
| DELETE | `/api/studies/{id}/` | Delete study (owner only) |
| POST | `/api/studies/{id}/clone/` | Clone study |
| GET | `/api/studies/{id}/pgn/` | Export study as PGN |

### Chapter API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/studies/{id}/chapters/` | List chapters |
| POST | `/api/studies/{id}/chapters/` | Create chapter |
| GET | `/api/studies/{id}/chapters/{chapter_id}/` | Get chapter |
| PATCH | `/api/studies/{id}/chapters/{chapter_id}/` | Update chapter |
| DELETE | `/api/studies/{id}/chapters/{chapter_id}/` | Delete chapter |
| POST | `/api/studies/{id}/chapters/import-pgn/` | Import PGN as chapters |
| PATCH | `/api/studies/{id}/chapters/reorder/` | Reorder chapters |

### Member API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/studies/{id}/members/` | List members |
| POST | `/api/studies/{id}/members/` | Invite member |
| PATCH | `/api/studies/{id}/members/{user_id}/` | Change role |
| DELETE | `/api/studies/{id}/members/{user_id}/` | Remove member |

### Interaction API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/studies/{id}/like/` | Like study |
| DELETE | `/api/studies/{id}/like/` | Unlike study |
| GET | `/api/users/{username}/studies/` | Get user's studies |

### WebSocket Events (Django Channels)

```python
# Study Consumer
class StudyConsumer(WebsocketConsumer):
    """Real-time study collaboration"""

    # Client -> Server
    # - join_study: Subscribe to study updates
    # - leave_study: Unsubscribe
    # - set_sync: Enable/disable sync mode
    # - set_record: Enable/disable record mode
    # - move: Make a move (when in record mode)
    # - add_variation: Add a variation
    # - add_comment: Add annotation comment
    # - add_shape: Draw arrow/circle
    # - remove_shape: Remove arrow/circle
    # - set_position: Navigate to position (broadcasts if synced)

    # Server -> Client
    # - position_changed: Current position updated (by sync leader)
    # - move_added: New move added to chapter
    # - variation_added: New variation added
    # - comment_added: New comment added
    # - shape_added: New shape drawn
    # - shape_removed: Shape removed
    # - member_joined: Member entered study
    # - member_left: Member left study
    # - sync_status: Sync status update
    # - chapter_changed: Active chapter changed
```

---

## Implementation Notes

### Django Services

Following the Hacksoft Django Styleguide, all business logic lives in services with proper validation and transactions:

```python
# <project_slug>/studies/services.py
import chess

from django.db import transaction

from <project_slug>.studies.models import Study, StudyChapter, StudyMember, StudyAnnotation
from <project_slug>.studies.pgn import parse_pgn
from <project_slug>.users.models import User


@transaction.atomic
def study_create(
    *,
    name: str,
    owner: User,
    visibility: str = Study.Visibility.PUBLIC
) -> Study:
    """Create a new study and set up owner membership."""
    study = Study(
        name=name,
        owner=owner,
        visibility=visibility
    )
    study.full_clean()
    study.save()

    # Create owner membership
    member = StudyMember(
        study=study,
        user=owner,
        role=StudyMember.Role.OWNER
    )
    member.full_clean()
    member.save()

    return study


@transaction.atomic
def study_clone(*, study: Study, user: User) -> Study:
    """Clone a study with all chapters."""
    new_study = Study(
        name=f"{study.name} (copy)",
        owner=user,
        visibility=Study.Visibility.UNLISTED,
        allow_cloning=study.allow_cloning,
        computer_analysis=study.computer_analysis
    )
    new_study.full_clean()
    new_study.save()

    # Clone all chapters
    for chapter in study.chapters.order_by('order'):
        new_chapter = StudyChapter(
            study=new_study,
            name=chapter.name,
            order=chapter.order,
            initial_fen=chapter.initial_fen,
            pgn=chapter.pgn,
            orientation=chapter.orientation
        )
        new_chapter.full_clean()
        new_chapter.save()

    return new_study


@transaction.atomic
def chapter_create(
    *,
    study: Study,
    name: str,
    created_by: User,
    initial_fen: str | None = None,
    pgn: str | None = None,
    source_url: str | None = None
) -> StudyChapter:
    """Create a new chapter in a study."""
    from <project_slug>.studies.exceptions import MaxChaptersError

    if study.chapters.count() >= 64:
        raise MaxChaptersError()

    chapter = StudyChapter(
        study=study,
        name=name,
        order=study.chapters.count(),
        initial_fen=initial_fen or chess.STARTING_FEN,
        pgn=pgn or "",
        source_url=source_url or ""
    )
    chapter.full_clean()
    chapter.save()

    # Update study chapter count
    study.chapter_count = study.chapters.count()
    study.save(update_fields=['chapter_count'])

    return chapter


@transaction.atomic
def chapter_import_pgn(
    *,
    study: Study,
    pgn_content: str,
    created_by: User
) -> list[StudyChapter]:
    """Import PGN content as one or more chapters."""
    games = parse_pgn(pgn_content)
    chapters = []

    for game_data in games:
        chapter = chapter_create(
            study=study,
            name=game_data['name'],
            created_by=created_by,
            initial_fen=game_data['initial_fen'],
            pgn=game_data['pgn']
        )
        chapters.append(chapter)

    return chapters


@transaction.atomic
def member_invite(
    *,
    study: Study,
    user: User,
    invited_by: User,
    role: str = StudyMember.Role.CONTRIBUTOR
) -> StudyMember:
    """Invite a user to a study with specified role."""
    member = StudyMember(
        study=study,
        user=user,
        role=role,
        invited_by=invited_by
    )
    member.full_clean()
    member.save()

    # Update study member count
    study.member_count = study.members.count()
    study.save(update_fields=['member_count'])

    return member


@transaction.atomic
def annotation_add(
    *,
    chapter: StudyChapter,
    ply: int,
    user: User,
    move_san: str,
    comment: str | None = None,
    nag: str | None = None,
    shapes: list | None = None
) -> StudyAnnotation:
    """Add annotation to a position."""
    annotation = StudyAnnotation(
        chapter=chapter,
        ply=ply,
        move_san=move_san,
        comment=comment or "",
        nag=nag or "",
        shapes=shapes or [],
        created_by=user
    )
    annotation.full_clean()
    annotation.save()
    return annotation
```

### React Components

Following Bulletproof React with direct imports (no barrel files), kebab-case file names, and the three-part API pattern:

```
frontend/src/features/studies/
├── api/
│   ├── get-studies.ts         # Schema + fetcher + useStudies hook
│   ├── get-study.ts           # Schema + fetcher + useStudy hook
│   ├── create-study.ts        # Mutation hook with cache invalidation
│   ├── clone-study.ts         # Mutation hook
│   ├── create-chapter.ts      # Mutation hook
│   └── import-pgn.ts          # Mutation hook
├── components/
│   ├── study-list.tsx
│   ├── study-card.tsx
│   ├── study-page.tsx
│   ├── study-board.tsx        # Chessground integration
│   ├── chapter-list.tsx
│   ├── chapter-panel.tsx
│   ├── member-list.tsx
│   ├── invite-member-modal.tsx
│   ├── annotation-panel.tsx
│   ├── move-tree.tsx
│   ├── sync-controls.tsx
│   └── study-chat.tsx
├── types/
│   └── study.ts               # Zod schemas + inferred types
├── hooks/
│   ├── use-study-sync.ts      # WebSocket sync state
│   └── use-chapter-navigation.ts
└── stores/
    └── study-ui-store.ts      # Client-side UI state only (board orientation, etc.)
```

**Important:** Zustand stores are for **client-side UI state only** (e.g., board orientation, selected squares). Server state (studies, chapters, annotations) is managed by **TanStack Query**.

### Chessground Integration

```typescript
// frontend/src/features/studies/components/StudyBoard.tsx

import { Chessground } from 'chessground';

interface StudyBoardProps {
  fen: string;
  orientation: 'white' | 'black';
  shapes: Shape[];
  onMove: (move: Move) => void;
  onShapeAdd: (shape: Shape) => void;
  onShapeRemove: (shape: Shape) => void;
  isContributor: boolean;
}

// Chessground configuration for study board:
// - Movable pieces (if contributor)
// - Drawable shapes (arrows, circles)
// - Premove support
// - Highlight last move
// - Analysis mode (all legal moves allowed)
```

### PGN Handling

```python
# studies/pgn.py

import chess
import chess.pgn
from io import StringIO

def parse_pgn(pgn_content: str) -> list[dict]:
    """Parse PGN content and return list of chapter data."""
    games = []
    pgn = StringIO(pgn_content)

    while True:
        game = chess.pgn.read_game(pgn)
        if game is None:
            break
        games.append({
            'name': game.headers.get('Event', 'Untitled'),
            'initial_fen': game.headers.get('FEN', chess.STARTING_FEN),
            'pgn': str(game),
        })

    return games

def export_study_pgn(study: Study) -> str:
    """Export entire study as PGN with all chapters."""
    chapters = study.chapters.order_by('order')
    pgns = []

    for chapter in chapters:
        pgn = f'[Event "{chapter.name}"]\n'
        if chapter.initial_fen != chess.STARTING_FEN:
            pgn += f'[FEN "{chapter.initial_fen}"]\n'
        pgn += f'\n{chapter.pgn}'
        pgns.append(pgn)

    return '\n\n'.join(pgns)
```

---

## Real-Time Sync Architecture

### Sync Leader Model
- First owner or contributor to join becomes sync leader
- Sync leader's position is broadcast to synced viewers
- Leadership transfers when leader leaves or disables sync

### Position Broadcasting
```python
# WebSocket message format for position sync
{
    "type": "position_changed",
    "data": {
        "chapter_id": "uuid",
        "ply": 15,
        "fen": "r1bqkb1r/...",
        "lastMove": ["e2", "e4"],
        "shapes": [{"brush": "green", "orig": "e4", "dest": "d5"}]
    }
}
```

### Conflict Resolution
- Last-write-wins for annotations
- Variations are additive (no deletion of others' variations)
- Owner can revert changes via chapter history

---

## Related Documents

- [Analysis Board](../04-training/analysis-board.md) - Single-user analysis
- [Chat & Messaging](./chat-messaging.md) - Study chat integration
- [Teams & Clubs](./teams-clubs.md) - Sharing with teams
- [WebSocket Architecture](../01-architecture/websocket-architecture.md) - Real-time infrastructure
- [Game Engine](../02-core-features/game-engine.md) - Chess logic (python-chess)
- [RESEARCH.md](./RESEARCH.md) - Detailed Lichess research

---

*Document created: December 2025*
