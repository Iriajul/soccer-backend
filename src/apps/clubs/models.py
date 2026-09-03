"""Club model — port of `src/clubs/schemas/club.schema.ts`."""
from django.db import models

from common.objectid import ObjectIdField


class Club(models.Model):
    id = ObjectIdField(primary_key=True)

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clubs"

    def __str__(self):
        return self.name
