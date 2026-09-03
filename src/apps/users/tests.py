"""Contract tests for the /users endpoints (parity with the NestJS API)."""
from rest_framework.test import APITestCase

from apps.clubs.models import Club
from apps.users.models import User
from common.roles import UserRole


class UsersContractTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="FC Test")
        self.super_admin = User.objects.create_user(
            email="sa@test.com", password="Admin123!", name="SA",
            role=UserRole.SUPER_ADMIN, is_first_login=False,
        )
        self.owner = User.objects.create_user(
            email="owner@test.com", password="OwnerPass1!", name="Owner",
            role=UserRole.CLUB_OWNER, club_id=self.club, is_first_login=False,
        )
        self.coach = User.objects.create_user(
            email="coach@test.com", password="CoachPass1!", name="Coach",
            role=UserRole.COACH, club_id=self.club, is_first_login=False,
        )
        self.player = User.objects.create_user(
            email="player@test.com", password="PlayerPass1!", name="Player",
            role=UserRole.PLAYER, club_id=self.club, is_first_login=False,
        )

    def _bearer(self, email, password):
        tok = self.client.post("/auth/login", {"email": email, "password": password}, format="json").json()["access_token"]
        return f"Bearer {tok}"

    # ── invite ────────────────────────────────────────────────────────────────
    def test_invite_success_201(self):
        r = self.client.post(
            "/users/invite",
            {"name": "New Coach", "email": "nc@test.com", "role": "COACH"},
            format="json", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["message"], "Invitation sent successfully")
        self.assertIn("userId", body)
        created = User.objects.get(email="nc@test.com")
        self.assertTrue(created.is_first_login)
        self.assertEqual(created.club_id_id, self.club.id)  # inherited owner's club

    def test_invite_duplicate_email_409(self):
        r = self.client.post(
            "/users/invite",
            {"name": "Dup", "email": "coach@test.com", "role": "PLAYER"},
            format="json", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json(), {"statusCode": 409, "message": "User with this email already exists", "error": "Conflict"})

    def test_invite_hierarchy_forbidden_403(self):
        # A COACH (60) cannot invite another COACH (60) — not strictly greater.
        r = self.client.post(
            "/users/invite",
            {"name": "X", "email": "x@test.com", "role": "COACH"},
            format="json", HTTP_AUTHORIZATION=self._bearer("coach@test.com", "CoachPass1!"),
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["message"], "You do not have permission to create a user with the role: COACH")

    # ── /users/me ─────────────────────────────────────────────────────────────
    def test_me_shape_populated_club_and_context(self):
        r = self.client.get("/users/me", HTTP_AUTHORIZATION=self._bearer("coach@test.com", "CoachPass1!"))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["_id"], self.coach.id)             # _id here (not id)
        self.assertEqual(body["clubId"], {"_id": self.club.id, "name": self.club.name})  # populated
        self.assertIn("context", body)
        self.assertNotIn("__v", body)                             # excluded on /users/me
        self.assertIn("childPlayerIds", body)
        self.assertIn("parentIds", body)

    def test_me_requires_auth_401(self):
        r = self.client.get("/users/me")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), {"statusCode": 401, "message": "Unauthorized", "error": "Unauthorized"})

    # ── role update ────────────────────────────────────────────────────────────
    def test_update_role_missing_user_409_not_404(self):
        # COMPATIBILITY: NestJS returns 409, not 404, for a missing user here.
        r = self.client.patch(
            "/users/64f000000000000000000000/role",
            {"role": "PLAYER"}, format="json",
            HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json(), {"statusCode": 409, "message": "User not found", "error": "Conflict"})

    def test_update_role_success(self):
        r = self.client.patch(
            f"/users/{self.player.id}/role",
            {"role": "PARENT"}, format="json",
            HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["message"], "Role updated successfully")
        self.assertEqual(body["user"], {"id": self.player.id, "name": self.player.name, "newRole": "PARENT"})

    # ── list ─────────────────────────────────────────────────────────────────
    def test_list_shape_and_meta(self):
        r = self.client.get("/users", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(set(body.keys()), {"data", "meta"})
        self.assertEqual(set(body["meta"].keys()), {"total", "page", "lastPage"})
        self.assertIsInstance(body["data"], list)
        if body["data"]:
            self.assertIn("__v", body["data"][0])   # list items include __v

    def test_list_subordinate_role_filter_empty_page(self):
        # A COACH asking for CLUB_OWNER (higher) gets an empty page, not 403.
        r = self.client.get("/users?role=CLUB_OWNER", HTTP_AUTHORIZATION=self._bearer("coach@test.com", "CoachPass1!"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"data": [], "meta": {"total": 0, "page": 1, "lastPage": 0}})
