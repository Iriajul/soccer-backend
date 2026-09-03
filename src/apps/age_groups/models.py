"""AgeGroup model — port of `src/age-groups/schemas/age-group.schema.ts`."""
from django.db import models

from common.objectid import ObjectIdField


class AgeGroup(models.Model):
    id = ObjectIdField(primary_key=True)

    name = models.CharField(max_length=255)  # e.g. "U-12"
    description = models.CharField(max_length=1024, null=True, blank=True)

    club_id = models.ForeignKey(
        "clubs.Club",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="age_groups",
        db_column="club_id",
    )
    # Assigned COORDINATOR (optional).
    coordinator_id = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="+",
        db_column="coordinator_id",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "age_groups"

    def __str__(self):
        return self.name
