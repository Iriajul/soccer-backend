"""Contract tests for /age-groups and /teams (shared setup)."""
from rest_framework.test import APITestCase

from apps.clubs.models import Club
from apps.users.models import User
from apps.age_groups.models import AgeGroup
from apps.teams.models import Team
from common.roles import UserRole


class _Base(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="FC Test")
        self.owner = User.objects.create_user(
            email="owner@test.com", password="OwnerPass1!", name="Owner",
            role=UserRole.CLUB_OWNER, club_id=self.club, is_first_login=False,
        )
        self.coordinator = User.objects.create_user(
            email="coord@test.com", password="CoordPass1!", name="Coord",
            role=UserRole.COORDINATOR, club_id=self.club, is_first_login=False,
        )
        self.coach = User.objects.create_user(
            email="coach@test.com", password="CoachPass1!", name="Coach",
            role=UserRole.COACH, club_id=self.club, is_first_login=False,
        )
        self.age_group = AgeGroup.objects.create(
            name="U-12", club_id=self.club, coordinator_id=self.coordinator
        )

    def _bearer(self, email, password):
        tok = self.client.post("/auth/login", {"email": email, "password": password}, format="json").json()["access_token"]
        return f"Bearer {tok}"


class AgeGroupsTests(_Base):
    def test_create_duplicate_name_409(self):
        r = self.client.post(
            "/age-groups", {"name": "U-12"}, format="json",
            HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["message"], "An Age Group named 'U-12' already exists in your club.")

    def test_list_joins_teams_and_totalTeams(self):
        Team.objects.create(name="T1", club_id=self.club, age_group_id=self.age_group, coach_id=self.coach)
        r = self.client.get("/age-groups", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"))
        self.assertEqual(r.status_code, 200)
        ag = r.json()[0]
        self.assertEqual(ag["totalTeams"], 1)
        # age-groups findAll uses .lean() (no toJSON transform) → profileImage
        # is ABSENT when unset, verified against the NestJS oracle.
        self.assertEqual(ag["coordinatorId"], {
            "_id": self.coordinator.id, "name": self.coordinator.name,
            "email": self.coordinator.email,
        })
        self.assertEqual(ag["teams"][0]["coachId"], {"_id": self.coach.id, "name": self.coach.name})

    def test_delete_malformed_id_500(self):
        r = self.client.delete("/age-groups/not-an-id", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"))
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("error", r.json())      # 500 body has no `error` key
        self.assertIn("timestamp", r.json())


class TeamsTests(_Base):
    def test_create_returns_raw_unpopulated(self):
        r = self.client.post(
            "/teams", {"name": "U-12 Elite", "ageGroupId": self.age_group.id, "coachId": self.coach.id},
            format="json", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["ageGroupId"], self.age_group.id)   # raw string, not object
        self.assertEqual(body["coachId"], self.coach.id)
        self.assertEqual(body["roster"], [])
        self.assertIn("__v", body)

    def test_create_wrong_club_age_group_404(self):
        r = self.client.post(
            "/teams", {"name": "X", "ageGroupId": "64f000000000000000000000"},
            format="json", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["message"], "Age Group not found in your club.")

    def test_list_populated(self):
        Team.objects.create(name="T1", club_id=self.club, age_group_id=self.age_group, coach_id=self.coach)
        r = self.client.get("/teams", HTTP_AUTHORIZATION=self._bearer("coach@test.com", "CoachPass1!"))
        self.assertEqual(r.status_code, 200)
        t = r.json()[0]
        self.assertEqual(t["ageGroupId"], {"_id": self.age_group.id, "name": "U-12"})
        self.assertEqual(t["coachId"]["email"], self.coach.email)
        self.assertIsInstance(t["clubId"], str)   # clubId stays a raw string

    def test_roster_add_and_remove_typo(self):
        team = Team.objects.create(name="T1", club_id=self.club, age_group_id=self.age_group, coach_id=self.coach)
        player = User.objects.create_user(
            email="p@test.com", password="p", name="P", role=UserRole.PLAYER,
            club_id=self.club, is_first_login=False,
        )
        auth = self._bearer("coach@test.com", "CoachPass1!")
        r = self.client.patch(f"/teams/{team.id}/roster", {"playerId": player.id, "action": "add"}, format="json", HTTP_AUTHORIZATION=auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "Player added successfully", "roster": [player.id]})
        # duplicate add → 409
        r2 = self.client.patch(f"/teams/{team.id}/roster", {"playerId": player.id, "action": "add"}, format="json", HTTP_AUTHORIZATION=auth)
        self.assertEqual(r2.status_code, 409)
        # remove → the misspelled message is PRESERVED
        r3 = self.client.patch(f"/teams/{team.id}/roster", {"playerId": player.id, "action": "remove"}, format="json", HTTP_AUTHORIZATION=auth)
        self.assertEqual(r3.json()["message"], "Player removeed successfully")

    def test_roster_malformed_team_id_500(self):
        r = self.client.patch("/teams/bad-id/roster", {"playerId": "64f000000000000000000000", "action": "add"}, format="json", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"))
        self.assertEqual(r.status_code, 500)

    def test_delete_coordinator_forbidden(self):
        team = Team.objects.create(name="T1", club_id=self.club, age_group_id=self.age_group, coach_id=self.coach)
        r = self.client.delete(f"/teams/{team.id}", HTTP_AUTHORIZATION=self._bearer("coord@test.com", "CoordPass1!"))
        self.assertEqual(r.status_code, 403)  # COORDINATOR not allowed to delete
