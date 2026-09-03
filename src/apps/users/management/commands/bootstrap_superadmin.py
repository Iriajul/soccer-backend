"""
Create the initial SUPER_ADMIN if none exists — the Django equivalent of the
NestJS `UsersService.onModuleInit`. Run it after migrate (e.g. from the
container entrypoint) so a fresh deployment has a super admin.
"""
from django.core.management.base import BaseCommand

from apps.users import services


class Command(BaseCommand):
    help = "Bootstrap the initial SUPER_ADMIN (mirrors NestJS onModuleInit)."

    def handle(self, *args, **options):
        user = services.bootstrap_super_admin()
        if user is None:
            self.stdout.write("A SUPER_ADMIN already exists; nothing to do.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Created SUPER_ADMIN {user.email}"))
