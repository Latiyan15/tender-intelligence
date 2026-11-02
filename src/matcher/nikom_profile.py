"""
Nikom InfraSolutions Pvt. Ltd. Company Profile & Capabilities Model
Defines the business domains, technical capabilities, verified audited financials,
past completed works, active order book, and OEM partnerships based on verified
corporate records and financial filings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Optional


@dataclass
class CompletedWork:
    client: str
    work_name: str
    po_no: str
    completed_value_cr: float
    completion_date: str
    within_lookback: bool
    has_completion_certificate: bool
    include_in_eval: bool


@dataclass
class ActiveOrder:
    client: str
    order_name: str
    order_value_cr: float
    contract_no: str
    contract_date: str


@dataclass
class NikomProfile:
    """Comprehensive, audited business profile for Nikom InfraSolutions Pvt. Ltd."""

    company_name: str = "Nikom InfraSolutions Pvt. Ltd."
    founded_year: int = 2002
    years_in_business: int = 22
    headquarters: str = "65, Jyoti Building, Nehru Place, New Delhi - 110019, India"
    bankers: str = "ICICI Bank, 65, Jyoti Building, 66, Nehru Place, New Delhi"
    branches: List[str] = field(default_factory=lambda: [
        "Mumbai", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune", "Dehradun"
    ])

    # Enterprise Classification
    enterprise_type: str = "Medium Enterprise"  # Under MSME / UDYAM (Turnover ~Rs. 123 Cr, Investment < Rs. 50 Cr)
    msme_registered: bool = True
    nsic_registered: bool = True
    udyam_registered: bool = True
    # Note on statutory EMD: Qualifies for UDYAM exemptions; on tenders strictly reserving MSE exemptions for Micro/Small,
    # Nikom provides ICICI Bank Guarantee or standard Bid Security Declaration.

    # ── Audited Financials & Filings ───────────────────────────────────────────
    # Turnovers (INR Crores & Raw)
    turnover_fy23_cr: float = 48.50
    turnover_fy24_cr: float = 67.18
    turnover_fy25_cr: float = 91.21
    turnover_fy26_prov_cr: float = 123.07

    # Benchmark Turnover Figures
    audited_3yr_avg_turnover_cr: float = 70.11   # FY 2022-23 to FY 2024-25 (Audited): Rs. 70.11 Cr
    current_3yr_avg_turnover_cr: float = 100.75  # FY 2023-24 to FY 2025-26 (incl. Prov): Rs. 100.75 Cr
    peak_turnover_cr: float = 123.07             # Latest FY 2025-26 Provisional: Rs. 123.07 Cr

    annual_turnover_inr: float = 1_230_700_000.0          # Rs. 123.07 Cr
    average_annual_turnover_inr: float = 701_100_000.0     # Rs. 70.11 Cr (Audited standard)
    average_turnover_with_prov_inr: float = 1_007_500_000.0 # Rs. 100.75 Cr

    # Net Worth (Share Capital + Reserves, 100% positive, growing year-on-year)
    net_worth_fy23_cr: float = 14.88
    net_worth_fy24_cr: float = 21.14
    net_worth_fy25_cr: float = 28.58
    net_worth_fy26_prov_cr: float = 38.57
    net_worth_inr: float = 285_800_000.0                   # Rs. 28.58 Cr (Audited FY25)
    net_worth_prov_inr: float = 385_700_000.0              # Rs. 38.57 Cr (Prov. FY26)

    # Profitability (100% profitable, positive PAT in all 3+ years)
    profitable_years_out_of_3: int = 3
    pat_fy24_cr: float = 6.29   # PBT Rs. 8.42 Cr
    pat_fy25_cr: float = 8.45   # PBT Rs. 10.51 Cr
    pat_fy26_prov_cr: float = 5.07  # PBT Rs. 5.30 Cr

    # Liquidity & Working Capital
    working_capital_cr: float = 61.12                      # Rs. 61.12 Cr (Prov. FY26; FY25 was 64.50 Cr)
    working_capital_inr: float = 611_200_000.0
    current_ratio: float = 2.56                            # 2.56x (FY26 Prov) / 2.50x (FY25) - strong liquidity
    debt_equity_ratio: float = 0.00                        # 0.00x - Virtually zero debt company!
    cash_bank_balance_cr: float = 14.52                    # Rs. 14.52 Cr (incl. FDs, net of OD)
    cash_bank_balance_inr: float = 145_200_000.0

    # Services & Recurring Turnover (AMC + O&M + FMS)
    services_turnover_cr: float = 13.89                    # Rs. 13.89 Cr (FY26 Prov) / Rs. 16.68 Cr (FY25)
    services_turnover_inr: float = 138_900_000.0

    # Bid Capacity & Contract Thresholds
    calculated_bid_capacity_cr: float = 201.16             # Rs. 201.16 Cr (Formula: A x N x 2 - B)
    calculated_bid_capacity_inr: float = 2_011_600_000.0
    min_tender_value_inr: float = 300_000.0                # Rs. 3 Lakhs (small service/spare lots)
    sweet_spot_min_inr: float = 1_500_000.0                # Rs. 15 Lakhs
    sweet_spot_max_inr: float = 350_000_000.0              # Rs. 35 Crores (comfort zone)
    single_work_capacity_inr: float = 363_000_000.0        # Rs. 36.3 Crores (historical single contract)
    max_turnover_capacity_inr: float = 1_500_000_000.0     # Rs. 150 Crores (consortium / JV capacity)

    # ── Active Order Book (Orders Won FY 2025-26: Total Rs. 104.17 Cr) ─────────
    order_in_hand_cr: float = 104.17                       # Rs. 104.17 Cr active order book
    order_in_hand_inr: float = 1_041_700_000.0
    order_billable_fy27_cr: float = 71.35
    order_billable_fy28_cr: float = 13.20
    turnover_booked_q1_q2_cr: float = 37.26                # Booked 01.04.2026 - 31.07.2026
    estimated_turnover_fy27_cr: float = 108.62

    # ── Core Business Domains ──────────────────────────────────────────────────
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

    # ── Verified Past Clients ───────────────────────────────────────────────────
    verified_clients: List[str] = field(default_factory=lambda: [
        "ONGC (Oil and Natural Gas Corporation)",
        "AAI (Airports Authority of India)",
        "NATGRID (National Intelligence Grid)",
        "C-DAC (Centre for Development of Advanced Computing)",
        "C-DOT (Centre for Development of Telematics)",
        "IOCL (Indian Oil Corporation Limited)",
        "Power Grid Corporation of India Limited",
        "NTPC Limited",
        "NHPC Limited",
        "Punjab National Bank (PNB)",
        "Bank of India (BOI)",
        "NIC / NICSI (National Informatics Centre)",
        "Income Tax Department (ITD)",
        "CRIS (Centre for Railway Information Systems)",
        "IIT Hyderabad",
        "IIT Gandhinagar",
        "IIT Roorkee",
        "NIT Trichy",
        "NIT Goa",
        "Southern Railway Chennai",
        "Tata Power / TPDDL",
        "UPCL (Uttarakhand Power Corporation Limited)",
        "DRDO (Defence Research and Development Organisation)",
        "GRSE (Garden Reach Shipbuilders & Engineers)",
        "NFL (National Fertilizers Limited)",
        "Jabalpur Smart City Limited (JSCL)"
    ])

    # ── Domain Keywords for Matching ───────────────────────────────────────────
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

    # ── OEM Partnerships ───────────────────────────────────────────────────────
    partner_oems: List[str] = field(default_factory=lambda: [
        "Schneider Electric", "APC", "Vertiv", "Emerson Network Power",
        "Eaton", "Delta", "Legrand", "Honeywell", "Siemens", "Johnson Controls",
        "Cummins", "Kirloskar", "Cisco", "CommScope", "Panduit", "D-Link", "Fortinet", "Palo Alto",
        "Dell EMC", "HPE"
    ])

    # ── Quality Certifications ─────────────────────────────────────────────────
    certifications: List[str] = field(default_factory=lambda: [
        "ISO 9001:2015 (Quality Management System)",
        "ISO 27001:2022 (Information Security Management)",
        "ISO 20000-1:2018 (IT Service Management)",
        "ISO 14001:2015 (Environmental Management System)",
        "ISO 45001:2018 (Occupational Health & Safety)",
        "CMMI Level 3 (Software & Process Maturity)"
    ])

    # ── Verified Completed Works (Similar Past Experience) ─────────────────────
    completed_works: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "client": "AAI Hyderabad",
            "work_name": "Establishment of Non-IT Infrastructure for Disaster Recovery (DR) Site at Hyderabad",
            "po_no": "AAI/CHQ/ITD/DR/NON-IT/PO-03/2019-20/172",
            "value_cr": 21.68,
            "completion_date": "2021-07-08",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Disaster Recovery / Data Center Turnkey EPC"
        },
        {
            "client": "ONGC Vasudhara Bhavan Mumbai",
            "work_name": "Development of RO Communication Data Center (Group-A) & Creation of Common Data Center for Assets (Group-B)",
            "po_no": "MR/MM/MRG/MM/2019/DC/RO&AS/431811 dated 05.02.2020",
            "value_cr": 20.40,
            "completion_date": "2023-07-21",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Turnkey Data Center EPC & Server Infrastructure"
        },
        {
            "client": "AAI 10 Airports (Tier-II)",
            "work_name": "Establishment of Airport Operations Control Centers across 10 Airports",
            "po_no": "4500035405",
            "value_cr": 25.93,
            "completion_date": "2018-05-21",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Control Center / Data Center Infrastructure"
        },
        {
            "client": "Income Tax Department (ITD)",
            "work_name": "Design, Supply, Installation, Testing and Commissioning of Infrastructure for facilities at ITD Premises",
            "po_no": "4500035654",
            "value_cr": 10.71,
            "completion_date": "2017-09-16",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Enterprise Infrastructure / Data Center"
        },
        {
            "client": "ONGC 11 High Panvel",
            "work_name": "Revamping of Server Room at 11 High and Creation of Data Center at Panvel, Mumbai",
            "po_no": "MR/MM/MRG/MM/2019/DC-11-High/372707 dated 15.11.2019",
            "value_cr": 5.14,
            "completion_date": "2020-12-22",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Server Room Revamping & Data Center"
        },
        {
            "client": "IIT Roorkee",
            "work_name": "Design, Site Preparation, Supply, Installation, Testing, Commissioning and AMC of Basic Infrastructure for Data Centre",
            "po_no": "CDAC/L21/T815 dated 28.05.2021",
            "value_cr": 4.55,
            "completion_date": "2022-06-30",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Turnkey Data Center & AMC"
        },
        {
            "client": "C-DAC Bangalore",
            "work_name": "Design, Site Preparation, Supply, Installation, Commissioning & Maintenance of Basic Data Centre Infrastructure",
            "po_no": "CDAC/L21/T758 dated 09.11.2020",
            "value_cr": 3.87,
            "completion_date": "2022-03-31",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Data Center Infrastructure & Maintenance"
        },
        {
            "client": "NIT Trichy",
            "work_name": "SITC and AMC Services of Basic Infrastructure for establishment of Data Centre",
            "po_no": "CDAC/NITT/DC/2021",
            "value_cr": 3.62,
            "completion_date": "2022-12-15",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Data Center SITC & AMC"
        },
        {
            "client": "IIT Gandhinagar",
            "work_name": "Design, Site Preparation, SITC and AMC of Basic Infrastructure for Data Centre",
            "po_no": "CDAC/L21/T830 dated 22.03.2021",
            "value_cr": 3.22,
            "completion_date": "2022-09-30",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Data Center Infrastructure & AMC"
        },
        {
            "client": "Jabalpur Smart City Limited (JSCL)",
            "work_name": "Integrated City Operation Centre in existing JSCL Building",
            "po_no": "JSCL/1414/2018 dated 20.03.2018",
            "value_cr": 3.14,
            "completion_date": "2019-06-15",
            "within_lookback": True,
            "has_certificate": True,
            "category": "NOC / Command Operation Center"
        },
        {
            "client": "IIT Hyderabad",
            "work_name": "Preparation, SITC, Operations and Maintenance of Basic Infrastructure for Data Centre",
            "po_no": "IITH/PUR/NISHA/NT/2020/282 dated 20.01.2021",
            "value_cr": 3.01,
            "completion_date": "2022-04-30",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Data Center SITC & O&M"
        },
        {
            "client": "CRIS (Railways)",
            "work_name": "SITC allied electrical works: UPS, PAC 24TRx4, Server Racks, CCTV, Fire Detection & Suppression, Rodent Repellant",
            "po_no": "2014/CRIS/Elect/24",
            "value_cr": 2.89,
            "completion_date": "2017-01-19",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Electrical, UPS, PAC & Fire Suppression"
        },
        {
            "client": "ONGC Laxmi Nagar",
            "work_name": "Upgradation and Revamping of ONGC Data Centre on Turnkey basis",
            "po_no": "DLH/CORP-INFOCOM/REV/2016-18",
            "value_cr": 2.48,
            "completion_date": "2018-08-13",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Turnkey DC Revamping"
        },
        {
            "client": "NIT Goa",
            "work_name": "Establishment of Airport Infrastructure at Goa",
            "po_no": "4500034404 dated 28.10.2017",
            "value_cr": 2.31,
            "completion_date": "2018-09-28",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Airport / Control Room Infrastructure"
        },
        {
            "client": "AAI Lucknow",
            "work_name": "Establishment of Airport Infrastructure at Lucknow",
            "po_no": "4500034645 dated 25.10.2017",
            "value_cr": 2.25,
            "completion_date": "2018-09-28",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Airport / Control Room Infrastructure"
        },
        {
            "client": "ONGC Urja Bhawan",
            "work_name": "Infrastructure Upgradation Job for Infocom Data Centre at Deendayal Urja Bhawan",
            "po_no": "DLI/DUD/C&S/C/INFOCOM/IDCupgr/rev/2019-20",
            "value_cr": 2.13,
            "completion_date": "2019-06-10",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Infocom Data Centre Upgradation"
        },
        {
            "client": "GRSE Kolkata",
            "work_name": "Data Center at CGO GRSE, 61 Park Kolkata",
            "po_no": "PUR/SP/LOA/DATA CENTER",
            "value_cr": 1.53,
            "completion_date": "2018-02-21",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Data Center"
        },
        {
            "client": "NFL Corporate Office Noida",
            "work_name": "Upgradation / Revamp of Data Centre along with Comprehensive AMC",
            "po_no": "NFL/NOI/1042/1/1801",
            "value_cr": 1.40,
            "completion_date": "2018-02-08",
            "within_lookback": False,
            "has_certificate": True,
            "category": "Data Centre Revamp & CAMC"
        },
        {
            "client": "NHPC Limited",
            "work_name": "Supply and installation of Integrated racks infrastructure in Server room at Corporate Office, NHPC",
            "po_no": "NH/Cont(E&M-IV)/CO-56/PR10017/202/2018/SO-86/2019/339",
            "value_cr": 1.04,
            "completion_date": "2020-01-10",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Integrated Server Racks Infrastructure"
        },
        {
            "client": "C-DAC Pune",
            "work_name": "Supply & Installation of 200 KVA Modular & 100 KVA Monolithic UPS with batteries",
            "po_no": "CDAC/L20/T754 dated 03.11.2020",
            "value_cr": 0.73,
            "completion_date": "2021-08-15",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Modular Online UPS & Batteries"
        },
        {
            "client": "CRIS Chennai",
            "work_name": "Relocation of Passenger Reservation System (PRS) and UTS Servers",
            "po_no": "rev 25/cris/2018/RATE/24-10-2018",
            "value_cr": 0.59,
            "completion_date": "2019-05-15",
            "within_lookback": True,
            "has_certificate": True,
            "category": "Railway Server Relocation & Commissioning"
        },
        {
            "client": "C-DOT NOC New Delhi",
            "work_name": "Design, Build, Site Preparation, SITC of NOC Setup on Turnkey basis",
            "po_no": "PO/CDOT/NOC/2024 dated 09.01.2024",
            "value_cr": 0.04,
            "completion_date": "2024-08-07",
            "within_lookback": True,
            "has_certificate": True,
            "category": "NOC Turnkey Setup"
        }
    ])

    # ── Active Orders Won FY 2025-26 (Order Book: Total Rs. 104.17 Cr) ─────────
    active_orders_fy26: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"client": "NATGRID Server", "value_cr": 28.66, "contract_no": "GEMC-5116877373519509", "date": "2026-02-26"},
        {"client": "C-DAC Mohali", "value_cr": 25.37, "contract_no": "GEMC-511687744832917", "date": "2026-02-11"},
        {"client": "Alliance L&T", "value_cr": 19.00, "contract_no": "L&T PAN 2", "date": "Ongoing"},
        {"client": "IOCL Gurgaon (AMC)", "value_cr": 8.91, "contract_no": "GEMC-511687741352239", "date": "2026-02-13"},
        {"client": "AAI Chennai Networking", "value_cr": 5.14, "contract_no": "GEMC-511687716919946", "date": "2025-05-30"},
        {"client": "PNB Mumbai (AMC)", "value_cr": 2.93, "contract_no": "GEMC-511687749684587", "date": "2026-04-02"},
        {"client": "UPCL (Uttarakhand Power)", "value_cr": 2.36, "contract_no": "365/UPCL/IT/Tender/06/2024-", "date": "2025-08-08"},
        {"client": "NATGRID Firewall", "value_cr": 2.34, "contract_no": "GEMC-511687795935043", "date": "2026-03-13"},
        {"client": "IOCL DCIM", "value_cr": 2.16, "contract_no": "PO Awaited", "date": "2026-01-15"},
        {"client": "C-DAC Pune AMC", "value_cr": 1.71, "contract_no": "GEMC-511687701154965", "date": "2025-05-15"},
        {"client": "IOCL PLHO", "value_cr": 1.67, "contract_no": "GEMC-511687736853235", "date": "2025-06-17"},
        {"client": "C-DOT Mehrauli CAMC", "value_cr": 1.49, "contract_no": "PO2526DCPL00160", "date": "2026-02-13"},
        {"client": "C-DOT Mehrauli Electrical Panel", "value_cr": 1.47, "contract_no": "PO2526DCPL00156", "date": "2026-02-06"},
        {"client": "AAI Kolkata", "value_cr": 0.43, "contract_no": "GEMC-511687798623780", "date": "2025-10-10"},
        {"client": "ONGC PAC", "value_cr": 0.26, "contract_no": "GEMC-511687784659747", "date": "2026-03-17"},
        {"client": "NATGRID Firewall 2 nos", "value_cr": 0.24, "contract_no": "GEMC-511687710512834", "date": "2026-03-23"},
        {"client": "IIT Roorkee Humidifier", "value_cr": 0.05, "contract_no": "PO2526IITR001", "date": "2025-11-20"}
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to serializable dictionary for API and eligibility checking."""
        return {
            "company_name": self.company_name,
            "founded_year": self.founded_year,
            "years_in_business": self.years_in_business,
            "headquarters": self.headquarters,
            "bankers": self.bankers,
            "branches": self.branches,
            "enterprise_type": self.enterprise_type,
            "msme_registered": self.msme_registered,
            "nsic_registered": self.nsic_registered,
            "udyam_registered": self.udyam_registered,
            "turnover_fy23_cr": self.turnover_fy23_cr,
            "turnover_fy24_cr": self.turnover_fy24_cr,
            "turnover_fy25_cr": self.turnover_fy25_cr,
            "turnover_fy26_prov_cr": self.turnover_fy26_prov_cr,
            "audited_3yr_avg_turnover_cr": self.audited_3yr_avg_turnover_cr,
            "current_3yr_avg_turnover_cr": self.current_3yr_avg_turnover_cr,
            "peak_turnover_cr": self.peak_turnover_cr,
            "annual_turnover_inr": self.annual_turnover_inr,
            "average_annual_turnover_inr": self.average_annual_turnover_inr,
            "average_turnover_with_prov_inr": self.average_turnover_with_prov_inr,
            "net_worth_inr": self.net_worth_inr,
            "net_worth_prov_inr": self.net_worth_prov_inr,
            "net_worth_fy25_cr": self.net_worth_fy25_cr,
            "net_worth_fy26_prov_cr": self.net_worth_fy26_prov_cr,
            "profitable_years_out_of_3": self.profitable_years_out_of_3,
            "working_capital_cr": self.working_capital_cr,
            "current_ratio": self.current_ratio,
            "debt_equity_ratio": self.debt_equity_ratio,
            "cash_bank_balance_cr": self.cash_bank_balance_cr,
            "services_turnover_cr": self.services_turnover_cr,
            "calculated_bid_capacity_cr": self.calculated_bid_capacity_cr,
            "calculated_bid_capacity_inr": self.calculated_bid_capacity_inr,
            "order_in_hand_cr": self.order_in_hand_cr,
            "order_in_hand_inr": self.order_in_hand_inr,
            "sweet_spot_min_inr": self.sweet_spot_min_inr,
            "sweet_spot_max_inr": self.sweet_spot_max_inr,
            "single_work_capacity_inr": self.single_work_capacity_inr,
            "max_turnover_capacity_inr": self.max_turnover_capacity_inr,
            "core_domains": self.core_domains,
            "verified_clients": self.verified_clients,
            "partner_oems": self.partner_oems,
            "certifications": self.certifications,
            "completed_works": self.completed_works,
            "active_orders_fy26": self.active_orders_fy26
        }

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like indexing for backward compatibility."""
        return getattr(self, key)


NIKOM_PROFILE = NikomProfile()
