"""Shared database connection helper.

Uses a module-level connection pool so serverless functions reuse
connections instead of opening a new one per request.
"""
import os

import psycopg
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ["DATABASE_URL"]

_pool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=5,
    open=False,  # lazy: open on first use
)


def get_conn():
    """Context manager yielding a pooled connection.

    Opens the pool lazily on first use so serverless cold starts don't
    pay the connection cost at import time.
    """
    if _pool.closed:
        _pool.open()
    return _pool.connection()