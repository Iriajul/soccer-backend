"""Contract tests for /clubs."""
from rest_framework.test import APITestCase

from apps.clubs.models import Club
from apps.users.models import User
from common.roles import UserRole


class ClubsContractTests(APITestCase):
    def setUp(self):
        self.club = Club.objects.create(name="FC Test")
        self.sa = User.objects.create_user(
            email="sa@test.com", password="Admin123!", name="SA",
            role=UserRole.SUPER_ADMIN, is_first_login=False,
        )
        self.owner = User.objects.create_user(
            email="owner@test.com", password="OwnerPass1!", name="Owner",
            role=UserRole.CLUB_OWNER, club_id=self.club, is_first_login=False,
        )

    def _bearer(self, email, password):
        tok = self.client.post("/auth/login", {"email": email, "password": password}, format="json").json()["access_token"]
        return f"Bearer {tok}"

    def test_create_club_transactional_201(self):
        r = self.client.post(
            "/clubs", {"name": "New FC", "ownerName": "Boss", "ownerEmail": "boss@fc.com"},
            format="json", HTTP_AUTHORIZATION=self._bearer("sa@test.com", "Admin123!"),
        )
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["message"], "Club and Club Owner created successfully")
        self.assertIn("__v", body["club"])
        self.assertTrue(User.objects.filter(email="boss@fc.com", role=UserRole.CLUB_OWNER).exists())

    def test_create_club_duplicate_owner_rolls_back_500(self):
        # Owner email already exists → invite 409 → surfaced as the club 500,
        # and the club must NOT persist (rollback).
        before = Club.objects.count()
        r = self.client.post(
            "/clubs", {"name": "Dup FC", "ownerName": "X", "ownerEmail": "owner@test.com"},
            format="json", HTTP_AUTHORIZATION=self._bearer("sa@test.com", "Admin123!"),
        )
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["message"], "Failed to create club and owner. Transaction rolled back.")
        self.assertEqual(Club.objects.count(), before)  # rolled back

    def test_create_club_requires_super_admin_403(self):
        r = self.client.post(
            "/clubs", {"name": "X", "ownerName": "Y", "ownerEmail": "y@z.com"},
            format="json", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"),
        )
        self.assertEqual(r.status_code, 403)

    def test_my_club_super_admin_400(self):
        r = self.client.get("/clubs/my-club", HTTP_AUTHORIZATION=self._bearer("sa@test.com", "Admin123!"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["message"], "Your account is not assigned to any club.")

    def test_my_club_owner_ok_no_version(self):
        r = self.client.get("/clubs/my-club", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["_id"], self.club.id)
        self.assertNotIn("__v", body)

    def test_detail_cross_club_forbidden(self):
        other = Club.objects.create(name="Other FC")
        r = self.client.get(f"/clubs/{other.id}", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["message"], "You do not have permission to view this club.")

    def test_detail_owner_shape_includes_created(self):
        r = self.client.get(f"/clubs/{self.club.id}", HTTP_AUTHORIZATION=self._bearer("owner@test.com", "OwnerPass1!"))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("totalMembers", body)
        self.assertIn("createdAt", body["owner"])   # detail owner includes createdAt
        self.assertEqual(body["owner"]["isDefaultPassword"], self.owner.is_first_login)
