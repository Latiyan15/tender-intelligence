def __getattr__(name):
    if name in ("TenderRepository", "init_db", "get_connection"):
        from src.database.db import TenderRepository, init_db, get_connection
        return {"TenderRepository": TenderRepository, "init_db": init_db, "get_connection": get_connection}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["TenderRepository", "init_db", "get_connection"]
