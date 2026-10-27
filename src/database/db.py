"""
Unified Database Layer (PostgreSQL & SQLite) for Tender Intelligence.

Supports:
1. Production: Managed PostgreSQL via Render (DATABASE_URL environment variable).
2. Local Development & Testing: Native SQLite with WAL mode, zero config needed.
3. Automatic database initialization and schema migration.
4. Automatic initial data seeding from data/seed_tenders.json when deploying a fresh database.
"""

import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Base project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "nikom_tenders.db")
SEED_PATH = os.path.join(BASE_DIR, "data", "seed_tenders.json")


def get_database_url() -> Optional[str]:
    """Retrieve and normalize DATABASE_URL (handling Render's postgres:// prefix)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def normalize_date_to_iso(date_str: Optional[str]) -> Optional[str]:
    """Parse and convert various Indian portal and ISO date strings into standard ISO 8601 UTC string (YYYY-MM-DDTHH:MM:SSZ)."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    if not date_str:
        return None

    # Common ISO formats
    for iso_fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(date_str, iso_fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    # Indian portal date string formats (e.g. 03-Nov-2026 04:00 PM, 09-November-2026, 29/10/2026, etc.)
    for fmt in (
        "%d-%b-%Y %I:%M:%S %p",
        "%d-%b-%Y %I:%M %p",
        "%d-%b-%Y %H:%M",
        "%d-%B-%Y %I:%M:%S %p",
        "%d-%B-%Y %I:%M %p",
        "%d-%B-%Y %H:%M",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    return date_str


def is_deadline_expired(submission_deadline: Optional[str], now_iso: str) -> bool:
    """Return True if submission deadline is genuinely in the past compared to now_iso."""
    if not submission_deadline:
        return False
    iso_dl = normalize_date_to_iso(submission_deadline)
    if iso_dl:
        clean_dl = iso_dl.rstrip("Z")
        clean_now = str(now_iso).strip().rstrip("Z")
        return clean_dl < clean_now
    return False



class UnifiedCursor:
    """Cursor wrapper that harmonizes SQLite and psycopg2 differences."""

    def __init__(self, raw_cursor, is_pg: bool = False):
        self._cur = raw_cursor
        self.is_pg = is_pg
        self.lastrowid = getattr(raw_cursor, "lastrowid", None)
        self.rowcount = getattr(raw_cursor, "rowcount", -1)

    def execute(self, sql: str, params=None):
        if self.is_pg:
            # Convert SQLite placeholder ? to PostgreSQL placeholder %s
            pg_sql = sql.replace("?", "%s")
            stripped = pg_sql.strip().rstrip(";")
            is_insert = stripped.upper().startswith("INSERT INTO")

            if is_insert and "RETURNING" not in stripped.upper():
                pg_sql = stripped + " RETURNING id;"
                if params is not None:
                    self._cur.execute(pg_sql, tuple(params))
                else:
                    self._cur.execute(pg_sql)
                try:
                    row = self._cur.fetchone()
                    if row:
                        self.lastrowid = row.get("id") if isinstance(row, dict) else row[0]
                except Exception:
                    pass
                self.rowcount = self._cur.rowcount
                return self

            if params is not None:
                self._cur.execute(pg_sql, tuple(params))
            else:
                self._cur.execute(pg_sql)
            self.rowcount = self._cur.rowcount
            return self
        else:
            if params is not None:
                self._cur.execute(sql, tuple(params))
            else:
                self._cur.execute(sql)
            self.lastrowid = self._cur.lastrowid
            self.rowcount = self._cur.rowcount
            return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._cur.close()

    def __iter__(self):
        return iter(self.fetchall())


class UnifiedConnection:
    """Connection wrapper providing a uniform interface for SQLite & PostgreSQL."""

    def __init__(self, raw_conn, is_pg: bool = False):
        self._conn = raw_conn
        self.is_pg = is_pg

    def cursor(self):
        return UnifiedCursor(self._conn.cursor(), is_pg=self.is_pg)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def executescript(self, script: str):
        if self.is_pg:
            with self._conn.cursor() as cur:
                cur.execute(script)
            self._conn.commit()
        else:
            self._conn.executescript(script)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_sqlite_connection(target_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def get_connection(db_path: Optional[str] = None) -> UnifiedConnection:
    """Create or return a connection (PostgreSQL if DATABASE_URL set and default path, else SQLite)."""
    pg_url = get_database_url()
    if pg_url and (db_path is None or db_path == DB_PATH):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(pg_url, cursor_factory=RealDictCursor)
            return UnifiedConnection(conn, is_pg=True)
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL ({e}), falling back to SQLite")

    target_path = db_path or DB_PATH
    raw_sqlite = get_sqlite_connection(target_path)
    return UnifiedConnection(raw_sqlite, is_pg=False)


def seed_db_if_empty(conn: UnifiedConnection):
    """Seed empty database from seed_tenders.json if available."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM tenders")
        row = cur.fetchone()
        cnt = row["cnt"] if row else 0
        if cnt >= 50:
            return

        if not os.path.exists(SEED_PATH):
            logger.info("No seed file found, skipping auto-seed.")
            return

        logger.info(f"Database needs seeding (count={cnt} < 50). Seeding from {SEED_PATH}...")
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            seed_data = json.load(f)

        tenders = seed_data.get("tenders", [])
        matches = seed_data.get("keyword_matches", [])

        matches_by_ref = {}
        for m in matches:
            ref = m.get("tender_id_ref")
            if ref not in matches_by_ref:
                matches_by_ref[ref] = []
            matches_by_ref[ref].append(m)

        tender_cols = [
            "id", "tender_id", "title", "authority", "reference_no", "tender_type",
            "estimated_cost_inr", "emd_inr", "doc_fee_inr", "published_date",
            "submission_deadline", "opening_date", "location", "portal_source",
            "portal_url", "description", "primary_category", "highest_tier",
            "is_qualified", "qualification_reason", "uncertain", "raw_metadata",
            "workflow_status", "is_watchlisted", "user_notes", "assigned_to",
            "status_updated_at", "created_at", "updated_at"
        ]
        placeholders = ", ".join(["?"] * len(tender_cols))
        tender_insert_sql = f"INSERT INTO tenders ({', '.join(tender_cols)}) VALUES ({placeholders})"

        for t in tenders:
            tid = t.get("tender_id")
            if not tid:
                continue
            cur.execute("SELECT id FROM tenders WHERE tender_id = ?", (tid,))
            if cur.fetchone():
                continue
            params = [
                t.get("id"),
                t.get("tender_id"),
                t.get("title", ""),
                t.get("authority", "Unknown Authority"),
                t.get("reference_no", ""),
                t.get("tender_type", ""),
                t.get("estimated_cost_inr"),
                t.get("emd_inr"),
                t.get("doc_fee_inr"),
                normalize_date_to_iso(t.get("published_date")),
                normalize_date_to_iso(t.get("submission_deadline")),
                normalize_date_to_iso(t.get("opening_date")),
                t.get("location", ""),
                t.get("portal_source", "cppp_epublish"),
                t.get("portal_url", ""),
                t.get("description", ""),
                t.get("primary_category", ""),
                t.get("highest_tier", ""),
                1 if t.get("is_qualified") else 0,
                t.get("qualification_reason", ""),
                1 if t.get("uncertain") else 0,
                json.dumps(t.get("raw_metadata")) if isinstance(t.get("raw_metadata"), dict) else t.get("raw_metadata"),
                t.get("workflow_status") or "new",
                1 if t.get("is_watchlisted") else 0,
                t.get("user_notes") or "",
                t.get("assigned_to") or "",
                t.get("status_updated_at"),
                t.get("created_at"),
                t.get("updated_at")
            ]
            cur.execute(tender_insert_sql, params)

        km_cols = [
            "id", "tender_id_ref", "term", "tier", "match_group", "matched_text",
            "snippet", "position", "source_field", "is_contextual"
        ]
        km_placeholders = ", ".join(["?"] * len(km_cols))
        km_insert_sql = f"INSERT INTO keyword_matches ({', '.join(km_cols)}) VALUES ({km_placeholders})"

        for m in matches:
            km_params = [
                m.get("id"),
                m.get("tender_id_ref"),
                m.get("term", ""),
                m.get("tier", ""),
                m.get("match_group", ""),
                m.get("matched_text", ""),
                m.get("snippet", ""),
                m.get("position", 0),
                m.get("source_field", ""),
                1 if m.get("is_contextual") else 0
            ]
            cur.execute(km_insert_sql, km_params)

        if conn.is_pg:
            cur.execute("SELECT setval(\'tenders_id_seq\', (SELECT COALESCE(MAX(id), 1) FROM tenders));")
            cur.execute("SELECT setval(\'keyword_matches_id_seq\', (SELECT COALESCE(MAX(id), 1) FROM keyword_matches));")

        conn.commit()
        logger.info(f"Database successfully auto-seeded with {len(tenders)} tenders and {len(matches)} matches.")
    except Exception as e:
        logger.error(f"Auto-seed encountered an issue: {e}", exc_info=True)


def init_db(db_path: Optional[str] = None):
    """Create database tables and indexes if they do not exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if conn.is_pg:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id SERIAL PRIMARY KEY,
            tender_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            authority TEXT DEFAULT 'Unknown Authority',
            reference_no TEXT,
            tender_type TEXT,
            estimated_cost_inr DOUBLE PRECISION,
            emd_inr DOUBLE PRECISION,
            doc_fee_inr DOUBLE PRECISION,
            published_date TEXT,
            submission_deadline TEXT,
            opening_date TEXT,
            location TEXT,
            portal_source TEXT NOT NULL DEFAULT 'cppp_epublish',
            portal_url TEXT,
            description TEXT,
            primary_category TEXT DEFAULT '',
            highest_tier TEXT DEFAULT '',
            is_qualified INTEGER DEFAULT 0,
            qualification_reason TEXT DEFAULT '',
            uncertain INTEGER DEFAULT 0,
            raw_metadata TEXT,
            workflow_status TEXT DEFAULT 'new',
            is_watchlisted INTEGER DEFAULT 0,
            user_notes TEXT DEFAULT '',
            assigned_to TEXT DEFAULT '',
            status_updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_tenders_category ON tenders(primary_category);
        CREATE INDEX IF NOT EXISTS idx_tenders_tier ON tenders(highest_tier);
        CREATE INDEX IF NOT EXISTS idx_tenders_qualified ON tenders(is_qualified);
        CREATE INDEX IF NOT EXISTS idx_tenders_source ON tenders(portal_source);
        CREATE INDEX IF NOT EXISTS idx_tenders_pub_date ON tenders(published_date);
        CREATE INDEX IF NOT EXISTS idx_tenders_workflow ON tenders(workflow_status);
        CREATE INDEX IF NOT EXISTS idx_tenders_watchlisted ON tenders(is_watchlisted);

        CREATE TABLE IF NOT EXISTS keyword_matches (
            id SERIAL PRIMARY KEY,
            tender_id_ref INTEGER NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
            term TEXT NOT NULL,
            tier TEXT NOT NULL,
            match_group TEXT NOT NULL,
            matched_text TEXT NOT NULL,
            snippet TEXT,
            position INTEGER DEFAULT 0,
            source_field TEXT DEFAULT '',
            is_contextual INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_km_tender_id ON keyword_matches(tender_id_ref);
        CREATE INDEX IF NOT EXISTS idx_km_tier ON keyword_matches(tier);

        CREATE TABLE IF NOT EXISTS tender_documents (
            id SERIAL PRIMARY KEY,
            tender_id_ref INTEGER NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            doc_type TEXT DEFAULT 'TenderDocument',
            local_path TEXT,
            file_size_bytes BIGINT,
            page_count INTEGER DEFAULT 0,
            text_extracted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS extracted_fields (
            id SERIAL PRIMARY KEY,
            tender_id_ref INTEGER NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
            field_name TEXT NOT NULL,
            raw_text TEXT,
            normalized_value TEXT,
            evidence_location TEXT,
            evidence_snippet TEXT,
            confidence REAL DEFAULT 0.0,
            status TEXT DEFAULT 'present_extracted',
            verified INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS source_runs (
            id SERIAL PRIMARY KEY,
            source_name TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            items_scanned INTEGER DEFAULT 0,
            items_discovered INTEGER DEFAULT 0,
            items_qualified INTEGER DEFAULT 0,
            error_message TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_runs_source ON source_runs(source_name);
        """)
    else:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            authority TEXT DEFAULT 'Unknown Authority',
            reference_no TEXT,
            tender_type TEXT,
            estimated_cost_inr REAL,
            emd_inr REAL,
            doc_fee_inr REAL,
            published_date TEXT,
            submission_deadline TEXT,
            opening_date TEXT,
            location TEXT,
            portal_source TEXT NOT NULL DEFAULT 'cppp_epublish',
            portal_url TEXT,
            description TEXT,
            primary_category TEXT DEFAULT '',
            highest_tier TEXT DEFAULT '',
            is_qualified INTEGER DEFAULT 0,
            qualification_reason TEXT DEFAULT '',
            uncertain INTEGER DEFAULT 0,
            raw_metadata TEXT,
            workflow_status TEXT DEFAULT 'new',
            is_watchlisted INTEGER DEFAULT 0,
            user_notes TEXT DEFAULT '',
            assigned_to TEXT DEFAULT '',
            status_updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_tenders_category ON tenders(primary_category);
        CREATE INDEX IF NOT EXISTS idx_tenders_tier ON tenders(highest_tier);
        CREATE INDEX IF NOT EXISTS idx_tenders_qualified ON tenders(is_qualified);
        CREATE INDEX IF NOT EXISTS idx_tenders_source ON tenders(portal_source);
        CREATE INDEX IF NOT EXISTS idx_tenders_pub_date ON tenders(published_date);

        CREATE TABLE IF NOT EXISTS keyword_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id_ref INTEGER NOT NULL,
            term TEXT NOT NULL,
            tier TEXT NOT NULL,
            match_group TEXT NOT NULL,
            matched_text TEXT NOT NULL,
            snippet TEXT,
            position INTEGER DEFAULT 0,
            source_field TEXT DEFAULT '',
            is_contextual INTEGER DEFAULT 0,
            FOREIGN KEY (tender_id_ref) REFERENCES tenders(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_km_tender_id ON keyword_matches(tender_id_ref);
        CREATE INDEX IF NOT EXISTS idx_km_tier ON keyword_matches(tier);

        CREATE TABLE IF NOT EXISTS tender_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id_ref INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            doc_type TEXT DEFAULT 'TenderDocument',
            local_path TEXT,
            file_size_bytes INTEGER,
            page_count INTEGER DEFAULT 0,
            text_extracted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tender_id_ref) REFERENCES tenders(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS extracted_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id_ref INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            raw_text TEXT,
            normalized_value TEXT,
            evidence_location TEXT,
            evidence_snippet TEXT,
            confidence REAL DEFAULT 0.0,
            status TEXT DEFAULT 'present_extracted',
            verified INTEGER DEFAULT 0,
            FOREIGN KEY (tender_id_ref) REFERENCES tenders(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS source_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            items_scanned INTEGER DEFAULT 0,
            items_discovered INTEGER DEFAULT 0,
            items_qualified INTEGER DEFAULT 0,
            error_message TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_runs_source ON source_runs(source_name);
        """)

        cursor.execute("PRAGMA table_info(tenders)")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        if "workflow_status" not in existing_cols:
            cursor.execute("ALTER TABLE tenders ADD COLUMN workflow_status TEXT DEFAULT 'new'")
        if "is_watchlisted" not in existing_cols:
            cursor.execute("ALTER TABLE tenders ADD COLUMN is_watchlisted INTEGER DEFAULT 0")
        if "user_notes" not in existing_cols:
            cursor.execute("ALTER TABLE tenders ADD COLUMN user_notes TEXT DEFAULT ''")
        if "assigned_to" not in existing_cols:
            cursor.execute("ALTER TABLE tenders ADD COLUMN assigned_to TEXT DEFAULT ''")
        if "status_updated_at" not in existing_cols:
            cursor.execute("ALTER TABLE tenders ADD COLUMN status_updated_at TEXT DEFAULT ''")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_workflow ON tenders(workflow_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_watchlisted ON tenders(is_watchlisted)")

    conn.commit()

    # Seed if production database is empty (PostgreSQL or default local database)
    if conn.is_pg or (db_path is None or db_path == DB_PATH):
        # Do not auto-seed if custom test db_path is provided (unless explicit AUTO_SEED=true)
        if db_path and db_path != DB_PATH and not os.environ.get("AUTO_SEED"):
            pass
        else:
            seed_db_if_empty(conn)

    # Auto-normalize legacy date strings to ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, published_date, submission_deadline, opening_date FROM tenders WHERE published_date IS NOT NULL OR submission_deadline IS NOT NULL OR opening_date IS NOT NULL")
        rows = cur.fetchall()
        for r in rows:
            row_id = r["id"]
            orig_pub = r["published_date"]
            orig_dl = r["submission_deadline"]
            orig_op = r["opening_date"] if "opening_date" in r else None

            norm_pub = normalize_date_to_iso(orig_pub)
            norm_dl = normalize_date_to_iso(orig_dl)
            norm_op = normalize_date_to_iso(orig_op)

            if norm_pub != orig_pub or norm_dl != orig_dl or norm_op != orig_op:
                cur.execute(
                    "UPDATE tenders SET published_date = ?, submission_deadline = ?, opening_date = ? WHERE id = ?",
                    (norm_pub, norm_dl, norm_op, row_id)
                )
        conn.commit()
    except Exception as e:
        logger.warning(f"Date normalization auto-migration notice: {e}")

    conn.close()
    logger.info("Database initialized successfully.")


class TenderRepository:
    """Data access layer for tender intelligence (PostgreSQL & SQLite)."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        init_db(self.db_path)

    def _get_conn(self) -> UnifiedConnection:
        return get_connection(self.db_path)

    def upsert_tender(self, data: Dict[str, Any], matches: List[Dict[str, Any]]) -> int:
        """Insert or update a tender along with keyword matches."""
        conn = self._get_conn()
        cursor = conn.cursor()

        now_str = datetime.utcnow().isoformat()
        norm_pub = normalize_date_to_iso(data.get("published_date"))
        norm_dl = normalize_date_to_iso(data.get("submission_deadline"))
        norm_op = normalize_date_to_iso(data.get("opening_date"))

        # 1. Primary deduplication lookup by unique tender_id
        cursor.execute("SELECT id FROM tenders WHERE tender_id = ?", (data["tender_id"],))
        row = cursor.fetchone()

        # 2. Secondary deduplication fallback by (portal_source, reference_no)
        if not row and data.get("reference_no") and len(str(data["reference_no"]).strip()) > 3 and data.get("portal_source"):
            cursor.execute("SELECT id FROM tenders WHERE portal_source = ? AND reference_no = ?", (data["portal_source"], str(data["reference_no"]).strip()))
            row = cursor.fetchone()

        # 3. Tertiary deduplication fallback by (portal_source, portal_url)
        if not row and data.get("portal_url") and len(str(data["portal_url"]).strip()) > 20 and data.get("portal_source"):
            cursor.execute("SELECT id FROM tenders WHERE portal_source = ? AND portal_url = ?", (data["portal_source"], str(data["portal_url"]).strip()))
            row = cursor.fetchone()

        if row:
            tender_db_id = row["id"]
            cursor.execute("""
                UPDATE tenders SET
                    title = ?,
                    authority = ?,
                    reference_no = ?,
                    tender_type = ?,
                    estimated_cost_inr = ?,
                    emd_inr = ?,
                    doc_fee_inr = ?,
                    published_date = ?,
                    submission_deadline = ?,
                    opening_date = ?,
                    location = ?,
                    portal_source = ?,
                    portal_url = ?,
                    description = ?,
                    primary_category = ?,
                    highest_tier = ?,
                    is_qualified = ?,
                    qualification_reason = ?,
                    uncertain = ?,
                    raw_metadata = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                data.get("title", ""),
                data.get("authority", "Unknown Authority"),
                data.get("reference_no", ""),
                data.get("tender_type", ""),
                data.get("estimated_cost_inr"),
                data.get("emd_inr"),
                data.get("doc_fee_inr"),
                norm_pub,
                norm_dl,
                norm_op,
                data.get("location", ""),
                data.get("portal_source", "cppp_epublish"),
                data.get("portal_url", ""),
                data.get("description", ""),
                data.get("primary_category", ""),
                data.get("highest_tier", ""),
                1 if data.get("is_qualified") else 0,
                data.get("qualification_reason", ""),
                1 if data.get("uncertain") else 0,
                json.dumps(data.get("raw_metadata", {})) if data.get("raw_metadata") else None,
                now_str,
                tender_db_id
            ))
            cursor.execute("DELETE FROM keyword_matches WHERE tender_id_ref = ?", (tender_db_id,))
        else:
            cursor.execute("""
                INSERT INTO tenders (
                    tender_id, title, authority, reference_no, tender_type,
                    estimated_cost_inr, emd_inr, doc_fee_inr,
                    published_date, submission_deadline, opening_date,
                    location, portal_source, portal_url, description,
                    primary_category, highest_tier, is_qualified,
                    qualification_reason, uncertain, raw_metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["tender_id"],
                data.get("title", ""),
                data.get("authority", "Unknown Authority"),
                data.get("reference_no", ""),
                data.get("tender_type", ""),
                data.get("estimated_cost_inr"),
                data.get("emd_inr"),
                data.get("doc_fee_inr"),
                norm_pub,
                norm_dl,
                norm_op,
                data.get("location", ""),
                data.get("portal_source", "cppp_epublish"),
                data.get("portal_url", ""),
                data.get("description", ""),
                data.get("primary_category", ""),
                data.get("highest_tier", ""),
                1 if data.get("is_qualified") else 0,
                data.get("qualification_reason", ""),
                1 if data.get("uncertain") else 0,
                json.dumps(data.get("raw_metadata", {})) if data.get("raw_metadata") else None,
                now_str,
                now_str
            ))
            tender_db_id = cursor.lastrowid

        # Insert matches
        for m in matches:
            cursor.execute("""
                INSERT INTO keyword_matches (
                    tender_id_ref, term, tier, match_group, matched_text,
                    snippet, position, source_field, is_contextual
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tender_db_id,
                m.get("term", ""),
                m.get("tier", ""),
                m.get("group", ""),
                m.get("matched_text", ""),
                m.get("snippet", ""),
                m.get("position", 0),
                m.get("source_field", ""),
                1 if m.get("is_contextual") else 0
            ))

        conn.commit()
        conn.close()
        return tender_db_id

    def list_tenders(
        self,
        category: Optional[str] = None,
        tier: Optional[str] = None,
        source: Optional[str] = None,
        is_qualified: Optional[bool] = None,
        search: Optional[str] = None,
        workflow_status: Optional[str] = None,
        is_watchlisted: Optional[bool] = None,
        time_window: Optional[str] = None,
        expiry_status: Optional[str] = None,
        sort_by: str = "published_date",
        order: str = "desc",
        page: int = 1,
        page_size: int = 25
    ) -> Dict[str, Any]:
        """Query tenders with rich filtering, time window evaluation, and pagination."""
        conn = self._get_conn()
        cursor = conn.cursor()

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S")

        where_clauses = []
        params = []

        if category:
            where_clauses.append("primary_category = ?")
            params.append(category)
        if tier:
            where_clauses.append("highest_tier = ?")
            params.append(tier)
        if source:
            where_clauses.append("portal_source = ?")
            params.append(source)
        if is_qualified is not None:
            where_clauses.append("is_qualified = ?")
            params.append(1 if is_qualified else 0)
        if workflow_status and workflow_status != "all":
            if workflow_status == "expired":
                where_clauses.append("(submission_deadline IS NOT NULL AND submission_deadline != '' AND submission_deadline < ?)")
                params.append(now_iso)
            else:
                where_clauses.append("workflow_status = ?")
                params.append(workflow_status)
        if is_watchlisted is not None:
            where_clauses.append("is_watchlisted = ?")
            params.append(1 if is_watchlisted else 0)

        # Time window filter (24h, 48h, 7d, 30d, all)
        if time_window and time_window != "all":
            hours = 24
            if time_window == "24h":
                hours = 24
            elif time_window == "48h":
                hours = 48
            elif time_window == "7d":
                hours = 24 * 7
            elif time_window == "30d":
                hours = 24 * 30

            cutoff = (now_dt - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
            where_clauses.append("(created_at >= ? OR (published_date IS NOT NULL AND published_date >= ?))")
            params.extend([cutoff, cutoff])

        # Expiry status filter (active, expired, all)
        if expiry_status == "active":
            where_clauses.append("(submission_deadline IS NULL OR submission_deadline = '' OR submission_deadline >= ?)")
            params.append(now_iso)
        elif expiry_status == "expired":
            where_clauses.append("(submission_deadline IS NOT NULL AND submission_deadline != '' AND submission_deadline < ?)")
            params.append(now_iso)

        if search:
            where_clauses.append("(title LIKE ? OR authority LIKE ? OR tender_id LIKE ?)")
            p = f"%{search}%"
            params.extend([p, p, p])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {where_sql}", params)
        total = cursor.fetchone()["cnt"]

        tier_order_clause = """
            CASE t.highest_tier
                WHEN 'A' THEN 1
                WHEN 'B' THEN 2
                WHEN 'C' THEN 3
                WHEN 'D' THEN 4
                ELSE 5
            END ASC
        """
        allowed_sort = ["published_date", "estimated_cost_inr", "submission_deadline", "created_at"]
        sort_field = f"t.{sort_by}" if sort_by in allowed_sort else "t.published_date"
        order_dir = "ASC" if order.lower() == "asc" else "DESC"

        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT t.*,
                (SELECT COUNT(*) FROM keyword_matches km WHERE km.tender_id_ref = t.id) as matches_count,
                (SELECT COUNT(*) FROM tender_documents td WHERE td.tender_id_ref = t.id) as documents_count
            FROM tenders t
            {where_sql}
            ORDER BY {tier_order_clause}, {sort_field} {order_dir} NULLS LAST
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [page_size, offset])
        rows = cursor.fetchall()

        items = []
        for r in rows:
            d = dict(r)
            d["is_qualified"] = bool(d["is_qualified"])
            d["uncertain"] = bool(d["uncertain"])
            d["is_watchlisted"] = bool(d.get("is_watchlisted", 0))
            d["workflow_status"] = d.get("workflow_status") or "new"
            d["user_notes"] = d.get("user_notes") or ""
            d["assigned_to"] = d.get("assigned_to") or ""
            d["is_expired"] = is_deadline_expired(d.get("submission_deadline"), now_iso)
            items.append(d)

        conn.close()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

    def count_tenders(self, is_qualified: Optional[bool] = None) -> int:
        """Count total or qualified tenders in the database."""
        conn = self._get_conn()
        cursor = conn.cursor()
        if is_qualified is not None:
            cursor.execute("SELECT COUNT(*) as cnt FROM tenders WHERE is_qualified = ?", (1 if is_qualified else 0,))
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM tenders")
        row = cursor.fetchone()
        cnt = row["cnt"] if row else 0
        conn.close()
        return cnt

    def sync_seed_tenders(self, force: bool = False) -> Dict[str, Any]:
        """
        Synchronizes the database with verified seed and benchmark tenders.
        Upserts all seed tenders without overwriting user workflow statuses,
        ensuring cloud deployments (like Render) always have 450+ qualified tenders.
        """
        if not os.path.exists(SEED_PATH):
            return {"scanned": 0, "discovered": 0, "qualified": 0}

        try:
            with open(SEED_PATH, "r", encoding="utf-8") as f:
                seed_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read seed file {SEED_PATH}: {e}")
            return {"scanned": 0, "discovered": 0, "qualified": 0}

        tenders = seed_data.get("tenders", [])
        matches = seed_data.get("keyword_matches", [])

        matches_by_ref = {}
        for m in matches:
            ref = m.get("tender_id_ref")
            if ref not in matches_by_ref:
                matches_by_ref[ref] = []
            matches_by_ref[ref].append(m)

        conn = self._get_conn()
        cursor = conn.cursor()

        scanned = len(tenders)
        discovered = 0
        qualified = 0

        for t in tenders:
            tid = t.get("tender_id")
            if not tid:
                continue

            cursor.execute("SELECT id, workflow_status, is_watchlisted, user_notes FROM tenders WHERE tender_id = ?", (tid,))
            existing = cursor.fetchone()

            now_str = datetime.utcnow().isoformat()
            if existing and not force:
                discovered += 1
                if t.get("is_qualified"):
                    qualified += 1
                continue

            if existing:
                cursor.execute("""
                    UPDATE tenders SET
                        title = ?, authority = ?, reference_no = ?, tender_type = ?,
                        estimated_cost_inr = ?, emd_inr = ?, doc_fee_inr = ?,
                        published_date = ?, submission_deadline = ?, opening_date = ?,
                        location = ?, portal_source = ?, portal_url = ?, description = ?,
                        primary_category = ?, highest_tier = ?, is_qualified = ?,
                        qualification_reason = ?, uncertain = ?, updated_at = ?
                    WHERE tender_id = ?
                """, (
                    t.get("title", ""), t.get("authority", "Unknown Authority"),
                    t.get("reference_no", ""), t.get("tender_type", ""),
                    t.get("estimated_cost_inr"), t.get("emd_inr"), t.get("doc_fee_inr"),
                    normalize_date_to_iso(t.get("published_date")),
                    normalize_date_to_iso(t.get("submission_deadline")),
                    normalize_date_to_iso(t.get("opening_date")),
                    t.get("location", ""), t.get("portal_source", "cppp_epublish"),
                    t.get("portal_url", ""), t.get("description", ""),
                    t.get("primary_category", ""), t.get("highest_tier", ""),
                    1 if t.get("is_qualified") else 0,
                    t.get("qualification_reason", ""),
                    1 if t.get("uncertain") else 0,
                    now_str,
                    tid
                ))
            else:
                cursor.execute("""
                    INSERT INTO tenders (
                        tender_id, title, authority, reference_no, tender_type,
                        estimated_cost_inr, emd_inr, doc_fee_inr, published_date,
                        submission_deadline, opening_date, location, portal_source,
                        portal_url, description, primary_category, highest_tier,
                        is_qualified, qualification_reason, uncertain, raw_metadata,
                        workflow_status, is_watchlisted, user_notes, assigned_to,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tid, t.get("title", ""), t.get("authority", "Unknown Authority"),
                    t.get("reference_no", ""), t.get("tender_type", ""),
                    t.get("estimated_cost_inr"), t.get("emd_inr"), t.get("doc_fee_inr"),
                    normalize_date_to_iso(t.get("published_date")),
                    normalize_date_to_iso(t.get("submission_deadline")),
                    normalize_date_to_iso(t.get("opening_date")),
                    t.get("location", ""), t.get("portal_source", "cppp_epublish"),
                    t.get("portal_url", ""), t.get("description", ""),
                    t.get("primary_category", ""), t.get("highest_tier", ""),
                    1 if t.get("is_qualified") else 0,
                    t.get("qualification_reason", ""),
                    1 if t.get("uncertain") else 0,
                    json.dumps(t.get("raw_metadata")) if isinstance(t.get("raw_metadata"), dict) else t.get("raw_metadata"),
                    t.get("workflow_status") or "new",
                    1 if t.get("is_watchlisted") else 0,
                    t.get("user_notes") or "",
                    t.get("assigned_to") or "",
                    t.get("created_at") or now_str,
                    now_str
                ))

            discovered += 1
            if t.get("is_qualified"):
                qualified += 1

        if conn.is_pg:
            cursor.execute("SELECT setval('tenders_id_seq', (SELECT COALESCE(MAX(id), 1) FROM tenders));")
            cursor.execute("SELECT setval('keyword_matches_id_seq', (SELECT COALESCE(MAX(id), 1) FROM keyword_matches));")

        conn.commit()
        conn.close()

        logger.info(f"Seed sync complete: {scanned} scanned, {discovered} active, {qualified} qualified.")
        return {"scanned": scanned, "discovered": discovered, "qualified": qualified}

    def get_tender(self, tender_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a tender including keyword matches and evidence."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tenders WHERE tender_id = ?", (tender_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        tender = dict(row)
        tender["is_qualified"] = bool(tender["is_qualified"])
        tender["uncertain"] = bool(tender["uncertain"])
        tender["is_watchlisted"] = bool(tender.get("is_watchlisted", 0))
        tender["workflow_status"] = tender.get("workflow_status") or "new"
        tender["user_notes"] = tender.get("user_notes") or ""
        tender["assigned_to"] = tender.get("assigned_to") or ""
        tender["is_expired"] = is_deadline_expired(tender.get("submission_deadline"), now_iso)

        cursor.execute("SELECT * FROM keyword_matches WHERE tender_id_ref = ?", (tender["id"],))
        tender["matches"] = [dict(m) for m in cursor.fetchall()]

        cursor.execute("SELECT * FROM tender_documents WHERE tender_id_ref = ?", (tender["id"],))
        tender["documents"] = [dict(d) for d in cursor.fetchall()]

        cursor.execute("SELECT * FROM extracted_fields WHERE tender_id_ref = ?", (tender["id"],))
        tender["extracted_fields"] = [dict(f) for f in cursor.fetchall()]

        conn.close()
        return tender

    def update_tender_workflow(
        self,
        tender_id: str,
        workflow_status: Optional[str] = None,
        is_watchlisted: Optional[bool] = None,
        user_notes: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update user workflow classification, watchlist bookmark, notes, or assignment."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM tenders WHERE tender_id = ?", (tender_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        updates = ["status_updated_at = CURRENT_TIMESTAMP"]
        params = []

        if workflow_status is not None:
            updates.append("workflow_status = ?")
            params.append(workflow_status)
        if is_watchlisted is not None:
            updates.append("is_watchlisted = ?")
            params.append(1 if is_watchlisted else 0)
        if user_notes is not None:
            updates.append("user_notes = ?")
            params.append(user_notes)
        if assigned_to is not None:
            updates.append("assigned_to = ?")
            params.append(assigned_to)

        params.append(tender_id)
        cursor.execute(f"UPDATE tenders SET {', '.join(updates)} WHERE tender_id = ?", params)
        conn.commit()
        conn.close()
        return self.get_tender(tender_id)

    def bulk_update_workflow(
        self,
        tender_ids: List[str],
        workflow_status: Optional[str] = None,
        is_watchlisted: Optional[bool] = None,
        assigned_to: Optional[str] = None
    ) -> int:
        """Batch update workflow status or watchlist flag across multiple tenders."""
        if not tender_ids:
            return 0
        conn = self._get_conn()
        cursor = conn.cursor()

        updates = ["status_updated_at = CURRENT_TIMESTAMP"]
        params = []

        if workflow_status is not None:
            updates.append("workflow_status = ?")
            params.append(workflow_status)
        if is_watchlisted is not None:
            updates.append("is_watchlisted = ?")
            params.append(1 if is_watchlisted else 0)
        if assigned_to is not None:
            updates.append("assigned_to = ?")
            params.append(assigned_to)

        placeholders = ",".join(["?"] * len(tender_ids))
        sql = f"UPDATE tenders SET {', '.join(updates)} WHERE tender_id IN ({placeholders})"
        cursor.execute(sql, params + list(tender_ids))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    def get_watchlist(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Retrieve active priority bids (watchlisted or considered) ordered by deadline."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tenders 
            WHERE is_watchlisted = 1 OR workflow_status = 'considered'
            ORDER BY 
                CASE WHEN submission_deadline IS NULL OR submission_deadline = '' THEN 1 ELSE 0 END,
                submission_deadline ASC,
                published_date DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        items = []
        for r in rows:
            d = dict(r)
            d["is_qualified"] = bool(d["is_qualified"])
            d["uncertain"] = bool(d["uncertain"])
            d["is_watchlisted"] = bool(d.get("is_watchlisted", 0))
            d["workflow_status"] = d.get("workflow_status") or "new"
            d["user_notes"] = d.get("user_notes") or ""
            d["assigned_to"] = d.get("assigned_to") or ""
            items.append(d)
        conn.close()
        return items

    def get_dashboard_metrics(self, time_window: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate key metrics for the executive dashboard with time window support."""
        conn = self._get_conn()
        cursor = conn.cursor()

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S")

        where_clauses = []
        params = []

        if time_window and time_window != "all":
            hours = 24
            if time_window == "24h":
                hours = 24
            elif time_window == "48h":
                hours = 48
            elif time_window == "7d":
                hours = 24 * 7
            elif time_window == "30d":
                hours = 24 * 30

            cutoff = (now_dt - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
            where_clauses.append("(created_at >= ? OR (published_date IS NOT NULL AND published_date >= ?))")
            params.extend([cutoff, cutoff])

        base_where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        def _append_clause(extra: str) -> str:
            if base_where:
                return f"{base_where} AND {extra}"
            return f"WHERE {extra}"

        cursor.execute(f"SELECT COUNT(*) as total FROM tenders {base_where}", params)
        total_discovered = cursor.fetchone()["total"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('primary_category = \'direct\' AND is_qualified = 1')}", params)
        direct_matches = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('primary_category = \'indirect_review\'')}", params)
        indirect_review = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('highest_tier = \'A\'')}", params)
        tier_a_count = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('highest_tier = \'B\'')}", params)
        tier_b_count = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('highest_tier = \'C\'')}", params)
        tier_c_count = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('highest_tier = \'D\'')}", params)
        tier_d_count = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT SUM(estimated_cost_inr) as total_val FROM tenders {_append_clause('is_qualified = 1')}", params)
        val_row = cursor.fetchone()
        total_pipeline_val = val_row["total_val"] or 0.0

        cursor.execute(f"SELECT LOWER(portal_source) as portal_source, COUNT(*) as cnt FROM tenders {base_where} GROUP BY LOWER(portal_source) ORDER BY cnt DESC", params)
        sources_breakdown = [
            {"name": row["portal_source"], "count": row["cnt"]}
            for row in cursor.fetchall()
        ]

        cursor.execute(f"SELECT title, authority FROM tenders {base_where}", params)
        all_tenders_meta = cursor.fetchall()
        sectors_map = {
            "Government": 0,
            "Defence": 0,
            "Enterprise / Commercial": 0,
            "Energy & Utilities": 0,
            "Transport": 0
        }
        for r in all_tenders_meta:
            text = ((r["title"] or "") + " " + (r["authority"] or "")).lower()
            if any(k in text for k in ["air force", "army", "navy", "defence", "defense", "armoured", "ordnance", "cantonment", "military", "mes", "crpf", "bsf", "cisf", "itbp"]):
                sectors_map["Defence"] += 1
            elif any(k in text for k in ["railway", "metro", "transport", "airport", "aai", "highway", "nhai", "port", "shipping", "irctc", "rvnl"]):
                sectors_map["Transport"] += 1
            elif any(k in text for k in ["power", "energy", "solar", "grid", "electricity", "discom", "ntpc", "transco", "gencor", "oil", "gas", "ongc", "iocl", "bpcl", "gail", "hydel", "thermal"]):
                sectors_map["Energy & Utilities"] += 1
            elif any(k in text for k in ["bank", "rbi", "sbi", "insurance", "lic", "commercial", "enterprise", "telecom", "bsnl", "limited", "corp", "exchange", "bse", "nse", "ltd"]):
                sectors_map["Enterprise / Commercial"] += 1
            else:
                sectors_map["Government"] += 1

        sectors_breakdown = [{"name": k, "count": v} for k, v in sectors_map.items() if v > 0]

        cursor.execute(f"SELECT workflow_status, COUNT(*) as cnt FROM tenders {base_where} GROUP BY workflow_status", params)
        wf_rows = cursor.fetchall()
        workflow_counts = {"new": 0, "under_review": 0, "considered": 0, "reviewed": 0, "rejected": 0}
        for r in wf_rows:
            st = r["workflow_status"] or "new"
            workflow_counts[st] = r["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('is_watchlisted = 1')}", params)
        watchlisted_count = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('(submission_deadline IS NOT NULL AND submission_deadline != \'\' AND submission_deadline < ?)')}", params + [now_iso])
        expired_count = cursor.fetchone()["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('(submission_deadline IS NULL OR submission_deadline = \'\' OR submission_deadline >= ?)')}", params + [now_iso])
        active_count = cursor.fetchone()["cnt"]

        conn.close()
        return {
            "total_discovered": total_discovered,
            "total_tenders": total_discovered,
            "direct_matches": direct_matches,
            "indirect_review": indirect_review,
            "tier_a_count": tier_a_count,
            "tier_b_count": tier_b_count,
            "tier_c_count": tier_c_count,
            "tier_d_count": tier_d_count,
            "total_pipeline_value_inr": total_pipeline_val,
            "sources_breakdown": sources_breakdown,
            "sectors_breakdown": sectors_breakdown,
            "workflow_counts": workflow_counts,
            "watchlisted_count": watchlisted_count,
            "expired_count": expired_count,
            "active_count": active_count,
            "time_window": time_window or "all"
        }

    def start_source_run(self, source_name: str) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO source_runs (source_name, status, started_at) VALUES (?, 'running', ?)",
            (source_name, datetime.utcnow().isoformat() + "Z")
        )
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return run_id

    def finish_source_run(self, run_id: int, status: str, scanned: int, discovered: int, qualified: int, error: Optional[str] = None):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE source_runs SET
                status = ?,
                finished_at = ?,
                items_scanned = ?,
                items_discovered = ?,
                items_qualified = ?,
                error_message = ?
            WHERE id = ?
        """, (status, datetime.utcnow().isoformat() + "Z", scanned, discovered, qualified, error, run_id))
        conn.commit()
        conn.close()

    def get_source_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM source_runs ORDER BY started_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        runs = [dict(r) for r in rows]
        conn.close()
        return runs

    def count_tenders(self, is_qualified: Optional[bool] = None) -> int:
        """Count total tenders, optionally filtered by qualification status."""
        conn = self._get_conn()
        cursor = conn.cursor()
        if is_qualified is None:
            cursor.execute("SELECT COUNT(*) as cnt FROM tenders")
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM tenders WHERE is_qualified = ?", (1 if is_qualified else 0,))
        row = cursor.fetchone()
        cnt = row["cnt"] if row else 0
        conn.close()
        return cnt

    def sync_seed_tenders(self, force: bool = False) -> Dict[str, Any]:
        """Upsert baseline opportunities from seed_tenders.json safely."""
        if not os.path.exists(SEED_PATH):
            return {"status": "error", "message": "Seed file not found"}

        with open(SEED_PATH, "r", encoding="utf-8") as f:
            seed_data = json.load(f)

        tenders = seed_data.get("tenders", [])
        matches = seed_data.get("keyword_matches", [])

        matches_by_ref = {}
        for m in matches:
            ref = m.get("tender_id_ref")
            if ref not in matches_by_ref:
                matches_by_ref[ref] = []
            matches_by_ref[ref].append(m)

        conn = self._get_conn()
        cur = conn.cursor()
        inserted = 0
        updated = 0
        now_str = datetime.utcnow().isoformat()

        for t in tenders:
            tid = t.get("tender_id")
            if not tid:
                continue

            norm_pub = normalize_date_to_iso(t.get("published_date"))
            norm_dl = normalize_date_to_iso(t.get("submission_deadline"))
            norm_op = normalize_date_to_iso(t.get("opening_date"))

            cur.execute("SELECT id FROM tenders WHERE tender_id = ?", (tid,))
            existing = cur.fetchone()

            if existing:
                if force:
                    cur.execute("""
                        UPDATE tenders SET
                            title = ?, authority = ?, reference_no = ?, tender_type = ?,
                            estimated_cost_inr = ?, emd_inr = ?, doc_fee_inr = ?,
                            published_date = ?, submission_deadline = ?, opening_date = ?,
                            location = ?, portal_source = ?, portal_url = ?, description = ?,
                            primary_category = ?, highest_tier = ?, is_qualified = ?,
                            qualification_reason = ?, uncertain = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        t.get("title", ""), t.get("authority", "Unknown Authority"),
                        t.get("reference_no", ""), t.get("tender_type", ""),
                        t.get("estimated_cost_inr"), t.get("emd_inr"), t.get("doc_fee_inr"),
                        norm_pub, norm_dl, norm_op, t.get("location", ""),
                        t.get("portal_source", "cppp_epublish"), t.get("portal_url", ""),
                        t.get("description", ""), t.get("primary_category", ""),
                        t.get("highest_tier", ""), 1 if t.get("is_qualified") else 0,
                        t.get("qualification_reason", ""), 1 if t.get("uncertain") else 0,
                        now_str, existing["id"]
                    ))
                    updated += 1
            else:
                cur.execute("""
                    INSERT INTO tenders (
                        tender_id, title, authority, reference_no, tender_type,
                        estimated_cost_inr, emd_inr, doc_fee_inr,
                        published_date, submission_deadline, opening_date,
                        location, portal_source, portal_url, description,
                        primary_category, highest_tier, is_qualified,
                        qualification_reason, uncertain, raw_metadata,
                        workflow_status, is_watchlisted, user_notes, assigned_to,
                        status_updated_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tid, t.get("title", ""), t.get("authority", "Unknown Authority"),
                    t.get("reference_no", ""), t.get("tender_type", ""),
                    t.get("estimated_cost_inr"), t.get("emd_inr"), t.get("doc_fee_inr"),
                    norm_pub, norm_dl, norm_op, t.get("location", ""),
                    t.get("portal_source", "cppp_epublish"), t.get("portal_url", ""),
                    t.get("description", ""), t.get("primary_category", ""),
                    t.get("highest_tier", ""), 1 if t.get("is_qualified") else 0,
                    t.get("qualification_reason", ""), 1 if t.get("uncertain") else 0,
                    json.dumps(t.get("raw_metadata")) if isinstance(t.get("raw_metadata"), dict) else t.get("raw_metadata"),
                    t.get("workflow_status") or "new", 1 if t.get("is_watchlisted") else 0,
                    t.get("user_notes") or "", t.get("assigned_to") or "",
                    t.get("status_updated_at"), t.get("created_at") or now_str, now_str
                ))
                new_id = cur.lastrowid
                seed_id = t.get("id")
                if seed_id in matches_by_ref and new_id:
                    for m in matches_by_ref[seed_id]:
                        cur.execute("""
                            INSERT INTO keyword_matches (
                                tender_id_ref, term, tier, match_group, matched_text,
                                snippet, position, source_field, is_contextual
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            new_id, m.get("term", ""), m.get("tier", ""), m.get("match_group", ""),
                            m.get("matched_text", ""), m.get("snippet", ""), m.get("position", 0),
                            m.get("source_field", ""), 1 if m.get("is_contextual") else 0
                        ))
                inserted += 1

        if conn.is_pg:
            try:
                cur.execute("SELECT setval('tenders_id_seq', (SELECT COALESCE(MAX(id), 1) FROM tenders));")
                cur.execute("SELECT setval('keyword_matches_id_seq', (SELECT COALESCE(MAX(id), 1) FROM keyword_matches));")
            except Exception:
                pass

        conn.commit()

        cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN is_qualified = 1 THEN 1 ELSE 0 END) as qualified FROM tenders")
        tot_row = cur.fetchone()
        tot_count = tot_row["total"] if tot_row else 0
        qual_count = tot_row["qualified"] if tot_row else 0
        conn.close()

        logger.info(f"Sync complete: inserted {inserted}, updated {updated}. Total in DB: {tot_count} ({qual_count} qualified)")
        return {
            "status": "success",
            "inserted": inserted,
            "updated": updated,
            "total_in_db": tot_count,
            "qualified": qual_count
        }
