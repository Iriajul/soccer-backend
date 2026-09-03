"""
Email helpers — port of `src/mail/mail.service.ts` (nodemailer).

Both functions send via Django's email backend (SMTP in prod; the
development settings use the console backend so local flows never fail).
Send failures raise, so callers can reproduce the NestJS transactional
rollback on a failed invite email.
"""
from django.conf import settings
from django.core.mail import send_mail


def _from_addr():
    return f'"Soccer Club Management" <{settings.EMAIL_HOST_USER}>'


def send_invitation_email(to: str, temp_password: str):
    html = (
        "<h2>Welcome to the Soccer Club Management Platform</h2>"
        "<p>You have been invited to join the staff.</p>"
        f"<p>Your temporary password is: <strong>{temp_password}</strong></p>"
        "<p>Please log in and you will be prompted to reset this password "
        "immediately.</p>"
    )
    send_mail(
        subject="Welcome to the Club!",
        message=f"Your temporary password is: {temp_password}",
        from_email=_from_addr(),
        recipient_list=[to],
        html_message=html,
        fail_silently=False,
    )


def send_password_reset_email(to: str, token: str):
    html = (
        "<h2>Password Reset Request</h2>"
        "<p>You have requested to reset your password.</p>"
        f"<p>Your reset token is: <strong>{token}</strong></p>"
        "<p>This token is valid for 15 minutes.</p>"
    )
    send_mail(
        subject="Reset your Password",
        message=f"Your reset token is: {token}",
        from_email=_from_addr(),
        recipient_list=[to],
        html_message=html,
        fail_silently=False,
    )
