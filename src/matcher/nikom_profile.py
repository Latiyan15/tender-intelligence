"""
Nikom InfraSolutions Pvt. Ltd. Company Profile & Capabilities Model
Defines the business domains, technical capabilities, financial criteria,
past track record, and OEM partnerships based on verified empirical contracts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set


@dataclass
class NikomProfile:
    """Comprehensive business profile for Nikom InfraSolutions Pvt. Ltd."""

    company_name: str = "Nikom InfraSolutions Pvt. Ltd."
    founded_year: int = 2002
    headquarters: str = "65, Jyoti Building, Nehru Place, New Delhi, India"
    bankers: str = "ICICI Bank, 65, Jyoti Building, 66, Nehru Place, New Delhi"
    branches: List[str] = field(default_factory=lambda: [
        "Mumbai", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune", "Dehradun"
    ])

    # Core business domains verified by executed contracts
    core_domains: List[str] = field(default_factory=lambda: [
        "Data Center Turnkey EPC & Modernization (Tier I - Tier IV)",
        "Disaster Recovery (DR) Site & Near Site DC Establishment",
        "Server Room Revamping & NOC / Command Center Build",
        "High Capacity & Modular Online UPS (10 KVA - 500 KVA, Monolithic & Modular)",
        "Precision Air Conditioning (PAC) & CRAC/CRAH/Chilled Water Cooling",
        "Clean Agent Fire Suppression (Novec 1230, FM-200, FK-5-1-12) & VESDA",
        "Data Center Infrastructure Management (DCIM) & Centralized Power Monitoring",
        "Server Racks with Cold/Hot Aisle Containment, Smart PDU / iPDU",
        "Next-Generation Firewalls (NGFW), Enterprise Servers & Core Switching",
        "Structured Cabling, OFC Laying & Data Center Pathways",
        "Non-IT Infrastructure Operations & Maintenance (O&M)",
        "Comprehensive Annual Maintenance Contracts (CAMC) & 24x7 Facility Management (FMS)"
    ])

    # Verified clients from historical execution records
    verified_clients: List[str] = field(default_factory=lambda: [
        "ONGC (Oil and Natural Gas Corporation)",
        "IOCL (Indian Oil Corporation Limited)",
        "AAI (Airports Authority of India)",
        "C-DAC (Centre for Development of Advanced Computing)",
        "C-DOT (Centre for Development of Telematics)",
        "NATGRID (National Intelligence Grid)",
        "Power Grid Corporation of India Limited",
        "NTPC Limited",
        "NHPC Limited",
        "Punjab National Bank (PNB)",
        "Bank of India (BOI)",
        "NIC / NICSI (National Informatics Centre)",
        "IIT Hyderabad",
        "IIT Gandhinagar",
        "IIT Roorkee",
        "NIT Trichy",
        "Southern Railway Chennai",
        "Tata Power / TPDDL",
        "UPCL (Uttarakhand Power Corporation Limited)",
        "DRDO (Defence Research and Development Organisation)",
        "GRSE (Garden Reach Shipbuilders & Engineers)"
    ])

    # Domain keywords for NLP/regex matching
    high_match_keywords: Set[str] = field(default_factory=lambda: {
        "data center", "datacenter", "data centre", "server room", "noc", "command center",
        "disaster recovery site", "dr site", "dr center", "near site data centre",
        "precision air conditioning", "precision air conditioner", "precision ac", "pac unit", "crac", "crah", "precision cooling",
        "online ups", "modular ups", "monolithic ups", "high capacity ups", "ups system", "uninterruptible power supply",
        "battery bank", "symetra px", "smart pdu", "ipdu", "power distribution unit",
        "aisle containment", "cold aisle containment", "hot aisle containment", "server rack", "integrated racks infrastructure",
        "false flooring", "raised access floor", "gas flooding", "novec 1230", "fm-200", "vesda", "fire suppression",
        "ibms", "dcim", "centralized power monitoring", "water leak detection", "rodent repellent",
        "next generation firewall", "firewall appliance", "amc of data center", "fms of data center",
        "camc of data center", "non-it infrastructure", "data centre infra management"
    })

    adjacent_match_keywords: Set[str] = field(default_factory=lambda: {
        "cctv", "surveillance system", "access control system", "biometric",
        "structured cabling", "fiber optic cabling", "ofc laying", "lan cabling", "network cabling",
        "electrical substation", "isolation transformer", "ht panel", "lt panel", "dg set", "electrical panel",
        "hvac", "chiller plant", "air handling unit", "ahu",
        "it infrastructure", "hardware supply", "core switch", "blade server", "rack server", "san storage"
    })

    excluded_domains: Set[str] = field(default_factory=lambda: {
        "road construction", "highway", "expressway", "bridge", "culvert", "civil building construction",
        "residential quarters", "staff quarters", "hostel building", "masonry", "plastering",
        "sewage treatment", "stp plant", "septic tank", "drainage work", "water supply pipeline",
        "drinking water fountain", "water cooler", "reverse osmosis", "mineral water plant",
        "medical gas", "hospital bed", "operation theatre", "surgical equipment", "pharmaceutical", "drugs",
        "passenger lift", "elevator", "escalator", "weighbridge", "lorry weighbridge", "bandsaw machine",
        "data entry operator", "computer operator", "peon", "security guard", "safai karmachari",
        "catering", "canteen", "mess service", "vehicle hiring", "car rental", "transportation service",
        "printing of calendars", "stationery", "uniforms", "dredging", "mining", "split air conditioner"
    })

    # Financial thresholds (in INR) based on audited turnover (~Rs. 25-50 Cr)
    annual_turnover_inr: float = 431_717_226.0       # Rs. 43.17 Cr (FY 2019-20 peak)
    projected_turnover_inr: float = 500_000_000.0   # Rs. 50.00 Cr
    min_tender_value_inr: float = 300_000.0         # Rs. 3 Lakhs (e.g. small UPS/refilling jobs)
    sweet_spot_min_inr: float = 1_500_000.0         # Rs. 15 Lakhs
    sweet_spot_max_inr: float = 250_000_000.0       # Rs. 25 Crores
    max_turnover_capacity_inr: float = 1_000_000_000.0 # Rs. 100 Crores (consortium limit)
    single_work_capacity_inr: float = 362_956_764.0  # Rs. 36.3 Crores (C-DOT Mehrauli DC-build record)

    # OEM Partnerships
    partner_oems: List[str] = field(default_factory=lambda: [
        "Schneider Electric", "APC", "Vertiv", "Emerson Network Power",
        "Eaton", "Delta", "Legrand", "Honeywell", "Siemens", "Johnson Controls",
        "Cummins", "Kirloskar", "Cisco", "CommScope", "Panduit", "D-Link", "Fortinet", "Palo Alto"
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
