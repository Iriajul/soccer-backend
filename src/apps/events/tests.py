"""Contract tests for /events, /performance, /connections, /dashboard."""
from rest_framework.test import APITestCase

from apps.clubs.models import Club
from apps.users.models import User
from apps.age_groups.models import AgeGroup
from apps.teams.models import Team
from apps.performance.models import Performance
from apps.connections.models import ConnectionRequest, ConnectionStatus
from common.roles import UserRole


class _Base(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="FC Test")
        self.owner = User.objects.create_user(email="owner@t.com", password="p1!", name="Owner", role=UserRole.CLUB_OWNER, club_id=self.club, is_first_login=False)
        self.coach = User.objects.create_user(email="coach@t.com", password="p1!", name="Coach", role=UserRole.COACH, club_id=self.club, is_first_login=False)
        self.other_coach = User.objects.create_user(email="oc@t.com", password="p1!", name="OC", role=UserRole.COACH, club_id=self.club, is_first_login=False)
        self.player = User.objects.create_user(email="player@t.com", password="p1!", name="Player", role=UserRole.PLAYER, club_id=self.club, is_first_login=False)
        self.parent = User.objects.create_user(email="parent@t.com", password="p1!", name="Parent", role=UserRole.PARENT, club_id=self.club, is_first_login=False)
        self.ag = AgeGroup.objects.create(name="U-12", club_id=self.club)
        self.team = Team.objects.create(name="T1", club_id=self.club, age_group_id=self.ag, coach_id=self.coach, roster=[self.player.id])

    def _b(self, email):
        tok = self.client.post("/auth/login", {"email": email, "password": "p1!"}, format="json").json()["access_token"]
        return f"Bearer {tok}"


class EventsTests(_Base):
    def test_create_event_raw_shape(self):
        r = self.client.post("/events", {"title": "Match", "description": "vs X", "date": "2030-01-01T10:00:00.000Z", "teamId": self.team.id}, format="json", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(r.status_code, 201)
        b = r.json()
        self.assertEqual(b["teamId"], self.team.id)
        self.assertEqual(b["createdBy"], self.coach.id)
        self.assertEqual(b["clubId"], self.club.id)
        self.assertEqual(b["date"], "2030-01-01T10:00:00.000Z")
        self.assertIn("__v", b)

    def test_create_event_coach_not_own_team_403(self):
        r = self.client.post("/events", {"title": "M", "description": "d", "date": "2030-01-01T10:00:00.000Z", "teamId": self.team.id}, format="json", HTTP_AUTHORIZATION=self._b("oc@t.com"))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["message"], "You can only create events for your own team.")

    def test_schedule_populated_createdby_and_sorted(self):
        for d in ["2030-03-01T10:00:00.000Z", "2030-01-01T10:00:00.000Z"]:
            self.client.post("/events", {"title": "M", "description": "d", "date": d, "teamId": self.team.id}, format="json", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        r = self.client.get(f"/events/team/{self.team.id}", HTTP_AUTHORIZATION=self._b("player@t.com"))
        self.assertEqual(r.status_code, 200)
        rows = r.json()
        self.assertEqual(rows[0]["date"], "2030-01-01T10:00:00.000Z")  # ascending
        # createdBy is populated via a non-lean query → the User toJSON transform
        # adds profileImage (null when unset), verified against the NestJS oracle.
        self.assertEqual(rows[0]["createdBy"], {"_id": self.coach.id, "name": self.coach.name, "profileImage": None})

    def test_schedule_malformed_team_500(self):
        r = self.client.get("/events/team/not-valid", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("error", r.json())


class PerformanceTests(_Base):
    def test_upsert_and_get(self):
        r = self.client.put(f"/performance/{self.player.id}", {"passing": 80, "dribbling": 85, "shooting": 75, "defense": 70, "stamina": 90}, format="json", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["recordedBy"], self.coach.id)
        g = self.client.get(f"/performance/{self.player.id}", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(g.json()["passing"], 80)

    def test_get_no_record_default_zeros(self):
        p2 = User.objects.create_user(email="p2@t.com", password="p1!", name="P2", role=UserRole.PLAYER, club_id=self.club, is_first_login=False)
        r = self.client.get(f"/performance/{p2.id}", HTTP_AUTHORIZATION=self._b("owner@t.com"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"playerId": p2.id, "passing": 0, "dribbling": 0, "shooting": 0, "defense": 0, "stamina": 0, "recordedBy": None})

    def test_upsert_non_player_400(self):
        r = self.client.put(f"/performance/{self.coach.id}", {"passing": 1, "dribbling": 1, "shooting": 1, "defense": 1, "stamina": 1}, format="json", HTTP_AUTHORIZATION=self._b("owner@t.com"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["message"], "Performance ratings can only be recorded for players.")

    def test_player_views_only_own_403(self):
        r = self.client.get(f"/performance/{self.player.id}", HTTP_AUTHORIZATION=self._b("parent@t.com"))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["message"], "You can only view your children's performance ratings.")

    def test_rating_out_of_range_400_message(self):
        r = self.client.put(f"/performance/{self.player.id}", {"passing": 200, "dribbling": 1, "shooting": 1, "defense": 1, "stamina": 1}, format="json", HTTP_AUTHORIZATION=self._b("owner@t.com"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("passing must not be greater than 100", r.json()["message"])

    def test_team_report_shape(self):
        self.client.put(f"/performance/{self.player.id}", {"passing": 90, "dribbling": 90, "shooting": 90, "defense": 90, "stamina": 90}, format="json", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        r = self.client.get(f"/performance/team/{self.team.id}/report", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(r.status_code, 200)
        b = r.json()
        self.assertEqual(b["teamName"], "T1")
        self.assertEqual(b["average"]["passing"], 90)
        self.assertEqual(b["individualReports"][0]["overallScore"], 90)
        self.assertEqual(len(b["topPerformers"]), 1)


class ConnectionsTests(_Base):
    def test_full_state_machine_and_linking(self):
        # Coach initiates → PENDING (needs both).
        r = self.client.post("/connections/request", {"parentId": self.parent.id, "childId": self.player.id}, format="json", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(r.status_code, 201)
        req_id = r.json()["_id"]
        self.assertEqual(r.json()["status"], "PENDING")
        # Parent approves PENDING → WAITING_ON_CHILD.
        r2 = self.client.patch(f"/connections/{req_id}/approve", HTTP_AUTHORIZATION=self._b("parent@t.com"))
        self.assertEqual(r2.json()["status"], "WAITING_ON_CHILD")
        # Child approves WAITING_ON_CHILD → APPROVED, links written.
        r3 = self.client.patch(f"/connections/{req_id}/approve", HTTP_AUTHORIZATION=self._b("player@t.com"))
        self.assertEqual(r3.json()["status"], "APPROVED")
        self.parent.refresh_from_db(); self.player.refresh_from_db()
        self.assertIn(self.player.id, self.parent.child_player_ids)
        self.assertIn(self.parent.id, self.player.parent_ids)

    def test_duplicate_request_409(self):
        ConnectionRequest.objects.create(requester_id=self.coach, parent_id=self.parent, child_id=self.player, club_id=self.club, status=ConnectionStatus.PENDING)
        r = self.client.post("/connections/request", {"parentId": self.parent.id, "childId": self.player.id}, format="json", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(r.status_code, 409)

    def test_my_children_deep_data(self):
        self.parent.child_player_ids = [self.player.id]; self.parent.save()
        r = self.client.get("/connections/my-children", HTTP_AUTHORIZATION=self._b("parent@t.com"))
        self.assertEqual(r.status_code, 200)
        row = r.json()[0]
        self.assertEqual(row["player"]["_id"], self.player.id)
        self.assertEqual(row["team"], {"id": self.team.id, "name": "T1"})
        self.assertIn("upcomingSchedules", row)

    def test_my_children_requires_parent_403(self):
        r = self.client.get("/connections/my-children", HTTP_AUTHORIZATION=self._b("coach@t.com"))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["message"], "Only parents can access this endpoint.")


class DashboardTests(_Base):
    def test_super_admin_stats(self):
        sa = User.objects.create_user(email="sa@t.com", password="p1!", name="SA", role=UserRole.SUPER_ADMIN, is_first_login=False)
        r = self.client.get("/dashboard/super-admin", HTTP_AUTHORIZATION=self._b("sa@t.com"))
        self.assertEqual(r.status_code, 200)
        b = r.json()
        self.assertEqual(set(b.keys()), {"overview", "roleBreakdown"})
        self.assertEqual(set(b["overview"].keys()), {"totalClubs", "totalTeams", "totalUsers"})
        self.assertEqual(b["overview"]["totalClubs"], 1)
        self.assertEqual(b["roleBreakdown"]["COACH"], 2)

    def test_dashboard_requires_super_admin_403(self):
        r = self.client.get("/dashboard/super-admin", HTTP_AUTHORIZATION=self._b("owner@t.com"))
        self.assertEqual(r.status_code, 403)
