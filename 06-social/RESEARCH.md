# Lichess Social Features Research

> Research document covering Lichess teams, studies, chat, messaging, and social features.
> Last updated: December 31, 2025

> **Implementation Note**: When implementing these features, follow the [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md) for backend services and the [Bulletproof React Styleguide](/.claude/skills/bulletproof-react-styleguide/SKILL.md) for frontend components. This project uses cookiecutter-django, so paths should use `<project_slug>/` instead of `apps/`.

---

## Table of Contents
1. [Teams/Clubs](#teamsclubs)
2. [Team Battles](#team-battles)
3. [Studies](#studies)
4. [Study Sharing](#study-sharing)
5. [Chat System](#chat-system)
6. [Messaging](#messaging)
7. [Following](#following)
8. [Forum](#forum)
9. [Moderation](#moderation)

---

## Teams/Clubs

### Overview
Teams (also referred to as clubs) are a core social feature on Lichess that allow players to organize around shared interests, identities, or purposes.

### Team Purposes
Teams serve various purposes on Lichess:
- Fan/friend communities for specific players
- Users of the same chess product or tool
- Tournament organization (Swiss/Arena/Team Battles)
- Geographic communities (country, state, region)
- Shared interest groups (hobbies, identities)
- Chess clubs and organizations

### Creating a Team
- Any registered user can create a team
- Teams are created with a name, description, and joining policy
- The creator automatically becomes the team leader

### Joining Policy Options
1. **Open**: Anyone can join immediately
2. **Confirmation Required**: Prospective members must request to join; leaders approve/deny
3. **By Request**: Similar to confirmation, with team leaders controlling membership

### Team Membership
- Players can see team names on user profiles
- Clicking a team name navigates to the team page where users can join
- Team membership is required for Swiss tournaments (members must join the hosting team)
- Teams range from large impersonal groups to small intimate communities

### Team Leader Roles and Permissions

#### Adding Team Leaders
- Go to team page > "Settings" (left sidebar) > "Team leaders"
- Type usernames of users to make leaders
- Must include your own username to retain leader status

#### Leader Capabilities
Team leaders can:
- Send messages to all team members
- Create team battles
- Create arena tournaments
- Create Swiss tournaments
- Kick members from the team
- Approve/deny join requests
- Manage team settings
- Add/remove other team leaders

#### Permission System
Lichess has updated Team Leader Permissions to be fully customizable:
- **Admin Permission**: Full control, can decide which leaders have tournament permissions
- **Tournament Permission**: "Create, manage and join team tournaments"
- Leaders with Admin permission can control what other leaders can do

#### Protection Mechanisms
- Team creators cannot be kicked by other team leaders
- Removing yourself from leaders list removes your admin access permanently
- Best practice: Only give leader access to trusted individuals

### Team Page Features
Teams have 5 action buttons for leaders:
1. Create team battle
2. Create Swiss tournament
3. Create arena tournament
4. Send message to members
5. Team settings

### API Endpoints (Teams)
Key API endpoints for teams:
- `GET /api/team/{teamId}` - Get team information
- `GET /api/team/{teamId}/users` - Get team members (ordered by join date)
- `POST /api/team/{teamId}/join` - Join a team
- `POST /api/team/{teamId}/quit` - Leave a team
- Personal access tokens required for authenticated endpoints

---

## Team Battles

### Overview
Team Battles are arena tournaments where teams compete against each other. They are one of the most popular competitive formats on Lichess.

### Format
- Up to 11 teams can participate in a single Team Battle
- Players are only paired against players from opposing teams (never teammates)
- All standard arena tournament rules apply
- Duration and time controls are configurable by the creator

### Creating a Team Battle
1. Navigate to: `lichess.org/tournament/team-battle/new/YOUR_TEAM_ID_HERE`
2. Or click the "Team Battle" button on your team page
3. First page: Tournament details (time control, duration, etc.)
4. Second page: Select participating teams (up to 10 other teams)

Requirements:
- Must be a team leader with Tournament permission
- Must be a member of at least one team

### Scoring System

#### Individual Scoring (Arena Format)
| Result | Base Points | With Streak | With Berserk |
|--------|-------------|-------------|--------------|
| Win | 2 points | 4 points | +1 extra |
| Draw | 1 point | 2 points | N/A |
| Loss | 0 points | 0 points | N/A |

**Streak System:**
- Win 2 consecutive games to start a "fire streak" (flame icon)
- All subsequent wins worth double until failing to win
- Draws break the streak, losses break the streak

**Berserk Mode:**
- Clicking Berserk at game start halves your clock time
- Grants +1 extra tournament point on win
- Cancels increment (except 1+2 which becomes 1+0)
- Not available for 0+1 or 0+2 time controls
- Must play at least 7 moves to receive bonus
- Drawing within first 10 moves earns no points

#### Team Scoring
- Each team's score = sum of their "leaders'" points
- Leaders = the N highest-scoring players on each team
- Creator sets N (number of leaders) - maximum is 20
- Lower-rated players don't hurt team scores (only top N count)

### Tiebreaker Rules
When teams have equal points:
1. Higher average performance rating of team leaders wins
2. Example: Team A (105 pts, 1980 avg perf) beats Team B (105 pts, 1850 avg perf)

Note: Lichess reports "Average performance" for all members, not just leaders, so manual calculation may be needed.

---

## Studies

### Overview
Studies are Lichess's collaborative analysis feature, allowing users to create, analyze, and share chess positions and games.

### Core Features
- Create annotated game analyses
- Organize content into chapters (up to 64 chapters per study)
- Real-time collaborative analysis
- Stockfish integration for computer analysis
- Opening book and tablebase access
- Drawing tools (arrows, circles)
- PGN import/export

### Study Visibility Settings
1. **Public**: Visible to everyone, listed in study searches
2. **Unlisted**: Accessible only via direct link
3. **Invite-only**: Only invited members can view

Note: Individual chapters cannot have different privacy settings than the parent study.

### Creating a Study
1. Navigate to lichess.org/study
2. Click "Create a study"
3. Set study name, visibility, and initial settings
4. Add chapters via:
   - Empty board
   - Starting position
   - PGN import
   - Game URL import

### Chapter Management
- Maximum 64 chapters per study
- Chapters can be reordered
- Export individual chapters or entire study to PGN
- Clone studies to duplicate content
- Move chapters between studies via PGN export/import

### Sync Mode
- **Sync Enabled**: All viewers see the same position in real-time
- **Sync Disabled**: Each viewer browses independently
- Users can toggle their sync status with the SYNC button
- Green checkmark = in sync with leader

### Record Mode
- **REC On** (green checkmark): Your moves and annotations are saved
- **REC Off**: Browsing mode, changes not saved
- Arrows/circles only visible to synced viewers when in record mode

---

## Study Sharing

### Member Roles
1. **Owner**: Full control, can delete study
2. **Contributor**: Can edit content, make variations
3. **Spectator**: View-only access (for invite-only studies)

### Contributor Capabilities
Contributors CAN:
- Use the share button
- Turn on Stockfish analysis
- Use opening book/tablebase
- Practice with computer
- Draw arrows and circles associated with moves
- Make variations

Contributors CANNOT:
- Use annotation glyphs
- Request computer analysis (server-side)
- Change study settings

### Inviting Members
1. Open study
2. Click "Members" tab (next to "Chapters")
3. Below your username, click "Add members"
4. Type Lichess usernames to invite

### Sharing with Teams
To share a study with a team:
1. Set study visibility to "Unlisted"
2. Copy the study link
3. Use team messaging to send link to members
4. Anyone with the link can view (but not edit unless invited as contributor)

### PGN Tags and Topics
- Studies can be tagged with topics for organization
- Access via "PGN tags" panel below the board
- Click "Manage topics" to add/edit
- Multiple topics can be assigned
- Helps with discoverability in study search

### API Endpoints (Studies)
- `GET /api/study/{studyId}.pgn` - Export study as PGN
- `GET /api/study/{studyId}/{chapterId}.pgn` - Export single chapter
- `POST /api/study/{studyId}/import-pgn` - Import PGN into study
- Query parameters: `?comments=false&variations=false&clocks=false`
- Import returns list of created chapters with `id` and `name`

---

## Chat System

### Chat Types on Lichess
1. **Game Chat**: Between players during a game
2. **Tournament/Lobby Chat**: General discussion in tournament lobbies
3. **Team Chat**: Within team pages
4. **Spectator Chat**: Viewers commenting on games
5. **Study Chat**: Within collaborative studies

### Chat Controls

#### Disabling Chat
Multiple methods available:
1. **Green Button**: Click green button (top-right during games) to turn black/hide chat
2. **Zen Mode**: Preferences > Game Display > Zen Mode > Yes
   - Hides chat during games
   - Automatically exits after game ends
3. **Notes Tab**: Switch to Notes tab; persists to next game
4. **Kid Mode**: Complete chat restriction (see Moderation section)
5. **Tournament Creators**: Can disable chat entirely for tournaments

### Chat Etiquette (Official Rules)
Core principle: "Treat chat like you would treat a good friend: with politeness, respect and kindness."

#### Prohibited Content
- Threatening, bullying, or offensive material
- Death threats or wishes ("kill yourself", "kys", "get cancer")
- Racist messages
- Using "rape" as metaphor for defeat
- Sensitive/shocking content
- Spam and excessive character repetition
- Unrelated tournament/team links
- Stream promotion or recruitment
- Public cheating accusations (use report system)

#### Consequences
Violations result in:
- Timeout (temporary)
- Warning
- Site-wide communication ban (for severe/repeated offenses)

---

## Messaging

### Direct Messaging System
- Access via inbox icon in top navigation
- Send messages by visiting user profile and clicking "Compose message"
- Threaded conversation view

### Inbox Limitations
- Limited to displaying last 50 conversations
- Search by username to find older conversations
- Deleting a conversation resets that user's ability to message you

### Privacy Controls
Settings available for who can message you:
- **Everyone**: All users can send messages
- **Friends only**: Only users you follow can message
- **Existing conversations only**: Only continue existing threads
- **Nobody**: Disable all incoming messages

Note: Some users (like Lichess founder thibault) disable all private messages.

### Message Moderation
- Private messages are stored by Lichess
- May be reviewed if reported or flagged by automated systems
- Moderators can review when violations are reported

### Known Issues
- Duplicate message detection may block identical messages sent to multiple users
- Workaround for messaging issues: Invite users to a study for communication

---

## Following

### Follow System Overview
Lichess uses a "follow" system (not mutual friend requests):
- Unilateral: You follow someone without their approval
- Following makes them appear in your "Friends" list
- Similar to Twitter/X follow model

### How to Follow
- Visit user profile
- Click the thumbs-up button

### Benefits of Following
When you follow someone, you see their:
- Recent forum posts
- Blog posts
- Stream activity
- Teams they join
- Simuls they participate in
- Activity feed on your home page

### Viewing Your Follows
- **Friends link**: Right side of your profile page
- **Friends Online**: Button in bottom-right of Lichess pages
- **Direct URL**: `lichess.org/@/[username]/following`

### Follower Visibility (Removed Feature)
- Public follower counts and lists were **permanently removed**
- Reason: Spam prevention and reducing system strain
- You cannot see who follows you (except via activity notifications)
- When someone follows you, it appears in your daily activity log

### Messaging Integration
- Privacy setting: "Only people I follow can message me"
- Creates a quasi-friend system where following enables communication

---

## Forum

### Forum Structure
Lichess has four sub-forums:
1. **General Chess Discussion**: Chess topics, strategies, discussions
2. **Game Analysis**: Share and discuss your games
3. **Lichess Feedback**: Bug reports, feature requests, platform issues
4. **Off-Topic**: Non-chess discussions

### Posting Guidelines
- Use descriptive titles (avoid "Help", "Bug", or single words)
- Posts in wrong category will be closed by moderators
- Text is preferred; excessive images discouraged

### Embedding Content
- **Games**: Paste game URL directly; auto-embeds
- **Studies**: Same as games; paste URL
- **Images**: Paste image URL; converts to viewable image on submit
- **Videos**: Limited support

### Forum Etiquette Rules
- No advertisements (team recruitment, tournament promotion, YouTube channels)
- No public shaming or cheating accusations
- No profanity or personal insults
- Explain viewpoints respectfully or link to relevant FAQ
- Use report system for suspected cheaters

### Moderation Actions
- Thread closing for violations
- Thread deletion for severe violations
- User warnings or bans for repeated offenses

---

## Moderation

### Reporting System

#### How to Report
1. **Profile Report Button**: Triangle with exclamation mark on user profiles
2. **Direct URL**: `lichess.org/report`
3. **Chat Warn Button**: Next to chat messages
4. **Forum Report**: Report button on posts

#### What to Include in Reports
- Links to specific games or tournaments
- Clear explanation of the violation
- Evidence (screenshots if applicable)
- Context for moderator review

Vague reports like "this user insulted me" without evidence are difficult to act on.

### Report Processing
- Reports forwarded to volunteer moderators
- Typical review time: 1-2 days
- Moderators review evidence and take appropriate action
- No need to submit duplicate reports

### Moderation Actions
| Violation | Possible Action |
|-----------|-----------------|
| First offense (minor) | Warning |
| Repeated minor offenses | Chat ban |
| Severe chat violations | Communication ban (site-wide) |
| Cheating (confirmed) | Account ban |
| Terms of Service violation | Account restrictions or ban |

### Notification Policy
- You receive notification **only** if reported user is banned
- No notification for warnings or chat bans
- Lack of notification doesn't mean report was ignored

### Chat Ban vs Account Ban
- **Chat Ban**: Cannot use chat/messaging, can still play games
- **Account Ban**: Full account restriction
- Chat bans are private (not visible on profile)

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
- Parents should retain password to prevent disabling
- Can still play games (opponents can only send moves)

**Enabling/Disabling:**
- Settings > Account > Kid Mode
- `lichess.org/account/kid`
- Requires password to disable

### Automated Detection
- **Irwin**: Internal cheat detection system
- Analyzes games and user behavior
- Flags suspicious patterns for moderator review

### Becoming a Moderator
- Not possible to apply directly
- Lichess contacts promising candidates
- Moderators are volunteers

---

## API Summary

### Teams API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/team/{teamId}` | GET | Get team info |
| `/api/team/{teamId}/users` | GET | Stream team members |
| `/api/team/{teamId}/join` | POST | Join team |
| `/api/team/{teamId}/quit` | POST | Leave team |
| `/api/team/{teamId}/kick/{userId}` | POST | Kick member (auth required) |
| `/api/team/of/{username}` | GET | Get user's teams |
| `/api/team/all` | GET | List popular teams |
| `/api/team/search` | GET | Search teams |

### Studies API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/study/{studyId}.pgn` | GET | Export study PGN |
| `/api/study/{studyId}/{chapterId}.pgn` | GET | Export chapter PGN |
| `/api/study/{studyId}/import-pgn` | POST | Import PGN to study |
| `/study/by/{username}` | GET | List user's studies |

Query parameters for export:
- `?comments=true/false` - Include comments
- `?variations=true/false` - Include variations
- `?clocks=true/false` - Include clock times

### Authentication
- Personal access tokens: `lichess.org/account/oauth/token`
- OAuth2 flow for applications
- Check for "OAuth2" badge in API docs to determine if auth required
- Support available on Discord: #lichess-api-support channel

---

## Sources

### Official Lichess Resources
- [Lichess Team Battle FAQ](https://lichess.org/page/team-battle-faq)
- [Lichess Chat Etiquette](https://lichess.org/page/chat-etiquette)
- [Lichess Forum Etiquette](https://lichess.org/page/forum-etiquette)
- [Lichess Report FAQ](https://lichess.org/page/report-faq)
- [Lichess Kid Mode](https://lichess.org/page/kid-mode)
- [Lichess API Documentation](https://lichess.org/api)
- [Lichess Community Forum](https://lichess.org/forum)

### Forum Discussions
- [Very Cool New Features for Team Leaders](https://lichess.org/forum/lichess-feedback/very-cool-new-features-for-team-leaders)
- [Team Battles Discussion](https://lichess.org/forum/general-chess-discussion/team-battles-2)
- [About the Lichess Follow System](https://lichess.org/forum/lichess-feedback/about-the-lichess-follow-system)
- [How to Create a Team Tournament](https://lichess.org/forum/off-topic-discussion/how-to-create-a-team-tournament)
- [Studies Privacy Settings](https://lichess.org/forum/lichess-feedback/studies-privacy-settings-for-individual-chapters)
- [Study Sharing Feature Request](https://lichess.org/forum/lichess-feedback/study-sharing-feature-request)
- [Team Leader Permissions Request](https://lichess.org/forum/lichess-feedback/req-diffrent-admin-permissions-in-team-leaders)
- [Private Messages Screening](https://lichess.org/forum/general-chess-discussion/are-private-messages-screened-actively-by-lichess)
- [Followers and Following](https://lichess.org/forum/lichess-feedback/followers-and-following)
- [Posting Games in Forum](https://lichess.org/forum/lichess-feedback/posting-games-in-the-forum)

### Technical Resources
- [Lichess API GitHub Repository](https://github.com/lichess-org/api)
- [lichess Python Library Documentation](https://lichess-api.readthedocs.io/en/latest/index.html)
- [Teams Python API](https://lichess-api.readthedocs.io/en/latest/source/teams.html)
- [Studies Python API](https://lichess-api.readthedocs.io/en/latest/source/studies.html)
- [Swiss Tournament Maker Script](https://github.com/lichess-org/swiss-maker)

### Community Teams
- [Team Leaders Club](https://lichess.org/team/team-leaders-club)
- [Team Leaders Only](https://lichess.org/team/team-leaders-only)
- [Team Battles Club (TBC)](https://lichess.org/team/team-battles-club-tbc)

---

## Research Summary

I have completed comprehensive research on Lichess social features. The document above should be saved to:

**File Path**: `/Users/dustycyanide/Documents/projects/ai/vibefaster/django_react_shipfast/lichess_specs/06-social/RESEARCH.md`

### Key Findings

**Teams/Clubs:**
- Teams support configurable joining policies (open, confirmation required)
- Team leaders have customizable permissions (Admin, Tournament)
- Team creators cannot be kicked, providing protection
- Teams are required for Swiss tournaments

**Team Battles:**
- Up to 11 teams compete in arena-style format
- Scoring uses top N players per team (configurable, max 20)
- Tiebreakers based on average performance rating

**Studies:**
- Collaborative analysis with real-time sync
- Up to 64 chapters per study
- Three visibility levels: public, unlisted, invite-only
- Contributor permissions are limited (no annotation glyphs)

**Chat & Messaging:**
- Multiple chat types (game, tournament, team, study)
- Zen Mode and Kid Mode for chat restrictions
- Inbox limited to 50 conversations
- Privacy controls for who can message you

**Following:**
- Unilateral follow system (no friend requests)
- Follower counts were permanently removed
- Following enables activity feed notifications

**Forum:**
- Four categories: General, Game Analysis, Feedback, Off-Topic
- Strict etiquette rules against advertising and public shaming

**Moderation:**
- Report via profile button or lichess.org/report
- Irwin automated cheat detection
- Kid Mode for complete safety restrictions
- Chat bans vs account bans distinction
