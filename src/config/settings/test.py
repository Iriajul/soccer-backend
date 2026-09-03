from .base import *  # noqa: F401,F403

# Tests default to development-mode NestJS behavior (static temp passwords,
# console invites, verbose 500 messages) unless a test overrides NODE_ENV.
NODE_ENV = "development"
