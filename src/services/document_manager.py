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

    def evaluate_eligibility(self, tender_id: str) -> Dict[str, Any]:
        """
        Runs the 1-Page Qualify Eligibility Engine against Nikom's Corporate Profile.
        If official documents are uploaded/attached, analyzes the uploaded document with
        AWS Bedrock (Claude Sonnet 4.6) and compares extracted requirements against Nikom data.
        """
        tender = self.repo.get_tender(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        # ── Step 1: Check for user-uploaded / attached documents ───────────────
        tdir = self.get_tender_storage_dir(tender_id)
        attached_docs = []
        if os.path.exists(tdir):
            for f in os.listdir(tdir):
                if f.lower().endswith(('.pdf', '.docx', '.txt', '.xlsx')):
                    attached_docs.append(f)

        # If an official document has been uploaded, analyze it with AWS Bedrock AI
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
                        ai_result["attached_documents"] = attached_docs
                        return ai_result
                except Exception as e:
                    logger.error(f"Bedrock document evaluation exception ({e}), falling back to heuristic profile matching.")

        # ── Step 2: Baseline / Heuristic Evaluation (Prior to Document Upload) ─
        est_cost = tender.get("estimated_cost_inr") or 0.0
        emd_amt = tender.get("emd_inr") or 0.0
        doc_fee = tender.get("doc_fee_inr") or 0.0
        deadline = tender.get("submission_deadline")
        tier = (tender.get("highest_tier") or "B").upper()

        criteria = []

        # 1. Annual Financial Turnover
        # Typical requirement: 30% to 50% of tender value over past 3 financial years
        required_turnover = est_cost * 0.4 if est_cost > 0 else 50000000.0  # default 5 Cr
        turnover_met = NIKOM_PROFILE.audited_3yr_avg_turnover_cr * 10000000 >= required_turnover
        criteria.append({
            "key": "turnover",
            "name": "Annual Financial Turnover",
            "requirement": f"Average turnover of ₹ {required_turnover / 10000000:.2f} Cr over last 3 FYs" if est_cost else "Required average turnover (typically 40% of value)",
            "nikom_profile": f"Audited Avg: ₹ {NIKOM_PROFILE.audited_3yr_avg_turnover_cr:.2f} Cr (Peak: ₹ {NIKOM_PROFILE.peak_turnover_cr:.2f} Cr | Prov 3-Yr Avg: ₹ {NIKOM_PROFILE.current_3yr_avg_turnover_cr:.2f} Cr)",
            "status": "Met" if turnover_met else "Check",
            "badge_color": "green" if turnover_met else "amber",
            "notes": "Verified against audited balance sheets: FY23 ₹48.50 Cr, FY24 ₹67.18 Cr, FY25 ₹91.21 Cr, FY26 Prov ₹123.07 Cr."
        })

        # 2. Net Worth & Financial Health
        net_worth_cr = NIKOM_PROFILE.net_worth_fy25_cr
        criteria.append({
            "key": "net_worth",
            "name": "Net Worth & Financial Solvency",
            "requirement": "Positive Net Worth as of March 31 with profitable operations in last 3 FYs",
            "nikom_profile": f"Net Worth: ₹ {net_worth_cr:.2f} Cr (FY25 Audited) / ₹ {NIKOM_PROFILE.net_worth_fy26_prov_cr:.2f} Cr (FY26 Prov) | Zero Debt (0.00x)",
            "status": "Met",
            "badge_color": "green",
            "notes": f"100% positive net worth across all years, 3 of 3 profitable years (PAT FY25 ₹8.45 Cr), Current Ratio {NIKOM_PROFILE.current_ratio}x, Working Capital ₹{NIKOM_PROFILE.working_capital_cr:.2f} Cr."
        })

        # 3. Similar Work Past Experience (The 80% / 50% / 40% Rule)
        single_work_req = est_cost * 0.8 if est_cost > 0 else 0.0
        exp_met = single_work_req <= 216800000.0 or est_cost == 0.0  # Compared to AAI Hyderabad Rs 21.68 Cr
        criteria.append({
            "key": "experience",
            "name": "Similar Work Past Experience",
            "requirement": f"SITC completion in {tender.get('primary_category') or 'Data Center / IT Infra'} ({'Single work of ₹ ' + f'{single_work_req/10000000:.2f} Cr (80%)' if single_work_req else 'Relevant client completion credentials'})",
            "nikom_profile": "Verified completed contracts: AAI Hyderabad (₹21.68 Cr), ONGC Vasudhara Bhavan (₹20.40 Cr), AAI 10 Airports (₹25.93 Cr), ONGC Panvel (₹5.14 Cr).",
            "status": "Met" if exp_met else "Check",
            "badge_color": "green" if exp_met else "amber",
            "notes": f"Total completed works in record: ₹162.24 Cr. Active in-hand order book: ₹{NIKOM_PROFILE.order_in_hand_cr:.2f} Cr (NATGRID, C-DAC, Alliance L&T, IOCL)."
        })

        # 4. Bid Capacity
        bid_cap_req = est_cost if est_cost > 0 else 0.0
        bid_cap_met = NIKOM_PROFILE.calculated_bid_capacity_inr >= bid_cap_req
        criteria.append({
            "key": "bid_capacity",
            "name": "Calculated Bid Capacity (A x N x 2 - B)",
            "requirement": f"Available bid capacity >= ₹ {est_cost / 10000000:.2f} Cr" if est_cost else "Bid capacity covering estimated contract value",
            "nikom_profile": f"₹ {NIKOM_PROFILE.calculated_bid_capacity_cr:.2f} Crores available capacity",
            "status": "Met" if bid_cap_met else "Check",
            "badge_color": "green" if bid_cap_met else "amber",
            "notes": f"Assessed based on peak annual turnover and ₹{NIKOM_PROFILE.order_in_hand_cr:.2f} Cr existing commitments."
        })

        # 5. Quality & Security Certifications
        req_certs = ["ISO 9001:2015", "ISO 27001:2022"]
        if tier == "A":
            req_certs.append("CMMI Level 3")
        criteria.append({
            "key": "certifications",
            "name": "Quality & Process Certifications",
            "requirement": "Valid " + ", ".join(req_certs),
            "nikom_profile": "ISO 9001:2015, ISO 27001:2022, ISO 20000-1:2018, ISO 14001:2015, ISO 45001:2018, CMMI Level 3 (Active)",
            "status": "Met",
            "badge_color": "green",
            "notes": "All required Quality, InfoSec & IT Service management certifications active with international accreditation."
        })

        # 6. EMD & Bid Security
        if emd_amt > 0:
            criteria.append({
                "key": "emd",
                "name": "Earnest Money Deposit (EMD)",
                "requirement": f"₹ {emd_amt:,.2f} via BG / FDR (or MSME / UDYAM Exemption)",
                "nikom_profile": f"{NIKOM_PROFILE.enterprise_type} (UDYAM registered; ICICI Bank Guarantee limit available)",
                "status": "Met",
                "badge_color": "green",
                "notes": "Eligible for statutory UDYAM exemption; if tender strictly restricts exemption to Micro/Small (MSE), ICICI Bank Guarantee can be provided."
            })
        else:
            criteria.append({
                "key": "emd",
                "name": "Earnest Money Deposit (EMD)",
                "requirement": "Nil / Exempted / Bid Security Declaration",
                "nikom_profile": "Standard Bid Security Declaration available on company letterhead",
                "status": "Met",
                "badge_color": "green",
                "notes": "No advance cash deposit or Bank Guarantee requested in notice."
            })

        # 7. Key Submission Dates
        is_past = False
        if deadline:
            try:
                dl_clean = deadline.replace("Z", "+00:00")
                dl_dt = datetime.fromisoformat(dl_clean)
                is_past = dl_dt.timestamp() < datetime.utcnow().timestamp()
            except Exception:
                pass

        criteria.append({
            "key": "timeline",
            "name": "Bid Timeline & Deadlines",
            "requirement": f"Submission by: {deadline[:16].replace('T', ' ') if deadline else 'Check Official Pack'}",
            "nikom_profile": "Bidding team ready for 48h fast-track proposal turnaround",
            "status": "Not Met" if is_past else "Met",
            "badge_color": "red" if is_past else "green",
            "notes": "Submission period active." if not is_past else "Bid submission window has concluded."
        })

        met_count = sum(1 for c in criteria if c["status"] == "Met")
        total_count = len(criteria)
        overall_verdict = "Qualified" if met_count >= 4 else "Review Required"

        return {
            "tender_id": tender_id,
            "overall_verdict": overall_verdict,
            "verdict_score": round((met_count / total_count) * 100),
            "met_criteria_count": met_count,
            "total_criteria_count": total_count,
            "company_evaluated": NIKOM_PROFILE["company_name"],
            "document_analyzed": None,
            "ai_powered": False,
            "notice": "Preliminary baseline. Upload the official tender document / RFP above to run deep AI qualification against Nikom data.",
            "criteria": criteria,
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
