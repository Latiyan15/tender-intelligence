"""
High-Performance SQLite Native Repository for Nikom Tender Intelligence
Uses Python's built-in sqlite3 with WAL mode, foreign keys, and indexes.
Requires zero external dependencies.
"""

import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "nikom_tenders.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create or return a SQLite connection with foreign keys and row factory."""
    target_path = db_path or DB_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[str] = None):
    """Create database tables and indexes if they do not exist."""
    target_path = db_path or DB_PATH
    conn = get_connection(target_path)
    cursor = conn.cursor()

    cursor.executescript("""
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

    # Non-destructive migration for workflow management columns on existing databases
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
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


class TenderRepository:
    """Data access layer for tender intelligence."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        init_db(self.db_path)

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def upsert_tender(self, data: Dict[str, Any], matches: List[Dict[str, Any]]) -> int:
        """Insert or update a tender along with keyword matches."""
        conn = self._get_conn()
        cursor = conn.cursor()

        now_str = datetime.utcnow().isoformat()

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
                data.get("published_date"),
                data.get("submission_deadline"),
                data.get("opening_date"),
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
            # Delete old matches
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
                data.get("published_date"),
                data.get("submission_deadline"),
                data.get("opening_date"),
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

        # Count total
        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {where_sql}", params)
        total = cursor.fetchone()["cnt"]

        # Validate sort field and enforce primary sorting by Tier
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
            d["is_expired"] = bool(d.get("submission_deadline") and d["submission_deadline"] < now_iso)
            items.append(d)

        conn.close()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

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
        tender["is_expired"] = bool(tender.get("submission_deadline") and tender["submission_deadline"] < now_iso)

        # Fetch matches
        cursor.execute("SELECT * FROM keyword_matches WHERE tender_id_ref = ?", (tender["id"],))
        tender["matches"] = [dict(m) for m in cursor.fetchall()]

        # Fetch documents
        cursor.execute("SELECT * FROM tender_documents WHERE tender_id_ref = ?", (tender["id"],))
        tender["documents"] = [dict(d) for d in cursor.fetchall()]

        # Fetch extracted fields
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

        # Sources breakdown (case-insensitive canonical grouping)
        cursor.execute(f"SELECT LOWER(portal_source) as portal_source, COUNT(*) as cnt FROM tenders {base_where} GROUP BY LOWER(portal_source) ORDER BY cnt DESC", params)
        sources_breakdown = [
            {"name": row["portal_source"], "count": row["cnt"]}
            for row in cursor.fetchall()
        ]

        # Dynamic sectors breakdown from live tender data (Simplified Sectors, Data Centre removed)
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

        # Workflow lifecycle counts
        cursor.execute(f"SELECT workflow_status, COUNT(*) as cnt FROM tenders {base_where} GROUP BY workflow_status", params)
        wf_rows = cursor.fetchall()
        workflow_counts = {"new": 0, "under_review": 0, "considered": 0, "reviewed": 0, "rejected": 0}
        for r in wf_rows:
            st = r["workflow_status"] or "new"
            workflow_counts[st] = r["cnt"]

        cursor.execute(f"SELECT COUNT(*) as cnt FROM tenders {_append_clause('is_watchlisted = 1')}", params)
        watchlisted_count = cursor.fetchone()["cnt"]

        # Expired and active counts
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
