# Soccer Club — API Reference

Complete request/response reference for **every** endpoint, for the mobile app
and admin dashboard teams.

- **Base URL:** `https://soccer-api.athlongoapp.com`
- **No `/api` prefix** — endpoints hang off the root (e.g. `/auth/login`).
- **Auth:** JWT Bearer. Send `Authorization: Bearer <access_token>` on every
  protected request.
- **No response envelope.** Success responses are the payload directly (no
  `{success, data}` wrapper). Treat any non-2xx status as an error.
- **Content-Type:** `application/json` everywhere **except** `PATCH /users/me`
  (which is `multipart/form-data`).
- **IDs** are 24-char hex strings, returned as `_id` (or `id` inside the auth
  `user` object — see §1).

### Error format
4xx errors:
```json
{ "statusCode": 403, "message": "…", "error": "Forbidden" }
```
Validation errors return `message` as an **array**:
```json
{ "statusCode": 400, "message": ["email must be an email"], "error": "Bad Request" }
```
Unhandled 500s use a **different** shape (no `error` key):
```json
{ "statusCode": 500, "timestamp": "…", "path": "/…", "message": "Internal server error" }
```

### Roles
`SUPER_ADMIN` > `CLUB_OWNER` > `TECH_DIRECTOR` > `COORDINATOR` > `COACH` > `PLAYER` = `PARENT`

---

## 1. Auth (`/auth`)

### POST /auth/login — public
**Body**
```json
{ "email": "admin@soccer.com", "password": "Admin123!" }
```
**200**
```json
{
  "access_token": "eyJ…",
  "refresh_token": "eyJ…",
  "user": {
    "id": "6a71…",
    "name": "System Admin",
    "email": "admin@soccer.com",
    "role": "SUPER_ADMIN",
    "profileImage": null,
    "clubId": "6a71…"
  }
}
```
> `clubId` is a plain string; it is **omitted** entirely for `SUPER_ADMIN` (no club).

**403 (first login — must set a password)**
```json
{ "message": "Password reset required on first login", "requiresPasswordReset": true, "resetToken": "eyJ…" }
```
**401** `{ "statusCode": 401, "message": "Invalid credentials", "error": "Unauthorized" }`

---

### POST /auth/first-login-reset — public
Completes first login using the `resetToken` from the 403 above.
**Body**
```json
{ "resetToken": "eyJ…", "newPassword": "NewPass123!" }
```
**200** — same shape as `/auth/login` (real tokens + user).
**401** `{ "statusCode": 401, "message": "Invalid or expired reset token", "error": "Unauthorized" }`

---

### POST /auth/refresh — public
**Body**
```json
{ "refreshToken": "eyJ…" }
```
**200** — same shape as login, **but** `user.clubId` is a **populated object**:
```json
{ "access_token": "eyJ…", "refresh_token": "eyJ…",
  "user": { "id": "…", "name": "…", "email": "…", "role": "COACH",
            "profileImage": null, "clubId": { "_id": "…", "name": "FC Barcelona" } } }
```
**401** `{ "statusCode": 401, "message": "Invalid or expired refresh token", "error": "Unauthorized" }`

---

### POST /auth/forgot-password — public
**Body** `{ "email": "user@example.com" }`
**200 (always, whether or not the email exists)**
```json
{ "message": "If the email is registered, a reset code has been sent" }
```

### POST /auth/reset-password — public
**Body** `{ "token": "eyJ…", "newPassword": "brandNew123!" }`
**200** `{ "message": "Password has been reset successfully" }`
**401** `{ "statusCode": 401, "message": "Invalid or expired reset token", "error": "Unauthorized" }`

### POST /auth/change-password — **auth required**
**Body** `{ "oldPassword": "old…", "newPassword": "new…" }`
**200** `{ "message": "Password changed successfully" }`
**400** `{ "statusCode": 400, "message": "Incorrect old password", "error": "Bad Request" }`

---

## 2. Users (`/users`) — all require auth

### POST /users/invite
Creates a staff/user account, emails a temp password. Caller must outrank the
new role (strictly higher weight). Non-super-admins can only invite into their
own club.

**Who can invite whom** (role weights — you may invite any role with a *strictly
lower* weight):

| Caller | Can invite |
|---|---|
| `SUPER_ADMIN` (100) | anyone |
| `CLUB_OWNER` (90) | TECH_DIRECTOR, COORDINATOR, COACH, PLAYER, PARENT |
| `TECH_DIRECTOR` (80) | COORDINATOR, COACH, PLAYER, PARENT |
| `COORDINATOR` (70) | COACH, PLAYER, PARENT |
| `COACH` (60) | **PLAYER, PARENT** |
| `PLAYER` / `PARENT` (50) | nobody |

> So a **coach can invite/add PLAYER and PARENT accounts** (but not another coach
> or higher). The invited user receives the temp-password email and completes the
> first-login flow to set their own password.

**Body**
```json
{ "name": "John Doe", "email": "john@example.com", "role": "COACH", "clubId": "6a71…" }
```
> `clubId` is optional and ignored unless the caller is `SUPER_ADMIN`.

**201** `{ "message": "Invitation sent successfully", "userId": "6a71…" }`
**409** `{ "statusCode": 409, "message": "User with this email already exists", "error": "Conflict" }`
**403** `{ "statusCode": 403, "message": "You do not have permission to create a user with the role: COACH", "error": "Forbidden" }`

---

### PATCH /users/:id/role
**Body** `{ "role": "COORDINATOR" }`
**200**
```json
{ "message": "Role updated successfully", "user": { "id": "6a71…", "name": "John Doe", "newRole": "COORDINATOR" } }
```
**409 (user not found — note: 409, not 404)** `{ "statusCode": 409, "message": "User not found", "error": "Conflict" }`
**403** cross-club / insufficient authority.

---

### GET /users/me
Own profile + role-specific `context`.
**200**
```json
{
  "_id": "6a71…",
  "name": "Coach Dan",
  "email": "dan@club.com",
  "role": "COACH",
  "isFirstLogin": false,
  "childPlayerIds": [],
  "parentIds": [],
  "createdAt": "2026-01-05T10:00:00.000Z",
  "updatedAt": "2026-01-05T10:00:00.000Z",
  "clubId": { "_id": "6a71…", "name": "FC Barcelona" },
  "context": { "teams": [ { "teamId": "…", "teamName": "U-12 Elite", "ageGroupId": "…" } ] }
}
```
> `context` shape by role: **PLAYER** → `{teamId, teamName, ageGroupId}` or `{}`; **COORDINATOR/COACH** → `{}` (see note*); others → `{}`. `profileImage` key is present only when set. `clubId` is populated here.
>
> *Coach/coordinator `context` is intentionally empty (matches the current production backend). See the note in the project docs.

---

### PATCH /users/me — `multipart/form-data`
The one non-JSON endpoint. All fields optional.
**Form fields:** `name`, `email`, `password`, `profileImage` (file).
**200** — updated user (password never returned), `clubId` as a raw string, includes `__v`:
```json
{ "_id": "6a71…", "name": "Jane Updated", "email": "jane@club.com",
  "profileImage": "/storage/1690000000000-123.jpg", "role": "COACH",
  "clubId": "6a71…", "isFirstLogin": false, "childPlayerIds": [], "parentIds": [],
  "createdAt": "…", "updatedAt": "…", "__v": 0 }
```
> `profileImage` is a **relative** path — prefix with the base URL to display: `https://soccer-api.athlongoapp.com/storage/…`.

---

### GET /users?page=1&limit=10&role=COACH&clubId=…
Paginated, club- and hierarchy-scoped. `clubId` filter is honored only for
`SUPER_ADMIN`. Non-super-admins only see users **below** their own role.
**200**
```json
{
  "data": [
    { "_id": "6a71…", "name": "John", "email": "john@club.com", "role": "COACH",
      "profileImage": null, "clubId": "6a71…", "isFirstLogin": false,
      "childPlayerIds": [], "parentIds": [], "createdAt": "…", "updatedAt": "…", "__v": 0 }
  ],
  "meta": { "total": 1, "page": 1, "lastPage": 1 }
}
```

---

## 3. Clubs (`/clubs`)

### POST /clubs — **SUPER_ADMIN only**
Creates a club **and** its `CLUB_OWNER` in one transaction.
**Body** `{ "name": "FC Barcelona", "ownerName": "Joan Laporta", "ownerEmail": "joan@fcb.com" }`
**201**
```json
{ "message": "Club and Club Owner created successfully",
  "club": { "_id": "6a71…", "name": "FC Barcelona", "isActive": true,
            "createdAt": "…", "updatedAt": "…", "__v": 0 } }
```
**500 (rolled back, e.g. owner email exists)** `{ "statusCode": 500, "timestamp":"…","path":"/clubs","message": "Failed to create club and owner. Transaction rolled back." }`

### GET /clubs — **SUPER_ADMIN only**
**200**
```json
[ { "_id": "6a71…", "name": "FC Barcelona", "isActive": true, "createdAt": "…", "updatedAt": "…",
    "owner": { "id": "…", "name": "Monir", "email": "monir@fcbarcelona.com",
               "profileImage": null, "isDefaultPassword": true },
    "totalMembers": 15 } ]
```

### GET /clubs/my-club — any auth
Caller's own club. **200** `{ "_id":"…","name":"…","isActive":true,"createdAt":"…","updatedAt":"…" }`
**400 (super admin has no club)** `{ "statusCode": 400, "message": "Your account is not assigned to any club.", "error": "Bad Request" }`

### GET /clubs/:id — any auth (own club only, unless super admin)
**200** — like the list item, but `owner` also includes `createdAt`, plus `totalMembers`.
**403** `{ "statusCode": 403, "message": "You do not have permission to view this club.", "error": "Forbidden" }`

---

## 4. Age Groups (`/age-groups`)

### POST /age-groups — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR
**Body** `{ "name": "U-12", "description": "Under 12", "coordinatorId": "6a71…" }` (last two optional)
**201** — raw saved doc (`_id, name, description?, clubId, coordinatorId?, createdAt, updatedAt, __v`).
**409** `{ "statusCode": 409, "message": "An Age Group named 'U-12' already exists in your club.", "error": "Conflict" }`

### GET /age-groups — any auth
**200** — each age group with its teams joined in:
```json
[ { "_id":"…","name":"U-12","clubId":"…",
    "coordinatorId": { "_id":"…","name":"Coord","email":"c@club.com" },
    "createdAt":"…","updatedAt":"…","__v":0,
    "totalTeams": 1,
    "teams": [ { "_id":"…","name":"U-12 Elite",
                 "coachId": { "_id":"…","name":"Coach Dan" }, "roster": ["…"], "ageGroupId":"…" } ] } ]
```

### DELETE /age-groups/:id — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR
**200** `{ "message": "Age group deleted successfully" }`
**404** `{ "statusCode": 404, "message": "Age group not found or you do not have permission to delete it.", "error": "Not Found" }`

---

## 5. Teams (`/teams`)

### POST /teams — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR, COORDINATOR
**Body** `{ "name": "U-12 Elite", "ageGroupId": "6a71…", "coachId": "6a71…" }` (`coachId` optional)
**201** — raw doc (unpopulated IDs):
```json
{ "_id":"…","name":"U-12 Elite","ageGroupId":"…","coachId":"…","clubId":"…",
  "roster": [], "createdAt":"…","updatedAt":"…","__v":0 }
```
**404** `{ "statusCode": 404, "message": "Age Group not found in your club.", "error": "Not Found" }`

### GET /teams — any auth
**200** — fully populated:
```json
[ { "_id":"…","name":"U-12 Elite","clubId":"…",
    "ageGroupId": { "_id":"…","name":"U-12" },
    "coachId": { "_id":"…","name":"Coach Dan","email":"dan@club.com","profileImage":null },
    "roster": [ { "_id":"…","name":"Player One","profileImage":null } ],
    "createdAt":"…","updatedAt":"…","__v":0 } ]
```

### DELETE /teams/:id — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR
**200** `{ "message": "Team deleted successfully" }`
**404** `{ "statusCode": 404, "message": "Team not found or you do not have permission to delete it.", "error": "Not Found" }`

### PATCH /teams/:id/roster — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR, COORDINATOR, COACH
**Body** `{ "playerId": "6a71…", "action": "add" }` — `action` is `"add"` or `"remove"`.
**200** `{ "message": "Player added successfully", "roster": ["6a71…"] }`
> On `remove` the message is `"Player removeed successfully"` (double-e — existing behavior, kept intentionally). `roster` is a plain array of ID strings.

**409** `{ "statusCode": 409, "message": "Player is already on this roster.", "error": "Conflict" }`

---

## 6. Events (`/events`)

### POST /events — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR, COORDINATOR, COACH
**Body**
```json
{ "title": "Saturday Training", "description": "Passing drills",
  "date": "2030-01-01T10:00:00.000Z", "teamId": "6a71…" }
```
**201** — raw doc:
```json
{ "_id":"…","title":"Saturday Training","description":"Passing drills",
  "date":"2030-01-01T10:00:00.000Z","teamId":"…","clubId":"…","createdBy":"…",
  "createdAt":"…","updatedAt":"…","__v":0 }
```
**403** `{ "statusCode": 403, "message": "You can only create events for your own team.", "error": "Forbidden" }`

### GET /events/team/:teamId — any auth
Events for a team, **sorted ascending by date**. `createdBy` is populated.
**200**
```json
[ { "_id":"…","title":"Early","description":"d","date":"2030-01-01T10:00:00.000Z",
    "teamId":"…","clubId":"…",
    "createdBy": { "_id":"…","name":"Coach Dan","profileImage":null },
    "createdAt":"…","updatedAt":"…","__v":0 } ]
```

---

## 7. Performance (`/performance`)

### PUT /performance/:playerId — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR, COORDINATOR, COACH
Creates or replaces a player's 5 ratings (all required, 0–100).
**Body** `{ "passing": 80, "dribbling": 85, "shooting": 75, "defense": 70, "stamina": 90 }`
**200**
```json
{ "_id":"…","playerId":"…","clubId":"…","passing":80,"dribbling":85,"shooting":75,
  "defense":70,"stamina":90,"recordedBy":"…","createdAt":"…","updatedAt":"…","__v":0 }
```
**400** `{ "statusCode": 400, "message": "Performance ratings can only be recorded for players.", "error": "Bad Request" }`
**403** `{ "statusCode": 403, "message": "You can only rate players assigned to your team roster.", "error": "Forbidden" }`

### GET /performance/:playerId — any auth (self/child/staff restricted)
**200 (record exists)** — the full document above.
**200 (no record yet)** — zeroed default:
```json
{ "playerId":"…","passing":0,"dribbling":0,"shooting":0,"defense":0,"stamina":0,"recordedBy":null }
```
**403** `{ "statusCode": 403, "message": "You can only view your own performance ratings.", "error": "Forbidden" }`

### GET /performance/team/:teamId/report — SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR, COORDINATOR, COACH
**200**
```json
{
  "teamId": "…",
  "teamName": "U-12 Elite",
  "average": { "passing": 78, "dribbling": 82, "shooting": 75, "defense": 70, "stamina": 88 },
  "topPerformers": [ { "playerId":"…","playerName":"Jane","passing":90,"dribbling":92,
                       "shooting":85,"defense":80,"stamina":95,"overallScore":88 } ],
  "individualReports": [ { "playerId":"…","playerName":"Jane","passing":90,"dribbling":92,
                           "shooting":85,"defense":80,"stamina":95,"overallScore":88 } ]
}
```
> Only rated players appear. `average`/`overallScore` are rounded. If nobody is rated: zeroed `average`, empty arrays.

---

## 8. Connections (`/connections`) — parent ↔ player linking. All require auth.

**How linking works (state machine):** a request links one PARENT to one PLAYER
(same club only). The initial status depends on **who initiates**:

| Initiator | Initial status | Then who approves |
|---|---|---|
| The **parent** (for themselves) | `WAITING_ON_CHILD` | the child/player approves → `APPROVED` |
| The **player/child** (for themselves) | `WAITING_ON_PARENT` | the parent approves → `APPROVED` |
| **Staff** (e.g. a **coach**/admin) | `PENDING` | **both** parent and child approve → `APPROVED` |

So a **coach can initiate a parent↔child link**, but it only becomes active once
**both the parent and the child approve** (`PATCH /connections/:id/approve`).
`PATCH /connections/:id/reject` sets it to `REJECTED`.

**On full approval**, the child's id is added to the parent's `childPlayerIds` and
the parent's id to the child's `parentIds`. A parent can be linked to **multiple
children**.

**Parent tracking their kids' evaluation:** once linked, a parent uses
`GET /connections/my-children` (each child with their **performance ratings**,
team, and upcoming schedule) or `GET /performance/:playerId` (allowed only for
their own children). "Evaluation" = the 5 performance ratings (passing,
dribbling, shooting, defense, stamina); it is a single current snapshot per
player (no history).

### POST /connections/request
**Body** `{ "parentId": "6a71…", "childId": "6a71…" }`
**201** — raw request doc:
```json
{ "_id":"…","requesterId":"…","parentId":"…","childId":"…","clubId":"…",
  "status":"PENDING","createdAt":"…","updatedAt":"…","__v":0 }
```
> Initial `status`: parent-initiated → `WAITING_ON_CHILD`; player-initiated → `WAITING_ON_PARENT`; staff-initiated → `PENDING`.

**409** `{ "statusCode": 409, "message": "A connection request already exists between these users.", "error": "Conflict" }`

### GET /connections/pending
**200** — parent/player see their actionable requests (with `parentId`/`childId`
populated to `{_id,name,email,profileImage}`). Staff currently get `[]` (existing
behavior). Example (parent/player):
```json
[ { "_id":"…","requesterId":"…",
    "parentId": { "_id":"…","name":"Parent","email":"p@x.com","profileImage":null },
    "childId":  { "_id":"…","name":"Player","email":"c@x.com","profileImage":null },
    "clubId":"…","status":"WAITING_ON_PARENT","createdAt":"…","updatedAt":"…","__v":0 } ]
```

### PATCH /connections/:id/approve
Advances the state machine; on full approval writes the link onto both users.
**200** — the updated request doc (raw).

### PATCH /connections/:id/reject
**200** — the updated request doc with `status: "REJECTED"`.

### GET /connections/my-children — PARENT only
**200**
```json
[ { "player": { "_id":"…","name":"Player","email":"c@x.com","profileImage":null },
    "team": { "id":"…","name":"U-12 Elite" },
    "performance": { "_id":"…","playerId":"…","passing":80, "…":"…" },
    "upcomingSchedules": [ { "_id":"…","title":"Match","date":"…","teamId":"…","…":"…" } ] } ]
```
**403** `{ "statusCode": 403, "message": "Only parents can access this endpoint.", "error": "Forbidden" }`

### GET /connections/my-parents — PLAYER only
**200** `[ { "_id":"…","name":"Parent","email":"p@x.com","profileImage":null } ]`

---

## 9. Dashboard (`/dashboard`)

### GET /dashboard/super-admin — **SUPER_ADMIN only**
**200**
```json
{ "overview": { "totalClubs": 2, "totalTeams": 5, "totalUsers": 26 },
  "roleBreakdown": { "SUPER_ADMIN": 1, "CLUB_OWNER": 2, "TECH_DIRECTOR": 2,
                     "COORDINATOR": 14, "COACH": 2, "PLAYER": 3, "PARENT": 2 } }
```

---

## 10. Health

### GET / — public
**200** — the plain string `Hello World!` (text, not JSON).

---

## Roles → allowed endpoints (quick matrix)

| Endpoint | Allowed roles |
|---|---|
| `POST /clubs`, `GET /clubs`, `GET /dashboard/super-admin` | SUPER_ADMIN |
| `POST /age-groups`, `DELETE /age-groups/:id`, `DELETE /teams/:id` | SUPER_ADMIN, CLUB_OWNER, TECH_DIRECTOR |
| `POST /teams` | + COORDINATOR |
| `PATCH /teams/:id/roster`, `POST /events`, `PUT /performance/:playerId`, `GET /performance/team/:id/report` | + COACH |
| `POST /users/invite`, `PATCH /users/:id/role`, `GET/PATCH /users/me`, `GET /users` | any authenticated (service enforces hierarchy) |
| `GET /teams`, `GET /age-groups`, `GET /events/team/:id`, `GET /performance/:playerId`, `GET /clubs/my-club`, `GET /clubs/:id` | any authenticated |
| `/connections/*` | any authenticated (service enforces relationship) |
| `GET /` | public |
| all `/auth/*` except `change-password` | public |
