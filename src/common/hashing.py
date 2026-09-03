"""
Password hashing/verification with NestJS bcrypt compatibility.

The existing users have raw bcrypt hashes (`bcrypt.hash(pw, 10)` → "$2b$10$...").
Django's password machinery identifies a hasher from an "<algorithm>$..."
prefix, so a migrated raw hash must be stored as "bcrypt$$2b$10$..." for
Django's BCryptPasswordHasher to verify it. `normalize_mongo_hash` does that
prefixing; it is used only by the one-time data migration.

New/changed passwords are hashed with Django's bcrypt hasher. The stored
format is internal and never exposed over the API.
"""
from django.contrib.auth.hashers import make_password, check_password

_BCRYPT_PREFIX = "bcrypt$"


def hash_password(raw: str) -> str:
    """Hash a new/changed password with bcrypt (Django-stored format)."""
    return make_password(raw, hasher="bcrypt")


def verify_password(raw: str, stored: str) -> bool:
    return check_password(raw, stored)


def normalize_mongo_hash(raw_hash: str) -> str:
    """Turn a raw NestJS bcrypt hash into Django's stored bcrypt format."""
    if not raw_hash:
        return raw_hash
    if raw_hash.startswith(_BCRYPT_PREFIX):
        return raw_hash
    return _BCRYPT_PREFIX + raw_hash
