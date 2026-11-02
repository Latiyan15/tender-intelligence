"""
Document Manager & Eligibility Analysis Service for Nikom Tender Intelligence
Handles authentic NIT document fetching (e.g., GeM direct PDF), user file uploads,
document indexing, and initial Qualify eligibility analysis against Nikom's corporate profile.
"""

import os
import re
import ssl
import io
import urllib.request
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Base documents storage directory
DOCUMENTS_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "tender_documents"
)
os.makedirs(DOCUMENTS_BASE_DIR, exist_ok=True)


from src.matcher.nikom_profile import NIKOM_PROFILE, NikomProfile


def sanitize_filename(filename: str) -> str:
    """Sanitizes file name to prevent directory traversal and remove invalid characters."""
    clean = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return clean.strip(" ._") or "tender_document"


def extract_pdf_info(file_path: str) -> Dict[str, Any]:
    """Extracts page count and text from PDF using pypdf for AI tender analysis."""
    info = {"page_count": 0, "text": "", "extracted": False}
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        info["page_count"] = len(reader.pages)
        text_parts = []
        # Extract up to 40 pages so full eligibility, BOQ, and RFP clauses are available for Bedrock
        for i in range(min(40, len(reader.pages))):
            page_text = reader.pages[i].extract_text() or ""
            if page_text:
                text_parts.append(page_text)
        info["text"] = "\n".join(text_parts)
        info["extracted"] = True
    except Exception as e:
        logger.warning(f"PDF info extraction notice ({e}) for {file_path}")
    return info


class DocumentManager:
    def __init__(self, db_repo=None):
        self.repo = db_repo
        self.storage_dir = DOCUMENTS_BASE_DIR
        self._eligibility_cache: Dict[str, Any] = {}

    def get_tender_storage_dir(self, tender_id: str) -> str:
        safe_id = sanitize_filename(tender_id)
        tdir = os.path.join(self.storage_dir, safe_id)
        os.makedirs(tdir, exist_ok=True)
        return tdir

    def can_auto_fetch(self, tender: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Checks whether direct document download is available from the government source (e.g. GeM).
        Returns download parameters if available, else None.
        """
        if not tender:
            return None

        src = (tender.get("portal_source") or "").lower()
        url = tender.get("portal_url") or ""
        tid = tender.get("tender_id") or ""

        # GeM Direct PDF
        if src == "gem" or tid.startswith("GEM/") or "bidplus.gem.gov.in" in url:
            m = re.search(r'(?:showbidDocument|getBidResultView|showradocumentPdf)/(\d+)', url)
            if m:
                doc_id = m.group(1)
                is_ra = "/R/" in tid or "showradocumentPdf" in url
                download_url = (
                    f"https://bidplus.gem.gov.in/showradocumentPdf/{doc_id}"
                    if is_ra else f"https://bidplus.gem.gov.in/showbidDocument/{doc_id}"
                )
                return {
                    "source": "gem",
                    "doc_id": doc_id,
                    "download_url": download_url,
                    "title": f"Official GeM Bid Notice ({doc_id}).pdf",
                    "doc_type": "Official GeM NIT",
                    "instructions": "Direct official signed government PDF available for automated retrieval."
                }

        return None

    def auto_fetch_document(self, tender_id: str) -> Dict[str, Any]:
        """
        Automatically fetches the official PDF from the portal (e.g. GeM) and attaches it to the tender.
        """
        tender = self.repo.get_tender(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        auto_info = self.can_auto_fetch(tender)
        if not auto_info:
            return {
                "success": False,
                "message": "This portal does not provide a direct PDF download link. Please visit the portal using the Bridge, download the tender pack, and upload it here.",
                "direct_available": False
            }

        download_url = auto_info["download_url"]
        doc_title = auto_info["title"]
        tdir = self.get_tender_storage_dir(tender_id)
        safe_fname = sanitize_filename(doc_title)
        dest_path = os.path.join(tdir, safe_fname)

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                download_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "application/pdf,application/octet-stream,*/*",
                    "Referer": "https://bidplus.gem.gov.in/all-bids"
                }
            )

            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                content = resp.read()

            if not content or len(content) < 500:
                raise ValueError("Downloaded content is empty or incomplete")

            # Check if valid PDF or HTML error page
            if not content.startswith(b"%PDF-"):
                raise ValueError("Downloaded resource is not a valid PDF binary")

            with open(dest_path, "wb") as f:
                f.write(content)

            file_size = len(content)
            pdf_info = extract_pdf_info(dest_path)

            # Record in DB
            doc_id = self._insert_document_record(
                tender_db_id=tender["id"],
                title=doc_title,
                url=f"/api/documents/file?tender_id={urllib.parse.quote(tender_id)}&filename={urllib.parse.quote(safe_fname)}",
                doc_type="OfficialNIT_GeM",
                local_path=dest_path,
                file_size_bytes=file_size,
                page_count=pdf_info.get("page_count", 0),
                text_extracted=1 if pdf_info.get("extracted") else 0
            )

            # Update tender workflow to doc_attached
            self.repo.update_tender_workflow(tender_id, workflow_status="doc_attached")
            self._eligibility_cache.pop(tender_id, None)

            return {
                "success": True,
                "message": f"Successfully retrieved official GeM PDF ({pdf_info.get('page_count', 0)} pages, {file_size / 1024:.1f} KB)",
                "document_id": doc_id,
                "title": doc_title,
                "filename": safe_fname,
                "file_size_bytes": file_size,
                "page_count": pdf_info.get("page_count", 0),
                "download_url": f"/api/documents/file?tender_id={urllib.parse.quote(tender_id)}&filename={urllib.parse.quote(safe_fname)}"
            }

        except Exception as e:
            logger.error(f"Auto-fetch failed for {tender_id}: {e}")
            return {
                "success": False,
                "message": f"Auto-download failed: {str(e)}. Please visit the official portal via the Bridge link and upload the document manually.",
                "direct_available": True
            }

    def save_uploaded_document(
        self,
        tender_id: str,
        filename: str,
        content: bytes,
        doc_type: str = "OfficialNIT_Upload"
    ) -> Dict[str, Any]:
        """
        Saves a user-uploaded document (.pdf, .zip, .xlsx, .docx) and registers it with the tender.
        """
        tender = self.repo.get_tender(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        tdir = self.get_tender_storage_dir(tender_id)
        safe_fname = sanitize_filename(filename)
        dest_path = os.path.join(tdir, safe_fname)

        with open(dest_path, "wb") as f:
            f.write(content)

        file_size = len(content)
        page_count = 0
        text_extracted = 0

        if safe_fname.lower().endswith(".pdf"):
            pdf_info = extract_pdf_info(dest_path)
            page_count = pdf_info.get("page_count", 0)
            text_extracted = 1 if pdf_info.get("extracted") else 0

        doc_id = self._insert_document_record(
            tender_db_id=tender["id"],
            title=safe_fname,
            url=f"/api/documents/file?tender_id={urllib.parse.quote(tender_id)}&filename={urllib.parse.quote(safe_fname)}",
            doc_type=doc_type,
            local_path=dest_path,
            file_size_bytes=file_size,
            page_count=page_count,
            text_extracted=text_extracted
        )

        # Mark tender status as doc_attached
        self.repo.update_tender_workflow(tender_id, workflow_status="doc_attached")
        self._eligibility_cache.pop(tender_id, None)

        return {
            "success": True,
            "document_id": doc_id,
            "filename": safe_fname,
            "file_size_bytes": file_size,
            "page_count": page_count,
            "message": f"Official document '{safe_fname}' attached successfully."
        }

    def list_tender_documents(self, tender_id: str) -> Dict[str, Any]:
        """
        Lists all documents for a tender, distinguishing between attached local files
        and portal-hosted files ready for download.
        """
        tender = self.repo.get_tender(tender_id)
        if not tender:
            return {"items": [], "total": 0, "auto_fetch_available": False}

        auto_fetch_info = self.can_auto_fetch(tender)

        conn = self.repo._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, url, doc_type, local_path, file_size_bytes, page_count, created_at
            FROM tender_documents
            WHERE tender_id_ref = ?
            ORDER BY id ASC
        """, (tender["id"],))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        attached_docs = []
        for r in rows:
            lpath = r.get("local_path")
            is_present = os.path.exists(lpath) if lpath else False
            attached_docs.append({
                "id": r["id"],
                "title": r["title"],
                "doc_type": r["doc_type"],
                "file_size_bytes": r["file_size_bytes"],
                "page_count": r.get("page_count", 0),
                "created_at": r["created_at"],
                "is_local": True,
                "is_present_on_disk": is_present,
                "download_url": f"/api/documents/file?tender_id={urllib.parse.quote(tender_id)}&filename={urllib.parse.quote(sanitize_filename(r['title']))}"
            })

        # Known portal document items that might exist on government site
        portal_docs = []
        if auto_fetch_info:
            auto_info_title = auto_fetch_info["title"]
            portal_docs.append({
                "title": auto_info_title,
                "doc_type": "Official Government NIT",
                "is_direct_downloadable": True,
                "direct_download_url": auto_fetch_info["download_url"],
                "already_attached": any(d["title"] == auto_info_title for d in attached_docs)
            })
        else:
            portal_docs.append({
                "title": f"Tender Notice ({tender.get('reference_no') or tender['tender_id']})",
                "doc_type": "Primary NIT & Specification Pack",
                "is_direct_downloadable": False,
                "portal_url": tender.get("portal_url"),
                "already_attached": len(attached_docs) > 0
            })

        return {
            "tender_id": tender_id,
            "attached_documents": attached_docs,
            "portal_documents": portal_docs,
            "auto_fetch_info": auto_fetch_info,
            "workflow_status": tender.get("workflow_status") or "new",
            "has_official_nit": len(attached_docs) > 0
        }

    def evaluate_eligibility(self, tender_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Runs the Unified AI Qualify & Eligibility Engine against Nikom's Corporate Profile.
        When official documents are uploaded or fetched, analyzes the tender document with
        AWS Bedrock (Claude Sonnet 4.6), extracts all real qualification clauses & BOQ specifications,
        and compares them directly against Nikom's audited corporate benchmarks.
        """
        tender = self.repo.get_tender(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        if not force_refresh and tender_id in self._eligibility_cache:
            return self._eligibility_cache[tender_id]

        # ── Step 1: Check for user-uploaded / attached documents ───────────────
        tdir = self.get_tender_storage_dir(tender_id)
        attached_docs = []
        if os.path.exists(tdir):
            for f in os.listdir(tdir):
                if f.lower().endswith(('.pdf', '.docx', '.txt', '.xlsx')):
                    attached_docs.append(f)

        # ── Step 2: If official document exists, analyze with AWS Bedrock AI ───
        if attached_docs:
            primary_doc = attached_docs[0]
            for f in attached_docs:
                if f.lower().endswith('.pdf'):
                    primary_doc = f
                    break

            doc_path = os.path.join(tdir, primary_doc)
            doc_text = ""
            if primary_doc.lower().endswith('.pdf'):
                pdf_info = extract_pdf_info(doc_path)
                doc_text = pdf_info.get("text", "")
            elif primary_doc.lower().endswith(('.txt', '.docx')):
                try:
                    with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
                        doc_text = f.read()
                except Exception:
                    pass

            if doc_text and len(doc_text.strip()) > 50:
                try:
                    from src.services.bedrock_service import BedrockTenderService
                    bedrock = BedrockTenderService()
                    if bedrock.is_configured():
                        logger.info(f"Running Bedrock Claude Sonnet analysis on uploaded document: '{primary_doc}' for {tender_id}")
                        ai_result = bedrock.evaluate_document_eligibility(tender, primary_doc, doc_text)
                        ai_result["tender_id"] = tender_id
                        ai_result["has_document"] = True
                        ai_result["document_analyzed"] = primary_doc
                        ai_result["attached_documents"] = attached_docs
                        self._eligibility_cache[tender_id] = ai_result
                        return ai_result
                    else:
                        return {
                            "tender_id": tender_id,
                            "has_document": True,
                            "document_analyzed": primary_doc,
                            "attached_documents": attached_docs,
                            "overall_verdict": "AWS Bedrock Not Configured",
                            "verdict_score": 0,
                            "met_criteria_count": 0,
                            "total_criteria_count": 0,
                            "company_evaluated": NIKOM_PROFILE.company_name,
                            "ai_powered": True,
                            "notice": "AWS Bedrock credentials are not configured in .env. Please set BEDROCK_API_KEY to enable AI qualification.",
                            "criteria": [],
                            "generated_at": datetime.utcnow().isoformat()
                        }
                except Exception as e:
                    logger.error(f"Bedrock document evaluation exception ({e}) for {tender_id}")
                    return {
                        "tender_id": tender_id,
                        "has_document": True,
                        "document_analyzed": primary_doc,
                        "attached_documents": attached_docs,
                        "overall_verdict": "AI Evaluation Failed",
                        "verdict_score": 0,
                        "met_criteria_count": 0,
                        "total_criteria_count": 0,
                        "company_evaluated": NIKOM_PROFILE.company_name,
                        "ai_powered": True,
                        "notice": f"Bedrock AI evaluation error: {str(e)}. Click 'Re-Evaluate' to retry.",
                        "criteria": [],
                        "generated_at": datetime.utcnow().isoformat()
                    }
            else:
                return {
                    "tender_id": tender_id,
                    "has_document": True,
                    "document_analyzed": primary_doc,
                    "attached_documents": attached_docs,
                    "overall_verdict": "Scanned Document (OCR Needed)",
                    "verdict_score": 0,
                    "met_criteria_count": 0,
                    "total_criteria_count": 0,
                    "company_evaluated": NIKOM_PROFILE.company_name,
                    "ai_powered": True,
                    "notice": f"The document '{primary_doc}' contains no extractable text (it appears to be a scanned image or protected PDF). Please upload an OCR-searchable PDF or text document to enable AI requirement extraction.",
                    "criteria": [],
                    "generated_at": datetime.utcnow().isoformat()
                }

        # ── Step 3: No document uploaded yet (Clean State, Zero Static Mock Data) ───
        return {
            "tender_id": tender_id,
            "has_document": False,
            "document_analyzed": None,
            "attached_documents": [],
            "overall_verdict": "Awaiting Document Upload",
            "verdict_score": None,
            "met_criteria_count": 0,
            "total_criteria_count": 0,
            "company_evaluated": NIKOM_PROFILE.company_name,
            "ai_powered": True,
            "notice": "No tender document attached yet. Please upload the official tender document (NIT/RFP PDF) or fetch it under 'Documents & Pack'. Once attached, AWS Bedrock will extract all qualification requirements directly from the document and compare them against Nikom's corporate data.",
            "criteria": [],
            "generated_at": datetime.utcnow().isoformat()
        }

    def delete_document(self, tender_id: str, document_id: int):
        """
        Deletes an attached document by ID: removes the physical file from disk
        and deletes the record from tender_documents. If no documents remain,
        reverts workflow_status from doc_attached to new.
        """
        tender = self.repo.get_tender(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        conn = self.repo._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, local_path
            FROM tender_documents
            WHERE id = ? AND tender_id_ref = ?
        """, (document_id, tender["id"]))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise ValueError(f"Document {document_id} not found for tender {tender_id}")

        doc_dict = dict(row)
        lpath = doc_dict.get("local_path")

        if lpath and os.path.exists(lpath):
            try:
                os.remove(lpath)
                logger.info(f"Removed physical document file: {lpath}")
            except Exception as e:
                logger.warning(f"Could not remove file {lpath}: {e}")

        cursor.execute("DELETE FROM tender_documents WHERE id = ?", (document_id,))
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM tender_documents WHERE tender_id_ref = ?", (tender["id"],))
        remaining_count = cursor.fetchone()[0]
        conn.close()

        if remaining_count == 0:
            current_status = tender.get("workflow_status")
            if current_status == "doc_attached":
                self.repo.update_tender_workflow(tender_id, workflow_status="new")

        self._eligibility_cache.pop(tender_id, None)

        return {
            "success": True,
            "message": f"Document '{doc_dict.get('title')}' removed successfully.",
            "remaining_count": remaining_count
        }

    def _insert_document_record(
        self,
        tender_db_id: int,
        title: str,
        url: str,
        doc_type: str,
        local_path: str,
        file_size_bytes: int,
        page_count: int,
        text_extracted: int
    ) -> int:
        conn = self.repo._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tender_documents (
                tender_id_ref, title, url, doc_type, local_path, file_size_bytes, page_count, text_extracted, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tender_db_id, title, url, doc_type, local_path, file_size_bytes, page_count, text_extracted, datetime.utcnow().isoformat()
        ))
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return doc_id
