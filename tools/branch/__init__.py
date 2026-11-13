"""分點進出 (broker-branch trading) tools backed by a PostgreSQL database.

These tools read the database described by ``branch_trades_schema.sql`` — see
``utils/neon_db.py`` for the connection and safety rules, and ``utils/branch_query.py``
for the shared lookups. They are the only tools in this server that read from a
database rather than a public API, so they are also the only ones whose data depends
on the user's own import pipeline having run.

Volumes are stored in shares (股) and always rendered in lots (張) — see
``utils/branch_format.py``.
"""
