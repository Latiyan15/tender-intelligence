import os
import re
import uuid
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "presales_uploads"
)
os.makedirs(UPLOADS_DIR, exist_ok=True)


def ocr_image_with_bedrock(img_bytes: bytes, filename: str = "scanned_page.png") -> str:
    """
    Transcribes a scanned document page or uploaded image into structured text
    using Bedrock Claude Sonnet 4.6 Vision in ap-southeast-2.
    Preserves exact tables, quantities, technical parameters, and amounts.
    """
    try:
        import boto3
        from botocore.config import Config

        config = Config(read_timeout=120, connect_timeout=20, retries={'max_attempts': 2})
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        session_token = os.getenv("AWS_SESSION_TOKEN")
        region = os.getenv("AWS_REGION", "ap-southeast-2")

        if access_key and secret_key:
            session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token,
                region_name=region
            )
            client = session.client("bedrock-runtime", config=config)
        else:
            profile = os.getenv("AWS_PROFILE", "tender")
            try:
                session = boto3.Session(profile_name=profile, region_name=region)
                client = session.client("bedrock-runtime", config=config)
            except Exception:
                session = boto3.Session(region_name=region)
                client = session.client("bedrock-runtime", config=config)

        ext = os.path.splitext(filename)[1].lower()
        fmt = "png"
        if ext in [".jpg", ".jpeg"]:
            fmt = "jpeg"
        elif ext in [".webp"]:
            fmt = "webp"
        elif ext in [".gif"]:
            fmt = "gif"

        prompt = (
            "You are a specialized tender document transcription and OCR specialist. "
            "Transcribe all text, numbers, tender specifications, tables, bidder criteria, and notes "
            "visible in this document page with 100% exact fidelity. "
            "Structure all tables into clean Markdown tables. Preserve all numbers, quantities, dates, currencies, and amounts."
        )

        res = client.converse(
            modelId="au.anthropic.claude-sonnet-4-6",
            messages=[{
                "role": "user",
                "content": [
                    {"image": {"format": fmt, "source": {"bytes": img_bytes}}},
                    {"text": prompt}
                ]
            }],
            inferenceConfig={"maxTokens": 4096, "temperature": 0.0}
        )
        return res["output"]["message"]["content"][0]["text"].strip()
    except Exception as e:
        logger.warning(f"Bedrock Vision OCR transcription failed for {filename}: {e}")
        return f"[OCR Transcription Error for {filename}: {e}]"


def extract_text_from_uploaded_file(file_path: str) -> str:
    """
    Extracts high-fidelity text from digital and scanned files.
    - Born-digital PDFs: Fast native extraction via PyMuPDF.
    - Scanned/rasterized PDFs: Automatically detects sparse pages and transcribes via Claude Vision OCR.
    - Image files (.png, .jpg, .jpeg, .webp, .bmp, .tiff): Native Claude Vision OCR.
    - Word (.docx, .doc), TXT, CSV, JSON, MD: Native text decoding.
    Results are cached on disk to prevent redundant OCR runs.
    """
    ext = os.path.splitext(file_path)[1].lower()
    cache_path = file_path + ".extracted.txt"

    # 1. Return direct cached text if available and valid (not an error string)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = f.read()
                if cached.strip() and "[OCR Transcription Error" not in cached and "[Error" not in cached:
                    return cached
        except Exception:
            pass

    # 2. Check for existing verified extraction from sibling project uploads of the same file
    base_name = os.path.basename(file_path)
    clean_base = re.sub(r'^PRJ-[A-Za-z0-9]+_doc_[A-Za-z0-9]+_', '', base_name)
    clean_base = re.sub(r'^[a-f0-9]{8}_', '', clean_base)
    uploads_dir = os.path.dirname(file_path)

    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            if fname.endswith(".extracted.txt") and clean_base in fname:
                sib_path = os.path.join(uploads_dir, fname)
                try:
                    with open(sib_path, "r", encoding="utf-8") as sf:
                        sib_cached = sf.read()
                        if sib_cached.strip() and "[OCR Transcription Error" not in sib_cached and "[Error" not in sib_cached and len(sib_cached) > 500:
                            logger.info(f"Reusing verified cached extraction from {fname} for {base_name}")
                            try:
                                with open(cache_path, "w", encoding="utf-8") as wf:
                                    wf.write(sib_cached)
                            except Exception:
                                pass
                            return sib_cached
                except Exception:
                    pass

    extracted_text = ""

    # 1. IMAGES (Direct OCR via Claude Sonnet 4.6 Vision)
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            extracted_text = ocr_image_with_bedrock(img_bytes, filename=os.path.basename(file_path))
        except Exception as e:
            logger.error(f"Error reading image file {file_path}: {e}")
            extracted_text = f"[Error reading image file: {e}]"

    # 2. PDF DOCUMENTS (Hybrid: Fast Digital Extraction + Vision OCR for Scanned Pages)
    elif ext == ".pdf":
        pages = []
        try:
            import pymupdf  # PyMuPDF
            doc = pymupdf.open(file_path)
            total_pages = len(doc)
            logger.info(f"Processing PDF '{os.path.basename(file_path)}' ({total_pages} pages)")

            for idx, page in enumerate(doc):
                txt = page.get_text("text") or ""
                # Check if page is scanned (sparse or no extractable digital text)
                if len(txt.strip()) < 50:
                    logger.info(f"Page {idx+1}/{total_pages} appears scanned/rasterized. Invoking Bedrock Vision OCR...")
                    try:
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        ocr_txt = ocr_image_with_bedrock(img_bytes, filename=f"page_{idx+1}.png")
                        pages.append(f"--- [Page {idx+1} of {total_pages} (Scanned OCR)] ---\n{ocr_txt}")
                    except Exception as ocr_err:
                        logger.warning(f"Failed page {idx+1} OCR: {ocr_err}")
                        pages.append(f"--- [Page {idx+1} of {total_pages}] ---\n{txt.strip()}")
                else:
                    pages.append(f"--- [Page {idx+1} of {total_pages}] ---\n{txt.strip()}")
            doc.close()
            extracted_text = "\n\n".join(pages)

        except Exception as e:
            logger.warning(f"PyMuPDF failed on {file_path}: {e}, falling back to pypdf")
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                for idx, p in enumerate(reader.pages):
                    txt = p.extract_text() or ""
                    if txt.strip():
                        pages.append(f"--- [Page {idx+1}] ---\n{txt.strip()}")
                extracted_text = "\n\n".join(pages)
            except Exception as e2:
                logger.error(f"pypdf fallback also failed: {e2}")
                extracted_text = f"[Error reading PDF: {e2}]"

    # 3. WORD DOCUMENTS (.docx)
    elif ext in [".docx", ".doc"]:
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(file_path) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                texts = [node.text for node in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                extracted_text = " ".join(texts)
        except Exception as e:
            logger.error(f"Error reading docx: {e}")
            extracted_text = f"[Error reading Word document: {e}]"

    # 4. PLAIN TEXT / CSV / JSON / MD
    else:
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    extracted_text = f.read()
                    break
            except Exception:
                continue
        if not extracted_text:
            extracted_text = "[Could not decode text file]"

    # Cache extracted text to disk ONLY if valid and not an error
    if extracted_text and not extracted_text.startswith("[Error") and "[OCR Transcription Error" not in extracted_text:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
        except Exception as cache_err:
            logger.debug(f"Could not write cache file: {cache_err}")

    return extracted_text


def extract_quick_dc_params(text: str) -> Dict[str, Any]:
    """
    Extracts key procurement parameters across all domains:
    - Data Centre (IT kW, racks, cooling, redundancy)
    - IT Hardware Supply (desktops, laptops, printers, quantities)
    - Power / UPS (kVA, battery VAH, standards)
    - General (Client/Buyer org, EMD, estimated cost, tender reference)
    """
    params: Dict[str, Any] = {}
    lower = text.lower()

    # 1. Tender Reference / Bid Number
    ref_match = re.search(r'(?:bid\s*no|tender\s*ref|tender\s*no|nit\s*no|ra\s*no|gem/\d{4}/[a-z]/\d+)[\:\s\-]+([A-Za-z0-9_\/\.\-]+)', text, re.I)
    if ref_match:
        params["tender_id"] = ref_match.group(1).strip()
    elif "gem/" in lower:
        gem_m = re.search(r'gem/\d{4}/[a-z]/\d+', text, re.I)
        if gem_m:
            params["tender_id"] = gem_m.group(0).strip()

    # 2. Client / Buyer Organization
    org_match = re.search(r'(?:issuing\s*authority|buyer|department|organisation|organization|ministry|submitted\s*to|client)[\:\s\-]+([A-Za-z0-9\.\,\s\-\(\)]{3,70})', text, re.I)
    if org_match:
        cand = org_match.group(1).split("\n")[0].strip()
        if len(cand) > 3 and not any(w in cand.lower() for w in ["date", "document", "contents", "table", "version", "reference"]):
            params["client_org"] = cand

    # 3. Category Detection
    is_dc = any(w in lower for w in ["data centre", "data center", "server room", "tier iii", "tier iv", "in-row", "cold aisle", "hot aisle"])
    is_ups = any(w in lower for w in ["online ups", "modular ups", "is 16242", "vah", "smf battery", "battery bank"])
    is_hw = any(w in lower for w in ["desktop", "laptop", "printer", "workstation", "scanner", "peripherals", "monitor"])

    if is_dc:
        params["category"] = "datacentre_turnkey"
    elif is_ups:
        params["category"] = "power_electrical"
    elif is_hw:
        params["category"] = "equipment_supply"
    else:
        params["category"] = "general_procurement"

    # 4. Data Centre Specific Parameters
    if is_dc:
        it_match = re.search(r'(?:it\s*load|design\s*it\s*load|capacity|it\s*power)[^\d]{1,25}(\d+(?:\.\d+)?)\s*(?:kw|kwe|kilowatt|mw)', text, re.I)
        if it_match:
            val = float(it_match.group(1))
            if "mw" in it_match.group(0).lower():
                val = val * 1000.0
            params["it_load_kw"] = val

        rack_match = re.search(r'(\d+)\s*(?:nos\.?|numbers|server\s*racks|racks|cabinets)', text, re.I)
        if rack_match:
            params["rack_count"] = int(rack_match.group(1))

        kw_rack_match = re.search(r'(\d+(?:\.\d+)?)\s*kw\s*(?:per|/)\s*rack', text, re.I)
        if kw_rack_match:
            params["kw_per_rack"] = float(kw_rack_match.group(1))

        if re.search(r'tier\s*iv|rated-4|2n\+1', text, re.I):
            params["redundancy"] = "Tier IV (2N+1 Fault Tolerant)"
        elif re.search(r'tier\s*iii|rated-3|concurrently\s*maintainable|2n\s*power', text, re.I):
            params["redundancy"] = "Tier III (2N Power, N+1 Cooling)"
        elif re.search(r'tier\s*ii|rated-2|n\+1', text, re.I):
            params["redundancy"] = "Tier II (N+1 Redundant)"

        if re.search(r'liquid\s*cooling|dlc|direct-to-chip|cdu', text, re.I):
            params["cooling_type"] = "Direct-to-Chip Liquid Cooling (DLC) + In-Row"
        elif re.search(r'chilled\s*water|chiller', text, re.I):
            params["cooling_type"] = "Chilled Water with In-Row / PAHU"
        elif re.search(r'in-row|inrow|dx', text, re.I):
            params["cooling_type"] = "Inverter DX In-Row with Hot-Aisle Containment"

    # 5. Hardware / UPS Parameters
    if is_hw or is_ups:
        items = []
        for line in text.split("\n"):
            line_str = line.strip()
            if any(k in line_str.lower() for k in ["desktop", "laptop", "printer", "ups", "server", "switch", "scanner"]):
                if len(line_str) < 120:
                    items.append(line_str)
        if items:
            params["hardware_items"] = items[:5]

    # 6. Commercial Cost / EMD
    cost_m = re.search(r'(?:estimated\s*cost|tender\s*value|value)[\:\s\-]+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)', text, re.I)
    if cost_m:
        params["estimated_cost"] = cost_m.group(1).strip()

    emd_m = re.search(r'(?:emd|earnest\s*money)[\:\s\-]+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)', text, re.I)
    if emd_m:
        params["emd"] = emd_m.group(1).strip()

    return params
