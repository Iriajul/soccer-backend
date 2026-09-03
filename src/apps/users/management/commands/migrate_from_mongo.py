"""
One-time data migration: MongoDB → PostgreSQL, PRESERVING every _id verbatim.

Usage:
    MONGODB_URI="mongodb+srv://..." python manage.py migrate_from_mongo [--flush]

Guarantees the compatibility contract:
  * Every document's `_id` is carried over UNCHANGED (24-hex string PK), so
    existing clients' stored ids keep working.
  * bcrypt password hashes are prefixed into Django's stored format
    ("bcrypt$$2b$..."), so existing users log in with no reset.
  * createdAt/updatedAt are preserved exactly (written via .update() to bypass
    Django's auto_now/auto_now_add).
  * Relationship ids (clubId, coachId, roster, childPlayerIds, ...) are copied
    as-is — references may dangle exactly as they do in Mongo.

Reads only; it never writes to Mongo. Run against an EMPTY Postgres (or use
--flush to clear the target tables first).
"""
from datetime import timezone as _tz

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.clubs.models import Club
from apps.users.models import User
from apps.age_groups.models import AgeGroup
from apps.teams.models import Team
from apps.events.models import Event
from apps.performance.models import Performance
from apps.connections.models import ConnectionRequest
from common.hashing import normalize_mongo_hash


def _oid(value):
    """bson ObjectId (or str) → plain 24-hex string; None stays None."""
    return None if value is None else str(value)


def _oid_list(value):
    return [_oid(v) for v in (value or [])]


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=_tz.utc)


class Command(BaseCommand):
    help = "Migrate data from MongoDB into PostgreSQL, preserving all ids."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Delete existing rows in the target tables first.")

    def handle(self, *args, **options):
        uri = getattr(settings, "MONGODB_URI", None) or __import__("os").environ.get("MONGODB_URI")
        if not uri:
            raise CommandError("Set MONGODB_URI to the source Mongo database.")

        try:
            from pymongo import MongoClient
        except ImportError as exc:
            raise CommandError("pymongo is required: pip install pymongo") from exc

        db = MongoClient(uri).get_default_database()

        if options["flush"]:
            for model in (ConnectionRequest, Performance, Event, Team, AgeGroup, User, Club):
                model.objects.all().delete()
            self.stdout.write("Flushed target tables.")

        self._migrate_clubs(db)
        self._migrate_users(db)
        self._migrate_age_groups(db)
        self._migrate_teams(db)
        self._migrate_events(db)
        self._migrate_performances(db)
        self._migrate_connections(db)
        self.stdout.write(self.style.SUCCESS("Mongo → Postgres migration complete."))

    # Each helper inserts rows, then rewrites the timestamps via .update() so
    # auto_now/auto_now_add don't clobber the originals.
    def _stamp(self, model, pk, doc):
        model.objects.filter(pk=pk).update(
            created_at=_aware(doc.get("createdAt")) or model.objects.get(pk=pk).created_at,
            updated_at=_aware(doc.get("updatedAt")) or model.objects.get(pk=pk).updated_at,
        )

    def _migrate_clubs(self, db):
        n = 0
        for d in db["clubs"].find():
            pk = _oid(d["_id"])
            Club.objects.update_or_create(
                id=pk, defaults={"name": d.get("name", ""), "is_active": d.get("isActive", True)},
            )
            self._stamp(Club, pk, d)
            n += 1
        self.stdout.write(f"clubs: {n}")

    def _migrate_users(self, db):
        n = 0
        for d in db["users"].find():
            pk = _oid(d["_id"])
            User.objects.update_or_create(
                id=pk,
                defaults={
                    "name": d.get("name", ""),
                    "email": d.get("email", ""),
                    "profile_image": d.get("profileImage"),
                    "password": normalize_mongo_hash(d.get("password", "")),
                    "role": d.get("role"),
                    "club_id_id": _oid(d.get("clubId")),
                    "is_first_login": d.get("isFirstLogin", True),
                    "child_player_ids": _oid_list(d.get("childPlayerIds")),
                    "parent_ids": _oid_list(d.get("parentIds")),
                },
            )
            self._stamp(User, pk, d)
            n += 1
        self.stdout.write(f"users: {n}")

    def _migrate_age_groups(self, db):
        n = 0
        for d in db["agegroups"].find():
            pk = _oid(d["_id"])
            AgeGroup.objects.update_or_create(
                id=pk,
                defaults={
                    "name": d.get("name", ""),
                    "description": d.get("description"),
                    "club_id_id": _oid(d.get("clubId")),
                    "coordinator_id_id": _oid(d.get("coordinatorId")),
                },
            )
            self._stamp(AgeGroup, pk, d)
            n += 1
        self.stdout.write(f"age_groups: {n}")

    def _migrate_teams(self, db):
        n = 0
        for d in db["teams"].find():
            pk = _oid(d["_id"])
            Team.objects.update_or_create(
                id=pk,
                defaults={
                    "name": d.get("name", ""),
                    "club_id_id": _oid(d.get("clubId")),
                    "age_group_id_id": _oid(d.get("ageGroupId")),
                    "coach_id_id": _oid(d.get("coachId")),
                    "roster": _oid_list(d.get("roster")),
                    # Preserve Mongoose's __v so GET /teams shows the same value.
                    "version": d.get("__v", 0),
                },
            )
            self._stamp(Team, pk, d)
            n += 1
        self.stdout.write(f"teams: {n}")

    def _migrate_events(self, db):
        n = 0
        for d in db["events"].find():
            pk = _oid(d["_id"])
            Event.objects.update_or_create(
                id=pk,
                defaults={
                    "title": d.get("title", ""),
                    "description": d.get("description", ""),
                    "date": _aware(d.get("date")),
                    "team_id_id": _oid(d.get("teamId")),
                    "club_id_id": _oid(d.get("clubId")),
                    "created_by_id": _oid(d.get("createdBy")),
                },
            )
            self._stamp(Event, pk, d)
            n += 1
        self.stdout.write(f"events: {n}")

    def _migrate_performances(self, db):
        n = 0
        for d in db["performances"].find():
            pk = _oid(d["_id"])
            Performance.objects.update_or_create(
                id=pk,
                defaults={
                    "player_id_id": _oid(d.get("playerId")),
                    "club_id_id": _oid(d.get("clubId")),
                    "passing": d.get("passing", 0),
                    "dribbling": d.get("dribbling", 0),
                    "shooting": d.get("shooting", 0),
                    "defense": d.get("defense", 0),
                    "stamina": d.get("stamina", 0),
                    "recorded_by_id": _oid(d.get("recordedBy")),
                },
            )
            self._stamp(Performance, pk, d)
            n += 1
        self.stdout.write(f"performances: {n}")

    def _migrate_connections(self, db):
        n = 0
        for d in db["connectionrequests"].find():
            pk = _oid(d["_id"])
            ConnectionRequest.objects.update_or_create(
                id=pk,
                defaults={
                    "requester_id_id": _oid(d.get("requesterId")),
                    "parent_id_id": _oid(d.get("parentId")),
                    "child_id_id": _oid(d.get("childId")),
                    "club_id_id": _oid(d.get("clubId")),
                    "status": d.get("status", "PENDING"),
                },
            )
            self._stamp(ConnectionRequest, pk, d)
            n += 1
        self.stdout.write(f"connection_requests: {n}")
