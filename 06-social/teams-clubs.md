---
title: Teams & Clubs
category: social
status: draft
styleguide: hacksoft-django-styleguide
dependencies:
  - user-authentication
  - websocket-architecture
lichess_equivalent: lila/modules/team, lila/modules/teamSearch
---

# Teams & Clubs

> Team management system enabling users to organize communities, run tournaments, and compete in team battles.

> **Styleguide Reference**: Backend follows [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) with business logic in **Services**. Frontend follows [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) with **direct imports** (no barrel files).

---

## Overview

Teams (also called clubs) are a core social feature allowing players to organize around shared interests, identities, or purposes. They serve as the foundation for:
- Community building (geographic, interest-based, or player-focused)
- Tournament organization (Swiss, Arena, Team Battles)
- Chess club and organization management

---

## Feature Breakdown

### Team Management

#### Creating Teams
- Any registered user can create a team
- Creator automatically becomes team leader with full admin permissions
- Teams require: name, description, and joining policy

#### Joining Policies

| Policy | Behavior |
|--------|----------|
| **Open** | Anyone can join immediately |
| **Confirmation Required** | Leaders must approve join requests |
| **Invite Only** | Only invited users can join |

#### Team Membership
- Team membership visible on user profiles
- Required for Swiss tournament participation
- Members can be kicked by team leaders

### Team Leader System

#### Role Hierarchy

| Permission Level | Capabilities |
|-----------------|--------------|
| **Owner** | Full control, cannot be kicked, can delete team |
| **Admin** | Full control, can manage other leaders' permissions |
| **Tournament Leader** | Create and manage team tournaments only |
| **Basic Leader** | Approve members, send messages, kick members |

#### Leader Capabilities
- Send messages to all team members
- Create team battles, arena tournaments, Swiss tournaments
- Kick members from the team
- Approve/deny join requests
- Manage team settings
- Add/remove other team leaders (with admin permission)

#### Protection Mechanisms
- Team creators cannot be kicked by other leaders
- Removing yourself from leaders list is permanent
- Permission changes are logged for audit

### Team Page Features

**Action Buttons for Leaders:**
1. Create team battle
2. Create Swiss tournament
3. Create arena tournament
4. Send message to members
5. Team settings

---

## Team Battles

### Overview
Team Battles are arena tournaments where teams compete against each other. Up to 11 teams can participate in a single battle.

### Format Rules
- Players only paired against opposing team members (never teammates)
- All standard arena tournament rules apply
- Duration and time controls configurable by creator

### Scoring System

#### Individual Scoring (Arena Format)

| Result | Base Points | With Streak | With Berserk |
|--------|-------------|-------------|--------------|
| Win | 2 points | 4 points | +1 extra |
| Draw | 1 point | 2 points | N/A |
| Loss | 0 points | 0 points | N/A |

**Streak System:**
- Win 2 consecutive games to start a "fire streak"
- Subsequent wins worth double until failing to win
- Draws and losses break the streak

**Berserk Mode:**
- Halves clock time at game start
- Grants +1 extra tournament point on win
- Must play at least 7 moves to receive bonus
- Not available for 0+1 or 0+2 time controls

#### Team Scoring
- Each team's score = sum of their "leaders'" points
- Leaders = the N highest-scoring players (configurable, max 20)
- Lower-rated players don't hurt team scores

### Tiebreaker Rules
When teams have equal points:
1. Higher average performance rating of team leaders wins
2. If still tied, team with more games played wins

---

## Database Schema

### Django Models

```python
# <project_slug>/teams/models.py
import uuid

from django.db import models


class Team(models.Model):
    """Team/Club entity"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=5000)

    # Joining policy
    class JoinPolicy(models.TextChoices):
        OPEN = 'open', 'Open'
        CONFIRMATION = 'confirmation', 'Confirmation Required'
        INVITE_ONLY = 'invite', 'Invite Only'

    join_policy = models.CharField(
        max_length=20,
        choices=JoinPolicy.choices,
        default=JoinPolicy.OPEN
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='created_teams'
    )
    member_count = models.PositiveIntegerField(default=0)

    # Settings
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['member_count']),
            models.Index(fields=['created_at']),
        ]


class TeamMembership(models.Model):
    """User membership in a team"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='team_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['team', 'user']
        indexes = [
            models.Index(fields=['team', 'joined_at']),
        ]


class TeamLeader(models.Model):
    """Team leader with permissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='leaders')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='team_leaderships')

    # Permissions
    is_owner = models.BooleanField(default=False)
    can_admin = models.BooleanField(default=False)
    can_tournament = models.BooleanField(default=True)

    appointed_at = models.DateTimeField(auto_now_add=True)
    appointed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='appointed_leaders'
    )

    class Meta:
        unique_together = ['team', 'user']


class TeamJoinRequest(models.Model):
    """Pending join request for confirmation-required teams"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='team_requests')
    message = models.TextField(max_length=500, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        DENIED = 'denied', 'Denied'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    class Meta:
        unique_together = ['team', 'user']


class TeamBattle(models.Model):
    """Team battle tournament"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)

    # Tournament settings
    time_control = models.CharField(max_length=20)  # e.g., "3+0", "5+3"
    duration_minutes = models.PositiveIntegerField()
    leaders_count = models.PositiveIntegerField(default=5)  # Top N players count

    # Participating teams (max 11)
    teams = models.ManyToManyField(Team, through='TeamBattleParticipant')

    # Scheduling
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True)

    # Creator
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        ACTIVE = 'active', 'Active'
        FINISHED = 'finished', 'Finished'

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SCHEDULED
    )


class TeamBattleParticipant(models.Model):
    """Team participation in a team battle"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    battle = models.ForeignKey(TeamBattle, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    # Scores (updated during battle)
    total_points = models.PositiveIntegerField(default=0)
    avg_performance = models.PositiveIntegerField(default=0)
    games_played = models.PositiveIntegerField(default=0)

    # Final ranking
    final_rank = models.PositiveIntegerField(null=True)

    class Meta:
        unique_together = ['battle', 'team']
```

---

## API Endpoints

### REST API (Django REST Framework)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/teams/` | List teams (with pagination, search) |
| POST | `/api/teams/` | Create a new team |
| GET | `/api/teams/{slug}/` | Get team details |
| PATCH | `/api/teams/{slug}/` | Update team settings |
| DELETE | `/api/teams/{slug}/` | Delete team (owner only) |
| GET | `/api/teams/{slug}/members/` | List team members |
| POST | `/api/teams/{slug}/join/` | Join or request to join team |
| POST | `/api/teams/{slug}/leave/` | Leave team |
| POST | `/api/teams/{slug}/kick/{user_id}/` | Kick member |
| GET | `/api/teams/{slug}/requests/` | List join requests |
| POST | `/api/teams/{slug}/requests/{id}/approve/` | Approve request |
| POST | `/api/teams/{slug}/requests/{id}/deny/` | Deny request |
| GET | `/api/teams/{slug}/leaders/` | List team leaders |
| POST | `/api/teams/{slug}/leaders/` | Add team leader |
| DELETE | `/api/teams/{slug}/leaders/{user_id}/` | Remove leader |
| GET | `/api/users/{username}/teams/` | Get user's teams |

### Team Battles API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/team-battles/` | List team battles |
| POST | `/api/team-battles/` | Create team battle |
| GET | `/api/team-battles/{id}/` | Get battle details |
| GET | `/api/team-battles/{id}/standings/` | Get live standings |
| POST | `/api/team-battles/{id}/join/` | Join battle (as team) |

### WebSocket Events (Django Channels)

```python
# Team Battle Consumer
class TeamBattleConsumer(WebsocketConsumer):
    """Real-time team battle updates"""

    # Client -> Server
    # - join_battle: Subscribe to battle updates
    # - leave_battle: Unsubscribe

    # Server -> Client
    # - standings_update: Updated team standings
    # - game_finished: Individual game result
    # - battle_finished: Battle completed
```

---

## Implementation Notes

### Django Services

Following the Hacksoft Django Styleguide, all business logic lives in services with proper validation and transactions:

```python
# <project_slug>/teams/services.py
from django.db import transaction

from <project_slug>.teams.models import Team, TeamMembership, TeamLeader, TeamJoinRequest
from <project_slug>.users.models import User


@transaction.atomic
def team_create(
    *,
    name: str,
    description: str,
    creator: User,
    join_policy: str = Team.JoinPolicy.OPEN
) -> Team:
    """Create a new team and set creator as owner."""
    team = Team(
        name=name,
        description=description,
        join_policy=join_policy,
        created_by=creator
    )
    team.full_clean()
    team.save()

    # Create owner membership and leadership
    membership = TeamMembership(team=team, user=creator)
    membership.full_clean()
    membership.save()

    leader = TeamLeader(
        team=team,
        user=creator,
        is_owner=True,
        can_admin=True,
        can_tournament=True,
        appointed_by=creator
    )
    leader.full_clean()
    leader.save()

    return team


@transaction.atomic
def team_join(
    *,
    team: Team,
    user: User,
    message: str = ""
) -> TeamMembership | TeamJoinRequest:
    """Join team or create request based on join policy."""
    if team.join_policy == Team.JoinPolicy.OPEN:
        membership = TeamMembership(team=team, user=user)
        membership.full_clean()
        membership.save()
        return membership

    request = TeamJoinRequest(team=team, user=user, message=message)
    request.full_clean()
    request.save()
    return request


@transaction.atomic
def team_kick_member(
    *,
    team: Team,
    user_to_kick: User,
    kicked_by: User
) -> None:
    """Kick member from team (requires leader permission)."""
    from <project_slug>.teams.selectors import team_leader_get_for_user
    from <project_slug>.teams.exceptions import NotTeamLeaderError, CannotKickOwnerError

    leader = team_leader_get_for_user(team=team, user=kicked_by)
    if not leader:
        raise NotTeamLeaderError()

    target_leader = team_leader_get_for_user(team=team, user=user_to_kick)
    if target_leader and target_leader.is_owner:
        raise CannotKickOwnerError()

    TeamMembership.objects.filter(team=team, user=user_to_kick).delete()
    TeamLeader.objects.filter(team=team, user=user_to_kick).delete()


@transaction.atomic
def team_add_leader(
    *,
    team: Team,
    user: User,
    appointed_by: User,
    can_admin: bool = False,
    can_tournament: bool = True
) -> TeamLeader:
    """Add user as team leader with specified permissions."""
    leader = TeamLeader(
        team=team,
        user=user,
        is_owner=False,
        can_admin=can_admin,
        can_tournament=can_tournament,
        appointed_by=appointed_by
    )
    leader.full_clean()
    leader.save()
    return leader
```

### React Components

Following Bulletproof React with direct imports (no barrel files), kebab-case file names, and the three-part API pattern:

```
frontend/src/features/teams/
├── api/
│   ├── get-teams.ts          # Schema + fetcher + useTeams hook
│   ├── get-team.ts           # Schema + fetcher + useTeam hook
│   ├── create-team.ts        # Mutation hook with cache invalidation
│   └── join-team.ts          # Mutation hook
├── components/
│   ├── team-card.tsx
│   ├── team-page.tsx
│   ├── team-member-list.tsx
│   ├── team-leader-panel.tsx
│   ├── join-request-list.tsx
│   └── team-battle-standings.tsx
├── types/
│   └── team.ts               # Zod schemas + inferred types
└── hooks/
    ├── use-team-battle.ts
    └── use-team-membership.ts
```

**Example API Hook (Three-Part Pattern):**

```typescript
// frontend/src/features/teams/api/get-teams.ts
import { useQuery, queryOptions } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@/lib/api-client';

// 1. Schema
export const teamSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  memberCount: z.number(),
  joinPolicy: z.enum(['open', 'confirmation', 'invite']),
});

export type Team = z.infer<typeof teamSchema>;

// 2. Fetcher
export const getTeams = async (params?: { search?: string }): Promise<Team[]> => {
  const response = await api.get('/teams/', { params });
  return z.array(teamSchema).parse(response);
};

// 3. Query options
export const getTeamsQueryOptions = (params?: { search?: string }) => {
  return queryOptions({
    queryKey: ['teams', params],
    queryFn: () => getTeams(params),
  });
};

// 4. Hook
export const useTeams = (params?: { search?: string }) => {
  return useQuery(getTeamsQueryOptions(params));
};
```

---

## Related Documents

- [Chat & Messaging](./chat-messaging.md) - Team chat integration
- [Arena Tournaments](../05-competitive/arena-tournaments.md) - Tournament system
- [Swiss Tournaments](../05-competitive/swiss-tournaments.md) - Swiss format
- [WebSocket Architecture](../01-architecture/websocket-architecture.md) - Real-time infrastructure
- [RESEARCH.md](./RESEARCH.md) - Detailed Lichess research

---

*Document created: December 2025*
