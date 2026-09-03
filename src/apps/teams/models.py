"""Team model — port of `src/teams/schemas/team.schema.ts`."""
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.objectid import ObjectIdField


class Team(models.Model):
    id = ObjectIdField(primary_key=True)

    name = models.CharField(max_length=255)  # e.g. "U-12 Boys Elite"

    club_id = models.ForeignKey(
        "clubs.Club",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="teams",
        db_column="club_id",
    )
    age_group_id = models.ForeignKey(
        "age_groups.AgeGroup",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="teams",
        db_column="age_group_id",
    )
    coach_id = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="+",
        db_column="coach_id",
    )
    # PLAYERs on the roster — a plain id-string array (like Mongo), so a
    # well-formed-but-nonexistent playerId can be added with no existence check.
    roster = ArrayField(models.CharField(max_length=24), default=list, blank=True)

    # Mirrors Mongoose's __v version key. It increments on each roster save()
    # (the only place a Team is re-saved with an array mutation), reproducing
    # the __v the clients see. Exposed as "__v" in responses.
    version = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams"

    def __str__(self):
        return self.name
