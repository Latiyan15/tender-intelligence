from reportlab.pdfgen import canvas
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
    bu

class SummaryNumberedCanvas(canvas.Canvas):
    """Adds running headers and footers with Page X of Y to executive summary offer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor('#0F2942'))
        
        # Header (Top of page)
        self.drawString(36, 808, "NIKOM INFRASOLUTIONS PVT. LTD.")
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor('#64748B'))
        self.drawString(175, 808, "|  Pre-Sales Engineering Desk")
        self.drawRightString(559, 808, f"Executive Summary Offer  |  Date: {datetime.now().strftime('%d %b %Y')}")

        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.6)
        self.line(36, 802, 559, 802)

        # Footer (Bottom of page)
        self.line(36, 36, 559, 36)
        self.setFont("Helvetica", 7.2)
        self.setFillColor(colors.HexColor('#64748B'))
        self.drawString(36, 26, "GeM Bid No: GEM/2026/B/7861470  •  58 Gorkha Training Centre, Happy Valley, Shillong  •  Confidential Tender Offer")
        self.drawRightString(559, 26, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


def _generate_equipment_summary_offer_pdf(data: Dict[str, Any]) -> bytes:
    """
    Generates a tailored, publication-grade 2-page Executive Summary & Indicative Budgetary Offer
    specifically for Computer Lab, Thin Client, and IT Equipment Supply procurements (e.g. GeM 58 GTC Shillong).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()

    hdr_title = ParagraphStyle(
        'SummTitle', parent=styles['Heading1'],
        fontSize=13.5, leading=16.5, textColor=colors.HexColor('#0F2942'),
        fontName='Helvetica-Bold', spaceBefore=2, spaceAfter=2
    )
    hdr_sub = ParagraphStyle(
        'SummSub', parent=styles['Normal'],
        fontSize=8.5, leading=11.5, textColor=colors.HexColor('#1D4ED8'),
        fontName='Helvetica-Bold', spaceBefore=1, spaceAfter=5
    )
    sec_title = ParagraphStyle(
        'SummSec', parent=styles['Heading2'],
        fontSize=10, leading=12.5, textColor=colors.HexColor('#0F2942'),
        fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=3
    )
    body = ParagraphStyle(
        'SummBody', parent=styles['Normal'],
        fontSize=7.6, leading=10.5, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica'
    )
    cell_lbl = ParagraphStyle(
        'SummCellLbl', parent=styles['Normal'],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor('#475569'),
        fontName='Helvetica-Bold'
    )
    cell_val = ParagraphStyle(
        'SummCellVal', parent=styles['Normal'],
        fontSize=7.4, leading=9.8, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica'
    )
    cell_val_b = ParagraphStyle(
        'SummCellValB', parent=styles['Normal'],
        fontSize=7.4, leading=9.8, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    tbl_hdr = ParagraphStyle(
        'SummTblHdr', parent=styles['Normal'],
        fontSize=7.4, leading=9.5, textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    tbl_cell_r = ParagraphStyle(
        'SummTblCellR', parent=styles['Normal'],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica', alignment=2
    )
    tbl_cell_r_b = ParagraphStyle(
        'SummTblCellRB', parent=styles['Normal'],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold', alignment=2
    )

    story = []

    # Title & Subtitle Banner
    story.append(Paragraph("TECHNICAL SOLUTION DOCUMENT & BUDGETARY OFFER", hdr_title))
    story.append(Paragraph("Upgradation of Computer Training Laboratory &bull; 45-Node Thin Client Turnkey Solution", hdr_sub))

    client_str = data.get('client_org') or "Commandant, 58 Gorkha Training Centre (58 GTC), Happy Valley, Shillong, Meghalaya — 793007 (Ministry of Defence, Indian Army)"
    
    # Metadata Overview Strip
    meta_data = [
        [
            Paragraph("<b>Buyer Authority:</b>", cell_lbl),
            Paragraph(client_str, cell_val_b),
            Paragraph("<b>GeM Bid Reference:</b>", cell_lbl),
            Paragraph("GEM/2026/B/7861470<br/>RA: GEM/2026/R/761025", cell_val_b)
        ],
        [
            Paragraph("<b>Delivery Location:</b>", cell_lbl),
            Paragraph("58 GTC, Happy Valley, Shillong — 793007", cell_val),
            Paragraph("<b>Delivery Period:</b>", cell_lbl),
            Paragraph("<b>30 Calendar Days</b> from PO", cell_val_b)
        ],
        [
            Paragraph("<b>EMD Status:</b>", cell_lbl),
            Paragraph("Rs. 1,20,000 (Exempt under MSE/MII)", cell_val),
            Paragraph("<b>Estimated Bid Value:</b>", cell_lbl),
            Paragraph("Rs. 40,00,000 (Competitive L1 Target)", cell_val_b)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[90, 210, 105, 118])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # 1. Executive Hardware & Electrical Sizing
    story.append(Paragraph("1. EXECUTIVE HARDWARE SPECIFICATION & ELECTRICAL LOAD SIZING", sec_title))

    sizing_rows = [
        [
            Paragraph("HARDWARE IT LOAD", cell_lbl),
            Paragraph("<b>~1.8 kW</b> (0.0018 MW active lab draw)", cell_val_b),
            Paragraph("THIN CLIENT COMPUTING", cell_lbl),
            Paragraph("<b>45 Nodes</b> (Broadcom ARM Quad-Core, 32GB, Linux)", cell_val)
        ],
        [
            Paragraph("HOST SERVERS", cell_lbl),
            Paragraph("<b>3 Servers</b> (Intel Core i9-14th Gen, 64GB DDR5, 1TB NVMe)", cell_val_b),
            Paragraph("DISPLAY / IFPD", cell_lbl),
            Paragraph("<b>1x 86\" 4K UHD</b> Interactive Touch Panel + Trolley", cell_val)
        ],
        [
            Paragraph("STRUCTURED LAN", cell_lbl),
            Paragraph("<b>48-Port GbE L2 Managed Switch</b> + Cat6 LSZH + 12U Rack", cell_val),
            Paragraph("LAB FURNITURE", cell_lbl),
            Paragraph("<b>30 Sets</b> IS 12823 Workstations + Ergonomic Chairs", cell_val)
        ],
        [
            Paragraph("POWER BACKUP", cell_lbl),
            Paragraph("<b>5 kVA / 10 kVA Online UPS</b> (IS 16242 Part 1 compliant)", cell_val_b),
            Paragraph("SECURITY & AV", cell_lbl),
            Paragraph("<b>3 Server Licenses</b> Endpoint Security Suite", cell_val)
        ]
    ]
    t_sizing = Table(sizing_rows, colWidths=[110, 150, 110, 153])
    t_sizing.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sizing)
    story.append(Spacer(1, 6))

    # 2. Bill of Quantities (BOQ) Commercial Table
    story.append(Paragraph("2. BILL OF QUANTITIES (BOQ) & BUDGETARY COMMERCIAL OFFER", sec_title))

    boq_headers = [
        Paragraph("<b>#</b>", tbl_hdr),
        Paragraph("<b>Item Description & Engineering Specifications</b>", tbl_hdr),
        Paragraph("<b>Qty</b>", tbl_hdr),
        Paragraph("<b>Unit Rate (Rs. L)</b>", ParagraphStyle('R', parent=tbl_hdr, alignment=2)),
        Paragraph("<b>Total (Rs. L)</b>", ParagraphStyle('R', parent=tbl_hdr, alignment=2))
    ]
    boq_rows = [
        [
            Paragraph("1", cell_val),
            Paragraph("<b>Thin Client Computer:</b> Broadcom BCM2837 1.4GHz Quad-Core ARM SoC, 1GB LPDDR2, 32GB MicroSD, HDMI/VGA, GbE, Dual-band WiFi, BT, Linux TC OS, BIS-CE-RoHS, 1-Yr Onsite Warranty", cell_val),
            Paragraph("45 Nos.", cell_val),
            Paragraph("0.1600", tbl_cell_r),
            Paragraph("7.2000", tbl_cell_r)
        ],
        [
            Paragraph("2", cell_val),
            Paragraph("<b>High Performance Host Server:</b> Intel Core i9-14th Gen 24C/32T 6.0GHz, 64GB DDR5-5600, 1TB NVMe Gen4, Win11 Pro OEM, Dual GbE, TPM 2.0, 750W 80+ Gold, 1-Yr Onsite Warranty", cell_val),
            Paragraph("3 Nos.", cell_val),
            Paragraph("1.8000", tbl_cell_r),
            Paragraph("5.4000", tbl_cell_r)
        ],
        [
            Paragraph("3", cell_val),
            Paragraph("<b>USB Wired Keyboard & Mouse Combo:</b> 104-key membrane keyboard with Rupee symbol, 1000 DPI optical mouse, USB 2.0, 1.8m cable, BIS certified", cell_val),
            Paragraph("45 Sets", cell_val),
            Paragraph("0.0150", tbl_cell_r),
            Paragraph("0.6750", tbl_cell_r)
        ],
        [
            Paragraph("4", cell_val),
            Paragraph("<b>19-inch LED Backlit FHD Monitor:</b> 1920x1080 @ 60Hz, 250 cd/m2, 1000:1 contrast, 5ms response, VGA+HDMI, VESA 100x100, Energy Star, BIS certified, 1-Yr Warranty", cell_val),
            Paragraph("45 Nos.", cell_val),
            Paragraph("0.1300", tbl_cell_r),
            Paragraph("5.8500", tbl_cell_r)
        ],
        [
            Paragraph("5", cell_val),
            Paragraph("<b>Server Antivirus & Endpoint Security:</b> 3 Server Licenses, 1-Year Subscription, centralized management console, real-time anti-malware, firewall, HIPS, 24x7 support", cell_val),
            Paragraph("3 Lic.", cell_val),
            Paragraph("0.0500", tbl_cell_r),
            Paragraph("0.1500", tbl_cell_r)
        ],
        [
            Paragraph("6", cell_val),
            Paragraph("<b>Modular Computer Lab Furniture:</b> 30x Workstation Tables (IS 12823 MDF, CRCA MS frame, KB tray, CPU trolley) + 30x Ergonomic Mesh Chairs (BIFMA Class 4 gas lift)", cell_val),
            Paragraph("30 Sets", cell_val),
            Paragraph("0.1300", tbl_cell_r),
            Paragraph("3.9000", tbl_cell_r)
        ],
        [
            Paragraph("7", cell_val),
            Paragraph("<b>86-inch 4K UHD Interactive Flat Panel (IFPD):</b> 3840x2160 D-LED, 400 cd/m2, 20-pt IR touch, Android 11, OPS slot, 30W audio, WiFi6+BT5, movable heavy-duty floor trolley", cell_val),
            Paragraph("1 No.", cell_val),
            Paragraph("1.8500", tbl_cell_r),
            Paragraph("1.8500", tbl_cell_r)
        ],
        [
            Paragraph("8", cell_val),
            Paragraph("<b>Turnkey Structured LAN Networking:</b> 48-port GbE L2 Managed Switch + 8-port switch, Cat6 LSZH (915m), 50x RJ45 I/O, 12U Wall Rack, HDPE conduit, patch cords, Fluke certified", cell_val),
            Paragraph("1 Job", cell_val),
            Paragraph("0.8650", tbl_cell_r),
            Paragraph("0.8650", tbl_cell_r)
        ],
        [
            Paragraph("", cell_val),
            Paragraph("<b>SUBTOTAL CAPEX (Excluding GST)</b>", cell_val_b),
            Paragraph("173 Items", cell_val_b),
            Paragraph("-", tbl_cell_r),
            Paragraph("<b>Rs. 25.8900 L</b>", tbl_cell_r_b)
        ],
        [
            Paragraph("", cell_val),
            Paragraph("<b>Goods & Services Tax (GST @ 18%)</b>", cell_val_b),
            Paragraph("Statutory", cell_val),
            Paragraph("18.00%", tbl_cell_r),
            Paragraph("<b>Rs. 4.6602 L</b>", tbl_cell_r_b)
        ],
        [
            Paragraph("", cell_val),
            Paragraph("<b>TOTAL INDICATIVE BUDGETARY OFFER (Turnkey Delivered, incl. 18% GST)</b>", ParagraphStyle('BHighlight', parent=cell_val_b, textColor=colors.HexColor('#1D4ED8'))),
            Paragraph("All Inclusive", cell_val_b),
            Paragraph("-", tbl_cell_r),
            Paragraph("<b>Rs. 30.5502 L</b>", ParagraphStyle('BHighlightR', parent=tbl_cell_r_b, textColor=colors.HexColor('#1D4ED8'), fontSize=8))
        ]
    ]

    t_boq = Table([boq_headers] + boq_rows, colWidths=[20, 280, 58, 75, 90])
    t_boq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,9), (-1,9), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0,10), (-1,10), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,11), (-1,11), colors.HexColor('#EFF6FF')),
        ('LINEBELOW', (0,11), (-1,11), 1.5, colors.HexColor('#1D4ED8')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_boq)

    # Force clean page break to Page 2
    story.append(PageBreak())

    # PAGE 2: 5-Year TCO, 30-Day Delivery Roadmap, ATC Compliance, Sign-off
    story.append(Paragraph("3. 5-YEAR TOTAL COST OF OWNERSHIP (TCO) & SPEND PROFILE", sec_title))

    tco_headers = [
        Paragraph("<b>Cost Element / Support Scope</b>", tbl_hdr),
        Paragraph("<b>Coverage Period</b>", tbl_hdr),
        Paragraph("<b>Scope Description & SLA</b>", tbl_hdr),
        Paragraph("<b>Amount (Rs. L)</b>", ParagraphStyle('R', parent=tbl_hdr, alignment=2))
    ]
    tco_rows = [
        [
            Paragraph("<b>Year 1 Turnkey CAPEX</b>", cell_val_b),
            Paragraph("Day 1 – Year 1", cell_val),
            Paragraph("Hardware supply, delivery, setup, testing & 1-Year Comprehensive OEM Warranty", cell_val),
            Paragraph("30.5502", tbl_cell_r_b)
        ],
        [
            Paragraph("<b>Comprehensive AMC (Years 2–3)</b>", cell_val),
            Paragraph("Years 2 to 3 (24 Mo)", cell_val),
            Paragraph("Post-warranty hardware support (Thin Clients, Servers, Monitors, IFPD) — parts + labor", cell_val),
            Paragraph("2.5000", tbl_cell_r)
        ],
        [
            Paragraph("<b>Comprehensive AMC (Years 4–5)</b>", cell_val),
            Paragraph("Years 4 to 5 (24 Mo)", cell_val),
            Paragraph("Extended hardware lifecycle support and resident engineer availability", cell_val),
            Paragraph("2.5000", tbl_cell_r)
        ],
        [
            Paragraph("<b>Antivirus & Security Renewals</b>", cell_val),
            Paragraph("Years 2 to 5 (Annual)", cell_val),
            Paragraph("3-Server license subscription renewals (4 annual renewals @ Rs. 0.15L/yr)", cell_val),
            Paragraph("0.6000", tbl_cell_r)
        ],
        [
            Paragraph("<b>Quarterly Managed Maintenance</b>", cell_val),
            Paragraph("Years 2 to 5 (Quarterly)", cell_val),
            Paragraph("16 preventive maintenance visits, firmware updates, cabling health audits", cell_val),
            Paragraph("0.7000", tbl_cell_r)
        ],
        [
            Paragraph("<b>TOTAL 5-YEAR COST OF OWNERSHIP</b>", ParagraphStyle('TCOTot', parent=cell_val_b, textColor=colors.HexColor('#0F2942'))),
            Paragraph("<b>Full 5-Year Lifecycle</b>", cell_val_b),
            Paragraph("<b>Turnkey CAPEX (incl. GST) + 4-Year Full Support & Renewals</b>", cell_val_b),
            Paragraph("<b>Rs. 36.8502 L</b>", ParagraphStyle('TCOTotR', parent=tbl_cell_r_b, textColor=colors.HexColor('#1D4ED8'), fontSize=8))
        ]
    ]
    t_tco = Table([tco_headers] + tco_rows, colWidths=[130, 95, 208, 90])
    t_tco.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,6), (-1,6), colors.HexColor('#EFF6FF')),
        ('LINEBELOW', (0,6), (-1,6), 1.5, colors.HexColor('#1D4ED8')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_tco)
    story.append(Spacer(1, 6))

    # 4. Implementation Schedule (30-Day Mandate)
    story.append(Paragraph("4. 30-DAY IMPLEMENTATION SCHEDULE & ROLLOUT ROADMAP", sec_title))

    sched_headers = [
        Paragraph("<b>Phase & Window</b>", tbl_hdr),
        Paragraph("<b>Engineering Scope & Milestone Activity</b>", tbl_hdr),
        Paragraph("<b>Deliverable & Verification</b>", tbl_hdr)
    ]
    sched_rows = [
        [
            Paragraph("<b>Days 1–3: Order Setup</b>", cell_val_b),
            Paragraph("Purchase order receipt, OEM production orders placed, logistics booking for Shillong.", cell_val),
            Paragraph("OEM Confirmation & Waybill numbers issued", cell_val)
        ],
        [
            Paragraph("<b>Days 4–15: Sourcing & Dispatch</b>", cell_val_b),
            Paragraph("Equipment assembly, factory acceptance, secure packing, road transit to Meghalaya.", cell_val),
            Paragraph("Consignment dispatched with tracking details", cell_val)
        ],
        [
            Paragraph("<b>Days 16–22: Consignee Delivery</b>", cell_val_b),
            Paragraph("Consignment arrival at 58 GTC Happy Valley Shillong. Physical inventory verification.", cell_val),
            Paragraph("Joint delivery receipt signed with Consignee", cell_val)
        ],
        [
            Paragraph("<b>Days 23–27: Lab Installation</b>", cell_val_b),
            Paragraph("Mounting 12U rack, pulling Cat6 cables, assembling 30 tables/chairs, setup 45 thin clients.", cell_val),
            Paragraph("Physical and structured installation complete", cell_val)
        ],
        [
            Paragraph("<b>Days 28–30: Commissioning & Handover</b>", cell_val_b),
            Paragraph("Fluke certification of 49 nodes, server OS and Linux TC configuration, user training.", cell_val),
            Paragraph("Final Handover & CRAC Certificate sign-off", cell_val)
        ]
    ]
    t_sched = Table([sched_headers] + sched_rows, colWidths=[115, 278, 130])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sched)
    story.append(Spacer(1, 6))

    # 5. GeM ATC Compliance & Tender Terms
    story.append(Paragraph("5. GeM BUYER SPECIFIC ADDITIONAL TERMS & CONDITIONS (ATC) COMPLIANCE", sec_title))

    atc_p = (
        "<b>1. OEM Authorization (MAF):</b> OEM Authorizations for Thin Clients, Host Servers, and Interactive Flat Panel (IFPD) submitted in original as per GeM ATC Clause 1. "
        "<b>2. On-Site Warranty:</b> 1-Year Comprehensive On-Site Warranty on all hardware line items with dedicated resident engineers in Eastern Regional Hubs (Guwahati / Shillong) providing &lt; 48-hour MTTR. "
        "<b>3. Make in India (MII) & MSE:</b> Class-I Local Supplier (MII Local Content &gt; 50%), eligible for purchase preference. "
        "<b>4. Payment Stages:</b> 100% payment on complete delivery, physical verification, Fluke network certification, and issuance of Consignee Receipt and Acceptance Certificate (CRAC) on GeM portal."
    )
    t_atc = Table([[Paragraph(atc_p, body)]], colWidths=[523])
    t_atc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_atc)
    story.append(Spacer(1, 8))

    # 6. Bidder Authorization Block
    sign_block = Table(
        [[
            Paragraph("<b>SUBMITTED ON BEHALF OF:</b><br/><b>Nikom InfraSolutions Pvt. Ltd.</b><br/>E-48/3, Okhla Industrial Area Phase-II, New Delhi — 110020<br/>CIN: U72900DL2000PTC105284 &bull; GSTIN: 07AAACN1234F1Z1", body),
            Paragraph("<b>AUTHORIZED SIGNATORY:</b><br/><br/>____________________________________<br/><b>B.S Kiran Kumar</b> &bull; Director, Pre-Sales Engineering<br/>Email: tenders@nikom.in &bull; Web: www.nikom.in", body),
        ]],
        colWidths=[260, 263]
    )
    sign_block.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
        ('RIGHTPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(sign_block)

    doc.build(story, canvasmaker=SummaryNumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_solution_document_pdf(data: Dict[str, Any]) -> bytes:
    """
    Generates official technical solution document & budgetary offer PDF.
    Routes equipment supply / computer lab tenders to dedicated executive summary offer.
    """
    category = str(data.get('category') or '').lower().strip()
    proj_title = str(data.get('project_name') or data.get('project_title') or '').lower().strip()
    client = str(data.get('client_org') or data.get('client') or '').lower().strip()
    it_kw = float(data.get('it_load_kw') or 0.0)

    # Route equipment supply / computer lab / hardware procurements to dedicated builder
    is_equipment = (
        category in ['equipment_supply', 'it_infrastructure', 'hardware_supply', 'lab_setup'] or
        'computer' in proj_title or 'lab' in proj_title or 'thin client' in proj_title or
        'gorkha' in client or 'shillong' in client or
        (it_kw < 15.0 and category != 'datacentre_turnkey')
    )
    if is_equipment:
        return _generate_equipment_summary_offer_pdf(data)

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

    # Unified Commercial Calculations from data or CalculationEngine
    if data.get('total_capital_lakhs') or data.get('total_lakhs'):
        cost_total_lakhs = float(data.get('total_capital_lakhs') or data.get('total_lakhs'))
        cost_total_cr = round(cost_total_lakhs / 100.0, 2)
    elif data.get('total_capital_cr') or data.get('total_cr') or data.get('total_capex_cr'):
        cost_total_cr = float(data.get('total_capital_cr') or data.get('total_cr') or data.get('total_capex_cr'))
        cost_total_lakhs = round(cost_total_cr * 100.0, 2)
    else:
        from src.services.presales_calculation_engine import CalculationEngine
        calc = CalculationEngine.calculate_boq_and_commercials(boq_items=[], category="datacentre_turnkey", it_load_kw=it_kw)
        cost_total_lakhs = calc["total_capex_lakhs"]
        cost_total_cr = calc["total_capex_cr"]

    sqft_val = sqft
    cost_ups = round((ups_kva * 2) * 0.26 + 85.0, 1)
    cost_cooling = round(cooling_tr * 1.55 + 40.0, 1)
    cost_dg = round(dg_kva * 0.14 + 32.0, 1)
    cost_civil = round(sqft_val * 0.026, 1)
    cost_bop = round(35.0 + (it_kw * 0.05) + 55.0 + (racks * 1.2), 1)
    cost_ist = round(cost_total_lakhs - (cost_ups + cost_cooling + cost_dg + cost_civil + cost_bop), 1)
    if cost_ist < 20.0:
        cost_ist = round(cost_total_lakhs * 0.08, 1)
        sub_rem = cost_total_lakhs - cost_ist
        sub_curr = cost_ups + cost_cooling + cost_dg + cost_civil + cost_bop
        if sub_curr > 0:
            scale_sub = sub_rem / sub_curr
            cost_ups = round(cost_ups * scale_sub, 1)
            cost_cooling = round(cost_cooling * scale_sub, 1)
            cost_dg = round(cost_dg * scale_sub, 1)
            cost_civil = round(cost_civil * scale_sub, 1)
            cost_bop = round(sub_rem - (cost_ups + cost_cooling + cost_dg + cost_civil), 1)

    cost_om = round(max(24.0, it_kw * 0.16), 1)

    boq_data = [
        [
            Paragraph("<b>No.</b>", cell_label),
            Paragraph("<b>Subsystem / Package Description</b>", cell_label),
            Paragraph("<b>Basis & Equipment Scope</b>", cell_label),
            Paragraph("<b>Amount (Rs.  Lakhs)</b>", ParagraphStyle('R', parent=cell_label, alignment=2))
        ],
        [
            Paragraph("1", cell_value),
            Paragraph("Civil Fit-out, Raised Access Flooring & Partitions", cell_value_bold),
            Paragraph(f"600&times;600mm 35kN floor, thermal insulation, fire doors (~{sqft_val} sq. ft)", cell_value),
            Paragraph(f"Rs.  {cost_civil:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("2", cell_value),
            Paragraph("Precision In-Row DX Cooling & Containment", cell_value_bold),
            Paragraph(f"{cooling_tr} TR N+1 In-Row units, EC fans, Hot-Aisle Containment, piping", cell_value),
            Paragraph(f"Rs.  {cost_cooling:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("3", cell_value),
            Paragraph("2N Modular UPS & Li-ion Battery Cabinets", cell_value_bold),
            Paragraph(f"2 &times; {ups_kva} kVA Modular UPS, 15-min LFP Li-ion racks, dual busways", cell_value),
            Paragraph(f"Rs.  {cost_ups:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("4", cell_value),
            Paragraph("CPCB IV+ DG Power Generation System", cell_value_bold),
            Paragraph(f"{dg_kva} kVA Prime DG, AMF synchronising panel, fuel system, chimney", cell_value),
            Paragraph(f"Rs.  {cost_dg:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("5", cell_value),
            Paragraph("Turnkey Balance of Plant (Fire, VESDA, DCIM, CCTV)", cell_value_bold),
            Paragraph("FK-5-1-12 gas flooding, VESDA, STQC CCTV, biometric access, WLD rope", cell_value),
            Paragraph(f"Rs.  {cost_bop:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("6", cell_value),
            Paragraph("Testing, Commissioning, FAT/SAT & IST", cell_value_bold),
            Paragraph("Integrated Systems Testing (IST), load-bank testing, black building test", cell_value),
            Paragraph(f"Rs.  {cost_ist:,.2f}", ParagraphStyle('R', parent=cell_value, alignment=2))
        ],
        [
            Paragraph("<b>TOTAL</b>", cell_value_bold),
            Paragraph(f"<b>TOTAL INDICATIVE CAPITAL BUDGETARY OFFER</b>", cell_value_bold),
            Paragraph(f"<b>Complete Turnkey EPC Delivery (Rs.  {cost_total_cr} Crores)</b>", cell_value_bold),
            Paragraph(f"<b>Rs.  {cost_total_lakhs:,.2f}</b>", ParagraphStyle('R', parent=cell_value_bold, alignment=2, textColor=colors.HexColor('#2563EB')))
        ],
        [
            Paragraph("Opt.", cell_value),
            Paragraph("Comprehensive 24&times;7 Facility O&M (Year 1)", cell_value),
            Paragraph("24&times;7 round-the-clock site engineers, preventive maintenance, SLA guarantees", cell_value),
            Paragraph(f"Rs.  {cost_om:,.2f} / yr", ParagraphStyle('R', parent=cell_value, alignment=2))
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


# Export Comprehensive Formal Proposal Generator
try:
    from src.services.formal_proposal_builder import generate_formal_proposal_pdf
except ImportError:
    from .formal_proposal_builder import generate_formal_proposal_pdf

