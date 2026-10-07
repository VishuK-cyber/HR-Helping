from pymongo import MongoClient

from config import MONGODB_DB, MONGODB_URI

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db = _client[MONGODB_DB]
        ensure_indexes(_db)
    return _db


def ensure_indexes(db) -> None:
    # Used by searchPolicy(). Safe to run repeatedly.
    db.policies.create_index(
        [("title", "text"), ("content", "text"), ("keywords", "text")],
        name="policy_text_index",
    )


def close_db() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
