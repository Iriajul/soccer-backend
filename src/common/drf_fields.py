"""Reusable serializer fields matching class-validator semantics."""
from rest_framework import serializers


def mongo_id_field(field_name, required=True):
    """
    A 24-hex ObjectId string field. Mirrors class-validator's @IsMongoId,
    including the "<field> must be a mongodb id" message.
    """
    return serializers.RegexField(
        r"^[0-9a-fA-F]{24}$",
        required=required,
        error_messages={
            "invalid": f"{field_name} must be a mongodb id",
            "blank": f"{field_name} should not be empty",
            "required": f"{field_name} should not be empty",
        },
    )
