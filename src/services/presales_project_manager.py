"""
Presales Project & Multi-Document Management System
===================================================
Manages multi-document project workspaces, document ingestion across multiple file formats
(PDF, DOCX, XLSX, XLS, CSV, TXT, MD, JSON), text extraction with page/sheet provenance,
and project lifecycle state.
"""

import os
import re
import uuid
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data"
)
PROJECTS_FILE = os.path.join(DATA_DIR, "presales_projects.json")
UPLOADS_DIR = os.path.join(DATA_DIR, "presales_uploads")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)


class PresalesDocument:
    """Represents an uploaded document associated with a project."""
    def __init__(
        self,
        doc_id: str,
        filename: str,
        file_path: str,
        file_type: str,
        size_kb: float,
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.doc_id = doc_id
        self.filename = filename
        self.file_path = file_path
        self.file_type = file_type.lower()
        self.size_kb = size_kb
        self.text_content = text_content
        self.metadata = metadata or {}
        self.uploaded_at = self.metadata.get("uploaded_at") or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "size_kb": self.size_kb,
            "char_count": len(self.text_content),
            "uploaded_at": self.uploaded_at,
            "metadata": self.metadata,
            "summary": self.metadata.get("summary", "")
        }


class PresalesProject:
    """
    Project-centric workspace container that cleanly isolates project documents,
    extracted requirements, compliance matrix, commercial calculations, validation reports,
    and workflow stage.
    """
    STAGES = [
        "input_received",
        "analyzing",
        "clarification_required",
        "solution_prepared",
        "under_review",
        "draft_generated",
        "validated",
        "approved"
    ]

    def __init__(
        self,
        project_id: str,
        title: str = "New Pre-Sales Opportunity",
        client_org: str = "Prospective Client",
        tender_id: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        stage: str = "input_received",
        documents: Optional[List[Dict[str, Any]]] = None,
        requirements: Optional[Dict[str, Any]] = None,
        clarifications: Optional[List[Dict[str, Any]]] = None,
        solution: Optional[Dict[str, Any]] = None,
        compliance_matrix: Optional[List[Dict[str, Any]]] = None,
        commercial_model: Optional[Dict[str, Any]] = None,
        validation_report: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.project_id = project_id
        self.title = title
        self.client_org = client_org
        self.tender_id = tender_id
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at or datetime.now(timezone.utc).isoformat()
        self.stage = stage if stage in self.STAGES else "input_received"
        self.documents = documents or []
        self.requirements = requirements or {}
        self.clarifications = clarifications or []
        self.solution = solution or {}
        self.compliance_matrix = compliance_matrix or []
        self.commercial_model = commercial_model or {}
        self.validation_report = validation_report or {}
        self.conversation_history = conversation_history or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "client_org": self.client_org,
            "tender_id": self.tender_id,
            "stage": self.stage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "document_count": len(self.documents),
            "documents": self.documents,
            "requirements": self.requirements,
            "clarifications": self.clarifications,
            "solution": self.solution,
            "compliance_matrix": self.compliance_matrix,
            "commercial_model": self.commercial_model,
            "validation_report": self.validation_report,
            "conversation_history": self.conversation_history
        }


class ProjectManager:
    """
    Manages persistence and operations for multi-document pre-sales projects.
    Thread-safe and supports concurrent multi-user project access with atomic writes.
    """
    _lock = threading.RLock()

    def __init__(self, projects_file: str = PROJECTS_FILE):
        self.projects_file = projects_file
        self._ensure_storage()

    def _ensure_storage(self):
        with self._lock:
            if not os.path.exists(self.projects_file):
                temp_file = f"{self.projects_file}.tmp.{uuid.uuid4().hex[:8]}"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                os.replace(temp_file, self.projects_file)

    def _load_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            try:
                with open(self.projects_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading presales projects: {e}")
                return {}

    def _save_all(self, data: Dict[str, Dict[str, Any]]):
        with self._lock:
            temp_file = f"{self.projects_file}.tmp.{uuid.uuid4().hex[:8]}"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, self.projects_file)

    def create_project(
        self,
        title: str = "New Technical Proposal",
        client_org: str = "Prospective Client",
        tender_id: Optional[str] = None
    ) -> PresalesProject:
        project_id = f"PRJ-{datetime.now(timezone.utc).strftime('%Y%m')}-{str(uuid.uuid4())[:6].upper()}"
        project = PresalesProject(
            project_id=project_id,
            title=title,
            client_org=client_org,
            tender_id=tender_id,
            stage="input_received"
        )
        with self._lock:
            all_p = self._load_all()
            all_p[project_id] = project.to_dict()
            self._save_all(all_p)
        logger.info(f"Created presales project {project_id}: '{title}' for {client_org}")
        return project

    def get_project(self, project_id: str) -> Optional[PresalesProject]:
        with self._lock:
            all_p = self._load_all()
            data = all_p.get(project_id)
            if not data:
                return None
            return PresalesProject(**data)

    def get_or_create_active_project(
        self,
        project_id: Optional[str] = None,
        title: Optional[str] = None,
        client_org: Optional[str] = None,
        tender_id: Optional[str] = None
    ) -> PresalesProject:
        with self._lock:
            if project_id:
                existing = self.get_project(project_id)
                if existing:
                    return existing
                # Auto-create with requested project_id so uploads never fail
                p = PresalesProject(
                    project_id=project_id,
                    title=title or "Data Centre & Technical Infrastructure Proposal",
                    client_org=client_org or "Enterprise / Institutional Client",
                    tender_id=tender_id,
                    stage="input_received"
                )
                all_p = self._load_all()
                all_p[project_id] = p.to_dict()
                self._save_all(all_p)
                logger.info(f"Auto-initialized presales project workspace {project_id}")
                return p

            # Return most recent project or create new
            all_p = self._load_all()
            if all_p:
                sorted_keys = sorted(
                    all_p.keys(),
                    key=lambda k: all_p[k].get("updated_at", ""),
                    reverse=True
                )
                return PresalesProject(**all_p[sorted_keys[0]])

            return self.create_project(
                title=title or "Data Centre & Technical Infrastructure Proposal",
                client_org=client_org or "Enterprise / Institutional Client",
                tender_id=tender_id
            )

    def save_project(self, project: PresalesProject):
        with self._lock:
            project.updated_at = datetime.now(timezone.utc).isoformat()
            all_p = self._load_all()
            all_p[project.project_id] = project.to_dict()
            self._save_all(all_p)

    def list_projects(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            all_p = self._load_all()
            projects = list(all_p.values())
            projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
            return projects[:limit]

    def update_stage(self, project_id: str, new_stage: str) -> bool:
        with self._lock:
            project = self.get_project(project_id)
            if not project:
                return False
            if new_stage in PresalesProject.STAGES:
                project.stage = new_stage
                self.save_project(project)
                return True
        return False

    def add_uploaded_file(
        self,
        project_id: str,
        filename: str,
        file_bytes: bytes
    ) -> Dict[str, Any]:
        """
        Ingests a document for a specific project, extracts structured text with
        page/sheet provenance, and appends it to project documents.
        """
        project = self.get_or_create_active_project(project_id=project_id)

        doc_id = f"doc_{str(uuid.uuid4())[:8]}"
        safe_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', filename)
        save_path = os.path.join(UPLOADS_DIR, f"{project_id}_{doc_id}_{safe_name}")

        with open(save_path, "wb") as f:
            f.write(file_bytes)

        size_kb = round(len(file_bytes) / 1024, 1)
        ext = os.path.splitext(filename)[1].lower()

        # Extract text & metadata
        extracted_info = self.extract_document_content(save_path, filename)
        text_content = extracted_info.get("text", "")
        metadata = extracted_info.get("metadata", {})
        metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
        metadata["original_filename"] = filename
        metadata["size_kb"] = size_kb

        doc_entry = {
            "doc_id": doc_id,
            "filename": filename,
            "file_path": save_path,
            "file_type": ext,
            "size_kb": size_kb,
            "char_count": len(text_content),
            "text": text_content,
            "uploaded_at": metadata["uploaded_at"],
            "metadata": metadata,
            "summary": extracted_info.get("summary", f"{ext.upper()} document ({size_kb} KB)")
        }

        project.documents.append(doc_entry)
        project.stage = "input_received"
        self.save_project(project)

        logger.info(f"Ingested {filename} into project {project_id} ({len(text_content):,} chars)")
        return doc_entry

    def remove_document(self, project_id: str, doc_id: str) -> bool:
        project = self.get_project(project_id)
        if not project:
            return False
        orig_len = len(project.documents)
        project.documents = [d for d in project.documents if d.get("doc_id") != doc_id]
        if len(project.documents) < orig_len:
            self.save_project(project)
            return True
        return False

    def get_full_project_text(self, project_id: str, max_chars: int = 120000) -> str:
        """
        Aggregates text from all documents associated with this project,
        annotated with document headers and provenance tags.
        """
        project = self.get_project(project_id)
        if not project or not project.documents:
            return ""

        sections = []
        for doc in project.documents:
            fpath = doc.get("file_path")
            fname = doc.get("filename", "Document")
            ftype = doc.get("file_type", "")
            if fpath and os.path.exists(fpath):
                content = self.extract_document_content(fpath, fname).get("text", "")
                sections.append(
                    f"================================================================================\n"
                    f"DOCUMENT PROVENANCE: {fname} [Type: {ftype.upper()}, ID: {doc.get('doc_id')}]\n"
                    f"================================================================================\n"
                    f"{content}"
                )

        full_text = "\n\n".join(sections)
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + f"\n\n[... Truncated to {max_chars:,} characters ...]"
        return full_text

    @staticmethod
    def extract_document_content(file_path: str, filename: str) -> Dict[str, Any]:
        """
        High-grade content extraction across PDF, DOCX, XLSX, XLS, CSV, TXT, JSON, MD.
        Retains sheet, table, and page provenance.
        """
        ext = os.path.splitext(file_path)[1].lower()
        metadata = {}

        if ext in [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            try:
                from src.services.presales_doc_parser import extract_text_from_uploaded_file
                text = extract_text_from_uploaded_file(file_path)
                num_pages = len(re.findall(r'---\s*\[Page\s*\d+', text)) or 1
                metadata["page_count"] = num_pages
                doc_type_lbl = "PDF" if ext == ".pdf" else "Scanned Image"
                summary = f"{doc_type_lbl} Document: {num_pages} pages, {len(text):,} characters extracted."
                return {"text": text, "metadata": metadata, "summary": summary}
            except Exception as e:
                logger.error(f"Error extracting {ext} document {file_path}: {e}")
                return {"text": f"[Error extracting {ext}: {e}]", "metadata": metadata, "summary": f"Failed extracting {ext}"}

        elif ext in [".docx", ".doc"]:
            try:
                import docx
                doc = docx.Document(file_path)
                parts = []
                p_count = 0
                tbl_count = 0

                for p in doc.paragraphs:
                    txt = p.text.strip()
                    if txt:
                        parts.append(txt)
                        p_count += 1

                for t_idx, table in enumerate(doc.tables):
                    tbl_count += 1
                    parts.append(f"\n--- [Table {t_idx + 1}] ---")
                    for row in table.rows:
                        row_vals = [c.text.strip() for c in row.cells]
                        if any(row_vals):
                            parts.append("| " + " | ".join(row_vals) + " |")

                text = "\n".join(parts)
                metadata["paragraphs"] = p_count
                metadata["tables"] = tbl_count
                summary = f"Word Document: {p_count} paragraphs, {tbl_count} tables extracted."
                return {"text": text, "metadata": metadata, "summary": summary}
            except Exception as e:
                logger.error(f"Error reading docx {file_path}: {e}")
                return {"text": f"[Error extracting DOCX: {e}]", "metadata": metadata, "summary": "Failed extracting Word doc"}

        elif ext in [".xlsx", ".xls"]:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, data_only=True)
                sheets_data = []
                total_rows = 0
                metadata["sheet_names"] = wb.sheetnames

                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    sheet_lines = [f"--- [Document: {filename} | Sheet: '{sheet_name}'] ---"]
                    s_rows = 0
                    for row in sheet.iter_rows(values_only=True):
                        row_vals = [str(c).strip() if c is not None else "" for c in row]
                        # check if row is non-empty
                        if any(v for v in row_vals):
                            sheet_lines.append("| " + " | ".join(row_vals) + " |")
                            s_rows += 1
                    if s_rows > 0:
                        total_rows += s_rows
                        sheets_data.append("\n".join(sheet_lines))

                text = "\n\n".join(sheets_data)
                metadata["sheet_count"] = len(wb.sheetnames)
                metadata["total_rows"] = total_rows
                summary = f"Excel BOQ Spreadsheet: {len(wb.sheetnames)} sheets, {total_rows} rows extracted."
                return {"text": text, "metadata": metadata, "summary": summary}
            except Exception as e:
                logger.error(f"Error reading Excel {file_path}: {e}")
                return {"text": f"[Error extracting Excel: {e}]", "metadata": metadata, "summary": "Failed extracting Excel"}

        elif ext == ".csv":
            try:
                import csv
                lines = []
                r_count = 0
                for enc in ["utf-8", "latin-1", "cp1252"]:
                    try:
                        with open(file_path, "r", encoding=enc) as f:
                            reader = csv.reader(f)
                            for row in reader:
                                if any(row):
                                    lines.append("| " + " | ".join(row) + " |")
                                    r_count += 1
                            break
                    except UnicodeDecodeError:
                        continue

                text = f"--- [Document: {filename} | CSV BOQ / Data] ---\n" + "\n".join(lines)
                metadata["row_count"] = r_count
                summary = f"CSV Spreadsheet: {r_count} rows extracted."
                return {"text": text, "metadata": metadata, "summary": summary}
            except Exception as e:
                logger.error(f"Error reading CSV {file_path}: {e}")
                return {"text": f"[Error extracting CSV: {e}]", "metadata": metadata, "summary": "Failed extracting CSV"}

        else:
            # Plain text, Markdown, JSON
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        raw = f.read()
                    text = f"--- [Document: {filename}] ---\n{raw}"
                    metadata["char_count"] = len(raw)
                    summary = f"Text Document: {len(raw):,} characters."
                    return {"text": text, "metadata": metadata, "summary": summary}
                except Exception:
                    continue

            return {"text": "[Unreadable file format]", "metadata": metadata, "summary": "Unreadable"}
