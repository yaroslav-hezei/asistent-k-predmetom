"""Postgres access: one connection pool per process.

The app opens the pool at startup when DATABASE_URL is set (see app.main). Use it as

    with pool.connection() as conn:
        conn.execute("select ...")

The `with` block commits on success and rolls back on an exception.

On Supabase, DATABASE_URL is the shared pooler in session mode (port 5432): the direct connection
is IPv6 only, and transaction mode (6543) does not support prepared statements.
"""

from psycopg_pool import ConnectionPool

POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 5
CONNECT_TIMEOUT_S = 10


def open_pool(database_url: str) -> ConnectionPool:
    """Open a pool and wait until the first connection works (fails fast on a wrong URL)."""
    pool = ConnectionPool(
        database_url,
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
        kwargs={"connect_timeout": CONNECT_TIMEOUT_S},
        open=False,
    )
    pool.open(wait=True, timeout=CONNECT_TIMEOUT_S)
    return pool
