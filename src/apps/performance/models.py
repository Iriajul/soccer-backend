"""Performance model — port of `src/performance/schemas/performance.schema.ts`."""
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from common.objectid import ObjectIdField


def _rating():
    return models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )


class Performance(models.Model):
    id = ObjectIdField(primary_key=True)

    # One record per player (unique), mirroring the Mongo unique index.
    player_id = models.ForeignKey(
        "users.User",
        unique=True,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="+",
        db_column="player_id",
    )
    club_id = models.ForeignKey(
        "clubs.Club",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="+",
        db_column="club_id",
    )

    passing = _rating()
    dribbling = _rating()
    shooting = _rating()
    defense = _rating()
    stamina = _rating()

    recorded_by = models.ForeignKey(
        "users.User",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="+",
        db_column="recorded_by",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "performance"

    def __str__(self):
        return f"Performance<{self.player_id_id}>"
