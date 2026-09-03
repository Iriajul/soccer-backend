"""Event model — port of `src/events/schemas/event.schema.ts`."""
from django.db import models

from common.objectid import ObjectIdField


class Event(models.Model):
    id = ObjectIdField(primary_key=True)

    title = models.CharField(max_length=512)
    description = models.TextField()
    date = models.DateTimeField()

    team_id = models.ForeignKey(
        "teams.Team",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="events",
        db_column="team_id",
    )
    # Set server-side from the team's clubId.
    club_id = models.ForeignKey(
        "clubs.Club",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="events",
        db_column="club_id",
    )
    # Set server-side from the requester's JWT.
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="+",
        db_column="created_by",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "events"

    def __str__(self):
        return self.title
