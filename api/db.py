from psycopg_pool import ConnectionPool

from . import config

_pool: ConnectionPool | None = None


def database_configured() -> bool:
    return bool(config.DATABASE_URL)


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not config.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not configured")
        _pool = ConnectionPool(
            conninfo=config.DATABASE_URL,
            min_size=1,
            max_size=5,
            kwargs={"connect_timeout": 10},
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
