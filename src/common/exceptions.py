"""
NestJS-compatible error layer.

The NestJS `AllExceptionsFilter` produces TWO different error body shapes,
and this module reproduces both exactly:

1. Thrown `HttpException` (4xx and the club-create 500) →
       {"statusCode", "message", "error"}
   with `message` a STRING, or an ARRAY of strings for validation failures.
   A custom object payload (e.g. the first-login 403) is returned AS-IS.

2. Unhandled runtime error (e.g. a Mongoose CastError from a malformed
   ObjectId path param, or a Mongo duplicate-key error) →
       {"statusCode", "timestamp", "path", "message"}
   with NO `error` key; `message` is "Internal server error" in production
   and the real message in development.

DO NOT replace these with DRF's default {"detail": ...}.
"""
from datetime import datetime, timezone

from django.conf import settings
from rest_framework import status as http_status
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
    NotAuthenticated,
    AuthenticationFailed,
)
from rest_framework.response import Response


_REASON = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    500: "Internal Server Error",
}


class NestHttpException(Exception):
    """
    Mirrors a NestJS HttpException.

    - message as a string  → body {statusCode, message, error}
    - message as a list    → body {statusCode, message:[...], error}  (validation)
    - message as a dict    → body is that dict verbatim (custom payload,
      e.g. the first-login 403 {message, requiresPasswordReset, resetToken})
    """

    def __init__(self, status_code: int, message):
        self.status_code = status_code
        if isinstance(message, dict):
            self.payload = message
        else:
            self.payload = {
                "statusCode": status_code,
                "message": message,
                "error": _REASON.get(status_code, "Error"),
            }
        super().__init__(str(message))


class BadRequest(NestHttpException):
    def __init__(self, message):
        super().__init__(400, message)


class Unauthorized(NestHttpException):
    def __init__(self, message="Unauthorized"):
        super().__init__(401, message)


class Forbidden(NestHttpException):
    def __init__(self, message):
        super().__init__(403, message)


class NotFound(NestHttpException):
    def __init__(self, message):
        super().__init__(404, message)


class Conflict(NestHttpException):
    def __init__(self, message):
        super().__init__(409, message)


class InternalServerError(NestHttpException):
    """A *thrown* 500 → keeps the `error` key (e.g. the club-create rollback)."""

    def __init__(self, message):
        super().__init__(500, message)


class CastError500(Exception):
    """
    Reproduces a Mongoose CastError reaching the generic filter branch:
    a malformed ObjectId path param → 500 with the timestamp/path body shape.
    Raise via `common.objectid` guards on the unguarded routes documented in
    PROJECT_DOCUMENTATION.md (DELETE /teams/:id, PATCH /teams/:id/roster,
    GET /events/team/:teamId).
    """

    def __init__(self, value):
        self.value = value
        super().__init__(f"Cast to ObjectId failed for value {value!r}")


def _iso_millis_z() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _unhandled_500_body(context, message_dev: str):
    request = context.get("request") if context else None
    is_dev = getattr(settings, "NODE_ENV", "development") == "development"
    path = request.get_full_path() if request is not None else ""
    body = {
        "statusCode": 500,
        "timestamp": _iso_millis_z(),
        "path": path,
        "message": message_dev if is_dev else "Internal server error",
    }
    return body


def _validation_messages(detail):
    """Flatten DRF serializer errors into a flat array of strings."""
    messages = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
        else:
            messages.append(str(node))

    walk(detail)
    return messages


def nest_exception_handler(exc, context):
    # 1. Our explicit NestJS-style exceptions.
    if isinstance(exc, NestHttpException):
        return Response(exc.payload, status=exc.status_code)

    # 2. Malformed-ObjectId → 500 with the timestamp/path body (no `error`).
    if isinstance(exc, CastError500):
        return Response(_unhandled_500_body(context, str(exc)), status=500)

    # 3. Validation errors → 400 {statusCode, message:[...], error:'Bad Request'}.
    if isinstance(exc, DRFValidationError):
        return Response(
            {
                "statusCode": 400,
                "message": _validation_messages(exc.detail),
                "error": "Bad Request",
            },
            status=400,
        )

    # 4. Missing/invalid auth → 401 {statusCode, message:'Unauthorized', error}.
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return Response(
            {"statusCode": 401, "message": "Unauthorized", "error": "Unauthorized"},
            status=401,
        )

    # 5. Any other DRF APIException → map to the {statusCode, message, error} shape.
    if isinstance(exc, APIException):
        code = exc.status_code
        detail = exc.detail
        message = detail if isinstance(detail, str) else _validation_messages(detail)
        return Response(
            {
                "statusCode": code,
                "message": message,
                "error": _REASON.get(code, "Error"),
            },
            status=code,
        )

    # 6. Anything else is an unhandled runtime error → generic 500 body shape.
    return Response(
        _unhandled_500_body(context, str(exc) or "Internal server error"),
        status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
