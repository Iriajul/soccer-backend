"""Contract tests for the /auth endpoints (parity with the NestJS API)."""
from rest_framework.test import APITestCase

from apps.clubs.models import Club
from apps.users.models import User
from common.roles import UserRole


class AuthContractTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="FC Test")
        self.coach = User.objects.create_user(
            email="coach@test.com", password="CoachPass1!", name="Coach Dan",
            role=UserRole.COACH, club_id=self.club, is_first_login=False,
        )
        self.newbie = User.objects.create_user(
            email="new@test.com", password="DevPass123!", name="New Guy",
            role=UserRole.COACH, club_id=self.club, is_first_login=True,
        )

    # ── login ──────────────────────────────────────────────────────────────
    def test_login_success_shape(self):
        r = self.client.post("/auth/login", {"email": "coach@test.com", "password": "CoachPass1!"}, format="json")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(set(body.keys()), {"access_token", "refresh_token", "user"})
        user = body["user"]
        self.assertEqual(set(user.keys()), {"id", "name", "email", "role", "profileImage", "clubId"})
        self.assertEqual(user["id"], self.coach.id)          # key is `id`, not `_id`
        self.assertEqual(user["clubId"], self.club.id)        # raw string on login
        self.assertIsNone(user["profileImage"])

    def test_login_first_login_403_custom_body(self):
        r = self.client.post("/auth/login", {"email": "new@test.com", "password": "DevPass123!"}, format="json")
        self.assertEqual(r.status_code, 403)
        body = r.json()
        self.assertEqual(body["message"], "Password reset required on first login")
        self.assertTrue(body["requiresPasswordReset"])
        self.assertIn("resetToken", body)
        # Custom body has NO statusCode/error keys.
        self.assertNotIn("statusCode", body)
        self.assertNotIn("error", body)

    def test_login_wrong_password_401(self):
        r = self.client.post("/auth/login", {"email": "coach@test.com", "password": "nope"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), {"statusCode": 401, "message": "Invalid credentials", "error": "Unauthorized"})

    def test_login_unknown_email_same_401(self):
        r = self.client.post("/auth/login", {"email": "ghost@test.com", "password": "whatever"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["message"], "Invalid credentials")

    def test_login_validation_array_message(self):
        r = self.client.post("/auth/login", {"email": "notanemail", "password": ""}, format="json")
        self.assertEqual(r.status_code, 400)
        body = r.json()
        self.assertEqual(body["error"], "Bad Request")
        self.assertIsInstance(body["message"], list)

    # ── first-login-reset ────────────────────────────────────────────────────
    def test_first_login_reset_flow(self):
        login = self.client.post("/auth/login", {"email": "new@test.com", "password": "DevPass123!"}, format="json").json()
        token = login["resetToken"]
        r = self.client.post("/auth/first-login-reset", {"resetToken": token, "newPassword": "BrandNew1!"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access_token", r.json())
        # Now a normal login with the new password works.
        r2 = self.client.post("/auth/login", {"email": "new@test.com", "password": "BrandNew1!"}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("access_token", r2.json())

    def test_first_login_reset_invalid_token_401(self):
        r = self.client.post("/auth/first-login-reset", {"resetToken": "garbage", "newPassword": "x"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["message"], "Invalid or expired reset token")

    # ── refresh ────────────────────────────────────────────────────────────
    def test_refresh_populates_club(self):
        login = self.client.post("/auth/login", {"email": "coach@test.com", "password": "CoachPass1!"}, format="json").json()
        r = self.client.post("/auth/refresh", {"refreshToken": login["refresh_token"]}, format="json")
        self.assertEqual(r.status_code, 200)
        club = r.json()["user"]["clubId"]
        self.assertEqual(club, {"_id": self.club.id, "name": self.club.name})  # populated on refresh

    def test_refresh_invalid_401(self):
        r = self.client.post("/auth/refresh", {"refreshToken": "bad"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["message"], "Invalid or expired refresh token")

    # ── forgot / reset ───────────────────────────────────────────────────────
    def test_forgot_password_generic_for_both(self):
        msg = {"message": "If the email is registered, a reset code has been sent"}
        self.assertEqual(self.client.post("/auth/forgot-password", {"email": "coach@test.com"}, format="json").json(), msg)
        self.assertEqual(self.client.post("/auth/forgot-password", {"email": "ghost@test.com"}, format="json").json(), msg)

    def test_reset_password_wrong_token_type_401(self):
        # COMPATIBILITY: source swallows the 400 into this 401.
        r = self.client.post("/auth/reset-password", {"token": "bad", "newPassword": "x"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["message"], "Invalid or expired reset token")

    # ── change-password ───────────────────────────────────────────────────────
    def _bearer(self, email, password):
        tok = self.client.post("/auth/login", {"email": email, "password": password}, format="json").json()["access_token"]
        return f"Bearer {tok}"

    def test_change_password_success(self):
        r = self.client.post(
            "/auth/change-password",
            {"oldPassword": "CoachPass1!", "newPassword": "CoachPass2!"},
            format="json", HTTP_AUTHORIZATION=self._bearer("coach@test.com", "CoachPass1!"),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "Password changed successfully"})

    def test_change_password_wrong_old_400(self):
        r = self.client.post(
            "/auth/change-password",
            {"oldPassword": "WRONG", "newPassword": "x"},
            format="json", HTTP_AUTHORIZATION=self._bearer("coach@test.com", "CoachPass1!"),
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["message"], "Incorrect old password")

    def test_change_password_requires_auth_401(self):
        r = self.client.post("/auth/change-password", {"oldPassword": "a", "newPassword": "b"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), {"statusCode": 401, "message": "Unauthorized", "error": "Unauthorized"})


class RootHelloTests(APITestCase):
    def test_root_hello(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"Hello World!")
