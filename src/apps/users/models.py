"""
User model — port of `src/users/schemas/user.schema.ts`.

External field names (via serializers) stay camelCase to preserve the API
contract: _id, name, email, profileImage, role, clubId, isFirstLogin,
childPlayerIds, parentIds, createdAt, updatedAt. `password` is never exposed.

`childPlayerIds` and `parentIds` are two INDEPENDENT user-id arrays in Mongo
(both written on connection approval), so they are modelled as two separate
non-symmetrical M2M fields rather than one reverse relation.
"""
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.objectid import ObjectIdField
from common.roles import UserRole
from common.hashing import hash_password


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.password = hash_password(password) if password else ""
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", UserRole.SUPER_ADMIN)
        extra.setdefault("name", "System Admin")
        extra.setdefault("is_first_login", False)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser):
    id = ObjectIdField(primary_key=True)

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    # Nullable; the serializer always emits the key as null when unset.
    profile_image = models.CharField(max_length=1024, null=True, blank=True)
    # `password` is inherited from AbstractBaseUser (bcrypt hash, never exposed).
    role = models.CharField(max_length=32, choices=UserRole.choices)

    # Required unless role == SUPER_ADMIN — enforced in the service/serializer,
    # mirroring the conditional `required` in the Mongoose schema.
    club_id = models.ForeignKey(
        "clubs.Club",
        null=True,
        blank=True,
        # COMPATIBILITY: Mongo has no FK constraints and no cascade. Deleting a
        # club must NOT error or cascade — references are allowed to dangle.
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="members",
        db_column="club_id",
    )

    is_first_login = models.BooleanField(default=True)

    # Stored as plain id-string arrays (like Mongo), not M2M — the connection
    # flow guarantees existence, but arrays mirror the source shape and allow
    # the same "no existence check / dangling" semantics.
    child_player_ids = ArrayField(
        models.CharField(max_length=24), default=list, blank=True
    )
    parent_ids = ArrayField(
        models.CharField(max_length=24), default=list, blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name} <{self.email}> ({self.role})"
