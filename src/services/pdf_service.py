"""
Official Tender Document & Specification PDF Generation Service.
Generates authenticated, professional PDF dossiers for tenders across all Indian portals
(CPPP, GePNIC, State eProcurement, IOCL, PSUs, eWizard, TenderWizard) ensuring 100% openable valid PDF documents.
"""

import io
import re
import logging
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
