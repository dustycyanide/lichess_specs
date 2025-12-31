---
title: Chat & Messaging
category: social
status: draft
styleguide: hacksoft-django-styleguide
dependencies:
  - user-authentication
  - websocket-architecture
lichess_equivalent: lila/modules/chat, lila/modules/msg, lila/modules/mod
---

# Chat & Messaging

> Real-time communication system including chat rooms, direct messaging, following, forums, and moderation.

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) with business logic in **Services**. Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) with **direct imports** (no barrel files).

---

## Overview

The communication system provides multiple channels for user interaction:
- **Real-time Chat**: Game, tournament, team, and study chat rooms
- **Direct Messaging**: Private threaded conversations
- **Following**: Unilateral follow system for activity feeds
- **Forums**: Categorized discussion boards
- **Moderation**: Reporting, blocking, and safety features

---

## Chat System

### Chat Types

| Type | Context | Participants |
|------|---------|--------------|
| **Game Chat** | During active games | Players only |
| **Spectator Chat** | Viewing games | All spectators |
| **Tournament Chat** | Tournament lobbies | Tournament participants |
| **Team Chat** | Team pages | Team members |
| **Study Chat** | Collaborative studies | Study members |

### Chat Controls

#### Disabling Chat

| Method | Scope | Behavior |
|--------|-------|----------|
| **Toggle Button** | Per-context | Hides chat for current session |
| **Zen Mode** | Account setting | Hides chat during games, exits after game |
| **Notes Tab** | Per-game | Persists to next game |
| **Kid Mode** | Account-wide | Complete chat restriction |

#### Chat Etiquette (Enforced Rules)

**Prohibited Content:**
- Threatening, bullying, or offensive material
- Racist or discriminatory messages
- Sensitive/shocking content
- Spam and excessive repetition
- Unrelated links (tournament/team promotion)
- Stream promotion or recruitment
- Public cheating accusations

**Consequences:**
- Timeout (temporary)
- Warning
- Site-wide communication ban (severe/repeated offenses)

---

## Direct Messaging

### Message System Features
- Inbox accessible via navigation
- Threaded conversation view
- Compose via user profile
- Limited to 50 conversations displayed (older accessible via search)

### Privacy Controls

| Setting | Behavior |
|---------|----------|
| **Everyone** | All users can send messages |
| **Friends Only** | Only users you follow can message |
| **Existing Conversations** | Only continue existing threads |
| **Nobody** | Disable all incoming messages |

### Message Storage
- Private messages stored server-side
- May be reviewed if reported or flagged by automated systems
- Moderators can review when violations are reported

---

## Following System

### Overview
Unilateral follow system (no mutual friend requests):
- You follow someone without their approval
- Followed users appear in your "Friends" list
- Similar to Twitter/X follow model

### Following Benefits
When you follow someone, you see their:
- Recent forum posts
- Blog posts
- Stream activity
- Teams they join
- Simuls they participate in
- Activity on your home feed

### Privacy Notes
- **Follower counts permanently removed** (spam prevention)
- You cannot see who follows you
- Following someone appears in their daily activity log
- Privacy setting: "Only people I follow can message me"

---

## Forum System

### Forum Structure

| Category | Purpose |
|----------|---------|
| **General Chess Discussion** | Chess topics, strategies, discussions |
| **Game Analysis** | Share and discuss games |
| **Lichess Feedback** | Bug reports, feature requests |
| **Off-Topic** | Non-chess discussions |

### Posting Features
- Use descriptive titles (single words discouraged)
- Embed games/studies by pasting URLs
- Embed images by pasting image URLs

### Forum Etiquette (Enforced Rules)
- No advertisements (recruitment, promotion)
- No public shaming or cheating accusations
- No profanity or personal insults
- Use report system for suspected cheaters

### Moderation Actions
- Thread closing for violations
- Thread deletion for severe violations
- User warnings or bans for repeated offenses

---

## Moderation System

### Reporting

#### How to Report
1. **Profile Report Button**: Triangle icon on user profiles
2. **Chat Warn Button**: Next to chat messages
3. **Forum Report**: Report button on posts
4. **Direct URL**: `/report` page

#### Report Requirements
- Links to specific games or tournaments
- Clear explanation of the violation
- Evidence (screenshots if applicable)
- Context for moderator review

### Report Processing
- Reports forwarded to volunteer moderators
- Typical review time: 1-2 days
- No duplicate reports needed
- Notification only if reported user is banned

### Moderation Actions

| Violation | Action |
|-----------|--------|
| First offense (minor) | Warning |
| Repeated minor offenses | Chat ban |
| Severe chat violations | Communication ban (site-wide) |
| Cheating (confirmed) | Account ban |
| Terms of Service violation | Account restrictions or ban |

### Blocking Users
- Click stop sign icon on user profile
- Blocked users cannot challenge you or interact directly

### Kid Mode
Complete safety mode for children:

**Restrictions:**
- No sending or receiving messages (except from class teachers)
- No access to forums, blogs, live streams, or videos
- Cannot be featured on Lichess TV
- Cannot join simuls
- Chat completely disabled

**Features:**
- Smiley face icon indicates active Kid Mode
- Managed accounts in classes have Kid Mode by default
- Requires password to disable
- Can still play games (opponents can only send moves)

### Automated Detection
- **Irwin**: Cheat detection system
- Analyzes games and user behavior
- Flags suspicious patterns for moderator review

---

## Database Schema

### Django Models

```python
# <project_slug>/chat/models.py
import uuid

from django.db import models


class ChatRoom(models.Model):
    """Chat room entity"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    class RoomType(models.TextChoices):
        GAME = 'game', 'Game'
        SPECTATOR = 'spectator', 'Spectator'
        TOURNAMENT = 'tournament', 'Tournament'
        TEAM = 'team', 'Team'
        STUDY = 'study', 'Study'

    room_type = models.CharField(max_length=20, choices=RoomType.choices)

    # Related entity (polymorphic reference)
    game_id = models.UUIDField(null=True, blank=True)
    tournament_id = models.UUIDField(null=True, blank=True)
    team_id = models.UUIDField(null=True, blank=True)
    study_id = models.UUIDField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_disabled = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['room_type', 'game_id']),
            models.Index(fields=['room_type', 'tournament_id']),
        ]


class ChatMessage(models.Model):
    """Individual chat message"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    # Moderation
    is_deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='deleted_messages'
    )

    class Meta:
        indexes = [
            models.Index(fields=['room', 'created_at']),
        ]


# messaging/models.py

class Conversation(models.Model):
    """Direct message conversation between two users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user1 = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='conversations_as_user1')
    user2 = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='conversations_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Read status
    user1_last_read = models.DateTimeField(null=True)
    user2_last_read = models.DateTimeField(null=True)

    class Meta:
        unique_together = ['user1', 'user2']
        indexes = [
            models.Index(fields=['user1', 'updated_at']),
            models.Index(fields=['user2', 'updated_at']),
        ]


class DirectMessage(models.Model):
    """Individual direct message"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]


# following/models.py

class UserFollow(models.Model):
    """Follow relationship between users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    follower = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='following')
    followed = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'followed']
        indexes = [
            models.Index(fields=['follower', 'created_at']),
            models.Index(fields=['followed', 'created_at']),
        ]


class UserBlock(models.Model):
    """Block relationship between users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    blocker = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['blocker', 'blocked']


# forum/models.py

class ForumCategory(models.Model):
    """Forum category"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=500)
    order = models.PositiveIntegerField(default=0)


class ForumTopic(models.Model):
    """Forum topic/thread"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    author = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='forum_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Status
    is_closed = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    # Counters
    post_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['category', '-updated_at']),
            models.Index(fields=['author', '-created_at']),
        ]


class ForumPost(models.Model):
    """Forum post/reply"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='forum_posts')
    content = models.TextField(max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['topic', 'created_at']),
        ]


# moderation/models.py

class Report(models.Model):
    """User report"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    reporter = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reports_filed')
    reported_user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reports_received')

    class ReportType(models.TextChoices):
        CHEATING = 'cheating', 'Cheating'
        CHAT_ABUSE = 'chat', 'Chat Abuse'
        HARASSMENT = 'harassment', 'Harassment'
        INAPPROPRIATE_CONTENT = 'content', 'Inappropriate Content'
        OTHER = 'other', 'Other'

    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    description = models.TextField(max_length=2000)
    evidence_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REVIEWED = 'reviewed', 'Reviewed'
        ACTION_TAKEN = 'action', 'Action Taken'
        DISMISSED = 'dismissed', 'Dismissed'

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )
    reviewed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['reported_user', 'created_at']),
        ]


class ModerationAction(models.Model):
    """Moderation action taken on a user"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='moderation_actions')
    moderator = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='actions_taken')
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, related_name='actions')

    class ActionType(models.TextChoices):
        WARNING = 'warning', 'Warning'
        CHAT_BAN = 'chat_ban', 'Chat Ban'
        COMMUNICATION_BAN = 'comm_ban', 'Communication Ban'
        ACCOUNT_BAN = 'account_ban', 'Account Ban'
        ACCOUNT_RESTRICTION = 'restriction', 'Account Restriction'

    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    reason = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    # Duration (null = permanent)
    expires_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
```

---

## API Endpoints

### Chat API (REST + WebSocket)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/{room_id}/messages/` | Get chat history |
| POST | `/api/chat/{room_id}/messages/` | Send message |
| DELETE | `/api/chat/messages/{id}/` | Delete message (moderator) |

### Messaging API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/messages/` | List conversations |
| GET | `/api/messages/{conversation_id}/` | Get conversation |
| POST | `/api/messages/{conversation_id}/` | Send message |
| POST | `/api/messages/compose/` | Start new conversation |
| PATCH | `/api/messages/{conversation_id}/read/` | Mark as read |

### Following API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/{username}/following/` | List users followed |
| POST | `/api/users/{username}/follow/` | Follow user |
| DELETE | `/api/users/{username}/follow/` | Unfollow user |
| POST | `/api/users/{username}/block/` | Block user |
| DELETE | `/api/users/{username}/block/` | Unblock user |

### Forum API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/forum/categories/` | List categories |
| GET | `/api/forum/topics/` | List topics |
| POST | `/api/forum/topics/` | Create topic |
| GET | `/api/forum/topics/{id}/` | Get topic with posts |
| POST | `/api/forum/topics/{id}/posts/` | Reply to topic |
| PATCH | `/api/forum/topics/{id}/close/` | Close topic (mod) |

### Moderation API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reports/` | File a report |
| GET | `/api/mod/reports/` | List pending reports (mod) |
| POST | `/api/mod/reports/{id}/action/` | Take action on report |

### WebSocket Events (Django Channels)

```python
# Chat Consumer
class ChatConsumer(WebsocketConsumer):
    """Real-time chat for rooms"""

    # Client -> Server
    # - join_room: Subscribe to room
    # - leave_room: Unsubscribe
    # - send_message: Send chat message

    # Server -> Client
    # - new_message: Message received
    # - message_deleted: Message removed
    # - user_joined: User entered room
    # - user_left: User left room


# Direct Message Consumer
class DirectMessageConsumer(WebsocketConsumer):
    """Real-time direct messaging"""

    # Client -> Server
    # - send_message: Send DM
    # - mark_read: Mark conversation read

    # Server -> Client
    # - new_message: Message received
    # - message_read: Recipient read message
    # - unread_count: Updated unread count
```

---

## Implementation Notes

### Django Services

Following the Hacksoft Django Styleguide, all business logic lives in services with proper validation and transactions:

```python
# <project_slug>/chat/services.py
from django.db import transaction

from <project_slug>.chat.models import ChatRoom, ChatMessage
from <project_slug>.users.models import User


@transaction.atomic
def chat_message_create(
    *,
    room: ChatRoom,
    user: User,
    content: str
) -> ChatMessage:
    """Create a chat message after validation."""
    message = ChatMessage(room=room, user=user, content=content)
    message.full_clean()
    message.save()
    return message


@transaction.atomic
def chat_message_delete(
    *,
    message: ChatMessage,
    deleted_by: User
) -> None:
    """Soft delete a chat message (moderator only)."""
    message.is_deleted = True
    message.deleted_by = deleted_by
    message.full_clean()
    message.save(update_fields=['is_deleted', 'deleted_by'])
```

```python
# <project_slug>/messaging/services.py
from django.db import transaction
from django.db.models import Q

from <project_slug>.messaging.models import Conversation, DirectMessage
from <project_slug>.users.models import User


def conversation_get_or_create(*, user1: User, user2: User) -> Conversation:
    """Get or create a conversation between two users."""
    # Ensure consistent ordering
    if user1.id > user2.id:
        user1, user2 = user2, user1

    conversation, _ = Conversation.objects.get_or_create(
        user1=user1,
        user2=user2
    )
    return conversation


@transaction.atomic
def direct_message_send(
    *,
    conversation: Conversation,
    sender: User,
    content: str
) -> DirectMessage:
    """Send a direct message."""
    message = DirectMessage(
        conversation=conversation,
        sender=sender,
        content=content
    )
    message.full_clean()
    message.save()

    # Update conversation timestamp
    conversation.save(update_fields=['updated_at'])
    return message
```

```python
# <project_slug>/following/services.py
from django.db import transaction

from <project_slug>.following.models import UserFollow, UserBlock
from <project_slug>.users.models import User


@transaction.atomic
def user_follow(*, follower: User, followed: User) -> UserFollow:
    """Follow a user."""
    follow = UserFollow(follower=follower, followed=followed)
    follow.full_clean()
    follow.save()
    return follow


@transaction.atomic
def user_block(*, blocker: User, blocked: User) -> UserBlock:
    """Block a user (also unfollows if following)."""
    # Remove any existing follow relationship
    UserFollow.objects.filter(follower=blocker, followed=blocked).delete()
    UserFollow.objects.filter(follower=blocked, followed=blocker).delete()

    block = UserBlock(blocker=blocker, blocked=blocked)
    block.full_clean()
    block.save()
    return block
```

```python
# <project_slug>/moderation/services.py
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from <project_slug>.moderation.models import Report, ModerationAction
from <project_slug>.users.models import User


@transaction.atomic
def report_create(
    *,
    reporter: User,
    reported_user: User,
    report_type: str,
    description: str,
    evidence_url: str = ""
) -> Report:
    """File a report against a user."""
    report = Report(
        reporter=reporter,
        reported_user=reported_user,
        report_type=report_type,
        description=description,
        evidence_url=evidence_url
    )
    report.full_clean()
    report.save()
    return report


@transaction.atomic
def moderation_action_take(
    *,
    report: Report,
    moderator: User,
    action_type: str,
    reason: str,
    duration: timedelta | None = None
) -> ModerationAction:
    """Take moderation action on a user."""
    expires_at = timezone.now() + duration if duration else None

    action = ModerationAction(
        user=report.reported_user,
        moderator=moderator,
        report=report,
        action_type=action_type,
        reason=reason,
        expires_at=expires_at
    )
    action.full_clean()
    action.save()

    # Update report status
    report.status = Report.Status.ACTION_TAKEN
    report.reviewed_by = moderator
    report.reviewed_at = timezone.now()
    report.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    return action
```

### React Components

Following Bulletproof React with direct imports (no barrel files), kebab-case file names, and the three-part API pattern:

```
frontend/src/features/chat/
├── api/
│   ├── get-chat-messages.ts    # Schema + fetcher + useChatMessages hook
│   └── send-message.ts         # Mutation hook
├── components/
│   ├── chat-panel.tsx
│   ├── chat-message.tsx
│   └── chat-input.tsx
├── types/
│   └── chat.ts                 # Zod schemas + inferred types
├── hooks/
│   └── use-chat-websocket.ts   # WebSocket connection hook
└── stores/
    └── chat-ui-store.ts        # Client-side UI state only (Zustand)

frontend/src/features/messaging/
├── api/
│   ├── get-conversations.ts
│   ├── get-conversation.ts
│   └── send-direct-message.ts
├── components/
│   ├── inbox-panel.tsx
│   ├── conversation-list.tsx
│   ├── conversation.tsx
│   └── compose-message.tsx
├── types/
│   └── messaging.ts
└── hooks/
    └── use-messaging-websocket.ts

frontend/src/features/following/
├── api/
│   ├── follow-user.ts
│   └── block-user.ts
├── components/
│   ├── follow-button.tsx
│   ├── following-list.tsx
│   └── block-button.tsx
└── types/
    └── following.ts

frontend/src/features/forum/
├── api/
│   ├── get-topics.ts
│   ├── get-topic.ts
│   └── create-post.ts
├── components/
│   ├── forum-category.tsx
│   ├── topic-list.tsx
│   ├── topic.tsx
│   └── post-editor.tsx
└── types/
    └── forum.ts
```

**Important:** Zustand stores are for **client-side UI state only** (e.g., unread indicators, typing status). Server state (conversations, messages) is managed by **TanStack Query**.

### User Settings Model Extension

```python
# Add to users/models.py

class UserSettings(models.Model):
    """User preferences"""
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='settings')

    # Chat settings
    zen_mode = models.BooleanField(default=False)
    kid_mode = models.BooleanField(default=False)

    # Message privacy
    class MessagePrivacy(models.TextChoices):
        EVERYONE = 'everyone', 'Everyone'
        FRIENDS = 'friends', 'Friends Only'
        EXISTING = 'existing', 'Existing Conversations'
        NOBODY = 'nobody', 'Nobody'

    message_privacy = models.CharField(
        max_length=15,
        choices=MessagePrivacy.choices,
        default=MessagePrivacy.EVERYONE
    )
```

---

## Related Documents

- [Teams & Clubs](./teams-clubs.md) - Team chat integration
- [Studies](./studies.md) - Study chat
- [WebSocket Architecture](../01-architecture/websocket-architecture.md) - Real-time infrastructure
- [User Authentication](../02-core-features/user-authentication.md) - User system
- [RESEARCH.md](./RESEARCH.md) - Detailed Lichess research

---

*Document created: December 2025*
