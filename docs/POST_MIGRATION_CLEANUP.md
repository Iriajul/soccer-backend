# Post-Migration Cleanup — deferred bug fixes

These are **intentional compatibility workarounds** in the Django port. They
reproduce genuine bugs in the original NestJS backend so that, at cutover, the
Flutter app and React admin receive **byte-identical** responses to what the old
backend returns today (golden-master = 58/58).

Each item should be fixed **deliberately, after cutover**, together with the
Flutter/React teams, and verified with its own before/after test — not silently
during the migration.

---

## Root cause (shared by all three)

The NestJS backend stores several id fields — `Team.coachId`, `AgeGroup.coordinatorId`,
and the `clubId` on `User` / `ConnectionRequest` — as **plain strings**, but a few
service queries look them up with `new Types.ObjectId(value)` and **no
`$in:[ObjectId, string]` fallback**. In MongoDB an ObjectId never matches a
string, so those queries silently return nothing.

The Django port stores ids consistently, so the "correct" data is actually
present — we deliberately suppress it in the three paths below.

---

## Item 1 — Coach `GET /users/me` context is always empty

- **File:** `apps/users/services.py` → `get_profile_with_context`, COACH branch.
- **Current (compat):** returns `context: {}` for a COACH.
- **Correct behavior (deferred):** `context: { teams: [{ teamId, teamName, ageGroupId }, …] }`
  for every team where the user is the coach.
- **Fix:** restore `Team.objects.filter(coach_id_id=user_id)` and build the
  `teams` list.
- **Client impact:** a coach's profile would begin returning their teams.

## Item 2 — Coordinator `GET /users/me` context is always empty

- **File:** `apps/users/services.py` → `get_profile_with_context`, COORDINATOR branch.
- **Current (compat):** returns `context: {}` for a COORDINATOR.
- **Correct behavior (deferred):** `context: { ageGroups: [{ ageGroupId, ageGroupName }, …] }`.
- **Fix:** restore `AgeGroup.objects.filter(coordinator_id_id=user_id)` (re-add
  the `AgeGroup` import).
- **Client impact:** a coordinator's profile would begin returning their age groups.

## Item 3 — Staff `GET /connections/pending` is always empty

- **File:** `apps/connections/services.py` → `get_pending_requests`, staff branch.
- **Current (compat):** returns `[]` for non-parent/non-player (staff) callers.
- **Correct behavior (deferred):** all non-`APPROVED` `ConnectionRequest`s in the
  caller's club, with `parentId`/`childId` populated.
- **Fix:** restore
  `ConnectionRequest.objects.filter(club_id_id=requester.club_id).exclude(status=APPROVED)`.
- **Client impact:** staff would begin seeing pending parent-child link requests.

---

## How to verify a fix (per item)

1. Remove the compat short-circuit and restore the real query.
2. Add a focused test asserting the now-populated response.
3. Run the golden-master suite — that item will now legitimately differ from the
   (still-buggy) NestJS oracle, which is expected once the fix is intentional.
