"""ConnectionsService — port of `src/connections/connections.service.ts`."""
from django.utils import timezone

from apps.users.models import User
from apps.teams.models import Team
from apps.performance.models import Performance
from apps.events.models import Event
from apps.events.serializers import event_raw_dict
from apps.performance.serializers import performance_doc_dict
from common.roles import UserRole
from common.tenancy import cast_object_id_or_500
from common.exceptions import NotFound, Forbidden, Conflict
from .models import ConnectionRequest, ConnectionStatus
from .serializers import connection_raw_dict, connection_populated_dict


def create_request(dto, requester):
    parent = User.objects.filter(id=dto["parentId"]).first()
    child = User.objects.filter(id=dto["childId"]).first()

    if not parent or parent.role != UserRole.PARENT:
        raise NotFound("Parent not found or invalid role.")
    if not child or child.role != UserRole.PLAYER:
        raise NotFound("Child not found or invalid role.")

    if (
        str(parent.club_id_id) != str(child.club_id_id)
        or str(parent.club_id_id) != str(requester.club_id)
    ):
        raise Forbidden("Cannot link users from different clubs.")

    existing = ConnectionRequest.objects.filter(
        parent_id_id=parent.id, child_id_id=child.id
    ).first()
    if existing and existing.status != ConnectionStatus.REJECTED:
        raise Conflict("A connection request already exists between these users.")

    if requester.role == UserRole.PARENT:
        if str(requester.user_id) != str(parent.id):
            raise Forbidden("You cannot make a request for another parent.")
        status = ConnectionStatus.WAITING_ON_CHILD
    elif requester.role == UserRole.PLAYER:
        if str(requester.user_id) != str(child.id):
            raise Forbidden("You cannot make a request for another player.")
        status = ConnectionStatus.WAITING_ON_PARENT
    else:
        status = ConnectionStatus.PENDING

    req = ConnectionRequest(
        requester_id_id=requester.user_id,
        parent_id_id=parent.id,
        child_id_id=child.id,
        club_id_id=parent.club_id_id,
        status=status,
    )
    req.save()
    return connection_raw_dict(req)


def get_pending_requests(requester):
    active = [
        ConnectionStatus.PENDING,
        ConnectionStatus.WAITING_ON_PARENT,
        ConnectionStatus.WAITING_ON_CHILD,
    ]
    if requester.role == UserRole.PARENT:
        qs = ConnectionRequest.objects.filter(
            parent_id_id=requester.user_id, status__in=active
        ).filter(status__in=[ConnectionStatus.WAITING_ON_PARENT, ConnectionStatus.PENDING])
    elif requester.role == UserRole.PLAYER:
        qs = ConnectionRequest.objects.filter(
            child_id_id=requester.user_id, status__in=active
        ).filter(status__in=[ConnectionStatus.WAITING_ON_CHILD, ConnectionStatus.PENDING])
    else:
        # COMPATIBILITY: Preserve NestJS production behavior — staff ALWAYS get
        # an empty list here. The source queries
        # `find({clubId: ObjectId(requester.clubId), ...})`, but ConnectionRequest
        # (and User) store clubId as a plain STRING, so the ObjectId match never
        # succeeds. Reproduced narrowly for byte-parity; do NOT restore the real
        # club query without a coordinated client change. See
        # docs/POST_MIGRATION_CLEANUP.md (item 3).
        return []
    return [connection_populated_dict(r) for r in qs]


def process_request(request_id, action, requester):
    cast_object_id_or_500(request_id)
    req = ConnectionRequest.objects.filter(id=request_id).first()
    if not req:
        raise NotFound("Request not found.")

    if str(req.club_id_id) != str(requester.club_id):
        raise Forbidden("Unauthorized.")

    if action == "reject":
        req.status = ConnectionStatus.REJECTED
        req.save(update_fields=["status", "updated_at"])
        return connection_raw_dict(req)

    if requester.role == UserRole.PARENT:
        if str(req.parent_id_id) != str(requester.user_id):
            raise Forbidden("Unauthorized.")
        if req.status == ConnectionStatus.WAITING_ON_PARENT:
            req.status = ConnectionStatus.APPROVED
        elif req.status == ConnectionStatus.PENDING:
            req.status = ConnectionStatus.WAITING_ON_CHILD
    elif requester.role == UserRole.PLAYER:
        if str(req.child_id_id) != str(requester.user_id):
            raise Forbidden("Unauthorized.")
        if req.status == ConnectionStatus.WAITING_ON_CHILD:
            req.status = ConnectionStatus.APPROVED
        elif req.status == ConnectionStatus.PENDING:
            req.status = ConnectionStatus.WAITING_ON_PARENT
    else:
        raise Forbidden("Only the parent or child can approve a connection request.")

    if req.status == ConnectionStatus.APPROVED:
        _add_to_set(req.parent_id_id, "child_player_ids", req.child_id_id)
        _add_to_set(req.child_id_id, "parent_ids", req.parent_id_id)

    req.save(update_fields=["status", "updated_at"])
    return connection_raw_dict(req)


def _add_to_set(user_id, field, value):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return
    arr = list(getattr(user, field) or [])
    if value not in arr:
        arr.append(value)
        setattr(user, field, arr)
        user.save(update_fields=[field, "updated_at"])


def get_my_children(requester):
    if requester.role != UserRole.PARENT:
        raise Forbidden("Only parents can access this endpoint.")
    parent = User.objects.filter(id=requester.user_id).first()
    if not parent:
        raise NotFound("Parent not found.")

    child_ids = list(parent.child_player_ids or [])
    users = {u.id: u for u in User.objects.filter(id__in=child_ids)}
    now = timezone.now()

    out = []
    for cid in child_ids:
        child = users.get(cid)
        if not child:
            continue
        team = Team.objects.filter(roster__contains=[cid]).first()
        perf = Performance.objects.filter(player_id_id=cid).first()
        schedules = []
        if team:
            evs = Event.objects.filter(team_id_id=team.id, date__gte=now).order_by("date")
            schedules = [event_raw_dict(e) for e in evs]
        out.append({
            "player": {
                "_id": child.id, "name": child.name, "email": child.email,
                "profileImage": child.profile_image or None,
            },
            "team": {"id": team.id, "name": team.name} if team else None,
            "performance": performance_doc_dict(perf) if perf else {
                "passing": 0, "dribbling": 0, "shooting": 0, "defense": 0, "stamina": 0
            },
            "upcomingSchedules": schedules,
        })
    return out


def get_my_parents(requester):
    if requester.role != UserRole.PLAYER:
        raise Forbidden("Only players can access this endpoint.")
    player = User.objects.filter(id=requester.user_id).first()
    if not player:
        raise NotFound("Player not found.")

    parent_ids = list(player.parent_ids or [])
    users = {u.id: u for u in User.objects.filter(id__in=parent_ids)}
    result = []
    for pid in parent_ids:
        u = users.get(pid)
        if not u:
            continue
        result.append({
            "_id": u.id, "name": u.name, "email": u.email,
            "profileImage": u.profile_image or None,
        })
    return result
