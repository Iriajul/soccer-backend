from .base import *  # noqa: F401,F403

DEBUG = True
NODE_ENV = "development"

# Locally, "send" mail to the console so forgot-password (which always sends,
# even in dev) never fails for lack of SMTP credentials.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
