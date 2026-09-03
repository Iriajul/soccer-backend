"""DashboardService — port of `src/dashboard/dashboard.service.ts`."""
from django.db.models import Count

from apps.users.models import User
from apps.clubs.models import Club
from apps.teams.models import Team


def get_super_admin_stats():
    total_clubs = Club.objects.count()
    total_teams = Team.objects.count()

    # Group users by role (only roles that actually occur appear — matches the
    # Mongo aggregation, which yields no key for absent roles).
    role_breakdown = {}
    total_users = 0
    for row in User.objects.values("role").annotate(count=Count("id")):
        role_breakdown[row["role"]] = row["count"]
        total_users += row["count"]

    return {
        "overview": {
            "totalClubs": total_clubs,
            "totalTeams": total_teams,
            "totalUsers": total_users,
        },
        "roleBreakdown": role_breakdown,
    }
