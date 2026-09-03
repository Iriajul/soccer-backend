"""ConnectionRequest model — port of `src/connections/schemas/connection.schema.ts`."""
from django.db import models

from common.objectid import ObjectIdField


class ConnectionStatus(models.TextChoices):
    PENDING = "PENDING", "PENDING"
    WAITING_ON_PARENT = "WAITING_ON_PARENT", "WAITING_ON_PARENT"
    WAITING_ON_CHILD = "WAITING_ON_CHILD", "WAITING_ON_CHILD"
    APPROVED = "APPROVED", "APPROVED"
    REJECTED = "REJECTED", "REJECTED"


class ConnectionRequest(models.Model):
    id = ObjectIdField(primary_key=True)

    requester_id = models.ForeignKey(
        "users.User", on_delete=models.DO_NOTHING, db_constraint=False,
        related_name="+", db_column="requester_id",
    )
    parent_id = models.ForeignKey(
        "users.User", on_delete=models.DO_NOTHING, db_constraint=False,
        related_name="+", db_column="parent_id",
    )
    child_id = models.ForeignKey(
        "users.User", on_delete=models.DO_NOTHING, db_constraint=False,
        related_name="+", db_column="child_id",
    )
    club_id = models.ForeignKey(
        "clubs.Club", on_delete=models.DO_NOTHING, db_constraint=False,
        related_name="+", db_column="club_id",
    )

    status = models.CharField(
        max_length=32,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "connection_requests"

    def __str__(self):
        return f"ConnectionRequest<{self.id} {self.status}>"
