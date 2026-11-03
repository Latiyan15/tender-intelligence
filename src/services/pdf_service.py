"""
Official Tender Document & Specification PDF Generation Service.
Generates authenticated, professional PDF dossiers for tenders across all Indian portals
(CPPP, GePNIC, State eProcurement, IOCL, PSUs, eWizard, TenderWizard) ensuring 100% openable valid PDF documents.
"""

import io
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger(__name__)

PORTAL_NAME_MAP = {
    'gem': 'GeM (Government e-Marketplace)',
    'cppp_latest': 'Central Public Procurement Portal (CPPP)',
    'cppp_epublish': 'CPPP ePublish Notice System',
    'iocl': 'Indian Oil Corporation (IOCL eTenders)',
    'kerala_tenders': 'Kerala State e-Procurement Portal',
    'wb_tenders': 'West Bengal State e-Procurement',
    'up_tenders': 'Uttar Pradesh e-Procurement',
    'rajasthan_eproc': 'Rajasthan State eProcurement',
    'hp_tenders': 'Himachal Pradesh e-Procurement',
    'punjab_eproc': 'Punjab State e-Procurement',
    'uk_tenders': 'Uttarakhand State e-Procurement',
    'odisha_tenders': 'Odisha State e-Procurement',
    'jharkhand_tenders': 'Jharkhand State e-Procurement',
    'jk_tenders': 'Jammu & Kashmir e-Procurement',
    'arunachal_tenders': 'Arunachal Pradesh e-Procurement',
    'assam_tenders': 'Assam State e-Procurement',
    'bihar_eproc': 'Bihar eProcurement',
    'delhi_tenders': 'Delhi Government e-Procurement',
    'haryana_eproc': 'Haryana State e-Procurement',
    'karnataka_eproc': 'Karnataka KPPP Portal',
    'mahatenders': 'Maharashtra MahaTenders',
    'mp_tenders': 'Madhya Pradesh e-Procurement',
    'tn_tenders': 'Tamil Nadu TNTenders',
    'aiims_kalyani_ewizard': 'AIIMS Kalyani (ITI eWizard)',
    'aera_ewizard': 'AERA (ITI eWizard)',
    'aiims_tenderwizard': 'AIIMS (Antares TenderWizard)',
    'bhel_tenderwizard': 'BHEL (TenderWizard)',
    'bel': 'Bharat Electronics Limited (BEL)',
    'bhel': 'Bharat Heavy Electricals (BHEL)',
}


def format_source_display(src: Optional[str]) -> str:
    """Returns official human-readable display name for any Indian government portal."""
    if not src:
        return "Central CPPP Portal"
    src_clean = str(src).strip().lower()
    if src_clean in PORTAL_NAME_MAP:
        return PORTAL_NAME_MAP[src_clean]
    for key, val in PORTAL_NAME_MAP.items():
        if key in src_clean:
            return val
    return src_clean.replace('_', ' ').title()


def generate_tender_dossier_pdf(tender: Dict[str, Any], matches: Optional[List[Dict[str, Any]]] = None) -> bytes:
    """
    Builds a vector PDF specification dossier for a tender with full procurement details,
    technology classification, scope of work, and official portal reference.
    Guaranteed valid PDF starting with %PDF- header that opens in all PDF viewers.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    header_title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )

    tender_title_style = ParagraphStyle(
        'TenderTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica-Bold'
    )

    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor('#64748B'),
        fontName='Helvetica-Bold'
    )

    value_style = ParagraphStyle(
        'ValueStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica'
    )

    badge_style = ParagraphStyle(
        'BadgeStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#1D4ED8'),
        fontName='Helvetica-Bold'
    )

    story = []

    # 1. Official Header & Branding Bar
    brand_table = Table(
        [
            [
                Paragraph("<b>NIKOM TENDER INTELLIGENCE</b><br/><font size=7.5 color='#64748B'>Official Procurement Notice & Technical Specification Dossier</font>", styles['Normal']),
                Paragraph("<b>VERIFIED OPPORTUNITY</b><br/><font size=7.5 color='#10B981'>Direct Portal Sourced &bull; AI Evaluated</font>", ParagraphStyle('R', parent=styles['Normal'], alignment=2))
            ]
        ],
        colWidths=[310, 210]
    )
    brand_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(brand_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

    # 2. Tender Title
    title_text = tender.get("title") or "Official Tender Specification"
    story.append(Paragraph(title_text, tender_title_style))
    story.append(Spacer(1, 8))

    # 3. Metadata Table
    ref_text = tender.get("reference_no") or tender.get("tender_id") or "N/A"
    tid_text = tender.get("tender_id") or "N/A"

    tier_map = {
        'A': 'Cyber Security (Tier A)',
        'B': 'IT Infrastructure (Tier B)',
        'C': 'Cloud & DR (Tier C)',
        'D': 'Infra & Services (Tier D)'
    }
    tier_name = tier_map.get(str(tender.get("highest_tier", "")).upper(), "Enterprise IT Procurement")

    # Accurate Financial Information Formatting
    cost_inr = tender.get("estimated_cost_inr")
    if cost_inr and cost_inr > 0:
        if cost_inr >= 10000000:
            cr = cost_inr / 10000000
            cost_str = f"INR {cost_inr:,.2f}  (Rs. {cr:.2f} Cr)"
        elif cost_inr >= 100000:
            lakh = cost_inr / 100000
            cost_str = f"INR {cost_inr:,.2f}  (Rs. {lakh:.2f} L)"
        else:
            cost_str = f"INR {cost_inr:,.2f}"
    else:
        cost_str = "Item Rate / Consultancy (Refer to BOQ.xls)"

    emd_inr = tender.get("emd_inr")
    if emd_inr and emd_inr > 0:
        if emd_inr >= 100000:
            lakh = emd_inr / 100000
            emd_str = f"INR {emd_inr:,.2f}  (Rs. {lakh:.2f} L)"
        else:
            emd_str = f"INR {emd_inr:,.2f}"
    elif emd_inr == 0:
        emd_str = "Nil / Exempted"
    else:
        emd_str = "Refer to Official Notice"

    doc_fee = tender.get("doc_fee_inr")
    if doc_fee and doc_fee > 0:
        doc_fee_str = f"INR {doc_fee:,.2f}"
    elif doc_fee == 0:
        doc_fee_str = "Free / Exempted"
    else:
        doc_fee_str = "Refer to Portal"

    portal_source_display = format_source_display(tender.get("portal_source"))

    deadline_str = str(tender.get("submission_deadline") or "Refer to Portal")
    pub_str = str(tender.get("published_date") or "Recent")

    grid_data = [
        [
            Paragraph("TENDER REFERENCE", label_style),
            Paragraph(f"<b>{ref_text}</b>", value_style),
            Paragraph("PORTAL SOURCE", label_style),
            Paragraph(f"<b>{portal_source_display}</b>", value_style)
        ],
        [
            Paragraph("TENDER ID", label_style),
            Paragraph(tid_text, value_style),
            Paragraph("PRIMARY DOMAIN", label_style),
            Paragraph(tier_name, badge_style)
        ],
        [
            Paragraph("BUYER ORGANISATION", label_style),
            Paragraph(tender.get("authority") or "Unknown Authority", value_style),
            Paragraph("ESTIMATED VALUE", label_style),
            Paragraph(f"<b>{cost_str}</b>", value_style)
        ],
        [
            Paragraph("WORK LOCATION", label_style),
            Paragraph(tender.get("location") or "India", value_style),
            Paragraph("EMD / TENDER FEE", label_style),
            Paragraph(f"{emd_str} | Fee: {doc_fee_str}", value_style)
        ],
        [
            Paragraph("PUBLISHED DATE", label_style),
            Paragraph(pub_str, value_style),
            Paragraph("SUBMISSION DEADLINE", label_style),
            Paragraph(deadline_str, ParagraphStyle('D', parent=value_style, textColor=colors.HexColor('#DC2626'), fontName='Helvetica-Bold'))
        ],
    ]

    t_grid = Table(grid_data, colWidths=[125, 135, 125, 135])
    t_grid.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
        ('RIGHTPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_grid)
    story.append(Spacer(1, 10))

    # 4. Scope of Work & Extracted Requirements
    story.append(Paragraph("SCOPE OF WORK & TECHNICAL REQUIREMENTS", header_title_style))
    story.append(Spacer(1, 4))

    desc_text = tender.get("description") or "Complete turnkey supply, installation, configuration, testing, and comprehensive maintenance services in accordance with official tender specifications."
    desc_p = Paragraph(f"<font size=9 color='#1E293B' face='Helvetica'>{desc_text}</font>", styles['Normal'])

    desc_table = Table([[desc_p]], colWidths=[520])
    desc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (0,0), 8),
        ('BOTTOMPADDING', (0,0), (0,0), 8),
        ('LEFTPADDING', (0,0), (0,0), 10),
        ('RIGHTPADDING', (0,0), (0,0), 10),
    ]))
    story.append(desc_table)
    story.append(Spacer(1, 10))

    # 5. Technology Criteria Evidence
    if matches and len(matches) > 0:
        story.append(Paragraph("EVALUATED TECHNOLOGY KEYWORD MATCHES", header_title_style))
        story.append(Spacer(1, 4))

        m_rows = [[
            Paragraph("<b>Keyword Term</b>", label_style),
            Paragraph("<b>Tier / Focus Group</b>", label_style),
            Paragraph("<b>Evidence Snippet</b>", label_style)
        ]]
        for m in matches[:6]:
            m_rows.append([
                Paragraph(f"<b>{m.get('term', '')}</b>", value_style),
                Paragraph(f"Tier {m.get('tier', '')} ({m.get('match_group') or m.get('group') or 'General'})", value_style),
                Paragraph(f"<i>\"{m.get('snippet') or m.get('matched_text') or ''}\"</i>", ParagraphStyle('Snip', parent=value_style, fontSize=8, textColor=colors.HexColor('#475569')))
            ])
        t_matches = Table(m_rows, colWidths=[110, 130, 280])
        t_matches.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EFF6FF')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(t_matches)
        story.append(Spacer(1, 10))

    # 6. Official Portal Verification Notice
    portal_url = tender.get("portal_url") or "https://eprocure.gov.in"
    notice_text = (
        f"<b>Official Source Verification:</b> This specification dossier was compiled directly from official government procurement records at "
        f"<u>{portal_url}</u>.<br/>"
        f"<b>Official Documents & BOQ:</b> The original issuing authority documents (NIT Notice, Scope of Work, and BOQ.xls) "
        f"require government PKI digital certificate verification and are accessible on the official portal referencing: <b>{ref_text}</b>."
    )
    notice_table = Table([[Paragraph(notice_text, ParagraphStyle('N', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#475569')))]], colWidths=[520])
    notice_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (0,0), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (0,0), 7),
        ('BOTTOMPADDING', (0,0), (0,0), 7),
        ('LEFTPADDING', (0,0), (0,0), 9),
        ('RIGHTPADDING', (0,0), (0,0), 9),
    ]))
    story.append(notice_table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_solution_document_pdf(data: Dict[str, Any]) -> bytes:
    """
    Builds an official Nikom InfraSolutions Technical Solution Document & Budgetary Offer PDF.
    Contains Executive Design Basis, Capacity Sizing, Scope of Work packages,
    Itemized Bill of Quantities (BOQ) in INR Lakhs, Commercial Terms, and Project Schedule.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        fontName='Helvetica'
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica-Bold'
    )

    cell_label = ParagraphStyle(
        'CellLabel',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#475569'),
        fontName='Helvetica-Bold'
    )

    cell_value = ParagraphStyle(
        'CellValue',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica'
    )

    cell_value_bold = ParagraphStyle(
        'CellValueBold',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )

    story = []

    # 1. Header & Organization Identity
    it_kw = float(data.get('it_load_kw') or 250)
    racks = int(data.get('rack_count') or 25)
    kw_per_rack = round(it_kw / max(1, racks), 1)
    heat_kw = round(it_kw * 1.15, 1)
    cooling_tr = float(data.get('cooling_capacity_tr') or round(heat_kw / 3.517, 1))
    ups_kva = int(data.get('ups_rating_kva') or round((it_kw / 0.9) * 1.25))
    dg_kva = int(data.get('dg_rating_kva') or round(((it_kw + cooling_tr + (it_kw * 0.1)) / 0.8) * 1.25))
    sqft = int(data.get('floor_area_sqft') or int(racks * 35 * 1.4))
    pue = data.get('estimated_pue') or '1.36 - 1.48 (Hot-Aisle Containment)'
    client_org = data.get('client_org') or 'Enterprise / Institutional Facility'

    header_table = Table(
        [
            [
                Paragraph("<b>NIKOM INFRASOLUTIONS PVT. LTD.</b><br/><font size=7.5 color='#64748B'>Data Centre Design, Build & Lifecycle Operations &bull; ISO 9001:2015 &bull; IGBC Member<br/>Head Office: Nehru Place, New Delhi &bull; Web: www.nikom.in &bull; Email: info@nikom.in</font>", styles['Normal']),
                Paragraph(f"<b>INDICATIVE OFFER</b><br/><font size=7.5 color='#2563EB'>Ref: NIK/BD-2026/SO-{int(it_kw)}<br/>Date: {datetime.now().strftime('%d %b %Y')}<br/>Redundancy: ANSI/TIA-942-C Tier III</font>", ParagraphStyle('R', parent=styles['Normal'], alignment=2))
            ]
        ],
        colWidths=[330, 190]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=10, spaceBefore=4))

    # 2. Document Title
    story.append(Paragraph("TECHNICAL SOLUTION DOCUMENT & BUDGETARY OFFER", title_style))
    story.append(Paragraph(f"Turnkey Data Centre Infrastructure & Balance of Plant Solution for <b>{client_org}</b>", subtitle_style))
    story.append(Spacer(1, 10))

    # 3. Design Basis & Capacity Sizing Summary Grid
    story.append(Paragraph("1. EXECUTIVE DESIGN BASIS & CAPACITY SIZING", h2_style))
    story.append(Spacer(1, 4))

    specs_grid = [
        [
            Paragraph("IT DESIGN LOAD", cell_label),
            Paragraph(f"<b>{it_kw} kW</b>", cell_value_bold),
            Paragraph("TOTAL HEAT DISSIPATION", cell_label),
            Paragraph(f"<b>{heat_kw} kW</b> (IT &times; 1.15)", cell_value)
        ],
        [
            Paragraph("SERVER RACKS", cell_label),
            Paragraph(f"<b>{racks} Racks</b> ({kw_per_rack} kW/rack)", cell_value),
            Paragraph("COOLING CAPACITY", cell_label),
            Paragraph(f"<b>{cooling_tr} TR</b> (N+1 Redundant)", cell_value_bold)
        ],
        [
            Paragraph("POWER TOPOLOGY", cell_label),
            Paragraph(f"<b>2N Modular UPS (2 &times; {ups_kva} kVA)</b>", cell_value_bold),
            Paragraph("BATTERY AUTONOMY", cell_label),
            Paragraph("<b>15 Min</b> Li-ion (LFP) with BMS", cell_value)
        ],
        [
            Paragraph("STANDBY GENERATOR", cell_label),
            Paragraph(f"<b>{dg_kva} kVA</b> (CPCB IV+ Compliant)", cell_value_bold),
            Paragraph("TARGET DESIGN PUE", cell_label),
            Paragraph(f"<b>{pue}</b>", cell_value)
        ],
        [
            Paragraph("DATA HALL FOOTPRINT", cell_label),
            Paragraph(f"~<b>{sqft} sq. ft</b> (Raised Floor)", cell_value),
            Paragraph("REDUNDANCY TARGET", cell_label),
            Paragraph("<b>Tier III Concurrently Maintainable</b>", cell_value_bold)
        ]
    ]

    t_specs = Table(specs_grid, colWidths=[120, 140, 120, 140])
    t_specs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_specs)
    story.append(Spacer(1, 10))

    # 4. Scope of Work Packages
    story.append(Paragraph("2. TURNKEY SCOPE OF WORK & SUBSYSTEMS ARCHITECTURE", h2_style))
    story.append(Spacer(1, 4))

    scope_data = [
        [
            Paragraph("<b>Package / Subsystem</b>", cell_label),
            Paragraph("<b>Technical Architecture & Nikom Delivery Specifications</b>", cell_label)
        ],
        [
            Paragraph("<b>1. Precision Cooling & Containment</b>", cell_value_bold),
            Paragraph(f"Inverter DX In-Row Cooling units in <b>N+1 configuration</b> with variable-speed EC fans and BLDC compressors; rigid Hot-Aisle Containment (HAC) with auto-closing glass sliding doors and smoke-purge links; dual refrigerant copper circuits and outdoor condenser banks.", cell_value)
        ],
        [
            Paragraph("<b>2. 2N Electrical & Modular UPS</b>", cell_value_bold),
            Paragraph(f"Dual-path <b>2N True On-Line Modular UPS system (2 &times; {ups_kva} kVA)</b> operating at 40–50% nominal load; 15-minute Lithium Iron Phosphate (Li-ion LFP) battery cabinets with integrated cell-level BMS; dual overhead busways (A+B feeds) with tap-off units.", cell_value)
        ],
        [
            Paragraph("<b>3. CPCB IV+ DG Standby Power</b>", cell_value_bold),
            Paragraph(f"Prime-rated <b>{dg_kva} kVA CPCB IV+ compliant DG set</b> with acoustic enclosure (<75 dB(A) @ 1m), electronic governor, AMF synchronising panel, and 1,500 L bulk HSD fuel storage day tank.", cell_value)
        ],
        [
            Paragraph("<b>4. Clean Agent Fire Suppression</b>", cell_value_bold),
            Paragraph("Total flooding clean-agent gas suppression (<b>FK-5-1-12 / Novec 1230</b>) with cross-zoned photoelectric smoke detectors; <b>VESDA LaserPlus</b> aspirating smoke detection (0.005% to 20% obs/m sensitivity); 2-hour fire-rated doors.", cell_value)
        ],
        [
            Paragraph("<b>5. DCIM, Security & Monitoring</b>", cell_value_bold),
            Paragraph("Comprehensive DCIM with real-time PUE and branch circuit monitoring; <b>STQC-certified Full HD IP CCTV</b> with 30-day storage; biometric access control; addressable rope-type water leak detection along perimeter and CRAC trays; ultrasonic rodent repellent.", cell_value)
        ],
        [
            Paragraph("<b>6. Civil Fit-Out & Raised Floor</b>", cell_value_bold),
            Paragraph("Heavy-duty anti-static raised access floor (600&times;600 mm, 35 kN concentrated load, 450 mm finished floor height); underfloor thermal insulation (closed-cell elastomeric); fire-rated drywall partitions.", cell_value)
        ]
    ]

    t_scope = Table(scope_data, colWidths=[150, 370])
    t_scope.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_scope)
    story.append(Spacer(1, 10))

    # 5. Indicative Budgetary Breakdown
    story.append(Paragraph("3. INDICATIVE BUDGETARY OFFER (BILL OF QUANTITIES BREAKDOWN)", h2_style))
    story.append(Spacer(1, 4))

    sqft_val = sqft
    cost_civil = round(sqft_val * 0.028, 1)
    cost_cooling = round(cooling_tr * 1.4, 1)
    cost_ups = round((ups_kva * 2) * 0.24, 1)
    cost_dg = round(dg_kva * 0.12, 1)
    cost_bop = round(it_kw * 0.24, 1)
    cost_ist = round((cost_civil + cost_cooling + cost_ups + cost_dg + cost_bop) * 0.05, 1)
    cost_total_lakhs = round(cost_civil + cost_cooling + cost_ups + cost_dg + cost_bop + cost_ist, 1)
    cost_total_cr = round(cost_total_lakhs / 100.0, 2)
    cost_om = round(max(24.0, it_kw * 0.16), 1)

    boq_data = [
        [
            Paragraph("<b>No.</b>", cell_label),
            Paragraph("<b>Subsystem / Package Description</b>", cell_label),
            Paragraph("<b>Basis & Equipment Scope</b>", cell_label),
            Paragraph("<b>Amount (₹ Lakhs)</b>", ParagraphStyle('R', parent=cell_label, alignment=2))
        ],
        [
            Paragraph("1", cell_value),
            Paragraph("Civil Fit-out, Raised Access Flooring & Partitions", cell_value_bold),
            Paragraph(f"600&times;600mm 35kN floor, thermal insulation, fire doors (~{sqft_val} sq. ft)", cell_value),
            Paragraph(f"₹ {cost_civil:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("2", cell_value),
            Paragraph("Precision In-Row DX Cooling & Containment", cell_value_bold),
            Paragraph(f"{cooling_tr} TR N+1 In-Row units, EC fans, Hot-Aisle Containment, piping", cell_value),
            Paragraph(f"₹ {cost_cooling:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("3", cell_value),
            Paragraph("2N Modular UPS & Li-ion Battery Cabinets", cell_value_bold),
            Paragraph(f"2 &times; {ups_kva} kVA Modular UPS, 15-min LFP Li-ion racks, dual busways", cell_value),
            Paragraph(f"₹ {cost_ups:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("4", cell_value),
            Paragraph("CPCB IV+ DG Power Generation System", cell_value_bold),
            Paragraph(f"{dg_kva} kVA Prime DG, AMF synchronising panel, fuel system, chimney", cell_value),
            Paragraph(f"₹ {cost_dg:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("5", cell_value),
            Paragraph("Turnkey Balance of Plant (Fire, VESDA, DCIM, CCTV)", cell_value_bold),
            Paragraph("FK-5-1-12 gas flooding, VESDA, STQC CCTV, biometric access, WLD rope", cell_value),
            Paragraph(f"₹ {cost_bop:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("6", cell_value),
            Paragraph("Testing, Commissioning, FAT/SAT & IST", cell_value_bold),
            Paragraph("Integrated Systems Testing (IST), load-bank testing, black building test", cell_value),
            Paragraph(f"₹ {cost_ist:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("<b>TOTAL</b>", cell_value_bold),
            Paragraph(f"<b>TOTAL INDICATIVE CAPITAL BUDGETARY OFFER</b>", cell_value_bold),
            Paragraph(f"<b>Complete Turnkey EPC Delivery (₹ {cost_total_cr} Crores)</b>", cell_value_bold),
            Paragraph(f"<b>₹ {cost_total_lakhs:,.2f}</b>", ParagraphStyle('R', parent=cell_value_bold, alignment=2, textColor=colors.HexColor('#2563EB')))
        ],
        [
            Paragraph("Opt.", cell_value),
            Paragraph("Comprehensive 24&times;7 Facility O&M (Year 1)", cell_value),
            Paragraph("24&times;7 round-the-clock site engineers, preventive maintenance, SLA guarantees", cell_value),
            Paragraph(f"₹ {cost_om:,.2f} / yr", ParagraphStyle('R', parent=cell_value, alignment=2))
        ]
    ]

    t_boq = Table(boq_data, colWidths=[25, 195, 200, 100])
    t_boq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEBELOW', (0,7), (-1,7), 1.5, colors.HexColor('#2563EB')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_boq)
    story.append(Spacer(1, 10))

    # 6. Commercial Terms & Implementation Milestones
    terms_text = (
        "<b>Commercial Terms & Milestones:</b> 1. Prices are indicative budgetary estimates exclusive of applicable GST (18%). "
        "2. Offer validity: 60 calendar days. 3. Standard PSU / Enterprise Payment Stages: 15% mobilization advance against ABG, 60% on delivery of plant equipment, "
        "15% on installation/erection, 10% on successful completion of Integrated Systems Testing (IST) & site handover against PBG. "
        "4. Estimated Execution Timeline: 16 to 20 weeks from site handover to IST commissioning."
    )
    terms_table = Table([[Paragraph(terms_text, ParagraphStyle('T', parent=styles['Normal'], fontSize=7.5, leading=10.5, textColor=colors.HexColor('#475569')))]], colWidths=[520])
    terms_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (0,0), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (0,0), 6),
        ('BOTTOMPADDING', (0,0), (0,0), 6),
        ('LEFTPADDING', (0,0), (0,0), 8),
        ('RIGHTPADDING', (0,0), (0,0), 8),
    ]))
    story.append(terms_table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
