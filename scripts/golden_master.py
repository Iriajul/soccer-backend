#!/usr/bin/env python3
"""
Golden-master contract diff: NestJS (oracle) vs Django (port).

Runs the SAME scripted flow independently against both backends, then compares
each step's HTTP status + JSON body under these normalization rules:

  * Generated ObjectIds: the VALUE is normalized to a stable placeholder
    (<IDn>), assigned in a canonical (sorted-key) traversal so that the same
    reference-consistency and nesting must hold on BOTH sides. Key name
    (`_id` vs `id`), 24-hex format, and populated-vs-raw structure are still
    compared strictly (they are part of the structure).
  * JWT strings (access_token / refresh_token / resetToken): masked to <JWT>
    (presence + string type still required).
  * createdAt / updatedAt / 500 `timestamp`: normalized to <TS>.
  * 500 `path`: compared EXACTLY (part of the contract).
  * 500 `message` + NestJS-dev-only `details`: the message is normalized and
    `details` dropped, because those are dev-only; the production 500 body is
    {statusCode,timestamp,path,message:"Internal server error"} on both.
  * Everything else (name, email, role, status, message text, numbers,
    booleans, __v, event `date`, array order, key sets) is compared exactly.

Usage:  python golden_master.py http://127.0.0.1:3000 http://127.0.0.1:3001
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error

OID_RE = re.compile(r"^[0-9a-fA-F]{24}$")
TOKEN_KEYS = {"access_token", "refresh_token", "resetToken"}
TS_KEYS = {"createdAt", "updatedAt", "timestamp"}


class Resp:
    def __init__(self, status, body):
        self.status = status
        self.body = body


class Client:
    def __init__(self, base):
        self.base = base.rstrip("/")

    def req(self, method, path, body=None, token=None, multipart=None):
        url = self.base + path
        headers = {}
        data = None
        if multipart is not None:
            boundary = "----gm%d" % int(time.time() * 1000)
            parts = []
            for k, v in multipart.items():
                parts.append(f"--{boundary}\r\nContent-Disposition: form-data; "
                             f'name="{k}"\r\n\r\n{v}\r\n')
            data = ("".join(parts) + f"--{boundary}--\r\n").encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        r = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(r) as resp:
                raw = resp.read().decode()
                return Resp(resp.status, _parse(raw))
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            return Resp(e.code, _parse(raw))


def _parse(raw):
    try:
        return json.loads(raw)
    except Exception:
        return raw


# ── flow ────────────────────────────────────────────────────────────────────
def run_flow(C, tag):
    caps = []

    def cap(label, resp):
        caps.append((label, resp))
        return resp

    def get_token(email, password):
        r = C.req("POST", "/auth/login", {"email": email, "password": password})
        return r.body["access_token"] if isinstance(r.body, dict) and "access_token" in r.body else None

    def onboard(email):
        """First-login an invited user (temp DevPass123!) → return access token."""
        login = C.req("POST", "/auth/login", {"email": email, "password": "DevPass123!"})
        rt = login.body.get("resetToken")
        reset = C.req("POST", "/auth/first-login-reset", {"resetToken": rt, "newPassword": "NewPass123!"})
        return reset.body["access_token"]

    cap("GET /", C.req("GET", "/"))

    admin = get_token("admin@soccer.com", "Admin123!")
    cap("login admin", C.req("POST", "/auth/login", {"email": "admin@soccer.com", "password": "Admin123!"}))
    cap("login bad-email 400", C.req("POST", "/auth/login", {"email": "x", "password": ""}))
    cap("login wrong 401", C.req("POST", "/auth/login", {"email": "admin@soccer.com", "password": "nope"}))

    owner_email = f"owner_{tag}@t.com"
    cap("create club 201", C.req("POST", "/clubs", {"name": f"Club {tag}", "ownerName": "Owner", "ownerEmail": owner_email}, token=admin))
    cap("create club dup-owner 500", C.req("POST", "/clubs", {"name": f"Club2 {tag}", "ownerName": "O2", "ownerEmail": owner_email}, token=admin))
    cap("my-club admin 400", C.req("GET", "/clubs/my-club", token=admin))

    owner = onboard(owner_email)
    cap("owner first-login-403", C.req("POST", "/auth/login", {"email": owner_email, "password": "DevPass123!"}))
    cap("my-club owner 200", C.req("GET", "/clubs/my-club", token=owner))

    # invite staff
    coord_email, coach_email, player_email, parent_email = (f"{r}_{tag}@t.com" for r in ("coord", "coach", "player", "parent"))
    cap("invite coordinator 201", C.req("POST", "/users/invite", {"name": "Coord", "email": coord_email, "role": "COORDINATOR"}, token=owner))
    cap("invite dup 409", C.req("POST", "/users/invite", {"name": "Coord", "email": coord_email, "role": "COORDINATOR"}, token=owner))
    cap("invite coach 201", C.req("POST", "/users/invite", {"name": "Coach", "email": coach_email, "role": "COACH"}, token=owner))
    cap("invite player 201", C.req("POST", "/users/invite", {"name": "Player", "email": player_email, "role": "PLAYER"}, token=owner))
    cap("invite parent 201", C.req("POST", "/users/invite", {"name": "Parent", "email": parent_email, "role": "PARENT"}, token=owner))

    coord, coach, player_t, parent_t = (onboard(e) for e in (coord_email, coach_email, player_email, parent_email))

    # ids via /users/me
    coord_id = C.req("GET", "/users/me", token=coord).body["_id"]
    coach_id = C.req("GET", "/users/me", token=coach).body["_id"]
    player_id = C.req("GET", "/users/me", token=player_t).body["_id"]
    parent_id = C.req("GET", "/users/me", token=parent_t).body["_id"]

    cap("invite hierarchy 403 (coach invites coach)", C.req("POST", "/users/invite", {"name": "X", "email": f"x_{tag}@t.com", "role": "COACH"}, token=coach))

    # age groups
    ag = cap("create age-group 201", C.req("POST", "/age-groups", {"name": "U-12", "coordinatorId": coord_id}, token=owner))
    ag_id = ag.body["_id"]
    cap("create age-group dup 409", C.req("POST", "/age-groups", {"name": "U-12"}, token=owner))
    cap("age-group delete malformed 500", C.req("DELETE", "/age-groups/not-an-id", token=owner))

    # teams
    team = cap("create team 201", C.req("POST", "/teams", {"name": "U-12 Elite", "ageGroupId": ag_id, "coachId": coach_id}, token=owner))
    team_id = team.body["_id"]
    cap("create team wrong-club-ag 404", C.req("POST", "/teams", {"name": "Y", "ageGroupId": "64f000000000000000000000"}, token=owner))
    cap("roster add 200", C.req("PATCH", f"/teams/{team_id}/roster", {"playerId": player_id, "action": "add"}, token=coach))
    cap("roster add dup 409", C.req("PATCH", f"/teams/{team_id}/roster", {"playerId": player_id, "action": "add"}, token=coach))
    cap("roster remove 200 (typo)", C.req("PATCH", f"/teams/{team_id}/roster", {"playerId": player_id, "action": "remove"}, token=coach))
    C.req("PATCH", f"/teams/{team_id}/roster", {"playerId": player_id, "action": "add"}, token=coach)  # re-add for later
    cap("roster malformed team 500", C.req("PATCH", "/teams/bad/roster", {"playerId": player_id, "action": "add"}, token=owner))
    cap("delete team as coordinator 403", C.req("DELETE", f"/teams/{team_id}", token=coord))

    cap("list age-groups 200", C.req("GET", "/age-groups", token=owner))
    cap("list teams 200", C.req("GET", "/teams", token=coach))

    # events
    C.req("POST", "/events", {"title": "Late", "description": "d", "date": "2030-03-01T10:00:00.000Z", "teamId": team_id}, token=coach)
    C.req("POST", "/events", {"title": "Early", "description": "d", "date": "2030-01-01T10:00:00.000Z", "teamId": team_id}, token=coach)
    cap("create event 201", C.req("POST", "/events", {"title": "Mid", "description": "d", "date": "2030-02-01T10:00:00.000Z", "teamId": team_id}, token=coach))
    cap("event schedule 200 (sorted, populated)", C.req("GET", f"/events/team/{team_id}", token=player_t))
    cap("event schedule malformed 500", C.req("GET", "/events/team/bad", token=coach))

    # performance
    cap("perf upsert 200", C.req("PUT", f"/performance/{player_id}", {"passing": 80, "dribbling": 85, "shooting": 75, "defense": 70, "stamina": 90}, token=coach))
    cap("perf get 200", C.req("GET", f"/performance/{player_id}", token=coach))
    cap("perf upsert non-player 400", C.req("PUT", f"/performance/{coach_id}", {"passing": 1, "dribbling": 1, "shooting": 1, "defense": 1, "stamina": 1}, token=owner))
    cap("perf rating out-of-range 400", C.req("PUT", f"/performance/{player_id}", {"passing": 200, "dribbling": 1, "shooting": 1, "defense": 1, "stamina": 1}, token=owner))
    cap("perf player-view-other 403", C.req("GET", f"/performance/{player_id}", token=parent_t))
    cap("perf team report 200", C.req("GET", f"/performance/team/{team_id}/report", token=coach))

    # users
    cap("users me coach (context) 200", C.req("GET", "/users/me", token=coach))
    cap("users me coordinator (context) 200", C.req("GET", "/users/me", token=coord))
    cap("users me player (context) 200", C.req("GET", "/users/me", token=player_t))
    cap("users list 200", C.req("GET", "/users?page=1&limit=50", token=owner))
    cap("users list role-too-high empty", C.req("GET", "/users?role=CLUB_OWNER", token=coach))
    cap("update role missing 409", C.req("PATCH", "/users/64f000000000000000000000/role", {"role": "PLAYER"}, token=owner))
    cap("update role malformed 500", C.req("PATCH", "/users/bad/role", {"role": "PLAYER"}, token=owner))
    cap("update role success 200", C.req("PATCH", f"/users/{parent_id}/role", {"role": "PLAYER"}, token=owner))
    C.req("PATCH", f"/users/{parent_id}/role", {"role": "PARENT"}, token=owner)  # revert
    cap("patch me multipart 200", C.req("PATCH", "/users/me", multipart={"name": "Owner Renamed"}, token=owner))

    # connections
    req = cap("connection request 201 (staff→PENDING)", C.req("POST", "/connections/request", {"parentId": parent_id, "childId": player_id}, token=coach))
    conn_id = req.body["_id"]
    cap("connections pending staff 200", C.req("GET", "/connections/pending", token=owner))
    cap("connection approve parent (PENDING→WAIT_CHILD)", C.req("PATCH", f"/connections/{conn_id}/approve", token=parent_t))
    cap("connection approve child (→APPROVED)", C.req("PATCH", f"/connections/{conn_id}/approve", token=player_t))
    cap("my-children parent 200", C.req("GET", "/connections/my-children", token=parent_t))
    cap("my-parents player 200", C.req("GET", "/connections/my-parents", token=player_t))
    cap("my-children as coach 403", C.req("GET", "/connections/my-children", token=coach))

    # misc auth
    cap("forgot-password 200", C.req("POST", "/auth/forgot-password", {"email": owner_email}))
    cap("change-password 200", C.req("POST", "/auth/change-password", {"oldPassword": "NewPass123!", "newPassword": "NewPass456!"}, token=owner))
    refresh = C.req("POST", "/auth/login", {"email": owner_email, "password": "NewPass456!"}).body.get("refresh_token")
    cap("refresh 200 (populated club)", C.req("POST", "/auth/refresh", {"refreshToken": refresh}))
    cap("refresh invalid 401", C.req("POST", "/auth/refresh", {"refreshToken": "bad"}))

    # dashboard
    cap("dashboard super-admin 200", C.req("GET", "/dashboard/super-admin", token=admin))
    cap("dashboard forbidden 403", C.req("GET", "/dashboard/super-admin", token=owner))

    return caps


# ── normalization + compare ───────────────────────────────────────────────────
def canon(v, idmap):
    if isinstance(v, dict):
        out = {}
        for k in sorted(v.keys()):
            if k in TS_KEYS:
                out[k] = "<TS>"
            elif k in TOKEN_KEYS:
                out[k] = "<JWT>" if isinstance(v[k], str) and v[k] else v[k]
            else:
                out[k] = canon(v[k], idmap)
        return out
    if isinstance(v, list):
        return [canon(x, idmap) for x in v]
    if isinstance(v, str) and OID_RE.match(v):
        idmap.setdefault(v, f"<ID{len(idmap) + 1}>")
        return idmap[v]
    return v


def normalize(resp):
    body = resp.body
    if resp.status == 500 and isinstance(body, dict):
        body = dict(body)
        body.pop("details", None)
        if "message" in body:
            body["message"] = "<500MSG>"
    return {"status": resp.status, "body": canon(body, {})}


def main():
    nest, dj = sys.argv[1], sys.argv[2]
    tag = f"gm{int(time.time())}"
    print(f"tag={tag}\nNEST={nest}\nDJANGO={dj}\n")

    nest_caps = run_flow(Client(nest), tag)
    dj_caps = run_flow(Client(dj), tag)

    passed = failed = 0
    for (label, nr), (_, dr) in zip(nest_caps, dj_caps):
        n, d = normalize(nr), normalize(dj_caps and dr)
        if n == d:
            passed += 1
            print(f"  MATCH   [{nr.status:>3}] {label}")
        else:
            failed += 1
            print(f"  MISMATCH      {label}")
            print(f"     NEST  : {json.dumps(n)}")
            print(f"     DJANGO: {json.dumps(d)}")

    print(f"\n=== {passed} matched, {failed} mismatched, {passed + failed} total ===")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
