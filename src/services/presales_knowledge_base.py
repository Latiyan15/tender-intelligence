"""
Presales Project-Centric Knowledge & Memory Base
================================================
Maintains strictly isolated knowledge tiers:
Tier 1: Current Project Knowledge (scoped to active project)
Tier 2: Nikom Company Knowledge (verified corporate credentials & project history)
Tier 3: Product & Engineering Knowledge (standards, datasheets, sizing guidelines)
Tier 4: Commercial Knowledge (tax rules, CAMC escalation, O&M manpower benchmarks)
Tier 5: Proposal Frameworks (modular section skeletons by project category)

Enforces provenance and anti-hallucination isolation across all retrievals.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# TIER 2: VERIFIED NIKOM CORPORATE PROFILE & CREDENTIALS
NIKOM_VERIFIED_CREDENTIALS = {
    "company_name": "Nikom InfraSolutions Pvt. Ltd.",
    "founded_year": 2000,
    "headquarters": "New Delhi, India",
    "track_record": {
        "experience_years": "25+ Years",
        "ai_compute_delivered": "206+ PetaFLOPS",
        "server_racks_deployed": "10,528+ Server Racks",
        "total_mw_commissioned": "55+ MW Critical Capacity",
        "tier_certified_deliveries": "ANSI/TIA-942-C Rated-3 (Tier III Concurrently Maintainable)"
    },
    "certifications": [
        "ISO 9001:2015 (Quality Management System)",
        "ISO 27001:2013 (Information Security Management)",
        "ISO 14001:2015 (Environmental Management)",
        "ISO 45001:2018 (Occupational Health & Safety)",
        "MeitY / STQC Empaneled Security Integrator"
    ],
    "key_project_credentials": [
        {
            "client": "Centre for Development of Telematics (C-DoT), Bengaluru",
            "scope": "Turnkey Tier III Upgradation of 252 kW Data Centre Facility with In-Row DX Cooling, 2N Modular UPS, Li-Ion Batteries, CPCB IV+ DG & STQC CCTV",
            "certification": "ANSI/TIA-942-C Rated-3 Certified",
            "value_range": "₹ 11.5 Cr CAPEX / ₹ 28.75 Cr 5-Year TCO"
        },
        {
            "client": "Bharat Electronics Limited (BEL), Bengaluru",
            "scope": "AI-Ready High-Density Data Centre Infrastructure (2,200 kW – 3,500 kW) with 100 kW Direct-to-Chip Liquid Cooling (DLC), CDUs & Chilled Water",
            "certification": "High-Density AI / GPU Architecture",
            "value_range": "₹ 48.0 Cr Turnkey Scope"
        },
        {
            "client": "NTPC Limited",
            "scope": "Critical Power Infrastructure & 2N Modular Online UPS Deployment with 24×7 Managed Facility Services",
            "certification": "Enterprise Power Redundancy",
            "value_range": "₹ 8.2 Cr Multi-site Scope"
        },
        {
            "client": "Indian Oil Corporation Limited (IOCL)",
            "scope": "Refinery NOC Infrastructure, Clean Agent Fire Suppression (FK-5-1-12) & VESDA Early Warning Aspirating Smoke Detection",
            "certification": "OISD-163 & NFPA 2001 Compliance",
            "value_range": "₹ 6.5 Cr Turnkey Scope"
        },
        {
            "client": "National Informatics Centre (NIC)",
            "scope": "Cloud Edge Data Centre Prefabricated White Space & Environmental Monitoring DCIM Suite",
            "certification": "Tier III Design Standard",
            "value_range": "₹ 14.8 Cr Scope"
        }
    ],
    "oem_alliances": [
        "Schneider Electric / APC (Elite Data Center Partner)",
        "Vertiv (Diamond Solution Partner)",
        "Delta Power Solutions (Authorized Enterprise Partner)",
        "Cummins India (CPCB IV+ Power Generation Partner)",
        "Caterpillar / Perkins (Critical Standby DG Sets)",
        "Cisco Systems / HPE / Dell Technologies (Authorized System Integrator)"
    ]
}


# TIER 3: PRODUCT & ENGINEERING KNOWLEDGE
ENGINEERING_STANDARDS_KNOWLEDGE = {
    "tier_standards": {
        "ANSI/TIA-942-C Rated-3": "Concurrently maintainable infrastructure. Any capacity component or distribution path can be removed/serviced on a planned basis without taking down computer hardware.",
        "ISO/IEC 22237": "International standard for data centre facilities and infrastructures.",
        "ASHRAE TC 9.9 (2021)": "Thermal Guidelines for Data Processing Environments: Recommended server inlet dry bulb 18–27 °C, dew point -9 to 15 °C, max relative humidity 60%."
    },
    "electrical_standards": {
        "IEC 61439-1/2 Form 4b": "Low-voltage switchgear and controlgear assemblies. Form 4b guarantees complete internal physical separation of busbars, functional units, and terminals for concurrent maintenance.",
        "IEC 62040-3": "Uninterruptible power systems (UPS) method of specifying performance and test requirements (VFI-SS-111 double-conversion topology).",
        "CPCB IV+": "Central Pollution Control Board Emission Norms for diesel generator sets up to 800 kW, strictly limiting NOx and particulate matter (effective July 2024)."
    },
    "fire_and_safety_standards": {
        "NFPA 2001 / ISO 14520": "Standard on Clean Agent Fire Extinguishing Systems (FK-5-1-12 / Dodecafluoro-2-methylpentan-3-one). Zero ODP, GWP < 1.",
        "NFPA 75 / 76": "Standard for the Fire Protection of Information Technology Equipment and Telecommunications Facilities.",
        "NBC 2016 Part 4": "National Building Code of India - Fire and Life Safety compliance."
    },
    "battery_technologies": {
        "Li-Ion (LFP)": "Lithium Iron Phosphate. 10–15 year lifespan, 3,500+ cycles, 60% smaller footprint and 70% lower weight than VRLA. Integrated cell-level BMS.",
        "SMF-VRLA": "Sealed Maintenance-Free Valve Regulated Lead-Acid. 3–5 year design life, heavy floor loading requirement, requires replacement at Year 4–5."
    }
}


# TIER 4: COMMERCIAL & PRICING RULES
COMMERCIAL_POLICIES = {
    "gst_rates": {
        "goods_hardware": 0.18, # 18% GST standard
        "services_works_contract": 0.18, # 18% GST works contract
        "exports_sez": 0.0 # 0% GST with LUT
    },
    "escalation_policies": {
        "camc_annual_escalation": 0.05, # 5% per annum for post-warranty maintenance
        "manpower_annual_escalation": 0.06 # 6% statutory minimum wage & inflation adjustment
    },
    "milestone_standards": {
        "psu_government": [
            {"milestone": "Advance against Advance Bank Guarantee (ABG)", "percentage": 15},
            {"milestone": "Supply of major plant equipment at site against MRC", "percentage": 60},
            {"milestone": "Installation, erection & pre-commissioning", "percentage": 15},
            {"milestone": "Integrated Systems Testing (IST), handover against PBG", "percentage": 10}
        ],
        "private_commercial": [
            {"milestone": "Mobilization advance against ABG", "percentage": 20},
            {"milestone": "Equipment delivery against proforma invoice", "percentage": 60},
            {"milestone": "Commissioning, testing & acceptance handover", "percentage": 20}
        ]
    },
    "pricing_integrity_policy": "NEVER invent or fabricate unit rates. If an official vendor rate is unavailable, mark clearly as '[Rate TBD - Vendor Quote Needed]'."
}


class KnowledgeBaseService:
    """
    Unified knowledge retrieval service adhering to strict context isolation.
    """

    def get_company_credentials(self) -> Dict[str, Any]:
        """Returns verified Nikom credentials."""
        return NIKOM_VERIFIED_CREDENTIALS

    def get_engineering_standard(self, standard_key: str) -> Optional[str]:
        """Retrieves technical standard definition."""
        for section in ENGINEERING_STANDARDS_KNOWLEDGE.values():
            if standard_key in section:
                return section[standard_key]
        return None

    def get_relevant_past_projects(self, category: str) -> List[Dict[str, Any]]:
        """
        Retrieves matching verified past projects without cross-contaminating client specifics.
        """
        projects = NIKOM_VERIFIED_CREDENTIALS["key_project_credentials"]
        if "datacentre" in category or "epc" in category:
            return [p for p in projects if "C-DoT" in p["client"] or "BEL" in p["client"] or "NIC" in p["client"]]
        elif "power" in category:
            return [p for p in projects if "NTPC" in p["client"] or "C-DoT" in p["client"]]
        elif "security" in category or "fire" in category:
            return [p for p in projects if "IOCL" in p["client"] or "C-DoT" in p["client"]]
        return projects[:3]

    def get_commercial_rules(self) -> Dict[str, Any]:
        """Returns verified statutory and commercial rules."""
        return COMMERCIAL_POLICIES

    def get_gold_standard_exemplar(self) -> Dict[str, Any]:
        """
        Retrieves the gold-standard C-DoT proposal structural exemplar.
        Used as few-shot memory for Claude to mirror publication-grade visual and executive polish.
        """
        import os
        exemplar_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "reference_proposals", "c_dot_exemplar.json"
        )
        if os.path.exists(exemplar_path):
            try:
                with open(exemplar_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read c_dot_exemplar.json: {e}")
        return {
            "document_title": "Upgradation of C-DoT Tier III Certified Data Centre @ Bengaluru",
            "document_reference": "NIKOM/BD-2026/C-DOT-REV1"
        }

