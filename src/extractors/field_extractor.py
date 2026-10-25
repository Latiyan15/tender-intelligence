"""
Field Extractor Module
Extracts normalized commercial, timeline, eligibility, and technical fields from tender text/HTML.
Supports Indian tender conventions (Lakhs, Crores, INR, Indian date formats, standard clauses).
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from src.models.tender import ExtractedField, FieldStatus

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extracts and normalizes tender fields from unstructured text or structured HTML tables."""

    MONTH_MAP = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    # Regex patterns for amounts
    AMOUNT_PATTERNS = [
        # Rs. 1,23,45,678 / INR 1,23,45,678 / ₹ 123456
        r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)\s*(?:/-)?',
        # Rs 15.5 Lakhs / Crores
        r'(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)\s*(crores?|cr\.?|lakhs?|lacs?|k)\b',
    ]

    DATE_PATTERNS = [
        # 25-10-2026 or 25/10/2026 or 25.10.2026
        r'\b(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})\b',
        # 25-Oct-2026 or 25-October-2026
        r'\b(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{4})\b',
        # 2026-10-25
        r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b'
    ]

    def __init__(self):
        pass

    def parse_amount_in_inr(self, text: str) -> Optional[float]:
        """
        Extract numerical amount in INR from text, handling Lakhs, Crores, commas.
        Returns amount in INR as float, or None.
        """
        if not text:
            return None

        # Check for Lakhs / Crores explicitly
        cr_match = re.search(r'([\d,]+(?:\.\d{1,2})?)\s*(?:cr\.?|crores?)\b', text, re.IGNORECASE)
        if cr_match:
            try:
                num = float(cr_match.group(1).replace(',', ''))
                return num * 10_000_000.0
            except ValueError:
                pass

        lakh_match = re.search(r'([\d,]+(?:\.\d{1,2})?)\s*(?:lacs?|lakhs?)\b', text, re.IGNORECASE)
        if lakh_match:
            try:
                num = float(lakh_match.group(1).replace(',', ''))
                return num * 100_000.0
            except ValueError:
                pass

        # Check standard currency number
        curr_match = re.search(r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)', text, re.IGNORECASE)
        if curr_match:
            try:
                num_str = curr_match.group(1).replace(',', '')
                val = float(num_str)
                if val > 0:
                    return val
            except ValueError:
                pass

        # Raw number match if formatted with commas (e.g. 15,00,000)
        comma_num = re.search(r'\b\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?\b', text)
        if comma_num:
            try:
                val = float(comma_num.group(0).replace(',', ''))
                return val
            except ValueError:
                pass

        return None

    def parse_date_string(self, text: str) -> Optional[datetime]:
        """Parse various Indian government tender date strings into datetime."""
        if not text:
            return None

        # Pattern 1: DD-MM-YYYY or DD/MM/YYYY
        m1 = re.search(r'\b(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})\b', text)
        if m1:
            try:
                d, m, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
                if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= y <= 2035:
                    return datetime(y, m, d)
            except Exception:
                pass

        # Pattern 2: DD-Mon-YYYY (e.g. 25-Oct-2026)
        m2 = re.search(r'\b(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{4})\b', text)
        if m2:
            try:
                d = int(m2.group(1))
                mon_str = m2.group(2)[:3].lower()
                y = int(m2.group(3))
                if mon_str in self.MONTH_MAP and 1 <= d <= 31 and 2000 <= y <= 2035:
                    return datetime(y, self.MONTH_MAP[mon_str], d)
            except Exception:
                pass

        # Pattern 3: YYYY-MM-DD
        m3 = re.search(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b', text)
        if m3:
            try:
                y, m, d = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
                if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= y <= 2035:
                    return datetime(y, m, d)
            except Exception:
                pass

        return None

    def extract_emd(self, text: str) -> ExtractedField:
        """Extract EMD amount, percentage, or exemption."""
        field = ExtractedField(field_name="emd_amount")

        # Check exemption
        if re.search(r'\b(?:emd\s+exempt(?:ed)?|nil\s+emd|no\s+emd|emd\s*:\s*(?:nil|exempted|not\s+applicable|na))\b', text, re.IGNORECASE):
            field.raw_text = "Exempted / Nil"
            field.normalized_value = 0.0
            field.status = FieldStatus.PRESENT_EXTRACTED
            field.confidence = 0.95
            field.verified = True
            return field

        # Search around 'EMD' or 'Earnest Money'
        for m in re.finditer(r'\b(?:emd|earnest\s+money)\b', text, re.IGNORECASE):
            start = max(0, m.start() - 10)
            end = min(len(text), m.end() + 100)
            snip = text[start:end]

            amt = self.parse_amount_in_inr(snip)
            if amt is not None:
                field.raw_text = snip.strip().replace('\n', ' ')
                field.normalized_value = amt
                field.status = FieldStatus.PRESENT_EXTRACTED
                field.confidence = 0.90
                field.verified = True
                return field

            # Check percentage e.g. "2% of estimated cost"
            pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*of\s*(?:estimated|tender)', snip, re.IGNORECASE)
            if pct_match:
                field.raw_text = snip.strip().replace('\n', ' ')
                field.normalized_value = f"{pct_match.group(1)}%"
                field.status = FieldStatus.PRESENT_EXTRACTED
                field.confidence = 0.85
                field.verified = True
                return field

        field.status = FieldStatus.ABSENT_FROM_SOURCE
        return field

    def extract_tender_fee(self, text: str) -> ExtractedField:
        """Extract Tender Fee / Document Cost."""
        field = ExtractedField(field_name="tender_fee")

        if re.search(r'\b(?:tender\s+fee|cost\s+of\s+tender|doc(?:ument)?\s+fee)\s*:\s*(?:nil|free|exempted|zero|na)\b', text, re.IGNORECASE):
            field.raw_text = "Nil / Exempted"
            field.normalized_value = 0.0
            field.status = FieldStatus.PRESENT_EXTRACTED
            field.confidence = 0.95
            field.verified = True
            return field

        for m in re.finditer(r'\b(?:tender\s+fee|cost\s+of\s+(?:bidding\s+)?document|doc(?:ument)?\s+fee)\b', text, re.IGNORECASE):
            start = max(0, m.start() - 10)
            end = min(len(text), m.end() + 100)
            snip = text[start:end]

            amt = self.parse_amount_in_inr(snip)
            if amt is not None:
                field.raw_text = snip.strip().replace('\n', ' ')
                field.normalized_value = amt
                field.status = FieldStatus.PRESENT_EXTRACTED
                field.confidence = 0.90
                field.verified = True
                return field

        field.status = FieldStatus.ABSENT_FROM_SOURCE
        return field

    def extract_estimated_value(self, text: str) -> ExtractedField:
        """Extract Estimated Tender Value."""
        field = ExtractedField(field_name="estimated_value")

        for m in re.finditer(r'\b(?:estimated\s+(?:tender\s+)?(?:cost|value)|tender\s+value|total\s+estimated\s+cost|contract\s+value)\b', text, re.IGNORECASE):
            start = max(0, m.start() - 10)
            end = min(len(text), m.end() + 100)
            snip = text[start:end]

            amt = self.parse_amount_in_inr(snip)
            if amt is not None:
                field.raw_text = snip.strip().replace('\n', ' ')
                field.normalized_value = amt
                field.status = FieldStatus.PRESENT_EXTRACTED
                field.confidence = 0.90
                field.verified = True
                return field

        field.status = FieldStatus.ABSENT_FROM_SOURCE
        return field

    def extract_submission_deadline(self, text: str) -> ExtractedField:
        """Extract submission end date & time."""
        field = ExtractedField(field_name="submission_deadline")

        for m in re.finditer(r'\b(?:bid\s+submission\s+end\s+date|submission\s+deadline|last\s+date\s+(?:and\s+time\s+)?(?:for\s+receipt|of\s+submission|of\s+tender)|closing\s+date)\b', text, re.IGNORECASE):
            start = max(0, m.start() - 10)
            end = min(len(text), m.end() + 100)
            snip = text[start:end]

            dt = self.parse_date_string(snip)
            if dt:
                field.raw_text = snip.strip().replace('\n', ' ')
                field.normalized_value = dt.strftime("%Y-%m-%d")
                field.status = FieldStatus.PRESENT_EXTRACTED
                field.confidence = 0.90
                field.verified = True
                return field

        field.status = FieldStatus.ABSENT_FROM_SOURCE
        return field

    def extract_turnover_requirement(self, text: str) -> ExtractedField:
        """Extract minimum annual financial turnover requirement."""
        field = ExtractedField(field_name="minimum_turnover")

        for m in re.finditer(r'\b(?:annual\s+(?:financial\s+)?turnover|average\s+turnover|turnover\s+of\s+the\s+bidder)\b', text, re.IGNORECASE):
            start = max(0, m.start() - 10)
            end = min(len(text), m.end() + 100)
            snip = text[start:end]

            amt = self.parse_amount_in_inr(snip)
            if amt is not None:
                field.raw_text = snip.strip().replace('\n', ' ')
                field.normalized_value = amt
                field.status = FieldStatus.PRESENT_EXTRACTED
                field.confidence = 0.85
                field.verified = True
                return field

        field.status = FieldStatus.ABSENT_FROM_SOURCE
        return field

    def extract_experience_requirement(self, text: str) -> ExtractedField:
        """Extract work experience criteria (e.g. 3 works of 40%, 7 years)."""
        field = ExtractedField(field_name="experience_requirement")

        matches = re.findall(r'(?:experience\s+of\s+having\s+successfully\s+completed|past\s+experience|similar\s+completed\s+works|eligibility\s+criteria\s+for\s+work\s+experience)[^.\n]{0,250}', text, re.IGNORECASE)
        if matches:
            best_match = matches[0].strip()
            field.raw_text = best_match
            field.normalized_value = best_match
            field.status = FieldStatus.PRESENT_EXTRACTED
            field.confidence = 0.80
            field.verified = True
            return field

        field.status = FieldStatus.ABSENT_FROM_SOURCE
        return field

    def extract_certifications(self, text: str) -> List[ExtractedField]:
        """Extract required quality/security certifications (ISO 9001, 27001, etc.)."""
        found_certs = []
        known_certs = [
            ("ISO 9001", r'\biso\s*9001(?::2015)?\b'),
            ("ISO 27001", r'\biso\s*(?:iec\s*)?27001(?::2013|:2022)?\b'),
            ("ISO 20000", r'\biso\s*(?:iec\s*)?20000(?:-1)?\b'),
            ("ISO 14001", r'\biso\s*14001\b'),
            ("ISO 45001", r'\biso\s*45001\b'),
            ("TIA-942", r'\btia\s*[-]?\s*942\b'),
            ("CMMI Level 3+", r'\bcmmi\s*(?:dev|services)?\s*(?:level|maturity)?\s*[345]\b'),
            ("Uptime Institute Tier", r'\buptime\s+institute\b')
        ]

        for cert_name, pattern in known_certs:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                ef = ExtractedField(
                    field_name=f"certification_{cert_name.lower().replace(' ', '_')}",
                    raw_text=m.group(0),
                    normalized_value=cert_name,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.95,
                    verified=True
                )
                found_certs.append(ef)

        return found_certs

    def extract_oem_requirements(self, text: str) -> ExtractedField:
        """Extract OEM authorization / MAF requirements."""
        field = ExtractedField(field_name="oem_requirements")

        m = re.search(r'(?:manufacturer\s+authori[zs]ation\s+(?:form|letter|certificate)|maf\b|oem\s+authori[zs]ation|authorized\s+partner\s+of\s+oem)[^.\n]{0,150}', text, re.IGNORECASE)
        if m:
            field.raw_text = m.group(0).strip()
            field.normalized_value = True
            field.status = FieldStatus.PRESENT_EXTRACTED
            field.confidence = 0.90
            field.verified = True
            return field

        field.status = FieldStatus.ABSENT_FROM_SOURCE
        field.normalized_value = False
        return field
