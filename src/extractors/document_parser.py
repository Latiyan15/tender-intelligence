"""
Document Parser Module
Extracts text and structured sections from tender documents (PDFs, HTML, text).
Handles searchable PDFs, extracts tables, and identifies key document sections.
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
import pypdf

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parses tender documents (primarily PDFs) to extract text and structured content."""

    SECTION_PATTERNS = {
        "scope_of_work": [
            r"(?:scope\s+of\s+work|brief\s+scope|work\s+description|schedule\s+of\s+requirements)",
            r"(?:technical\s+specifications|specifications\s+and\s+scope)",
            r"(?:project\s+overview|objective\s+of\s+the\s+work)"
        ],
        "eligibility_criteria": [
            r"(?:eligibility\s+criteria|qualifying\s+requirements|pre-?qualification\s+criteria)",
            r"(?:bidder\s+eligibility|minimum\s+eligibility\s+conditions)",
            r"(?:technical\s+and\s+financial\s+eligibility|eligibility\s+conditions)"
        ],
        "financial_commercial": [
            r"(?:commercial\s+terms|financial\s+bid|terms\s+of\s+payment|payment\s+terms)",
            r"(?:earnest\s+money\s+deposit|emd|tender\s+fee|performance\s+security|security\s+deposit)",
            r"(?:price\s+schedule|bill\s+of\s+quantit(?:y|ies)|boq)"
        ],
        "submission_timeline": [
            r"(?:critical\s+dates|tender\s+schedule|key\s+dates|important\s+dates)",
            r"(?:date\s+and\s+time\s+schedule|schedule\s+of\s+events)"
        ],
        "instructions_to_bidders": [
            r"(?:instruction[s]?\s+to\s+bidder[s]?|general\s+terms\s+and\s+conditions|gtc)",
            r"(?:special\s+terms\s+and\s+conditions|stc|invitation\s+for\s+bids|ifb)"
        ]
    }

    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 50) -> Dict[str, Any]:
        """
        Extract text from a PDF document.
        Returns extracted text, page count, searchable flag, and extracted sections.
        """
        result = {
            "success": False,
            "filepath": pdf_path,
            "filename": os.path.basename(pdf_path),
            "num_pages": 0,
            "extracted_pages": 0,
            "total_chars": 0,
            "is_searchable": False,
            "full_text": "",
            "sections": {},
            "error": None
        }

        if not os.path.exists(pdf_path):
            result["error"] = f"File not found: {pdf_path}"
            return result

        try:
            with open(pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                num_pages = len(reader.pages)
                result["num_pages"] = num_pages

                pages_to_read = min(num_pages, max_pages)
                page_texts = []

                for page_idx in range(pages_to_read):
                    try:
                        page = reader.pages[page_idx]
                        text = page.extract_text() or ""
                        page_texts.append(text)
                    except Exception as pe:
                        logger.warning(f"Error reading page {page_idx} of {pdf_path}: {pe}")
                        page_texts.append("")

                full_text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts)
                result["full_text"] = full_text
                result["extracted_pages"] = pages_to_read
                result["total_chars"] = len(full_text.strip())

                # A PDF is deemed searchable if reasonable alphanumeric density is found
                clean_text = re.sub(r'\s+', '', full_text)
                if len(clean_text) > 100:
                    result["is_searchable"] = True
                else:
                    result["is_searchable"] = False
                    result["error"] = "Document appears to be a scanned image or empty (no text extracted)"

                # Segment into recognized sections
                result["sections"] = self._segment_sections(full_text)
                result["success"] = True

        except Exception as e:
            logger.error(f"Failed to extract PDF {pdf_path}: {e}")
            result["error"] = str(e)

        return result

    def _segment_sections(self, text: str) -> Dict[str, str]:
        """Segment raw text into domain sections using heading regexes."""
        sections = {}
        for section_name, patterns in self.SECTION_PATTERNS.items():
            matched_blocks = []
            for pat in patterns:
                matches = list(re.finditer(pat, text, re.IGNORECASE))
                for m in matches:
                    start_pos = m.start()
                    # Capture up to 3000 chars after the header or until next major section
                    snippet = text[start_pos:start_pos + 3000]
                    matched_blocks.append(snippet)
            if matched_blocks:
                sections[section_name] = "\n\n...[NEXT MATCH]...\n\n".join(matched_blocks)
        return sections
