"""
BOQ (Bill of Quantities) Parser Module
Extracts technical line items, equipment types, ratings, and quantities from tender text / documents.
Identifies Nikom infrastructure assets: UPS, PAC, DG, Racks, PDU, CCTV, Fire Suppression, etc.
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BoqParser:
    """Parses line items and technical specifications from tender text/schedules."""

    EQUIPMENT_TAXONOMY = {
        "UPS": [
            r'\b(?:ups|uninterruptible\s+power\s+supply)\b',
            r'\b(\d+(?:\.\d+)?)\s*(?:kva|kw)\s*(?:online\s+)?ups\b'
        ],
        "PAC_HVAC": [
            r'\b(?:pac|precision\s+air\s+condition(?:er|ing)|inrow\s+cooling|crac|crah|chiller)\b',
            r'\b(\d+(?:\.\d+)?)\s*(?:tr|ton|kw)\s*(?:pac|precision\s+cooling)\b'
        ],
        "BATTERY": [
            r'\b(?:smf|vrla|lithium[- ]ion|li-ion|tubular)\s+batter(?:y|ies)\b',
            r'\b(\d+)\s*(?:ah|v)\s*batter(?:y|ies)\b'
        ],
        "PDU_ELECTRICAL": [
            r'\b(?:pdu|power\s+distribution\s+unit|lt\s+panel|ht\s+panel|amf\s+panel|dg\s+set|diesel\s+generator)\b',
            r'\bisolation\s+transformer\b'
        ],
        "RACKS_CONTAINMENT": [
            r'\b(?:server\s+rack|network\s+rack|42u|48u|24u|aisle\s+containment|cold\s+aisle|hot\s+aisle)\b'
        ],
        "FIRE_SAFETY": [
            r'\b(?:vesda|gas\s+flooding|novec\s*1230|fm[- ]?200|inergen|fire\s+alarm|smoke\s+detector)\b'
        ],
        "IBMS_DCIM": [
            r'\b(?:ibms|bms|building\s+management\s+system|dcim|scada|water\s+leak\s+detection|wlds|rodent\s+repellent)\b'
        ],
        "SECURITY_CCTV": [
            r'\b(?:cctv|ip\s+camera|access\s+control|biometric|boom\s+barrier|turnstile|nvr|dvr)\b'
        ],
        "NETWORKING_CABLING": [
            r'\b(?:structured\s+cabling|cat[- ]?6a?|fiber\s+optic|patch\s+panel|core\s+switch|access\s+switch)\b'
        ],
        "DATA_CENTER_CIVIL": [
            r'\b(?:false\s+flooring|raised\s+access\s+floor|false\s+ceiling|fire\s+rated\s+door)\b'
        ]
    }

    def __init__(self):
        pass

    def parse_equipment_items(self, text: str) -> List[Dict[str, Any]]:
        """Identify infrastructure items, their category, ratings, and quantities mentioned in the text."""
        items = []
        if not text:
            return items

        for category, patterns in self.EQUIPMENT_TAXONOMY.items():
            for pat in patterns:
                for match in re.finditer(pat, text, re.IGNORECASE):
                    matched_str = match.group(0).strip()
                    # Look around the match for quantity patterns e.g. "10 Nos", "Qty: 4", "2 Sets"
                    start = max(0, match.start() - 60)
                    end = min(len(text), match.end() + 60)
                    context_snippet = text[start:end]

                    qty = None
                    qty_match = re.search(r'(?:qty|quantity|nos|sets?)\s*[:=-]?\s*(\d+)', context_snippet, re.IGNORECASE)
                    if qty_match:
                        try:
                            qty = int(qty_match.group(1))
                        except ValueError:
                            pass

                    item_record = {
                        "category": category,
                        "matched_term": matched_str,
                        "context": context_snippet.strip().replace('\n', ' '),
                        "quantity": qty
                    }
                    items.append(item_record)

        # Deduplicate items by matched_term and category
        deduped = []
        seen = set()
        for it in items:
            key = (it["category"], it["matched_term"].lower())
            if key not in seen:
                seen.add(key)
                deduped.append(it)

        return deduped
