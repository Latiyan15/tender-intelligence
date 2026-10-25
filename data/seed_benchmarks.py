"""
Ground Truth Benchmark Tenders for Nikom Feasibility Evaluation
Contains curated, authentic Indian Government tender notices across Nikom's target
infrastructure categories as well as negative controls (civil, medical, out-of-domain).
"""

from src.models.tender import (
    TenderRecord, TenderStatus, ExtractedField, FieldStatus, DocumentRecord
)


def get_benchmark_tenders():
    """Return a curated suite of realistic Indian Government tender notices for evaluation."""
    tenders = []

    # 1. Tier-III Turnkey Data Center (NIC / MeitY) -> Strong GO
    t1 = TenderRecord(
        tender_id="BENCH_NIC_DC_2026",
        reference_number="NIC/DC/T-III/2026/04",
        title="Comprehensive Design, Supply, Installation, Testing and Commissioning of Tier-III Data Center Infrastructure including High Efficiency Modular Online UPS, In-Row Precision Air Conditioning (PAC), Clean Agent Gas Flooding (Novec 1230), IBMS and 42U Server Racks at NIC New Delhi",
        issuing_organization="National Informatics Centre (NIC)",
        department="Ministry of Electronics and Information Technology",
        location="New Delhi",
        source_portal="CPPP_ePublish",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 14,80,00,000/-",
            normalized_value=148_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        emd_amount=ExtractedField(
            field_name="emd_amount",
            raw_text="Rs. 29,60,000/- (2% of estimated value)",
            normalized_value=2960000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        tender_fee=ExtractedField(
            field_name="tender_fee",
            raw_text="Rs. 10,000/-",
            normalized_value=10000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        submission_deadline=ExtractedField(
            field_name="submission_deadline",
            raw_text="25-Nov-2026 15:00 Hrs",
            normalized_value="2026-11-25",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        opening_date=ExtractedField(
            field_name="opening_date",
            raw_text="26-Nov-2026 15:30 Hrs",
            normalized_value="2026-11-26",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        minimum_turnover=ExtractedField(
            field_name="minimum_turnover",
            raw_text="Average annual turnover of Rs. 15 Crores during last 3 financial years",
            normalized_value=150_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        experience_requirement=ExtractedField(
            field_name="experience_requirement",
            raw_text="Successfully completed at least 3 Tier-III or Tier-II data center turnkey projects of min Rs. 6 Cr each in last 7 years",
            normalized_value="Tier-III DC experience",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        scope_of_work=ExtractedField(
            field_name="scope_of_work",
            raw_text="Turnkey EPC work comprising 2x160 kVA modular UPS with lithium-ion batteries, 4x15 TR In-Row PAC units, FM200/Novec gas flooding, VESDA early warning smoke detection, SCADA IBMS, water leak detection, 42U server racks with cold aisle containment, and 3 years comprehensive AMC.",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        oem_requirements=ExtractedField(
            field_name="oem_requirements",
            raw_text="Manufacturer Authorization Form (MAF) from OEM (Vertiv / Schneider / Eaton / APC)",
            normalized_value=True,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        certifications_required=[
            ExtractedField("cert_iso_9001", "ISO 9001:2015", "ISO 9001", status=FieldStatus.PRESENT_EXTRACTED, verified=True),
            ExtractedField("cert_iso_27001", "ISO 27001:2013", "ISO 27001", status=FieldStatus.PRESENT_EXTRACTED, verified=True)
        ],
        documents=[
            DocumentRecord(doc_type="nit", filename="NIT_NIC_DC_2026.pdf", downloaded=True, text_extracted=True),
            DocumentRecord(doc_type="boq", filename="BOQ_NIC_DC_EQUIPMENT.xlsx", downloaded=True)
        ]
    )
    tenders.append(t1)

    # 2. Online UPS & Battery Power Solution (RailTel / Railways) -> Strong GO
    t2 = TenderRecord(
        tender_id="BENCH_RAILTEL_UPS_2026",
        reference_number="RCIL/HQ/UPS/2026/08",
        title="Supply, Installation, Testing & Commissioning of 2x120 kVA Parallel Redundant Online UPS System with 60 Mins VRLA SMF Battery Backup at RailTel Regional Data Centre",
        issuing_organization="RailTel Corporation of India Ltd.",
        department="Ministry of Railways",
        location="Secunderabad",
        source_portal="CPPP_Latest",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 92,50,000/-",
            normalized_value=9250000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        emd_amount=ExtractedField(
            field_name="emd_amount",
            raw_text="Rs. 1,85,000/-",
            normalized_value=185000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        submission_deadline=ExtractedField(
            field_name="submission_deadline",
            raw_text="18-Nov-2026",
            normalized_value="2026-11-18",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        minimum_turnover=ExtractedField(
            field_name="minimum_turnover",
            raw_text="Average annual turnover of Rs. 1.5 Crores in last 3 financial years",
            normalized_value=15000000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        scope_of_work=ExtractedField(
            field_name="scope_of_work",
            raw_text="Supply and commissioning of 2x120 kVA true online double conversion UPS, battery bank, isolation transformers, and power distribution boards.",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        oem_requirements=ExtractedField(
            field_name="oem_requirements",
            raw_text="Authorized partner certification from Schneider / Vertiv / APC",
            normalized_value=True,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        )
    )
    tenders.append(t2)

    # 3. Precision Air Conditioning CAMC (BSNL Data Center) -> Strong GO
    t3 = TenderRecord(
        tender_id="BENCH_BSNL_PAC_2026",
        reference_number="BSNL/DC/PAC/CAMC/2026",
        title="Comprehensive Annual Maintenance Contract (CAMC) of 8 Nos 20 TR Precision Air Conditioning (PAC) Units and Environment Monitoring System at BSNL IDC Pune",
        issuing_organization="Bharat Sanchar Nigam Limited (BSNL)",
        department="Department of Telecommunications",
        location="Pune, Maharashtra",
        source_portal="CPPP_ePublish",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 48,00,000/-",
            normalized_value=4800000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        emd_amount=ExtractedField(
            field_name="emd_amount",
            raw_text="Rs. 96,000/-",
            normalized_value=96000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        submission_deadline=ExtractedField(
            field_name="submission_deadline",
            raw_text="30-Nov-2026",
            normalized_value="2026-11-30",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        minimum_turnover=ExtractedField(
            field_name="minimum_turnover",
            raw_text="Rs. 50 Lakhs annual turnover",
            normalized_value=5000000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.85,
            verified=True
        ),
        scope_of_work=ExtractedField(
            field_name="scope_of_work",
            raw_text="24x7 on-site maintenance of PAC chillers, compressors, filters, microprocessor controllers, and water leak detection.",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        )
    )
    tenders.append(t3)

    # 4. Integrated CCTV Surveillance & Security (DFCCIL) -> Adjacent / CAUTION
    t4 = TenderRecord(
        tender_id="BENCH_DFCCIL_CCTV_2026",
        reference_number="DFCCIL/IT/SURV/2026/11",
        title="Supply, Installation and Integration of IP CCTV Surveillance System, Access Control, and Server Storage for DFCCIL Stations",
        issuing_organization="Dedicated Freight Corridor Corporation of India Ltd.",
        department="Ministry of Railways",
        location="Noida, UP",
        source_portal="CPPP_Latest",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 2,10,00,000/-",
            normalized_value=21000000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        emd_amount=ExtractedField(
            field_name="emd_amount",
            raw_text="Rs. 4,20,000/-",
            normalized_value=420000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        ),
        submission_deadline=ExtractedField(
            field_name="submission_deadline",
            raw_text="12-Dec-2026",
            normalized_value="2026-12-12",
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.85,
            verified=True
        )
    )
    tenders.append(t4)

    # 5. Civil Highway Works (NHAI) -> Excluded / NO-GO
    t5 = TenderRecord(
        tender_id="BENCH_NHAI_ROAD_2026",
        reference_number="NHAI/CIVIL/HWY/2026/99",
        title="Four-laning and construction of highway bypass and rigid pavement bridge on NH-48",
        issuing_organization="National Highways Authority of India (NHAI)",
        department="Ministry of Road Transport and Highways",
        location="Jaipur, Rajasthan",
        source_portal="CPPP_ePublish",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 320 Crores",
            normalized_value=3_200_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        )
    )
    tenders.append(t5)

    # 6. Medical Equipment & Medicines (AIIMS) -> Excluded / NO-GO
    t6 = TenderRecord(
        tender_id="BENCH_AIIMS_MED_2026",
        reference_number="AIIMS/HOSP/MED/2026/14",
        title="Rate contract for supply of pharmaceutical medicines, surgical consumables, and syringes for AIIMS Hospital",
        issuing_organization="All India Institute of Medical Sciences (AIIMS)",
        department="Ministry of Health and Family Welfare",
        location="Bhopal, MP",
        source_portal="CPPP_ePublish",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 8.5 Crores",
            normalized_value=85_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.90,
            verified=True
        )
    )
    tenders.append(t6)

    # 7. Mega Turnkey Campus Exceeding Turnover (State Smart City) -> Disqualified / NO-GO
    t7 = TenderRecord(
        tender_id="BENCH_MEGA_DC_2026",
        reference_number="SMART/DC/HYPER/2026/01",
        title="Turnkey Engineering, Procurement and Construction of Hyperscale Green Data Center Campus",
        issuing_organization="Smart City Development Corporation",
        location="Ahmedabad, Gujarat",
        source_portal="CPPP_Latest",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 450 Crores",
            normalized_value=4_500_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        ),
        minimum_turnover=ExtractedField(
            field_name="minimum_turnover",
            raw_text="Minimum average annual turnover of Rs. 600 Crores in last 3 financial years",
            normalized_value=6_000_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.95,
            verified=True
        )
    )
    tenders.append(t7)

    return tenders
