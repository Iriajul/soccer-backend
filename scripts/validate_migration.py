#!/usr/bin/env python3
"""
Validate the Mongo → Postgres migration WITHOUT normalizing ids.

Run from src/ with Django settings + MONGODB_URI, e.g.:
  MONGODB_URI=mongodb://127.0.0.1:27017/soccer?replicaSet=rs0&directConnection=true \
  DJANGO_SETTINGS_MODULE=config.settings.development \
  ../venv/bin/python ../scripts/validate_migration.py http://127.0.0.1:3000 http://127.0.0.1:3001

Checks: counts, exact id preservation, relationship integrity, timestamps,
bcrypt/login compatibility, and GET parity against the NestJS oracle.
"""
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import django
django.setup()

from pymongo import MongoClient  # noqa: E402
from apps.users.models import User  # noqa: E402
from apps.clubs.models import Club  # noqa: E402
from apps.age_groups.models import AgeGroup  # noqa: E402
from apps.teams.models import Team  # noqa: E402
from apps.events.models import Event  # noqa: E402
from apps.performance.models import Performance  # noqa: E402
from apps.connections.models import ConnectionRequest  # noqa: E402
from common.utils import iso_z  # noqa: E402
from common.hashing import normalize_mongo_hash  # noqa: E402

NEST, DJ = sys.argv[1], sys.argv[2]
db = MongoClient(os.environ["MONGODB_URI"]).get_default_database()

problems = []
summary = {}


def oid(v):
    return None if v is None else str(v)


def oid_list(v):
    return [str(x) for x in (v or [])]


def mts(dt):
    return iso_z(dt) if dt else None


def check(cond, msg):
    if not cond:
        problems.append(msg)


# ── field/relationship + id preservation per model ────────────────────────────
def validate_users():
    m = {str(d["_id"]): d for d in db.users.find()}
    p = {u.id: u for u in User.objects.all()}
    summary["users"] = (len(m), len(p))
    check(set(m) == set(p), f"users id set mismatch: mongo-only={set(m)-set(p)} pg-only={set(p)-set(m)}")
    bad_pw = 0
    for i, md in m.items():
        pu = p.get(i)
        if not pu:
            continue
        check(pu.name == md.get("name"), f"user {i} name")
        check(pu.email == md.get("email"), f"user {i} email")
        check(pu.role == md.get("role"), f"user {i} role")
        check(pu.is_first_login == md.get("isFirstLogin"), f"user {i} isFirstLogin")
        check(pu.club_id_id == oid(md.get("clubId")), f"user {i} clubId")
        check(list(pu.child_player_ids or []) == oid_list(md.get("childPlayerIds")), f"user {i} childPlayerIds")
        check(list(pu.parent_ids or []) == oid_list(md.get("parentIds")), f"user {i} parentIds")
        check(pu.profile_image == md.get("profileImage"), f"user {i} profileImage")
        check(mts(pu.created_at) == mts(md.get("createdAt")), f"user {i} createdAt")
        check(mts(pu.updated_at) == mts(md.get("updatedAt")), f"user {i} updatedAt")
        if pu.password != normalize_mongo_hash(md.get("password", "")):
            bad_pw += 1
    check(bad_pw == 0, f"{bad_pw} users have non-preserved password hashes")
    summary["users_pw_ok"] = len(m) - bad_pw


def validate_clubs():
    m = {str(d["_id"]): d for d in db.clubs.find()}
    p = {c.id: c for c in Club.objects.all()}
    summary["clubs"] = (len(m), len(p))
    check(set(m) == set(p), "clubs id set mismatch")
    for i, md in m.items():
        pc = p.get(i)
        check(pc and pc.name == md.get("name"), f"club {i} name")
        check(pc and pc.is_active == md.get("isActive"), f"club {i} isActive")
        check(mts(pc.created_at) == mts(md.get("createdAt")), f"club {i} createdAt")


def validate_age_groups():
    m = {str(d["_id"]): d for d in db.agegroups.find()}
    p = {a.id: a for a in AgeGroup.objects.all()}
    summary["age_groups"] = (len(m), len(p))
    check(set(m) == set(p), "age_groups id set mismatch")
    for i, md in m.items():
        pa = p.get(i)
        check(pa and pa.name == md.get("name"), f"ag {i} name")
        check(pa and pa.club_id_id == oid(md.get("clubId")), f"ag {i} clubId")
        check(pa and pa.coordinator_id_id == oid(md.get("coordinatorId")), f"ag {i} coordinatorId")


def validate_teams():
    m = {str(d["_id"]): d for d in db.teams.find()}
    p = {t.id: t for t in Team.objects.all()}
    summary["teams"] = (len(m), len(p))
    check(set(m) == set(p), "teams id set mismatch")
    for i, md in m.items():
        pt = p.get(i)
        check(pt and pt.club_id_id == oid(md.get("clubId")), f"team {i} clubId")
        check(pt and pt.age_group_id_id == oid(md.get("ageGroupId")), f"team {i} ageGroupId")
        check(pt and pt.coach_id_id == oid(md.get("coachId")), f"team {i} coachId")
        check(pt and list(pt.roster or []) == oid_list(md.get("roster")), f"team {i} roster")
        check(pt and pt.version == md.get("__v", 0), f"team {i} __v/version ({pt.version} vs {md.get('__v')})")


def validate_events():
    m = {str(d["_id"]): d for d in db.events.find()}
    p = {e.id: e for e in Event.objects.all()}
    summary["events"] = (len(m), len(p))
    check(set(m) == set(p), "events id set mismatch")
    for i, md in m.items():
        pe = p.get(i)
        check(pe and pe.team_id_id == oid(md.get("teamId")), f"event {i} teamId")
        check(pe and pe.club_id_id == oid(md.get("clubId")), f"event {i} clubId")
        check(pe and pe.created_by_id == oid(md.get("createdBy")), f"event {i} createdBy")
        check(pe and mts(pe.date) == mts(md.get("date")), f"event {i} date")


def validate_performances():
    m = {str(d["_id"]): d for d in db.performances.find()}
    p = {x.id: x for x in Performance.objects.all()}
    summary["performances"] = (len(m), len(p))
    check(set(m) == set(p), "performances id set mismatch")
    for i, md in m.items():
        pp = p.get(i)
        check(pp and pp.player_id_id == oid(md.get("playerId")), f"perf {i} playerId")
        check(pp and pp.recorded_by_id == oid(md.get("recordedBy")), f"perf {i} recordedBy")
        for k in ("passing", "dribbling", "shooting", "defense", "stamina"):
            check(pp and getattr(pp, k) == md.get(k), f"perf {i} {k}")


def validate_connections():
    m = {str(d["_id"]): d for d in db.connectionrequests.find()}
    p = {c.id: c for c in ConnectionRequest.objects.all()}
    summary["connections"] = (len(m), len(p))
    check(set(m) == set(p), "connections id set mismatch")
    for i, md in m.items():
        pc = p.get(i)
        check(pc and pc.parent_id_id == oid(md.get("parentId")), f"conn {i} parentId")
        check(pc and pc.child_id_id == oid(md.get("childId")), f"conn {i} childId")
        check(pc and pc.club_id_id == oid(md.get("clubId")), f"conn {i} clubId")
        check(pc and pc.status == md.get("status"), f"conn {i} status")


# ── HTTP helpers for login + GET parity ───────────────────────────────────────
_token_cache = {}


def http(base, method, path, body=None, token=None):
    url = base.rstrip("/") + path
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def token_for(base, email, password):
    key = (base, email)
    if key not in _token_cache:
        st, body = http(base, "POST", "/auth/login", {"email": email, "password": password})
        _token_cache[key] = body.get("access_token") if isinstance(body, dict) else None
    return _token_cache[key]


def mask_tokens(v):
    if isinstance(v, dict):
        return {k: ("<JWT>" if k in ("access_token", "refresh_token", "resetToken") else mask_tokens(v[k])) for k in v}
    if isinstance(v, list):
        return [mask_tokens(x) for x in v]
    return v


def main():
    validate_users()
    validate_clubs()
    validate_age_groups()
    validate_teams()
    validate_events()
    validate_performances()
    validate_connections()

    # ids for GET parity
    club_id = str(db.clubs.find_one()["_id"])
    team_id = str(db.teams.find_one()["_id"])
    player_id = str(db.users.find_one({"role": "PLAYER"})["_id"])

    creds = {
        "admin": ("admin@soccer.com", "Admin123!"),
        "owner": ("owner_seed1@t.com", "NewPass456!"),
        "coach": ("coach_seed1@t.com", "NewPass123!"),
        "player": ("player_seed1@t.com", "NewPass123!"),
        "parent": ("parent_seed1@t.com", "NewPass123!"),
    }

    # login compatibility on the MIGRATED Postgres backend
    print("\n== LOGIN COMPATIBILITY (Django/migrated) ==")
    login_ok = 0
    for who, (em, pw) in creds.items():
        st, body = http(DJ, "POST", "/auth/login", {"email": em, "password": pw})
        ok = st == 200 and isinstance(body, dict) and "access_token" in body
        login_ok += ok
        print(f"  {'OK ' if ok else 'FAIL'} login {who} ({em}) -> {st}")
        if not ok:
            problems.append(f"login failed for {who}")
    summary["login_ok"] = f"{login_ok}/{len(creds)}"

    # GET parity: identical real ids, exact bodies (only tokens masked)
    gets = [
        ("GET /", "GET", "/", None),
        ("clubs list", "GET", "/clubs", "admin"),
        ("club detail", "GET", f"/clubs/{club_id}", "owner"),
        ("my-club", "GET", "/clubs/my-club", "owner"),
        ("dashboard super-admin", "GET", "/dashboard/super-admin", "admin"),
        ("age-groups", "GET", "/age-groups", "owner"),
        ("teams (populated)", "GET", "/teams", "coach"),
        ("events schedule", "GET", f"/events/team/{team_id}", "player"),
        ("perf player", "GET", f"/performance/{player_id}", "coach"),
        ("perf team report", "GET", f"/performance/team/{team_id}/report", "coach"),
        ("users list", "GET", "/users?page=1&limit=50", "owner"),
        ("me owner", "GET", "/users/me", "owner"),
        ("me coach (ctx {})", "GET", "/users/me", "coach"),
        ("me player (ctx)", "GET", "/users/me", "player"),
        ("my-children", "GET", "/connections/my-children", "parent"),
        ("my-parents", "GET", "/connections/my-parents", "player"),
    ]
    print("\n== GET PARITY (real ids, exact) NestJS vs migrated Django ==")
    parity_ok = 0
    for label, method, path, who in gets:
        ntok = token_for(NEST, *creds[who]) if who else None
        dtok = token_for(DJ, *creds[who]) if who else None
        ns, nb = http(NEST, method, path, token=ntok)
        ds, db_ = http(DJ, method, path, token=dtok)
        same = ns == ds and mask_tokens(nb) == mask_tokens(db_)
        parity_ok += same
        print(f"  {'MATCH   ' if same else 'MISMATCH'} [{ns}] {label}")
        if not same:
            problems.append(f"GET parity mismatch: {label}")
            print(f"     NEST  : {json.dumps(mask_tokens(nb))[:400]}")
            print(f"     DJANGO: {json.dumps(mask_tokens(db_))[:400]}")
    summary["get_parity"] = f"{parity_ok}/{len(gets)}"

    print("\n== SUMMARY ==")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\n  PROBLEMS: {len(problems)}")
    for p in problems:
        print(f"    - {p}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
