"""
Nikom InfraSolutions Pvt. Ltd. Company Profile & Capabilities Model
Defines the business domains, technical capabilities, financial criteria,
and OEM partnerships used for automated tender feasibility matching.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set


@dataclass
class NikomProfile:
    """Comprehensive business profile for Nikom InfraSolutions Pvt. Ltd."""

    company_name: str = "Nikom InfraSolutions Pvt. Ltd."
    founded_year: int = 2002
    headquarters: str = "New Delhi, India"
    branches: List[str] = field(default_factory=lambda: [
        "Mumbai", "Bengaluru", "Hyderabad", "Chennai", "Kolkata"
    ])

    # Core business domains
    core_domains: List[str] = field(default_factory=lambda: [
        "Data Center Turnkey EPC (Tier I - Tier IV)",
        "Modular & Containerized Data Centers / Edge Data Centers",
        "Server Room & NOC / Command Center Build",
        "Precision Air Conditioning (PAC) & CRAC/CRAH/Chilled Water",
        "UPS & Critical Power Quality (Online UPS, Isolation Xmer, Battery Systems)",
        "Electrical Distribution (HT/LT Panels, AMF, Cabling, Busducts, DG Sets)",
        "Integrated Building Management Systems (IBMS, DCIM, Environmental Monitoring)",
        "Physical Security & Surveillance (IP CCTV, Access Control, Biometric, Barriers)",
        "Fire Detection & Gas Flooding (VESDA, FM-200, Novec 1230)",
        "Structured Cabling, Server Racks & Cold/Hot Aisle Containment",
        "Annual Maintenance Contracts (AMC) & 24x7 Facility Management (FMS)"
    ])

    # Domain keywords for NLP/regex matching
    high_match_keywords: Set[str] = field(default_factory=lambda: {
        "data center", "datacenter", "server room", "noc", "command center",
        "precision air conditioning", "precision ac", "pac unit", "crac", "crah",
        "online ups", "ups system", "uninterruptible power supply", "pdu", "power distribution unit",
        "aisle containment", "server rack", "network rack", "false flooring", "raised access floor",
        "gas flooding", "novec 1230", "fm-200", "vesda", "fire suppression",
        "ibms", "dcim", "scada", "water leak detection", "rodent repellent",
        "amc of data center", "fms of data center", "maintenance of ups", "pac maintenance"
    })

    adjacent_match_keywords: Set[str] = field(default_factory=lambda: {
        "cctv", "surveillance system", "access control system", "biometric",
        "structured cabling", "fiber optic cabling", "lan cabling", "network cabling",
        "electrical substation", "transformer", "ht panel", "lt panel", "dg set",
        "hvac", "chiller plant", "air handling unit", "ahu", "smart city",
        "it infrastructure", "hardware supply", "core switch", "fire alarm"
    })

    excluded_domains: Set[str] = field(default_factory=lambda: {
        "road construction", "highway", "bridge", "civil building construction",
        "medical equipment", "pharmaceutical", "catering", "canteen", "housekeeping",
        "sanitation", "security guard services", "vehicle hiring", "transportation",
        "printing", "stationery", "clothing", "uniforms", "dredging", "mining"
    })

    # Financial thresholds (in INR)
    min_tender_value_inr: float = 500_000.0          # Rs. 5 Lakhs (minimum project size)
    sweet_spot_min_inr: float = 2_500_000.0         # Rs. 25 Lakhs
    sweet_spot_max_inr: float = 250_000_000.0       # Rs. 25 Crores
    max_turnover_capacity_inr: float = 1_000_000_000.0 # Rs. 100 Crores
    single_work_capacity_inr: float = 300_000_000.0  # Rs. 30 Crores (max single contract capability)

    # OEM Partnerships
    partner_oems: List[str] = field(default_factory=lambda: [
        "Schneider Electric", "APC", "Vertiv", "Emerson Network Power",
        "Eaton", "Delta", "Legrand", "Honeywell", "Siemens", "Johnson Controls",
        "Cummins", "Kirloskar", "Cisco", "CommScope", "Panduit", "D-Link"
    ])

    # Quality Certifications
    certifications: List[str] = field(default_factory=lambda: [
        "ISO 9001:2015 (Quality Management)",
        "ISO 27001:2013 (Information Security)",
        "ISO 20000-1 (IT Service Management)",
        "ISO 14001:2015 (Environmental Management)",
        "ISO 45001:2018 (Occupational Health & Safety)"
    ])


NIKOM_PROFILE = NikomProfile()
