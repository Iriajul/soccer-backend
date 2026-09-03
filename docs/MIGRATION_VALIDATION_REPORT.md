# Mongo → Postgres Migration Validation Report

**Method:** seeded a full hierarchy into MongoDB through the **live NestJS API**
(so the data carries the real string/ObjectId quirks), ran `migrate_from_mongo`
into a freshly-emptied PostgreSQL, then validated with real (un-normalized) IDs
against the NestJS oracle.

Harness: `scripts/validate_migration.py` (field/relationship checks + login +
GET parity). **Result: 0 problems.**

## 1. Records migrated per table

| Model / collection | Mongo | Postgres | Match |
|---|---|---|---|
| users | 6 | 6 | ✓ |
| clubs | 1 | 1 | ✓ |
| age_groups | 1 | 1 | ✓ |
| teams | 1 | 1 | ✓ |
| events | 3 | 3 | ✓ |
| performances | 1 | 1 | ✓ |
| connection_requests | 1 | 1 | ✓ |

## 2. ID preservation

Every document's `_id` was carried over verbatim as the Postgres primary key
(24-hex string). Per-model id **sets are exactly equal** (no missing, no extra,
no regenerated ids).

## 3. Relationship integrity

All foreign references verified equal to the source, by real id:
- `User.clubId`, `childPlayerIds[]`, `parentIds[]`
- `AgeGroup.clubId`, `coordinatorId`
- `Team.clubId`, `ageGroupId`, `coachId`, `roster[]` (order preserved), `__v`→`version`
- `Event.teamId`, `clubId`, `createdBy`, `date`
- `Performance.playerId`, `clubId`, `recordedBy`, the 5 ratings
- `ConnectionRequest.parentId`, `childId`, `clubId`, `status` (the APPROVED link
  and its mirrored `childPlayerIds`/`parentIds` are consistent)

Timestamps (`createdAt`/`updatedAt`, and `Event.date`) preserved to millisecond
precision (written via `.update()` to bypass `auto_now`).

## 4. Password / login compatibility

All 6 users authenticate on the migrated Postgres backend (5/5 seeded credentials
tested + super admin): raw NestJS bcrypt hashes were prefixed to Django's
`bcrypt$…` format, so **no user is forced to reset**.

## 5. Skipped / malformed records

None in this dataset. The migration processes **every** document; optional fields
fall back to sensible defaults. It does not skip records. (See risks re:
genuinely malformed source docs.)

## 6. GET parity after migration (real ids, byte-exact)

16/16 endpoints identical between NestJS (Mongo) and Django (migrated Postgres),
using the **same real ids** — bodies matched exactly including preserved
timestamps and `__v`:

`GET /` · clubs list · club detail · my-club · dashboard · age-groups · teams
(populated) · events schedule · performance player · performance team report ·
users list · /users/me (owner, coach ctx `{}`, player ctx) · my-children ·
my-parents.

## 7. Rerun behavior (idempotency / safety)

`migrate_from_mongo` uses `update_or_create` keyed on `_id`. Ran 3×; the full
Postgres state hash was **byte-identical** across runs — no duplicate rows, no
array growth (`roster`/`childPlayerIds`/`parentIds`), no field drift. Safe to
re-run. A `--flush` flag clears target tables first when a clean reload is wanted.

## 8. Remaining production risks

1. **Run order (super-admin email collision).** Run `migrate_from_mongo` into an
   **empty** DB *before* `bootstrap_superadmin`. If bootstrap runs first, it
   creates `admin@soccer.com` with a new id; migrating the Mongo admin (same
   email, different id) then violates the email-unique constraint. Recommended
   go-live order: `migrate` (schema) → `migrate_from_mongo` → `bootstrap_superadmin`
   (which then no-ops because a SUPER_ADMIN already exists) → serve.
2. **Malformed source docs.** A source user missing `email`, or duplicate emails,
   would fail the unique constraint mid-run. Recommend a pre-flight count/dry check
   on the production dump before the real run.
3. **Deferred behavior bugs.** Three endpoints intentionally reproduce the NestJS
   ObjectId/string bug (see `docs/POST_MIGRATION_CLEANUP.md`) — expected, not a
   migration defect.
4. **Legacy mixed id types.** Production Mongo may hold *some* records with
   ObjectId (not string) `coachId`/`clubId`/`coordinatorId`. The migration copies
   them as strings regardless (parity-preserving); revisit alongside the item-1/2/3
   cleanup.
