"""
Mongo-style ObjectId support for a PostgreSQL-backed port.

CONTRACT: every record's primary key is a 24-character hexadecimal string,
exposed to clients as `_id` — exactly like the original Mongo/Mongoose API.
Existing production IDs are preserved verbatim during the data migration;
new records get a freshly generated, real-format ObjectId so clients cannot
tell the difference.

We generate ObjectIds in pure Python (4-byte timestamp + 5-byte random +
3-byte counter, the MongoDB 3.4+ layout) so runtime ID creation has no
dependency on pymongo/bson. `pymongo` is only used by the one-time migration.
"""
import os
import struct
import time
import threading

from django.db import models

_OBJECTID_HEX = 24
_counter_lock = threading.Lock()
_counter = int.from_bytes(os.urandom(3), "big")
# 5 random bytes fixed per process (Mongo spec).
_process_random = os.urandom(5)


def generate_object_id() -> str:
    """Return a new 24-char hex ObjectId string (Mongo-compatible layout)."""
    global _counter
    ts = struct.pack(">I", int(time.time()))  # 4 bytes, big-endian seconds
    with _counter_lock:
        _counter = (_counter + 1) % 0xFFFFFF
        counter = _counter
    counter_bytes = struct.pack(">I", counter)[1:]  # low 3 bytes
    return (ts + _process_random + counter_bytes).hex()


def is_object_id(value) -> bool:
    """True if `value` is a well-formed 24-char hex string (a valid ObjectId)."""
    if not isinstance(value, str) or len(value) != _OBJECTID_HEX:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


class ObjectIdField(models.CharField):
    """
    A CharField primary key holding a 24-hex ObjectId string.

    Usage on every model:
        id = ObjectIdField(primary_key=True)

    The DB column name stays `id`, but serializers expose it as `_id` to
    preserve the external contract.
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = _OBJECTID_HEX
        kwargs.setdefault("default", generate_object_id)
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("max_length", None)
        return name, path, args, kwargs
