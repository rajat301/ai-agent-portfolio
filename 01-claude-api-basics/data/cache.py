# cache.py — SQLite-backed suburb data cache.
#
# Why SQLite? Zero infrastructure. No Redis, no Postgres, no docker containers.
# One file on disk. Python has sqlite3 in the standard library — no pip install.
# Perfect for a local tool where data doesn't change hourly.
#
# Why cache at all? The ABS API is free but slow (5-30s per call).
# ABS RPPI is quarterly data — it never changes between releases.
# Caching with a 90-day TTL means we call the API once per city per quarter.
#
# Cache key: (suburb, state, data_type) — unique per suburb + data category.
# e.g., ("Kangaroo Point", "QLD", "growth_data") → ABS RPPI result for Brisbane

import sqlite3  # standard library — SQLite database driver, no install needed
import json     # standard library — serialize/deserialize Python dicts to JSON strings for storage
from datetime import datetime, timezone, timedelta  # for expiry timestamp arithmetic


class SuburbCache:
    """SQLite-backed key-value cache for suburb property data.

    Stores API responses so we never hit the same endpoint twice for the same suburb
    within the TTL window. Each entry has an expiry timestamp so stale data is ignored.

    Usage:
        cache = SuburbCache()
        data = cache.get("Kangaroo Point", "QLD", "growth_data")
        if data is None:
            data = fetch_from_api()
            cache.set("Kangaroo Point", "QLD", "growth_data", data, ttl_days=90)
    """

    def __init__(self, db_path: str = "data/suburb_cache.db"):
        # db_path: where to create/open the SQLite file.
        # Relative paths are relative to wherever the script is run from.
        # "data/suburb_cache.db" puts it inside the data/ package directory.
        self.db_path = db_path

        # Hit/miss counters — instance variables so stats() can report them.
        # Reset to 0 each time a new SuburbCache object is created.
        self._hits = 0    # incremented each time get() returns cached data
        self._misses = 0  # incremented each time get() returns None (cache miss)

        # Initialise the database — creates the file and table if they don't exist.
        # Safe to call on an existing database — CREATE TABLE IF NOT EXISTS is idempotent.
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        # Create a new connection each time rather than storing one as self._conn.
        # SQLite connections are not thread-safe; a fresh connection per call is safer
        # and cheap — SQLite connections have near-zero overhead for a local file.
        conn = sqlite3.connect(self.db_path)  # opens or creates the .db file at db_path
        conn.row_factory = sqlite3.Row        # makes rows accessible as dicts (row["column"])
        return conn

    def _init_db(self) -> None:
        # Create the cache table if it doesn't already exist.
        # IF NOT EXISTS means this is safe to call on every startup — no data loss.
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suburb_data (
                suburb     TEXT NOT NULL,   -- e.g., "Kangaroo Point"
                state      TEXT NOT NULL,   -- e.g., "QLD"
                data_type  TEXT NOT NULL,   -- e.g., "growth_data" or "demographics"
                value_json TEXT NOT NULL,   -- the full API response serialised as JSON string
                fetched_at TEXT NOT NULL,   -- ISO 8601 UTC timestamp of when we fetched the data
                expires_at TEXT NOT NULL,   -- ISO 8601 UTC timestamp after which data is considered stale
                PRIMARY KEY (suburb, state, data_type)  -- one row per suburb+state+type combo
            )
        """)
        conn.commit()  # write the CREATE TABLE statement to disk
        conn.close()   # release the file lock immediately — don't hold connections open

    def get(self, suburb: str, state: str, data_type: str, max_age_days: int = 30) -> dict | None:
        """Return cached data if it exists and hasn't expired. Return None otherwise.

        Args:
            suburb:      Suburb name, e.g. "Kangaroo Point"
            state:       State code, e.g. "QLD"
            data_type:   Category of data, e.g. "growth_data" or "demographics"
            max_age_days: Additional age check on top of stored expires_at.
                          Use this to force a shorter TTL for a specific call.
                          Defaults to 30 days — set to 0 to always use expires_at.
        Returns:
            Deserialised dict if cache hit, None if miss or expired.
        """
        conn = self._get_connection()

        # Query the row for this specific suburb + state + data_type combination
        row = conn.execute("""
            SELECT value_json, fetched_at, expires_at
            FROM suburb_data
            WHERE suburb = ? AND state = ? AND data_type = ?
        """, (suburb.strip(), state.strip().upper(), data_type)).fetchone()
        # fetchone() returns a sqlite3.Row or None — Row if found, None if no match

        conn.close()  # release file lock

        if row is None:
            # No cache entry at all for this key — definite miss
            self._misses += 1  # track for stats()
            return None

        # Parse the stored expiry timestamp (ISO 8601 UTC string) back to datetime
        expires_at = datetime.fromisoformat(row["expires_at"])  # e.g., "2026-08-14T10:30:00+00:00"

        # Get the current UTC time — must be timezone-aware to compare with stored timestamps
        now = datetime.now(timezone.utc)

        # Check 1: has the stored expires_at timestamp passed?
        if now > expires_at:
            self._misses += 1  # expired data counts as a miss — caller must re-fetch
            return None

        # Check 2: additional max_age_days check (allows callers to enforce shorter TTLs)
        if max_age_days > 0:
            fetched_at = datetime.fromisoformat(row["fetched_at"])  # when data was originally fetched
            age = now - fetched_at  # timedelta representing how old the data is
            if age > timedelta(days=max_age_days):
                self._misses += 1  # older than the caller's max age — treat as miss
                return None

        # Cache hit — data exists and is still fresh
        self._hits += 1  # track for stats()

        # Deserialise the JSON string back into a Python dict
        return json.loads(row["value_json"])

    def set(self, suburb: str, state: str, data_type: str, value_dict: dict, ttl_days: int = 30) -> None:
        """Store data in the cache with an expiry timestamp.

        Args:
            suburb:     Suburb name, e.g. "Kangaroo Point"
            state:      State code, e.g. "QLD"
            data_type:  Category of data, e.g. "growth_data"
            value_dict: The Python dict to cache (will be JSON-serialised)
            ttl_days:   How many days until this entry is considered stale.
                        Use 90 for quarterly ABS data, 30 for monthly benchmarks,
                        7 for anything that changes more frequently.
        """
        now = datetime.now(timezone.utc)  # current UTC time — used for both timestamps

        fetched_at = now.isoformat()                          # when we fetched it (now)
        expires_at = (now + timedelta(days=ttl_days)).isoformat()  # when it should be refreshed

        # Serialise the dict to a JSON string for storage
        # ensure_ascii=False preserves Unicode characters (suburb names, etc.)
        value_json = json.dumps(value_dict, ensure_ascii=False)

        conn = self._get_connection()

        # INSERT OR REPLACE = upsert: overwrites the row if (suburb, state, data_type) already exists.
        # This is safe to call repeatedly — no duplicate rows.
        conn.execute("""
            INSERT OR REPLACE INTO suburb_data
                (suburb, state, data_type, value_json, fetched_at, expires_at)
            VALUES
                (?, ?, ?, ?, ?, ?)
        """, (suburb.strip(), state.strip().upper(), data_type, value_json, fetched_at, expires_at))

        conn.commit()  # write to disk — without commit(), the insert is rolled back on close
        conn.close()   # release file lock

    def is_stale(self, suburb: str, state: str, data_type: str) -> bool:
        """Return True if the cached entry is expired or doesn't exist.

        Useful for checking before deciding whether to show a "cache hit" message.
        """
        # We reuse get() with a very short max_age check to determine staleness.
        # A None return means either missing or expired — both are "stale".
        result = self.get(suburb, state, data_type, max_age_days=0)  # max_age_days=0 skips age check
        return result is None  # True = stale/missing, False = fresh

    def clear_expired(self) -> int:
        """Delete all rows where expires_at is in the past. Returns the count deleted."""
        now = datetime.now(timezone.utc).isoformat()  # current UTC time as ISO string for comparison

        conn = self._get_connection()

        # DELETE rows where expires_at < now (expired entries)
        cursor = conn.execute("""
            DELETE FROM suburb_data
            WHERE expires_at < ?
        """, (now,))

        deleted_count = cursor.rowcount  # number of rows actually deleted
        conn.commit()  # make the deletion permanent
        conn.close()   # release file lock

        return deleted_count  # caller can log how many were cleaned up

    def stats(self) -> dict:
        """Return cache performance statistics.

        Returns a dict with:
            total_entries:   all rows currently in the database (including expired)
            expired_entries: rows whose expires_at has passed
            valid_entries:   entries that are still fresh
            hits:            number of successful cache lookups this session
            misses:          number of cache misses (not found or expired) this session
            hit_rate:        hits / (hits + misses) as a float, 0.0–1.0
        """
        now = datetime.now(timezone.utc).isoformat()  # current UTC time for expiry comparisons

        conn = self._get_connection()

        # Count all rows in the table
        total = conn.execute("SELECT COUNT(*) FROM suburb_data").fetchone()[0]

        # Count rows where the expiry timestamp has already passed
        expired = conn.execute(
            "SELECT COUNT(*) FROM suburb_data WHERE expires_at < ?", (now,)
        ).fetchone()[0]

        conn.close()

        # Calculate hit rate — avoid division by zero when no lookups have been made
        total_lookups = self._hits + self._misses
        hit_rate = self._hits / total_lookups if total_lookups > 0 else 0.0

        return {
            "total_entries":   total,              # includes expired ones not yet cleaned up
            "expired_entries": expired,            # ready to be removed by clear_expired()
            "valid_entries":   total - expired,    # currently usable entries
            "hits":            self._hits,         # successful reads from cache this session
            "misses":          self._misses,       # cache misses (went to API) this session
            "hit_rate":        round(hit_rate, 3), # 0.000–1.000; ideally > 0.8 in production
        }
