"""
Formal Ready-to-Submit Data Centre Technical Solution & Budgetary Proposal Generator.
Modeled after Nikom's official C-DoT Tier III Certified Data Centre Upgrade proposal.
Produces a comprehensive, publication-grade, submission-ready PDF dossier.
"""

import io
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger(__name__)


class FormalProposalCanvas(canvas.Canvas):
    """
    Two-pass canvas that adds running headers, running footers,
    and exact 'Page X of Y' page numbers to every page except the cover.
    """
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
            if self._pageNumber > 1:
                self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Top Running Header (Pages 2+)
        header_text = "NIKOM INFRASOLUTIONS PVT. LTD.   |   TECHNICAL SOLUTION & BUDGETARY OFFER"
        self.drawString(36, 808, header_text)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 802, 559, 802)

        # Bottom Running Footer
        self.line(36, 36, 559, 36)
        self.drawString(36, 24, "NIKOM   |   Budgetary and confidential")
        self.drawRightString(559, 24, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()




def _generate_equipment_supply_proposal_pdf(data: Dict[str, Any]) -> bytes:
    """
    Generates a tailored, publication-grade Technical Solution & Budgetary Commercial Offer
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

    cover_company = ParagraphStyle(
        'EqCoverCompany', parent=styles['Normal'],
        fontSize=15, leading=18, textColor=colors.HexColor('#0F2942'),
        fontName='Helvetica-Bold'
    )
    cover_tag = ParagraphStyle(
        'EqCoverTag', parent=styles['Normal'],
        fontSize=8, leading=11, textColor=colors.HexColor('#64748B'),
        fontName='Helvetica'
    )
    cover_title = ParagraphStyle(
        'EqCoverTitle', parent=styles['Heading1'],
        fontSize=20, leading=24, textColor=colors.HexColor('#0F2942'),
        fontName='Helvetica-Bold', alignment=0
    )
    cover_sub = ParagraphStyle(
        'EqCoverSub', parent=styles['Normal'],
        fontSize=11, leading=15, textColor=colors.HexColor('#1D4ED8'),
        fontName='Helvetica-Bold', alignment=0
    )
    badge_style = ParagraphStyle(
        'EqBadge', parent=styles['Normal'],
        fontSize=8, leading=11, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    sec_title = ParagraphStyle(
        'EqSecTitle', parent=styles['Heading1'],
        fontSize=12, leading=15, textColor=colors.HexColor('#0F2942'),
        fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=4
    )
    subsec_title = ParagraphStyle(
        'EqSubSecTitle', parent=styles['Heading2'],
        fontSize=9.5, leading=12, textColor=colors.HexColor('#1D4ED8'),
        fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=3
    )
    body_text = ParagraphStyle(
        'EqBody', parent=styles['Normal'],
        fontSize=7.8, leading=11, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica'
    )
    tbl_hdr = ParagraphStyle(
        'EqTblHdr', parent=styles['Normal'],
        fontSize=7.5, leading=9.5, textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    tbl_cell = ParagraphStyle(
        'EqTblCell', parent=styles['Normal'],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica'
    )
    tbl_cell_bold = ParagraphStyle(
        'EqTblCellBold', parent=styles['Normal'],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    tbl_cell_r = ParagraphStyle(
        'EqTblCellR', parent=styles['Normal'],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica', alignment=2
    )
    tbl_cell_r_bold = ParagraphStyle(
        'EqTblCellRBold', parent=styles['Normal'],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold', alignment=2
    )

    client_org = data.get('client_org') or data.get('client') or "Commandant, 58 Gorkha Training Centre (58 GTC), Happy Valley, Shillong, Meghalaya — 793007 (Ministry of Defence, Indian Army)"
    proj_name = data.get('project_name') or data.get('project_title') or "Upgradation of Computer Training Laboratory (45-Node Thin Client Solution)"

    story = []

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 1: EXECUTIVE COVER PAGE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("NIKOM INFRASOLUTIONS PVT. LTD.", cover_company))
    story.append(Paragraph("Pre-Sales & Technical Solutions Directorate &bull; Enterprise IT & Lab Infrastructure Solutions<br/>ISO 9001:2015 &bull; ISO 27001 Certified &bull; MSME Registered &bull; GeM Registered OEM & Solution Provider<br/>Head Office: Nehru Place, New Delhi &bull; Regional Support: North-East Operations Desk &bull; Web: www.nikom.in", cover_tag))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2.5, color=colors.HexColor('#1D4ED8'), spaceBefore=2, spaceAfter=18))

    story.append(Paragraph("TECHNICAL SOLUTION & BUDGETARY COMMERCIAL OFFER", cover_title))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"{proj_name}", cover_sub))
    story.append(Spacer(1, 12))

    ref_box = Table(
        [[
            Paragraph("<b>GeM Bid Reference:</b> GEM/2026/B/7861470", badge_style),
            Paragraph("<b>Reverse Auction (RA):</b> GEM/2026/R/761025", badge_style),
            Paragraph("<b>Scope:</b> 173 Equipment Units (8 Packages)", badge_style)
        ]],
        colWidths=[185, 175, 163]
    )
    ref_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DBEAFE')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(ref_box)
    story.append(Spacer(1, 16))

    meta_table_data = [
        [Paragraph("<b>Procuring Authority</b>", tbl_cell_bold), Paragraph(f"{client_org}", tbl_cell)],
        [Paragraph("<b>Submitted By</b>", tbl_cell_bold), Paragraph("Nikom InfraSolutions Pvt. Ltd., E-48/3, Okhla Industrial Area Phase-II, New Delhi — 110020", tbl_cell)],
        [Paragraph("<b>Engagement Desk</b>", tbl_cell_bold), Paragraph("Enterprise Solutions & Government Bidding Directorate &bull; Email: tenders@nikom.in", tbl_cell)],
        [Paragraph("<b>Offer Date</b>", tbl_cell_bold), Paragraph(datetime.now().strftime("%d %B %Y"), tbl_cell)],
        [Paragraph("<b>Commercial Validity</b>", tbl_cell_bold), Paragraph("180 Calendar Days from Bid End Date (07-Sep-2026)", tbl_cell)],
        [Paragraph("<b>Mandated Delivery Period</b>", tbl_cell_bold), Paragraph("<b>30 Calendar Days</b> from GeM Contract Award to 58 GTC Happy Valley, Shillong", tbl_cell)],
        [Paragraph("<b>EMD & Bank Guarantee</b>", tbl_cell_bold), Paragraph("EMD: <b>Rs. 1,20,000</b> (DD/BC in favour of Regimental Fund Account 58 GTC, payable at SBI Happy Valley Shillong)<br/>ePBG: <b>3% of contract value</b> with 18-month validity upon contract award", tbl_cell)],
        [Paragraph("<b>MII & MSME Status</b>", tbl_cell_bold), Paragraph("Class-1 Local Supplier (&ge;50% Local Content) &bull; Valid OEM Authorizations (MAF) on all hardware", tbl_cell)],
        [Paragraph("<b>Total Turnkey CAPEX (ex-GST)</b>", tbl_cell_bold), Paragraph("<b>Rs. 25.8900 Lakhs</b> (Twenty-Five Lakhs Eighty-Nine Thousand Rupees Only)", tbl_cell_bold)],
        [Paragraph("<b>Total Turnkey CAPEX (incl. 18% GST)</b>", tbl_cell_bold), Paragraph("<b>Rs. 30.5502 Lakhs</b> (Thirty Lakhs Fifty-Five Thousand and Twenty Rupees Only)", tbl_cell_bold)],
    ]
    meta_table = Table(meta_table_data, colWidths=[150, 373])
    meta_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    commit_box = Table(
        [[Paragraph("<b>Turnkey Execution Commitment:</b> Nikom InfraSolutions Pvt. Ltd. guarantees single-point turnkey accountability for the supply, on-site installation, structured cabling, network integration, user configuration, Fluke testing, operator training, and commissioning of the 45-node Computer Training Laboratory at 58 Gorkha Training Centre, Happy Valley, Shillong, in strict compliance with GeM Bid terms, Ministry of Defence quality standards, and OEM comprehensive on-site warranty.", body_text)]],
        colWidths=[523]
    )
    commit_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(commit_box)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 2: EXECUTIVE SUMMARY & SYSTEM SIZING ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. EXECUTIVE SUMMARY & SYSTEM SIZING ARCHITECTURE", sec_title))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F2942'), spaceBefore=2, spaceAfter=8))

    kpi_table_data = [[
        Paragraph("<font size=11 color='#1D4ED8'><b>173 Units</b></font><br/><font size=6.5 color='#475569'>TOTAL EQUIPMENT (8 PKGS)</font>", ParagraphStyle('EqK1', parent=styles['Normal'], alignment=1)),
        Paragraph("<font size=11 color='#059669'><b>~1.8 kW</b></font><br/><font size=6.5 color='#475569'>TOTAL LAB POWER DRAW</font>", ParagraphStyle('EqK2', parent=styles['Normal'], alignment=1)),
        Paragraph("<font size=11 color='#0F172A'><b>Rs. 25.89 L</b></font><br/><font size=6.5 color='#475569'>SUBTOTAL CAPEX (EX-GST)</font>", ParagraphStyle('EqK3', parent=styles['Normal'], alignment=1)),
        Paragraph("<font size=11 color='#1D4ED8'><b>Rs. 30.55 L</b></font><br/><font size=6.5 color='#475569'>TOTAL CAPEX (INCL. 18% GST)</font>", ParagraphStyle('EqK4', parent=styles['Normal'], alignment=1)),
    ]]
    kpi_tbl = Table(kpi_table_data, colWidths=[130, 131, 131, 131])
    kpi_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.1 Project Understanding & Procurement Scope", subsec_title))
    story.append(Paragraph("Nikom InfraSolutions has completed an in-depth correlation audit of all 4 tender documents for GeM Bid No. <b>GEM/2026/B/7861470</b> (Reverse Auction Ref: <b>GEM/2026/R/761025</b>) issued by <b>58 Gorkha Training Centre, Happy Valley, Shillong</b>. The procurement encompasses a comprehensive turnkey upgradation of the Regimental Computer Training Laboratory. All equipment, peripherals, software, networking, and modular furniture are 100% specification-compliant with GeM technical schedules and delivery timelines.", body_text))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.2 Thin Client Architecture & Virtualization Load Sizing", subsec_title))
    story.append(Paragraph("&bull; <b>Client-Server Topology:</b> 45 Thin Client nodes connect over high-speed Gigabit LAN to 3 Host Servers using standard RDP 10.x, Citrix HDX, VMware Horizon, and vSpace Pro virtualization protocols.<br/>&bull; <b>Host Server Load Distribution:</b> 45 concurrent user sessions distributed across 3 Host Servers = <b>15 sessions per host server</b>. Powered by Intel Core i9-14th Gen processors (24 Cores / 32 Threads up to 6.0 GHz) with 64 GB DDR5-5600 RAM and 1 TB PCIe Gen4 NVMe SSD, each server provides >2 dedicated CPU execution threads and >4 GB RAM per concurrent trainee, ensuring seamless execution of office productivity, defense training software, CBT modules, and web applications.<br/>&bull; <b>Electrical Power Footprint:</b> Each thin client consumes &le;5 Watts (45 &times; 5W = 225W). 45 LED monitors consume &le;18W (45 &times; 18W = 810W). 3 Host Servers consume ~250W each (750W). Total active computing power is <b>~1.8 kW</b> (0.0018 MW). This delivers over <b>80% electrical power savings</b> compared to 45 conventional desktop towers (which draw 9.0+ kW), drastically reducing UPS load, heat output, and utility expenditure.", body_text))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.3 Active LAN Network & Display Sizing", subsec_title))
    story.append(Paragraph("&bull; <b>Active Endpoints:</b> 45 Thin Clients + 3 Host Servers + 1 Interactive Flat Panel = <b>49 active network nodes</b>.<br/>&bull; <b>Network Switching:</b> 48-port Gigabit Layer 2 Managed Switch with cascaded uplink, full wire-speed switching fabric, IEEE 802.3af/at PoE capability, and storm control.<br/>&bull; <b>Structured Cabling:</b> 1 &times; 305m CAT6 UTP LSZH cable box with rigid 25mm/32mm HDPE-GI conduit protection, modular faceplates, keystone punch-downs, and Fluke DTX/DSX channel continuity certification.<br/>&bull; <b>Interactive Instructor Station:</b> 86-inch 4K UHD Interactive Flat Panel Display (3840&times;2160, 20-point IR touch, Android 13, 30W front audio, OPS slot) mounted on a heavy-duty powder-coated mobile floor trolley for instructor presentations and interactive training sessions.", body_text))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.4 Furniture & Seating Ergonomics", subsec_title))
    story.append(Paragraph("30 Modular Workstation Tables (pre-laminated MDF, CRCA MS tubular frame, sliding keyboard tray, CPU trolley) paired with 30 Ergonomic Pneumatic Swivel Chairs (high-density PU foam, breathable mesh back, Class 4 gas lift, BIFMA certified). The remaining 15 thin clients serve as instructor stations, hot-spares, and wall-mounted presentation nodes as designated by the buyer.", body_text))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 3: DETAILED TECHNICAL SPECIFICATIONS (PACKAGES A - H)
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. SUBSYSTEM SCOPE OF SUPPLY & DETAILED SPECIFICATIONS", sec_title))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F2942'), spaceBefore=2, spaceAfter=8))

    specs_table_data = [
        [Paragraph("<b>Package / Line Item</b>", tbl_hdr), Paragraph("<b>Qty</b>", tbl_hdr), Paragraph("<b>Detailed Technical Specifications & OEM Basis</b>", tbl_hdr), Paragraph("<b>Warranty & Certifications</b>", tbl_hdr)],
        [
            Paragraph("<b>Package A</b><br/>Thin Client Computing Nodes", tbl_cell_bold),
            Paragraph("45<br/>Nos.", tbl_cell),
            Paragraph("Broadcom BCM2837 1.4 GHz Quad-Core 64-bit ARM Cortex-A53 &bull; 1 GB LPDDR2 SDRAM &bull; 32 GB Internal MicroSD storage &bull; Broadcom VideoCore IV 3D GPU &bull; Full-size HDMI 1.4 (up to 1920&times;1200 @ 60Hz) &bull; Gigabit Ethernet RJ45 + Dual-Band Wi-Fi 802.11 b/g/n/ac + Bluetooth 4.2 BLE &bull; 4&times; USB 2.0 ports &bull; 3.5mm AV jack &bull; Power &le; 5W &bull; Fanless silent operation &bull; VESA mount bracket kit &bull; Linux-based secure embedded Thin Client OS &bull; RDP 10.x, Citrix HDX, VMware Horizon, vSpace Pro", tbl_cell),
            Paragraph("1-Year Comprehensive On-Site OEM Warranty<br/>BIS, CE, FCC, RoHS Compliant", tbl_cell)
        ],
        [
            Paragraph("<b>Package B</b><br/>High-Performance Host Servers", tbl_cell_bold),
            Paragraph("3<br/>Nos.", tbl_cell),
            Paragraph("Intel Core i9 14th Gen (24 Cores / 32 Threads, up to 6.0 GHz Max Turbo, 36 MB Smart Cache) &bull; 64 GB DDR5-5600 MHz RAM (expandable to 128 GB) &bull; 1 TB M.2 NVMe PCIe Gen4 x4 SSD &bull; Hardware RAID 0/1/5/10 &bull; Genuine Microsoft Windows 11 Pro 64-bit OEM &bull; Dual Gigabit Ethernet (2&times; RJ45, teaming/failover) &bull; 6&times; USB 3.2 + 2&times; USB 2.0 &bull; DisplayPort 1.4a + HDMI 2.1 &bull; Discrete Hardware TPM 2.0 &bull; 750W 80 PLUS Gold PSU &bull; Heavy-duty tower chassis", tbl_cell),
            Paragraph("1-Year Comprehensive On-Site OEM Warranty<br/>BIS, CE, FCC, RoHS, Energy Star 8.0", tbl_cell)
        ],
        [
            Paragraph("<b>Package C</b><br/>USB Wired Keyboard & Mouse", tbl_cell_bold),
            Paragraph("45<br/>Sets", tbl_cell),
            Paragraph("Full-size 104-key QWERTY membrane keyboard with official Rs. symbol &bull; 10 Million keystroke rated &bull; Spill-resistant design &bull; Non-fade laser-etched keycaps &bull; USB 2.0 wired, 1.8m cable &bull; Optical Mouse: 1000 DPI, 3-button + scroll wheel, ambidextrous, 3M click rated", tbl_cell),
            Paragraph("1-Year Replacement Warranty<br/>BIS, CE, RoHS Compliant", tbl_cell)
        ],
        [
            Paragraph("<b>Package D</b><br/>19-inch LED Backlit Monitors", tbl_cell_bold),
            Paragraph("45<br/>Nos.", tbl_cell),
            Paragraph("18.5-inch / 19.0-inch diagonal LED-backlit TFT/IPS anti-glare panel &bull; Native resolution HD (1366&times;768) / FHD (1920&times;1080) @ 60 Hz &bull; 16:9 aspect ratio &bull; Brightness: 200–250 cd/m&sup2; &bull; Contrast: 1000:1 &bull; Response time &le; 5ms GtG &bull; VGA + HDMI 1.4 inputs &bull; Tilt: -5&deg; to +20&deg; &bull; VESA 100&times;100mm &bull; Power &le; 18W &bull; Energy Star certified", tbl_cell),
            Paragraph("1-Year Comprehensive On-Site OEM Warranty<br/>BIS, CE, FCC, RoHS Compliant", tbl_cell)
        ],
        [
            Paragraph("<b>Package E</b><br/>Server Antivirus & Endpoint Security", tbl_cell_bold),
            Paragraph("3<br/>Lic.", tbl_cell),
            Paragraph("Real-time antivirus, anti-malware, anti-ransomware, HIPS, behavioral heuristics &bull; Integrated server firewall, intrusion prevention, web filtering, phishing protection &bull; Centralized web-based management console &bull; Compatible with Windows 11 Pro, Windows Server, RHEL, Ubuntu &bull; Daily automatic signature updates &bull; 24&times;7 OEM emergency telephone hotline", tbl_cell),
            Paragraph("1-Year Full Subscription<br/>24x7 OEM Support", tbl_cell)
        ],
        [
            Paragraph("<b>Package F</b><br/>86-inch 4K UHD Interactive Flat Panel", tbl_cell_bold),
            Paragraph("1<br/>No.", tbl_cell),
            Paragraph("86-inch 4K UHD 3840&times;2160 @ 60 Hz display &bull; D-LED backlight (50,000 hrs life) &bull; 400 cd/m&sup2; &bull; 4000:1 contrast &bull; 4mm toughened anti-glare 7H tempered glass &bull; 20-point IR touch &bull; &plusmn;1.0mm accuracy, &le;6ms response &bull; Android 13 embedded OS (4GB RAM / 32GB eMMC) &bull; Built-in interactive whiteboard &amp; wireless projection &bull; OPS JAE 80-pin expansion slot &bull; 2&times;15W (30W RMS) front stereo speakers &bull; Heavy-duty movable floor trolley with 4 lockable castors + wall mount bracket", tbl_cell),
            Paragraph("1-Year Comprehensive On-Site OEM Warranty<br/>BIS, CE, FCC, RoHS Compliant", tbl_cell)
        ],
        [
            Paragraph("<b>Package G</b><br/>Structured LAN Networking", tbl_cell_bold),
            Paragraph("1<br/>Job", tbl_cell),
            Paragraph("305m CAT6 UTP LSZH/CMR 23 AWG cable &bull; Single/dual-port RJ45 Keystone I/O faceplates &bull; 48-port Gigabit Layer 2 Managed Switch with PoE capability &bull; 25mm/32mm HDPE &amp; GI protective conduit &bull; OFC patch cords &amp; media converters &bull; 9U/12U lockable wall-mount network rack with 6-socket surge PDU &bull; Complete turnkey cable pulling, conduit laying, punching, Fluke channel continuity testing, IP configuration, commissioning", tbl_cell),
            Paragraph("1-Year Performance & Installation Warranty<br/>TIA-568.2-D Certified", tbl_cell)
        ],
        [
            Paragraph("<b>Package H</b><br/>Modular Computer Lab Furniture", tbl_cell_bold),
            Paragraph("1 Lot<br/>(30+30)", tbl_cell),
            Paragraph("<b>30&times; Workstation Tables:</b> 18/25mm pre-laminated MDF (IS 12823), scratch/water-resistant, 2mm PVC edge banding &bull; Heavy-duty CRCA MS tubular frame (40&times;40&times;1.2mm) with 50-micron epoxy powder coat &bull; Sliding keyboard tray, CPU trolley, wire manager grommet &bull; Approx. 1000&times;600&times;750mm &bull; <b>30&times; Ergonomic Chairs:</b> High-density PU foam (&ge;45 kg/m&sup3;), breathable mesh back, Class 4 gas lift, 5-star nylon base, BIFMA certified, 100 kg rated", tbl_cell),
            Paragraph("1-Year Comprehensive Replacement Warranty<br/>IS 12823 / BIFMA Certified", tbl_cell)
        ],
    ]
    specs_tbl = Table(specs_table_data, colWidths=[90, 35, 278, 120])
    specs_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    story.append(specs_tbl)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 4: ITEMIZED BILL OF QUANTITIES (BOQ) & COMMERCIAL OFFER
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. ITEMIZED BILL OF QUANTITIES (BOQ) & COMMERCIAL OFFER", sec_title))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F2942'), spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("<b>Pricing Basis:</b> Market-competitive GeM aligned budgetary rates for MII Class-1 OEM hardware. All rates quoted in Indian Rupees (INR) ex-GST, with uniform GST @ 18% applied. Turnkey supply, installation, testing, and 1-Year comprehensive on-site OEM warranty included.", body_text))
    story.append(Spacer(1, 6))

    boq_table_data = [
        [Paragraph("<b>Pkg</b>", tbl_hdr), Paragraph("<b>Item Description</b>", tbl_hdr), Paragraph("<b>Technical Specification Summary</b>", tbl_hdr), Paragraph("<b>Qty</b>", tbl_hdr), Paragraph("<b>Unit</b>", tbl_hdr), Paragraph("<b>Unit Rate (Rs.)</b>", tbl_hdr), Paragraph("<b>Amount (Rs. L)</b>", tbl_hdr)],
        [
            Paragraph("A", tbl_cell_bold),
            Paragraph("Thin Client Computer Nodes", tbl_cell_bold),
            Paragraph("BCM2837 1.4GHz Quad ARM, 1GB RAM, 32GB microSD, HDMI, GbE+WiFi, Linux OS, 1-Yr Warranty", tbl_cell),
            Paragraph("45", tbl_cell_r),
            Paragraph("Nos.", tbl_cell),
            Paragraph("8,500.00", tbl_cell_r),
            Paragraph("3.8250", tbl_cell_r_bold),
        ],
        [
            Paragraph("B", tbl_cell_bold),
            Paragraph("High Performance Host Servers", tbl_cell_bold),
            Paragraph("Intel Core i9-14th Gen 24C/32T, 64GB DDR5, 1TB NVMe Gen4, Win11 Pro OEM, 1-Yr Warranty", tbl_cell),
            Paragraph("3", tbl_cell_r),
            Paragraph("Nos.", tbl_cell),
            Paragraph("1,10,000.00", tbl_cell_r),
            Paragraph("3.3000", tbl_cell_r_bold),
        ],
        [
            Paragraph("C", tbl_cell_bold),
            Paragraph("USB Wired Keyboard & Mouse Combo", tbl_cell_bold),
            Paragraph("104-Key Membrane KB (Rs. symbol, spill-resistant) + 1000 DPI Optical Mouse, USB, 1-Yr Warranty", tbl_cell),
            Paragraph("45", tbl_cell_r),
            Paragraph("Sets", tbl_cell),
            Paragraph("900.00", tbl_cell_r),
            Paragraph("0.4050", tbl_cell_r_bold),
        ],
        [
            Paragraph("D", tbl_cell_bold),
            Paragraph("19-inch LED Backlit Monitors", tbl_cell_bold),
            Paragraph("18.5-inch / 19-inch LED TFT/IPS Anti-Glare, FHD/HD @ 60Hz, VGA+HDMI, VESA, &le;18W, 1-Yr Warranty", tbl_cell),
            Paragraph("45", tbl_cell_r),
            Paragraph("Nos.", tbl_cell),
            Paragraph("5,500.00", tbl_cell_r),
            Paragraph("2.4750", tbl_cell_r_bold),
        ],
        [
            Paragraph("E", tbl_cell_bold),
            Paragraph("Server Antivirus & Endpoint Security", tbl_cell_bold),
            Paragraph("Real-time AV+HIPS+Ransomware+Firewall, Central Console, Win11/Server/Linux, 1-Yr Sub", tbl_cell),
            Paragraph("3", tbl_cell_r),
            Paragraph("Lic.", tbl_cell),
            Paragraph("4,500.00", tbl_cell_r),
            Paragraph("0.1350", tbl_cell_r_bold),
        ],
        [
            Paragraph("F", tbl_cell_bold),
            Paragraph("86-inch 4K UHD Interactive Flat Panel", tbl_cell_bold),
            Paragraph("86-inch 4K UHD 3840&times;2160, 20-Pt IR Touch, Android 13, 30W Audio, Trolley Stand, 1-Yr Warranty", tbl_cell),
            Paragraph("1", tbl_cell_r),
            Paragraph("No.", tbl_cell),
            Paragraph("1,40,000.00", tbl_cell_r),
            Paragraph("1.4000", tbl_cell_r_bold),
        ],
        [
            Paragraph("G", tbl_cell_bold),
            Paragraph("Structured LAN Networking", tbl_cell_bold),
            Paragraph("Turnkey: 305m CAT6 LSZH, 48-port GbE Switch, 9U Rack+PDU, Fluke Tested, 1-Yr Warranty", tbl_cell),
            Paragraph("1", tbl_cell_r),
            Paragraph("Job", tbl_cell),
            Paragraph("2,20,000.00", tbl_cell_r),
            Paragraph("2.2000", tbl_cell_r_bold),
        ],
        [
            Paragraph("H", tbl_cell_bold),
            Paragraph("Modular Computer Lab Furniture", tbl_cell_bold),
            Paragraph("30x Workstation Tables (Pre-lam MDF, CRCA MS) + 30x Ergonomic Mesh Chairs, 1-Yr Warranty", tbl_cell),
            Paragraph("1", tbl_cell_r),
            Paragraph("Lot", tbl_cell),
            Paragraph("12,15,000.00", tbl_cell_r),
            Paragraph("12.1500", tbl_cell_r_bold),
        ],
        [
            Paragraph("", tbl_cell),
            Paragraph("<b>SUBTOTAL CAPEX (ex-GST)</b>", tbl_cell_bold),
            Paragraph("<b>Sum of Packages A through H (Turnkey Supply, Installation & 1-Yr Warranty)</b>", tbl_cell),
            Paragraph("<b>173</b>", tbl_cell_r_bold),
            Paragraph("<b>Units</b>", tbl_cell_bold),
            Paragraph("", tbl_cell),
            Paragraph("<b>Rs. 25.8900 L</b>", tbl_cell_r_bold),
        ],
        [
            Paragraph("", tbl_cell),
            Paragraph("<b>APPLICABLE GST @ 18%</b>", tbl_cell_bold),
            Paragraph("Statutory Goods and Services Tax on Turnkey IT Supply & Installation", tbl_cell),
            Paragraph("", tbl_cell),
            Paragraph("", tbl_cell),
            Paragraph("18.00%", tbl_cell_r),
            Paragraph("<b>Rs. 4.6602 L</b>", tbl_cell_r_bold),
        ],
        [
            Paragraph("", tbl_cell),
            Paragraph("<b>TOTAL TURNKEY CAPEX (INCL. 18% GST)</b>", ParagraphStyle('EqTB1', parent=tbl_cell_bold, textColor=colors.HexColor('#1D4ED8'))),
            Paragraph("<b>Total Contract Value payable via GeM Portal post CRAC</b>", ParagraphStyle('EqTB2', parent=tbl_cell, textColor=colors.HexColor('#1D4ED8'))),
            Paragraph("", tbl_cell),
            Paragraph("", tbl_cell),
            Paragraph("", tbl_cell),
            Paragraph("<b>Rs. 30.5502 L</b>", ParagraphStyle('EqTB3', parent=tbl_cell_r_bold, textColor=colors.HexColor('#1D4ED8'), fontSize=8)),
        ],
    ]
    boq_tbl = Table(boq_table_data, colWidths=[24, 110, 195, 25, 28, 68, 73])
    boq_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-4), [colors.white, colors.HexColor('#F8FAFC')]),
        ('BACKGROUND', (0,-3), (-1,-3), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0,-2), (-1,-2), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('LINEABOVE', (0,-3), (-1,-3), 1, colors.HexColor('#94A3B8')),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#1D4ED8')),
    ]))
    story.append(boq_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3.2 Five-Year Spend Profile (Total Cost of Ownership — TCO)", subsec_title))
    tco_table_data = [
        [Paragraph("<b>Component / Scope Description</b>", tbl_hdr), Paragraph("<b>Time Horizon</b>", tbl_hdr), Paragraph("<b>Amount (Rs. Lakhs)</b>", tbl_hdr), Paragraph("<b>Amount (Rs. Crores)</b>", tbl_hdr)],
        [Paragraph("Turnkey Supply, Installation & 1-Year Comprehensive OEM Warranty", tbl_cell), Paragraph("Year 1 (30-Day Delivery)", tbl_cell), Paragraph("30.5502", tbl_cell_r), Paragraph("0.3055", tbl_cell_r)],
        [Paragraph("Optional Comprehensive AMC — Year 2 (Hardware maintenance + AV renewal)", tbl_cell), Paragraph("Year 2", tbl_cell), Paragraph("1.5000", tbl_cell_r), Paragraph("0.0150", tbl_cell_r)],
        [Paragraph("Optional Comprehensive AMC — Year 3 (Hardware maintenance + AV renewal)", tbl_cell), Paragraph("Year 3", tbl_cell), Paragraph("1.5000", tbl_cell_r), Paragraph("0.0150", tbl_cell_r)],
        [Paragraph("Optional Comprehensive AMC — Year 4 (Hardware maintenance + AV renewal)", tbl_cell), Paragraph("Year 4", tbl_cell), Paragraph("1.6500", tbl_cell_r), Paragraph("0.0165", tbl_cell_r)],
        [Paragraph("Optional Comprehensive AMC — Year 5 (Hardware maintenance + AV renewal)", tbl_cell), Paragraph("Year 5", tbl_cell), Paragraph("1.6500", tbl_cell_r), Paragraph("0.0165", tbl_cell_r)],
        [Paragraph("<b>TOTAL 5-YEAR ESTIMATED LIFECYCLE TCO (INCL. 18% GST)</b>", tbl_cell_bold), Paragraph("<b>5 Years</b>", tbl_cell_bold), Paragraph("<b>Rs. 36.8502 L</b>", tbl_cell_r_bold), Paragraph("<b>Rs. 0.3685 Cr</b>", tbl_cell_r_bold)],
    ]
    tco_tbl = Table(tco_table_data, colWidths=[233, 110, 95, 85])
    tco_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('LINEABOVE', (0,-1), (-1,-1), 1.2, colors.HexColor('#1D4ED8')),
    ]))
    story.append(tco_tbl)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 5: IMPLEMENTATION ROADMAP & ATC COMPLIANCE MATRIX
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. IMPLEMENTATION ROADMAP & GEM ATC COMPLIANCE", sec_title))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F2942'), spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("4.1 30-Day Delivery & Commissioning Roadmap (Shillong Mandate)", subsec_title))
    roadmap_data = [
        [Paragraph("<b>Phase</b>", tbl_hdr), Paragraph("<b>Timeline</b>", tbl_hdr), Paragraph("<b>Execution Activities & Key Milestones at 58 GTC Happy Valley, Shillong</b>", tbl_hdr)],
        [Paragraph("Phase 1", tbl_cell_bold), Paragraph("Days 1–3", tbl_cell), Paragraph("GeM contract award acknowledgement; OEM MAF submission; vendor code setup with 58 GTC accounts.", tbl_cell)],
        [Paragraph("Phase 2", tbl_cell_bold), Paragraph("Days 4–7", tbl_cell), Paragraph("OEM procurement order placement; logistics coordination for road/air freight delivery to Shillong, Meghalaya.", tbl_cell)],
        [Paragraph("Phase 3", tbl_cell_bold), Paragraph("Days 8–18", tbl_cell), Paragraph("Equipment dispatch from OEM hubs; consolidated transit to 58 GTC Happy Valley, Shillong.", tbl_cell)],
        [Paragraph("Phase 4", tbl_cell_bold), Paragraph("Days 19–22", tbl_cell), Paragraph("Consignment arrival at 58 GTC; physical count verification and pre-delivery inspection by Board of Officers.", tbl_cell)],
        [Paragraph("Phase 5", tbl_cell_bold), Paragraph("Days 23–27", tbl_cell), Paragraph("Modular furniture assembly; server rack installation; CAT6 structured cabling, conduit laying & termination.", tbl_cell)],
        [Paragraph("Phase 6", tbl_cell_bold), Paragraph("Days 28–29", tbl_cell), Paragraph("86-inch IFPD mounting on trolley; Thin Client VESA mounting; OS binding to 3 host servers; Fluke channel testing.", tbl_cell)],
        [Paragraph("Phase 7", tbl_cell_bold), Paragraph("Day 30", tbl_cell_bold), Paragraph("Full system burn-in testing; operator & instructor training; CRAC generation on GeM portal; formal handover.", tbl_cell_bold)],
    ]
    roadmap_tbl = Table(roadmap_data, colWidths=[55, 60, 408])
    roadmap_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    story.append(roadmap_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("4.2 GeM Additional Terms & Conditions (ATC) Compliance Statement", subsec_title))
    atc_data = [
        [Paragraph("<b>ATC Clause / Subject</b>", tbl_hdr), Paragraph("<b>Tender Requirement</b>", tbl_hdr), Paragraph("<b>Nikom Compliance Status & Evidence Basis</b>", tbl_hdr)],
        [Paragraph("Clause 3 &bull; OEM MAF", tbl_cell_bold), Paragraph("Manufacturer Authorization Form for Thin Clients, Servers, IFPD, Switch", tbl_cell), Paragraph("<b>FULL COMPLIANCE:</b> OEM MAF certificates enclosed with technical bid.", tbl_cell)],
        [Paragraph("Clause 4 &bull; Service Support", tbl_cell_bold), Paragraph("Dedicated service center in Meghalaya or within 150 km of Shillong", tbl_cell), Paragraph("<b>FULL COMPLIANCE:</b> Regional service center in Guwahati / Shillong network; affidavit on Rs. 100 stamp paper provided.", tbl_cell)],
        [Paragraph("Clause 5 &bull; Legal Compliance", tbl_cell_bold), Paragraph("PAN, GSTIN, Cancelled Cheque, ISO 9001:2015, Non-Blacklisting", tbl_cell), Paragraph("<b>FULL COMPLIANCE:</b> All statutory documents verified and attached.", tbl_cell)],
        [Paragraph("Clause 6 &bull; Inspection", tbl_cell_bold), Paragraph("Pre-dispatch / on-arrival inspection by Board of Officers at 58 GTC", tbl_cell), Paragraph("<b>FULL ACCEPTANCE:</b> Inspection protocol accepted without deviation.", tbl_cell)],
        [Paragraph("Clause 7 &bull; Payment Terms", tbl_cell_bold), Paragraph("100% payment released via GeM portal post CRAC generation", tbl_cell), Paragraph("<b>FULL ACCEPTANCE:</b> GeM milestone payment terms accepted.", tbl_cell)],
        [Paragraph("Clause 8 &bull; Warranty & SLA", tbl_cell_bold), Paragraph("1-Year Comprehensive On-Site OEM Warranty, 48-hr resolution SLA", tbl_cell), Paragraph("<b>FULL COMPLIANCE:</b> 1-Year OEM warranty on all 8 packages; 48-hr SLA accepted.", tbl_cell)],
        [Paragraph("EMD &amp; ePBG Terms", tbl_cell_bold), Paragraph("EMD Rs. 1,20,000; ePBG 3% with 18-month validity upon contract award", tbl_cell), Paragraph("<b>FULL COMPLIANCE:</b> DD prepared in favour of Regimental Fund 58 GTC; ePBG to be submitted post-award.", tbl_cell)],
        [Paragraph("MII Purchase Preference", tbl_cell_bold), Paragraph("Class-1 Local Supplier (&ge;50% local content requirement)", tbl_cell), Paragraph("<b>FULL COMPLIANCE:</b> OEM local content declarations enclosed.", tbl_cell)],
    ]
    atc_tbl = Table(atc_data, colWidths=[110, 163, 250])
    atc_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2942')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    story.append(atc_tbl)
    story.append(Spacer(1, 10))

    # Bidder Sign-off block
    sign_block = Table(
        [[
            Paragraph("<b>SUBMITTED ON BEHALF OF:</b><br/><b>Nikom InfraSolutions Pvt. Ltd.</b><br/>E-48/3, Okhla Industrial Area Phase-II, New Delhi — 110020<br/>CIN: U72900DL2000PTC105284 &bull; GSTIN: 07AAACN1234F1Z1", body_text),
            Paragraph("<b>AUTHORIZED SIGNATORY:</b><br/><br/>____________________________________<br/><b>B.S Kiran Kumar</b> &bull; Director, Pre-Sales Engineering<br/>Email: tenders@nikom.in &bull; Mobile: +91-98100-XXXXX", body_text),
        ]],
        colWidths=[260, 263]
    )
    sign_block.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(sign_block)

    doc.build(story, canvasmaker=FormalProposalCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_formal_proposal_pdf(data: Dict[str, Any]) -> bytes:
    """
    Generates a full formal submission-ready proposal PDF document.
    Routes equipment supply / computer lab tenders to dedicated executive proposal.
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
        return _generate_equipment_supply_proposal_pdf(data)

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

    # Base typography styles
    cover_title_style = ParagraphStyle(
        'CoverTitle', parent=styles['Heading1'],
        fontSize=24, leading=29, textColor=colors.HexColor('#0F3870'),
        fontName='Helvetica-Bold', alignment=1
    )
    cover_sub_style = ParagraphStyle(
        'CoverSub', parent=styles['Normal'],
        fontSize=12, leading=16, textColor=colors.HexColor('#475569'),
        fontName='Helvetica', alignment=1
    )
    sec_title_style = ParagraphStyle(
        'SecTitle', parent=styles['Heading1'],
        fontSize=13, leading=16, textColor=colors.HexColor('#0F3870'),
        fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4
    )
    subsec_title_style = ParagraphStyle(
        'SubSecTitle', parent=styles['Heading2'],
        fontSize=10, leading=13, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=3
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=8, leading=11, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica'
    )
    body_bold = ParagraphStyle(
        'BodyBold', parent=styles['Normal'],
        fontSize=8, leading=11, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    bullet_style = ParagraphStyle(
        'Bullet', parent=styles['Normal'],
        fontSize=8, leading=11, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica', leftIndent=10, firstLineIndent=-8, spaceAfter=2
    )
    table_hdr = ParagraphStyle(
        'TableHdr', parent=styles['Normal'],
        fontSize=7.5, leading=9.5, textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontSize=7.5, leading=9.5, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica'
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold', parent=styles['Normal'],
        fontSize=7.5, leading=9.5, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    table_cell_right = ParagraphStyle(
        'TableCellR', parent=styles['Normal'],
        fontSize=7.5, leading=9.5, textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica', alignment=2
    )
    table_cell_right_bold = ParagraphStyle(
        'TableCellRBold', parent=styles['Normal'],
        fontSize=7.5, leading=9.5, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold', alignment=2
    )
    kpi_num_style = ParagraphStyle(
        'KpiNum', parent=styles['Normal'],
        fontSize=12, leading=14, textColor=colors.HexColor('#38BDF8'),
        fontName='Helvetica-Bold', alignment=1
    )
    kpi_sub_style = ParagraphStyle(
        'KpiSub', parent=styles['Normal'],
        fontSize=7, leading=9, textColor=colors.white,
        fontName='Helvetica', alignment=1
    )

    story = []

    # ─────────────────────────────────────────────────────────────────────────
    # Input Normalization & Engineering Sizing Baseline
    # ─────────────────────────────────────────────────────────────────────────
    it_kw = float(data.get('it_load_kw') or 250.0)
    racks = int(data.get('rack_count') or 25)
    kw_per_rack = round(it_kw / max(1, racks), 1)
    client_org = data.get('client_org') or data.get('client') or "Enterprise / Institutional Facility"
    project_title = data.get('project_name') or data.get('project_title') or f"Turnkey Technical Solution & Budgetary Proposal ({int(it_kw)} kW IT Load)"
    doc_date = datetime.now().strftime("%d %B %Y")
    ref_code = f"NIK/BD-{datetime.now().strftime('%Y')}/SO-{int(it_kw)}"

    heat_kw = round(it_kw * 1.15, 1)
    cooling_tr = float(data.get('cooling_capacity_tr') or round(heat_kw / 3.517, 1))
    ups_frame_kw = int(data.get('ups_rating_kva') or round((it_kw / 0.9) * 1.25))
    dg_kva = int(data.get('dg_rating_kva') or round(((it_kw + cooling_tr + (it_kw * 0.1)) / 0.8) * 1.25))
    tx_kva = int(round((it_kw * 3.96) / 50.0) * 50) if it_kw >= 150 else int(it_kw * 2)
    floor_sqft = int(data.get('floor_area_sqft') or round(racks * 45 + 100))

    # Unified Commercial Calculations from CalculationEngine or data
    if data.get('total_capital_lakhs') or data.get('total_lakhs'):
        total_capex_lakhs = float(data.get('total_capital_lakhs') or data.get('total_lakhs'))
        total_capex_cr = round(total_capex_lakhs / 100.0, 2)
    elif data.get('total_capital_cr') or data.get('total_cr') or data.get('total_capex_cr'):
        total_capex_cr = float(data.get('total_capital_cr') or data.get('total_cr') or data.get('total_capex_cr'))
        total_capex_lakhs = round(total_capex_cr * 100.0, 2)
    else:
        from src.services.presales_calculation_engine import CalculationEngine
        calc = CalculationEngine.calculate_boq_and_commercials(boq_items=[], category="datacentre_turnkey", it_load_kw=it_kw)
        total_capex_lakhs = calc["total_capex_lakhs"]
        total_capex_cr = calc["total_capex_cr"]

    scale = round(total_capex_lakhs / 735.42, 4) if total_capex_lakhs > 0 else round(it_kw / 252.0, 4)

    # Canonical EPC packages breakdown matching total_capex_lakhs
    capex_power = round((ups_frame_kw * 2) * 0.26 + 85.0, 2)
    capex_cooling = round(cooling_tr * 1.55 + 40.0, 2)
    capex_racks = round(racks * 2.24 + 10.0, 2)
    capex_standby = round(dg_kva * 0.14 + 32.0, 2)
    capex_ht = round(277.1, 2) if it_kw >= 200 else round(it_kw * 0.85, 2)
    capex_fire = round(35.0 + (it_kw * 0.05), 2)
    capex_dcim = round(55.0 + (racks * 1.2) + 25.0, 2)
    capex_services = round(103.0, 2)
    capex_sec = round(35.0, 2)
    capex_cert = round(35.0, 2)
    capex_civil = round(racks * 45 * 0.026 + 15.0, 2)

    # Reconcile packages sum to exactly total_capex_lakhs
    pkg_sum = capex_power + capex_cooling + capex_racks + capex_standby + capex_ht + capex_fire + capex_dcim + capex_services + capex_sec + capex_cert + capex_civil
    if abs(pkg_sum - total_capex_lakhs) > 0.01 and pkg_sum > 0:
        ratio = total_capex_lakhs / pkg_sum
        capex_power = round(capex_power * ratio, 2)
        capex_cooling = round(capex_cooling * ratio, 2)
        capex_racks = round(capex_racks * ratio, 2)
        capex_standby = round(capex_standby * ratio, 2)
        capex_ht = round(capex_ht * ratio, 2)
        capex_fire = round(capex_fire * ratio, 2)
        capex_dcim = round(capex_dcim * ratio, 2)
        capex_sec = round(capex_sec * ratio, 2)
        capex_services = round(capex_services * ratio, 2)
        capex_cert = round(capex_cert * ratio, 2)
        capex_civil = round(total_capex_lakhs - (capex_power + capex_cooling + capex_racks + capex_standby + capex_ht + capex_fire + capex_dcim + capex_sec + capex_services + capex_cert), 2)

    # 5-Year Spend Profile (TCO)
    if data.get('total_5yr_tco_cr') or data.get('tco_cr'):
        total_5yr_cr = float(data.get('total_5yr_tco_cr') or data.get('tco_cr'))
        total_5yr_lakhs = round(total_5yr_cr * 100.0, 2)
    else:
        camc_y4_5_lakhs = round(total_capex_lakhs * 0.078, 2)
        om_5yr_lakhs = round(max(108.0, it_kw * 0.45) * 5.0, 2)
        total_5yr_lakhs = round(total_capex_lakhs + camc_y4_5_lakhs + om_5yr_lakhs, 2)
        total_5yr_cr = round(total_5yr_lakhs / 100.0, 2)

    camc_diff = max(0.0, (total_5yr_lakhs - total_capex_lakhs) * 0.25)
    camc_y4_lakhs = round(camc_diff * 0.48, 2)
    camc_y5_lakhs = round(camc_diff * 0.52, 2)
    total_camc_lakhs = round(camc_y4_lakhs + camc_y5_lakhs, 2)
    total_camc_cr = round(total_camc_lakhs / 100.0, 2)

    om_remain = max(0.0, total_5yr_lakhs - total_capex_lakhs - total_camc_lakhs)
    om_y1_lakhs = round(om_remain * 0.17, 2)
    om_y2_lakhs = round(om_remain * 0.18, 2)
    om_y3_lakhs = round(om_remain * 0.20, 2)
    om_y4_lakhs = round(om_remain * 0.22, 2)
    om_y5_lakhs = round(om_remain - (om_y1_lakhs + om_y2_lakhs + om_y3_lakhs + om_y4_lakhs), 2)
    total_om_lakhs = round(om_y1_lakhs + om_y2_lakhs + om_y3_lakhs + om_y4_lakhs + om_y5_lakhs, 2)
    total_om_cr = round(total_om_lakhs / 100.0, 2)

    gst_lakhs = round(total_capex_lakhs * 0.18, 2)
    total_incl_gst_lakhs = round(total_capex_lakhs + gst_lakhs, 2)
    total_incl_gst_cr = round(total_incl_gst_lakhs / 100.0, 2)

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER PAGE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 100))
    # Geometric Corporate Emblem
    logo_table = Table(
        [[
            Paragraph(
                "<font size=48 color='#0F3870'><b>&#9632;</b></font>",
                ParagraphStyle('L', parent=styles['Normal'], alignment=1)
            )
        ]],
        colWidths=[522]
    )
    logo_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 30),
    ]))
    story.append(logo_table)
    story.append(Spacer(1, 40))

    story.append(Paragraph(project_title, cover_title_style))
    story.append(Spacer(1, 14))
    story.append(Paragraph(f"Turnkey Engineering Architecture, High-Density Upgrade & 5-Year Lifecycle TCO Offer", cover_sub_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"ANSI/TIA-942-C Rated-3 (Tier III Concurrently Maintainable) Certified Standard", cover_sub_style))

    story.append(Spacer(1, 180))
    story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor('#0F3870'), spaceAfter=15, spaceBefore=0, hAlign='CENTER'))
    story.append(Paragraph(f"<b>{doc_date}</b>", ParagraphStyle('CD', parent=styles['Normal'], alignment=1, fontSize=10, textColor=colors.HexColor('#1E293B'))))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>NIKOM INFRASOLUTIONS PVT. LTD.</b>", ParagraphStyle('CN', parent=styles['Normal'], alignment=1, fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#0F3870'))))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Managing DataCentre Lifecycle ..", ParagraphStyle('CT', parent=styles['Normal'], alignment=1, fontSize=8.5, fontName='Helvetica-Oblique', textColor=colors.HexColor('#64748B'))))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 2: EXECUTIVE METADATA & 5 HERO KPI BLOCKS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("TECHNICAL SOLUTION & BUDGETARY OFFER", ParagraphStyle('DocTop', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#2563EB'))))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"{project_title}", ParagraphStyle('DocH1', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#0F3870'), fontName='Helvetica-Bold')))
    story.append(Paragraph(f"Rack power density enhancement to {kw_per_rack} kW per rack, Tier III (TIA-942-C Rated-3) certified, PUE &le; 1.5", ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#64748B'))))
    story.append(Spacer(1, 14))

    # 5 Hero KPI Blocks
    kpi_grid_data = [
        [
            Paragraph(f"<b>{it_kw:g} kW</b>", kpi_num_style),
            Paragraph(f"<b>{kw_per_rack:g} kW</b>", kpi_num_style),
            Paragraph("<b>Tier III</b>", kpi_num_style),
            Paragraph("<b>PUE &le; 1.5</b>", kpi_num_style),
            Paragraph(f"<b>Rs. {total_5yr_cr:,.2f} cr</b>", kpi_num_style)
        ],
        [
            Paragraph("Design IT load", kpi_sub_style),
            Paragraph(f"Per rack (N+1 power)", kpi_sub_style),
            Paragraph("TIA-942-C Rated-3, 2N", kpi_sub_style),
            Paragraph("Annualised 25&ndash;100%", kpi_sub_style),
            Paragraph("5-year cost + GST", kpi_sub_style)
        ]
    ]
    t_kpis = Table(kpi_grid_data, colWidths=[104, 104, 104, 104, 106])
    t_kpis.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0F2A4A')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#1E40AF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1E40AF')),
    ]))
    story.append(t_kpis)
    story.append(Spacer(1, 16))

    # Metadata Table
    meta_data = [
        [Paragraph("<b>SUBMITTED TO</b>", table_cell_bold), Paragraph(client_org, table_cell)],
        [Paragraph("<b>SUBMITTED BY</b>", table_cell_bold), Paragraph("NIKOM INFRASOLUTIONS PVT. LTD.", table_cell)],
        [Paragraph("<b>CONTACT</b>", table_cell_bold), Paragraph("B.S Kiran Kumar / Pre-Sales Engineering Directorate", table_cell)],
        [Paragraph("<b>DATE</b>", table_cell_bold), Paragraph(doc_date, table_cell)],
        [Paragraph("<b>DOCUMENT</b>", table_cell_bold), Paragraph("Budgetary proposal (pre-survey), &plusmn;15% | Lithium-Ion battery solution | Revision 1, incorporating client comments", table_cell)],
        [Paragraph("<b>VALIDITY</b>", table_cell_bold), Paragraph("90 days from the date of submission", table_cell)]
    ]
    t_meta = Table(meta_data, colWidths=[130, 392])
    t_meta.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))

    # Document Context Box
    callout_data = [
        [Paragraph("<b>Turnkey Execution Commitment:</b> Nikom InfraSolutions guarantees end-to-end EPC single-point accountability for civil, electrical, precision cooling, fire, physical security, DCIM, and accredited ANSI/TIA-942-C Rated-3 two-stage certification with live migration maintaining 99.982% uptime.", body_style)]
    ]
    t_callout = Table(callout_data, colWidths=[522])
    t_callout.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F9FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BAE6FD')),
        ('LINELEFT', (0,0), (-1,-1), 3, colors.HexColor('#0284C7')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_callout)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 3: CONTENTS & REVISION BOX
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Contents", ParagraphStyle('TocH', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#0F3870'), fontName='Helvetica-Bold')))
    story.append(Spacer(1, 8))

    toc_items = [
        ("1", "Executive Summary"),
        ("2", "Requirement and Basis of Design"),
        ("3", "Proposed Technical Solution"),
        ("4", "Reuse, Upgrade and Replace (Preliminary)"),
        ("5", "Battery Technology &ndash; Lithium-Ion"),
        ("6", "Tier III Compliance and TIA-942-C Certification"),
        ("7", "Energy Efficiency and PUE"),
        ("8", "Standards and Compliance"),
        ("9", "Migration Methodology and Schedule"),
        ("10", "Budgetary Commercial Offer"),
        ("11", "Assumptions, Exclusions and Next Steps"),
        ("A", "Annexure A &ndash; Item-wise Bill of Quantities (BOQ)"),
        ("B", "Annexure B &ndash; CAMC Break-up, Years 4 and 5"),
        ("C", "Annexure C &ndash; Managed O&M Services, 5-Year Break-up")
    ]
    toc_data = [[Paragraph(f"<b>{num}</b>", table_cell_bold), Paragraph(title, table_cell)] for num, title in toc_items]
    t_toc = Table(toc_data, colWidths=[30, 492])
    t_toc.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 16))

    # About this Document Box
    about_text = (
        "<b>About this document:</b> This budgetary proposal responds to the client's request for a technical assessment and "
        "turnkey solution strategy for its Tier III Data Centre. Figures are pre-survey estimates (&plusmn;15%) and will be firmed up after "
        "the site inspection. The Draft RFP will carry OEM-neutral specifications to ensure transparent competitive procurement."
    )
    t_about = Table([[Paragraph(about_text, body_style)]], colWidths=[522])
    t_about.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_about)
    story.append(Spacer(1, 10))

    # Revision 1 Changes Box
    rev_text = (
        "<b>Revision 1 &ndash; changes made on client engineering comments:</b><br/>"
        "<b>(1)</b> Two 1000 kVA transformers, one per bus, fed by two HT cable runs from 11 kV incoming supply. "
        "<b>(2)</b> Passive structured cabling removed from scope; client will plan separately. "
        "<b>(3)</b> Certification of design and constructed facility to ANSI/TIA-942-C Rated-3 (Tier III). "
        "<b>(4)</b> Fuel storage increased from 12 hours to 48 hours at full load (bulk storage tank with PESO licensing). "
        "<b>(5)</b> Fire-rated (EI 60) glass partition at data centre entrance connecting NOC room added."
    )
    t_rev = Table([[Paragraph(rev_text, body_style)]], colWidths=[522])
    t_rev.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#93C5FD')),
        ('LINELEFT', (0,0), (-1,-1), 3, colors.HexColor('#2563EB')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_rev)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 4: SECTION 1 EXECUTIVE SUMMARY & SECTION 2 BASIS OF DESIGN
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1  Executive Summary", sec_title_style))
    story.append(Spacer(1, 4))

    # 4 Spend Cards
    spend_cards_data = [
        [
            Paragraph(f"<b>Rs. {total_capex_cr:,.2f} cr</b>", kpi_num_style),
            Paragraph(f"<b>Rs. {total_camc_cr:,.2f} cr</b>", kpi_num_style),
            Paragraph(f"<b>Rs. {total_om_cr:,.2f} cr</b>", kpi_num_style),
            Paragraph(f"<b>Rs. {total_5yr_cr:,.2f} cr</b>", kpi_num_style)
        ],
        [
            Paragraph("CAPEX incl. 3-yr warranty", kpi_sub_style),
            Paragraph("CAMC, Years 4&ndash;5", kpi_sub_style),
            Paragraph("Managed O&M, 5 years", kpi_sub_style),
            Paragraph("Total + GST", kpi_sub_style)
        ]
    ]
    t_spend = Table(spend_cards_data, colWidths=[130, 130, 130, 132])
    t_spend.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0F2A4A')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#1E40AF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1E40AF')),
    ]))
    story.append(t_spend)
    story.append(Spacer(1, 10))

    exec_p1 = (
        f"NIKOM proposes to raise all {racks} server racks to {kw_per_rack} kW each ({it_kw:g} kW design IT load) within the existing "
        f"floor area, at an estimated CAPEX of <b>Rs. {total_capex_cr:,.2f} crore</b> with Lithium-Ion (LFP) batteries (ex-GST, including 3-year "
        f"comprehensive warranty, HT works with two transformers, 48-hour fuel storage, intelligent rack access control, full DCIM with asset "
        f"tracking, and ANSI/TIA-942-C Rated-3 two-stage certification)."
    )
    story.append(Paragraph(exec_p1, body_style))
    story.append(Spacer(1, 6))

    bullets = [
        f"<b>Power:</b> 2N modular UPS, {ups_frame_kw} kW per side, with independent A/B dual distribution to every rack.",
        f"<b>Cooling:</b> Inverter DX in-row units (N+2) with variable EC fans and full hot-aisle containment, sized for peak ambient 36 &deg;C.",
        "<b>Energy:</b> Annualised PUE of 1.5 or lower at every IT load from 25% to 100%, about 1.36 at full design load, measured live via DCIM.",
        f"<b>Standby & Utility Power:</b> DG capacity raised to 2 &times; {dg_kva} kVA (N+1), CPCB IV+, with 48 hours of on-site fuel; two new {tx_kva} kVA transformers, one per bus, fed by two independent HT cable runs from 11 kV supply with type-tested HT panel.",
        "<b>Panels:</b> Every LT panel is a Type-Tested Assembly (TTA) to IEC 61439, Form 4b; the 11 kV panel is type-tested switchgear to IEC 62271-200.",
        "<b>Rack Security:</b> Electronic front and rear rack locks with card + PIN / biometric dual authentication, and event-triggered cameras recording every opening.",
        "<b>Entrance:</b> Fire-rated (EI 60) glass partition with access-controlled door connecting the data centre and NOC room.",
        "<b>DCIM & Asset Tracking:</b> Full DCIM suite with U-position RFID tracking strips on all racks covering all IT devices in real time.",
        "<b>Compliance:</b> STQC ER-certified CCTV equipment; ANSI/TIA-942-C Rated-3 independent certification for design documents and constructed facility."
    ]
    for b in bullets:
        story.append(Paragraph(f"&bull; {b}", bullet_style))
    story.append(Spacer(1, 10))

    # Section 2 Requirement and Basis of Design
    story.append(Paragraph("2  Requirement and Basis of Design", sec_title_style))
    story.append(Paragraph(f"The design target is {it_kw:g} kW of IT load ({racks} racks &times; {kw_per_rack:g} kW), delivered in the same footprint and sustainable to 2034.", body_style))
    story.append(Spacer(1, 6))

    basis_data = [
        [Paragraph("<b>Parameter</b>", table_hdr), Paragraph("<b>Existing Baseline</b>", table_hdr), Paragraph("<b>Proposed Design Basis</b>", table_hdr)],
        [Paragraph("Racks", table_cell_bold), Paragraph(f"{racks} racks", table_cell), Paragraph(f"<b>{racks} racks</b>, same positions and footprint", table_cell)],
        [Paragraph("Power Density", table_cell_bold), Paragraph(f"7.0 kW per rack", table_cell), Paragraph(f"<b>{kw_per_rack:g} kW per rack</b>", table_cell_bold)],
        [Paragraph("IT Design Load", table_cell_bold), Paragraph(f"{round(it_kw*0.5,1)} kW", table_cell), Paragraph(f"<b>{it_kw:g} kW</b>", table_cell_bold)],
        [Paragraph("Site & Climate", table_cell_bold), Paragraph("Bengaluru / Campus", table_cell), Paragraph("Design ambient 36 &deg;C dry bulb", table_cell)],
        [Paragraph("Cooling Architecture", table_cell_bold), Paragraph("In-row DX standard", table_cell), Paragraph("Inverter DX in-row (N+2), EC fans, full HAC", table_cell)],
        [Paragraph("Energy Efficiency", table_cell_bold), Paragraph("Unmeasured (>1.75)", table_cell), Paragraph("Annualised PUE &le; 1.5 (1.36 at full load)", table_cell_bold)],
        [Paragraph("Tier Rating", table_cell_bold), Paragraph("Tier III non-certified", table_cell), Paragraph("ANSI/TIA-942-C Rated-3 Certified", table_cell_bold)],
        [Paragraph("UPS Topology", table_cell_bold), Paragraph("Legacy standalone", table_cell), Paragraph(f"<b>2N Modular UPS</b>, {ups_frame_kw} kW per side", table_cell)],
        [Paragraph("Battery Backup", table_cell_bold), Paragraph("SMF-VRLA (aging)", table_cell), Paragraph("<b>15 Min Lithium-Ion (LFP)</b> with cell BMS", table_cell)],
        [Paragraph("DG & Fuel Autonomy", table_cell_bold), Paragraph("12h standard", table_cell), Paragraph(f"2 &times; {dg_kva} kVA (N+1), <b>48h bulk fuel PESO</b>", table_cell)],
        [Paragraph("Utility Supply", table_cell_bold), Paragraph("Single transformer", table_cell), Paragraph(f"2 &times; {tx_kva} kVA dry-type, 2 &times; 11 kV HT cables", table_cell)],
        [Paragraph("LT Switchboards", table_cell_bold), Paragraph("Non-TTA", table_cell), Paragraph("<b>TTA to IEC 61439, Form 4b</b>", table_cell_bold)],
        [Paragraph("DCIM & Asset Tracking", table_cell_bold), Paragraph("Basic BMS", table_cell), Paragraph("Full DCIM with <b>U-position RFID tracking</b>", table_cell)]
    ]
    t_basis = Table(basis_data, colWidths=[110, 150, 262])
    t_basis.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_basis)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 5: FACILITY LOAD ESTIMATE & TOPOLOGY
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Facility Load Estimate at Full Design Load", subsec_title_style))
    story.append(Spacer(1, 4))

    cooling_load_kw = round(it_kw * 0.369, 1)
    ups_loss_kw = round(it_kw * 0.036, 1)
    tx_loss_kw = round(it_kw * 0.024, 1)
    aux_kw = round(it_kw * 0.028, 1)
    facility_peak_kw = round(it_kw + cooling_load_kw + ups_loss_kw + tx_loss_kw + aux_kw, 1)
    calc_pue = round(facility_peak_kw / it_kw, 2)

    load_data = [
        [Paragraph("<b>Load Component</b>", table_hdr), Paragraph("<b>Power (kW)</b>", ParagraphStyle('R', parent=table_hdr, alignment=2))],
        [Paragraph(f"IT Load ({racks} racks &times; {kw_per_rack:g} kW)", table_cell_bold), Paragraph(f"{it_kw:g}", table_cell_right_bold)],
        [Paragraph("Cooling at 36 &deg;C peak (in-row units, condensers, UPS-room cooling)", table_cell), Paragraph(f"{cooling_load_kw:g}", table_cell_right)],
        [Paragraph("UPS Losses (2N double-conversion modular)", table_cell), Paragraph(f"{ups_loss_kw:g}", table_cell_right)],
        [Paragraph("Transformer and distribution losses", table_cell), Paragraph(f"{tx_loss_kw:g}", table_cell_right)],
        [Paragraph("Lighting, BMS, security, DG auxiliaries", table_cell), Paragraph(f"{aux_kw:g}", table_cell_right)],
        [Paragraph("<b>Total Facility Load at Peak Ambient</b>", table_cell_bold), Paragraph(f"<b>{facility_peak_kw:g} kW (PUE {calc_pue:0.2f})</b>", table_cell_right_bold)]
    ]
    t_load = Table(load_data, colWidths=[382, 140])
    t_load.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_load)
    story.append(Spacer(1, 8))

    dg_eval_p = (
        f"One {dg_kva} kVA Prime CPCB IV+ DG set carries the entire facility peak load ({facility_peak_kw:g} kW) with ample margin "
        f"for Lithium-Ion battery recharge and compressor starting inrush currents; the second {dg_kva} kVA set provides N+1 standby redundancy. "
        f"Two new {tx_kva} kVA dry-type transformers, each rated for 100% facility load independently, are fed by two diverse 11 kV HT cable runs, "
        f"ensuring zero power interruption during utility switchgear maintenance."
    )
    story.append(Paragraph(dg_eval_p, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Site Location and Infrastructure Topology", subsec_title_style))
    story.append(Spacer(1, 4))

    site_data = [
        [Paragraph("<b>Item</b>", table_hdr), Paragraph("<b>Technical Detail</b>", table_hdr)],
        [Paragraph("Site & Premises", table_cell_bold), Paragraph(f"{client_org} Main Campus & Facilities Yard", table_cell)],
        [Paragraph("Facility Footprint", table_cell_bold), Paragraph(f"Existing Data Centre Block; ~{floor_sqft} sq. ft raised access floor", table_cell)],
        [Paragraph("Climate Basis", table_cell_bold), Paragraph("Design ambient 36 &deg;C dry bulb; mild climate optimal for inverter DX heat dissipation", table_cell)],
        [Paragraph("Utility Incomer", table_cell_bold), Paragraph(f"11 kV supply over two independent HT cable runs to 2 &times; {tx_kva} kVA low-loss transformers", table_cell)],
        [Paragraph("Telecom / Fiber", table_cell_bold), Paragraph("Two diverse service-provider fiber entry paths into meet-me room (MMR)", table_cell)]
    ]
    t_site = Table(site_data, colWidths=[130, 392])
    t_site.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_site)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 6: SECTION 3 PROPOSED TECHNICAL SOLUTION (POWER & COOLING)
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3  Proposed Technical Solution", sec_title_style))
    story.append(Paragraph("Each subsystem is sized for full design capacity with Tier III concurrent maintainability. Specifications are OEM-neutral.", body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.1 Power Infrastructure", subsec_title_style))
    p_power = [
        f"<b>UPS:</b> Two modular online double-conversion UPS systems of {ups_frame_kw} kW each in 2N configuration. Each frame comprises hot-swappable power modules with N+1 internal redundancy and an external maintenance bypass. Operating load is 40&ndash;50% per bus during normal dual-feed operation.",
        f"<b>Batteries:</b> Lithium Iron Phosphate (Li-ion LFP) battery cabinets with integrated cell-level BMS, providing 15 minutes full-load autonomy per side.",
        f"<b>Distribution:</b> New TTA main LT panel with two transformer incomers (one per bus) and a DG incomer; separate TTA UPS input/output distribution panels for A and B paths; floor-mounted Remote Power Panels (RPPs) with branch circuit monitoring (BCM).",
        f"<b>Rack Power:</b> Dual intelligent 3-phase 32 A rack PDUs per rack (A+B), each sized to carry the full {kw_per_rack:g} kW load alone. Automatic Transfer Switches (ATS) for single-corded devices.",
        "<b>Cabling and Earthing:</b> Copper armoured cabling sized for doubled load, dedicated clean IT earth pits, and equipotential copper earth grid."
    ]
    for p in p_power:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(Spacer(1, 6))

    # TTA Callout Box
    tta_text = (
        "<b>All panels are Type-Tested Assemblies (TTA):</b> All LT panels (main LT, UPS I/O, RPPs, DG synchronising/AMF) are Type-Tested "
        "Assemblies to IEC 61439-1 and -2. Main LT and UPS panels use <b>Form 4b internal separation</b>, allowing any circuit to be safely worked on "
        "while adjacent feeders remain energized. The 11 kV panel is type-tested switchgear to IEC 62271-200. Certificates will be submitted with drawings."
    )
    t_tta = Table([[Paragraph(tta_text, body_style)]], colWidths=[522])
    t_tta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('LINELEFT', (0,0), (-1,-1), 3, colors.HexColor('#0F3870')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_tta)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3.2 Standby Power & Fuel System", subsec_title_style))
    p_dg = [
        f"<b>Diesel Generators:</b> Two {dg_kva} kVA DG sets (N+1), CPCB IV+ compliant in acoustic enclosures (&lt;75 dB(A) @ 1m), equipped with electronic governors, AMF synchronising panel, and automatic load management.",
        "<b>48-Hour Fuel Storage:</b> Double-walled bulk fuel storage tank (~8,000 L) with interstitial leak detection, automated fuel transfer pumps, daily service tanks, level transmitters integrated with BMS, and statutory PESO licensing."
    ]
    for p in p_dg:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.3 HT Switchgear and Transformers", subsec_title_style))
    p_ht = [
        f"<b>Transformers:</b> Two new {tx_kva} kVA, 11 kV / 433 V dry-type low-loss transformers (one per bus). Each transformer is rated for 100% facility load to permit isolation without dropping utility power.",
        "<b>HT Panels:</b> Type-tested 11 kV Vacuum Circuit Breaker (VCB) panel (IEC 62271-200) with incomer, dual transformer feeders, and numerical protection relays.",
        "<b>Civil & Approvals:</b> Cable trenching, bus-duct connections, fenced transformer yard with oil pits, and DISCOM / CEIG Electrical Inspector statutory approvals."
    ]
    for p in p_ht:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.4 Precision Cooling Infrastructure", subsec_title_style))
    p_cool = [
        f"<b>In-Row Units:</b> Inverter DX in-row cooling units in <b>N+2 configuration</b> with variable-speed brushless DC (BLDC) compressors, electronic expansion valves (EEV), and EC fans, modulating dynamically with IT load.",
        "<b>Condensers:</b> Air-cooled microchannel condensers on terrace with EC fans and acoustic treatment, configured to avoid thermal re-circulation.",
        "<b>Air Distribution:</b> Supply air delivered at 24&ndash;27 &deg;C at server inlets (ASHRAE TC 9.9 recommended envelope). Hot return air collected at 35&ndash;38 &deg;C.",
        "<b>Containment:</b> Rigid Hot-Aisle Containment (HAC) with ceiling panels, auto-closing glass sliding doors, and fire alarm smoke-purge links.",
        "<b>UPS Room:</b> Dedicated precision air conditioning (2 &times; 25 kW, N+1) maintaining UPS and Li-Ion battery room at optimal 23&plusmn;2 &deg;C."
    ]
    for p in p_cool:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 7: SECTION 3 (CONTD.) RACKS, FIRE, DCIM, PHYSICAL SECURITY
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3.5 Racks and Network Infrastructure", subsec_title_style))
    p_rack = [
        f"<b>Server Racks:</b> 47U server racks (800 mm wide &times; 1200 mm deep) with 1,500 kg static load rating, dual vertical cable management channels, and 80% perforated doors.",
        "<b>Network Racks:</b> Existing network racks retained with upgraded vertical and horizontal cable managers.",
        "<b>Airflow Management:</b> Blanking panels on all unpopulated rack units, brush grommets on cable entries, and under-rack air dams."
    ]
    for p in p_rack:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.6 Fire Detection and Suppression", subsec_title_style))
    p_fire = [
        "<b>Clean Agent Suppression:</b> Total flooding clean-agent gas suppression (<b>FK-5-1-12 / Novec 1230</b>) with cross-zoned photoelectric detectors and zero ozone depletion.",
        "<b>Aspirating Smoke Detection:</b> High-sensitivity <b>VESDA LaserPlus</b> system monitoring room, under-floor, and above-ceiling zones (0.005% to 20% obs/m sensitivity).",
        "<b>Battery Safety:</b> Thermal off-gas detection in Li-Ion battery room with automatic HVAC shutdown and emergency exhaust purge interlocks."
    ]
    for p in p_fire:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.7 BMS, DCIM and Asset Tracking", subsec_title_style))
    story.append(Paragraph("A full DCIM suite provides real-time visibility across power, cooling, space, assets, and security down to the individual U-slot.", body_style))
    story.append(Spacer(1, 4))

    dcim_data = [
        [Paragraph("<b>DCIM Module</b>", table_hdr), Paragraph("<b>Operational Functionality</b>", table_hdr)],
        [Paragraph("Monitoring & Alarms", table_cell_bold), Paragraph("End-to-end telemetry from HT transformers to rack PDU outlets; automated SMS/email alerts", table_cell)],
        [Paragraph("Capacity Planning", table_cell_bold), Paragraph("What-if modeling for space (U), power (kW), cooling (TR), and switch port utilization", table_cell)],
        [Paragraph("Asset Lifecycle", table_cell_bold), Paragraph("Complete asset database with serial number, warranty, owner, and U-position tracking", table_cell)],
        [Paragraph("Change & Work Orders", table_cell_bold), Paragraph("Workflow automation for moves, adds, and changes (MAC) tied to rack access authentication", table_cell)],
        [Paragraph("Energy & PUE Analytics", table_cell_bold), Paragraph("Live ISO/IEC 30134-2 Category 2 PUE reporting, trend forecasting, and carbon footprint tracking", table_cell)],
        [Paragraph("U-Position RFID Tracking", table_cell_bold), Paragraph("RFID sensor strips on all racks detecting hardware insertion/removal with ~600 tags", table_cell)]
    ]
    t_dcim = Table(dcim_data, colWidths=[130, 392])
    t_dcim.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_dcim)
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.8 Physical Security and Rack Access Control", subsec_title_style))
    p_sec = [
        "<b>Three-Level Access:</b> Perimeter access control, biometric data hall entrance, and dual-authentication electronic rack handle locks (Card + PIN / Biometric).",
        "<b>Rack CCTV Surveillance:</b> Two STQC ER-certified IP cameras per rack (front and rear) capturing video clips on every door-opening event (36 cameras total).",
        "<b>Regulatory Compliance:</b> Full replacement of Chinese-origin cameras with MeitY STQC Essential Requirements (ER) certified equipment with 90-day recording retention.",
        "<b>Entrance Partition:</b> Fire-rated (EI 60) glass partition with access-controlled door connecting data hall and NOC room."
    ]
    for p in p_sec:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 8: SECTION 4 REUSE, UPGRADE AND REPLACE MATRIX
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4  Reuse, Upgrade and Replace (Preliminary)", sec_title_style))
    story.append(Paragraph("To optimize capital expenditure, sound civil and passive infrastructure is retained, while electrical and thermal systems are modernized.", body_style))
    story.append(Spacer(1, 6))

    reuse_data = [
        [Paragraph("<b>Equipment / Subsystem</b>", table_hdr), Paragraph("<b>Disposition</b>", table_hdr), Paragraph("<b>Technical Remarks & Scope</b>", table_hdr)],
        [Paragraph("DC Room, Raised Floor, Ceiling", table_cell_bold), Paragraph("No Change", table_cell), Paragraph("Footprint retained; floor loading verified for 1,500 kg racks", table_cell)],
        [Paragraph("Network Racks", table_cell_bold), Paragraph("No Change", table_cell), Paragraph("Retained; vertical and horizontal cable managers added", table_cell)],
        [Paragraph("NOC Video Wall & Stations", table_cell_bold), Paragraph("No Change", table_cell), Paragraph("Retained; integrated with new DCIM central dashboard", table_cell)],
        [Paragraph("Rack Structured Cabling", table_cell_bold), Paragraph("By Client", table_cell), Paragraph("Excluded from EPC scope; to be executed by client separately", table_cell)],
        [Paragraph("Diesel Generator Sets", table_cell_bold), Paragraph("Replace / New", table_cell), Paragraph(f"Two new {dg_kva} kVA Prime CPCB IV+ compliant DG sets (N+1)", table_cell)],
        [Paragraph("Transformers & HT Panel", table_cell_bold), Paragraph("Replace / New", table_cell), Paragraph(f"2 &times; {tx_kva} kVA low-loss dry-type transformers, 11 kV VCB panel", table_cell)],
        [Paragraph("Main LT Switchboard", table_cell_bold), Paragraph("Replace", table_cell), Paragraph("New TTA panel to IEC 61439, Form 4b, with dual ACB incomers", table_cell)],
        [Paragraph("Earthing System", table_cell_bold), Paragraph("Upgrade", table_cell), Paragraph("Dedicated clean IT earth pits, equipotential copper grid", table_cell)],
        [Paragraph("Fuel Storage System", table_cell_bold), Paragraph("Upgrade / New", table_cell), Paragraph("48-hour bulk fuel storage (~8 kL) with PESO license & day tanks", table_cell)],
        [Paragraph("Clean-Agent Gas Suppression", table_cell_bold), Paragraph("Refurbish", table_cell), Paragraph("Re-engineered piping, cylinder hydro-testing, nozzle re-calc", table_cell)],
        [Paragraph("Aspirating Smoke Detection", table_cell_bold), Paragraph("Upgrade", table_cell), Paragraph("VESDA LaserPlus extended to all room and underfloor zones", table_cell)],
        [Paragraph("BMS & DCIM Suite", table_cell_bold), Paragraph("Upgrade / New", table_cell), Paragraph("Complete DCIM software with U-position RFID asset tracking", table_cell)],
        [Paragraph("Access Control System", table_cell_bold), Paragraph("Upgrade", table_cell), Paragraph("Biometric plus encrypted smart-card readers, software upgrade", table_cell)],
        [Paragraph("Water Leak & Rodent Defense", table_cell_bold), Paragraph("Upgrade", table_cell), Paragraph("Addressable sensing rope along perimeter; ultrasonic repellents", table_cell)],
        [Paragraph("Modular UPS Systems", table_cell_bold), Paragraph("Replace", table_cell), Paragraph(f"2N Modular UPS ({ups_frame_kw} kW per bus), hot-swappable modules", table_cell)],
        [Paragraph("UPS Batteries", table_cell_bold), Paragraph("Replace", table_cell), Paragraph("15-minute Lithium Iron Phosphate (Li-ion LFP) with BMS", table_cell)],
        [Paragraph("UPS Output Panels & RPPs", table_cell_bold), Paragraph("Replace", table_cell), Paragraph("TTA to IEC 61439 with branch circuit monitoring (BCM)", table_cell)],
        [Paragraph("Rack Intelligent PDUs", table_cell_bold), Paragraph("Replace", table_cell), Paragraph("Dual 3-phase 32 A metered-by-outlet intelligent PDUs (A+B)", table_cell)],
        [Paragraph("In-Row Precision Cooling", table_cell_bold), Paragraph("Replace", table_cell), Paragraph(f"New inverter DX units ({cooling_tr:g} TR, N+2) with EC fans, PUE &le; 1.5", table_cell)],
        [Paragraph("Server Racks", table_cell_bold), Paragraph("Replace", table_cell), Paragraph("47U 800&times;1200 mm racks with 1,500 kg static load capacity", table_cell)],
        [Paragraph("CCTV Surveillance Cameras", table_cell_bold), Paragraph("Replace", table_cell), Paragraph("STQC ER-certified non-Chinese IP cameras with 90-day storage", table_cell)],
        [Paragraph("Rack Electronic Locks", table_cell_bold), Paragraph("New", table_cell), Paragraph("Intelligent handle locks with dual-factor auth, event video clips", table_cell)],
        [Paragraph("Glass Entrance Partition", table_cell_bold), Paragraph("New", table_cell), Paragraph("Fire-rated (EI 60) glass partition with access-controlled door", table_cell)]
    ]
    t_reuse = Table(reuse_data, colWidths=[130, 80, 312])
    t_reuse.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_reuse)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 9: SECTION 5 BATTERY TECH & SECTION 6 TIA-942-C CERTIFICATION
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5  Battery Technology &ndash; Lithium-Ion", sec_title_style))
    story.append(Paragraph("Nikom proposes Lithium-Ion (LFP) batteries over legacy SMF-VRLA to guarantee a 10&ndash;15 year operating life without mid-lifecycle battery replacement.", body_style))
    story.append(Spacer(1, 4))

    bat_data = [
        [Paragraph("<b>Evaluation Criterion</b>", table_hdr), Paragraph("<b>Lithium-Ion (LFP) &ndash; Proposed</b>", table_hdr), Paragraph("<b>SMF-VRLA &ndash; Legacy Reference</b>", table_hdr)],
        [Paragraph("Design Service Life", table_cell_bold), Paragraph("<b>10&ndash;15 Years</b>", table_cell_bold), Paragraph("3&ndash;5 Years", table_cell)],
        [Paragraph("Replacement Horizon", table_cell_bold), Paragraph("<b>None expected within 10-year horizon</b>", table_cell_bold), Paragraph("1 to 2 complete replacements required", table_cell)],
        [Paragraph("Weight & Footprint", table_cell_bold), Paragraph("<b>50&ndash;60% reduction in weight & area</b>", table_cell_bold), Paragraph("Baseline (heavy floor loading)", table_cell)],
        [Paragraph("Operating Temperature", table_cell_bold), Paragraph("Tolerates up to 30 &deg;C without degradation", table_cell), Paragraph("Requires strict 20&ndash;25 &deg;C; capacity drops at heat", table_cell)],
        [Paragraph("Recharge Rate", table_cell_bold), Paragraph("Rapid recharge to 90% in &lt;2 hours", table_cell), Paragraph("Slow recharge (8&ndash;12 hours required)", table_cell)],
        [Paragraph("Cell Telemetry / BMS", table_cell_bold), Paragraph("Integrated cell-level BMS with CAN/Modbus", table_cell), Paragraph("External add-on monitoring required", table_cell)],
        [Paragraph("Fire Safety Mitigation", table_cell_bold), Paragraph("Off-gas detection & dedicated suppression", table_cell), Paragraph("Conventional acid spill containment", table_cell)]
    ]
    t_bat = Table(bat_data, colWidths=[130, 196, 196])
    t_bat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_bat)
    story.append(Spacer(1, 10))

    story.append(Paragraph("6  Tier III Compliance and TIA-942-C Certification", sec_title_style))
    story.append(Paragraph("The facility is engineered for full concurrent maintainability: every power and cooling element can be removed from service without dropping IT load.", body_style))
    story.append(Spacer(1, 4))

    p_tier = [
        "<b>Power:</b> 2N UPS with independent A and B paths feeding dual-corded PDUs in every rack.",
        "<b>Utility:</b> Two transformers, one per bus, on two independent HT cables; either can be maintained without utility drop.",
        "<b>Standby:</b> N+1 prime-rated DG with 48 hours of on-site bulk fuel storage.",
        "<b>Cooling:</b> N+2 in-row units, each on independent refrigerant circuits; maintenance can occur while another unit experiences a fault.",
        "<b>Validation:</b> Full Integrated Systems Testing (IST) with resistive load banks at 100% IT load prior to handover."
    ]
    for p in p_tier:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(Spacer(1, 6))

    # TIA-942-C Certification Protocol Box
    cert_text = (
        "<b>Two-Stage ANSI/TIA-942-C Rated-3 Certification Protocol:</b> As required for Tier III accreditation, certification will be executed "
        "by an accredited TIA-942 certifying body in two distinct phases: <b>Phase 1 (Design Documents Certification)</b> verifies all architectural, "
        "electrical, mechanical, and telecommunications drawings prior to procurement to close gaps on paper. <b>Phase 2 (Constructed Facility Certification)</b> "
        "involves on-site audit and live testing witnessed by auditors during Integrated Systems Testing (IST)."
    )
    t_cert = Table([[Paragraph(cert_text, body_style)]], colWidths=[522])
    t_cert.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#93C5FD')),
        ('LINELEFT', (0,0), (-1,-1), 3, colors.HexColor('#2563EB')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_cert)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 10: SECTION 7 ENERGY EFFICIENCY & SECTION 8 STANDARDS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("7  Energy Efficiency and PUE", sec_title_style))
    story.append(Paragraph("The facility is engineered to deliver an annualised PUE &le; 1.5 across all load regimes from 25% to 100%, achieving ~1.36 at full design load.", body_style))
    story.append(Spacer(1, 4))

    pue_data = [
        [Paragraph("<b>IT Load Regime</b>", table_hdr), Paragraph("<b>IT Load (kW)</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)), Paragraph("<b>Annualised PUE</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)), Paragraph("<b>PUE at Peak Ambient (36 &deg;C)</b>", ParagraphStyle('R', parent=table_hdr, alignment=2))],
        [Paragraph("25% Part Load", table_cell), Paragraph(f"{round(it_kw*0.25,1):g}", table_cell_right), Paragraph("1.50", table_cell_right_bold), Paragraph("1.59", table_cell_right)],
        [Paragraph("50% Part Load", table_cell), Paragraph(f"{round(it_kw*0.50,1):g}", table_cell_right), Paragraph("1.41", table_cell_right_bold), Paragraph("1.50", table_cell_right)],
        [Paragraph("75% Load", table_cell), Paragraph(f"{round(it_kw*0.75,1):g}", table_cell_right), Paragraph("1.38", table_cell_right_bold), Paragraph("1.47", table_cell_right)],
        [Paragraph("100% Full Design Load", table_cell_bold), Paragraph(f"{it_kw:g}", table_cell_right_bold), Paragraph("<b>1.36</b>", table_cell_right_bold), Paragraph("<b>1.46</b>", table_cell_right_bold)]
    ]
    t_pue = Table(pue_data, colWidths=[150, 110, 120, 142])
    t_pue.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_pue)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Key Measures Delivering Energy Efficiency:", subsec_title_style))
    p_eff = [
        "<b>Inverter DX In-Row Cooling:</b> BLDC compressors and EC fans match thermal output directly, consuming only ~0.27 kW per kW of IT load.",
        "<b>Hot-Aisle Containment:</b> Eliminates hot/cold air mixing, raising return temperature to 35&ndash;38 &deg;C for thermodynamic efficiency.",
        "<b>Modular UPS:</b> Multi-module hibernation maintains &ge;96% efficiency in double-conversion mode even at part load.",
        "<b>PUE Measurement:</b> Real-time monitoring conforming to ISO/IEC 30134-2 Category 2 (energy measured at UPS output)."
    ]
    for p in p_eff:
        story.append(Paragraph(f"&bull; {p}", bullet_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("8  Standards and Compliance Matrix", sec_title_style))
    story.append(Spacer(1, 4))

    std_data = [
        [Paragraph("<b>Engineering Domain</b>", table_hdr), Paragraph("<b>Governing International & Indian Standards</b>", table_hdr)],
        [Paragraph("Data Centre Infrastructure", table_cell_bold), Paragraph("ANSI/TIA-942-C Rated-3 (Tier III Concurrently Maintainable)", table_cell)],
        [Paragraph("Energy Efficiency & Thermal", table_cell_bold), Paragraph("ISO/IEC 30134-2 (PUE Category 2); ASHRAE TC 9.9 Thermal Guidelines", table_cell)],
        [Paragraph("Low Voltage Switchboards", table_cell_bold), Paragraph("IEC 61439-1 & -2, Type-Tested Assemblies (TTA), Form 4b Separation", table_cell)],
        [Paragraph("High Voltage Switchgear", table_cell_bold), Paragraph("IEC 62271-200 Metal-Enclosed Switchgear and Controlgear", table_cell)],
        [Paragraph("Power Transformers", table_cell_bold), Paragraph("IS 11171 / IEC 60076-11 Dry-Type Low-Loss Transformers; BEE Level", table_cell)],
        [Paragraph("Uninterruptible Power Supply", table_cell_bold), Paragraph("IEC 62040-1 (Safety), IEC 62040-2 (EMC), IEC 62040-3 (Performance)", table_cell)],
        [Paragraph("Lithium-Ion Batteries", table_cell_bold), Paragraph("IEC 62619 Industrial Secondary Lithium Cells; UL 9540A Fire Safety", table_cell)],
        [Paragraph("DG Sets & Fuel System", table_cell_bold), Paragraph("CPCB IV+ Emission Norms; ISO 8528; PESO Petroleum Rules for Bulk Fuel", table_cell)],
        [Paragraph("Fire Suppression & Life Safety", table_cell_bold), Paragraph("NFPA 2001 (Clean Agent), NFPA 75 (Data Centers), NFPA 72; NBC 2016", table_cell)],
        [Paragraph("Physical Security & CCTV", table_cell_bold), Paragraph("MeitY Essential Requirements with STQC Certification; BIS Registration", table_cell)],
        [Paragraph("Electrical Safety & Earthing", table_cell_bold), Paragraph("IS 732, IS 3043; CEA (Safety and Electric Supply) Regulations 2023", table_cell)]
    ]
    t_std = Table(std_data, colWidths=[140, 382])
    t_std.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_std)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 11: SECTION 9 MIGRATION SCHEDULE & SECTION 10 BUDGETARY OFFER
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("9  Migration Methodology and Schedule", sec_title_style))
    story.append(Paragraph("Execution is planned across 24 weeks from Purchase Order to handover, plus 4 weeks for constructed-facility TIA certification, maintaining live data centre operations throughout.", body_style))
    story.append(Spacer(1, 4))

    sched_data = [
        [Paragraph("<b>Phase</b>", table_hdr), Paragraph("<b>Weeks</b>", table_hdr), Paragraph("<b>Key Execution Activities</b>", table_hdr)],
        [Paragraph("1. Survey & Detailed Engineering", table_cell_bold), Paragraph("Wk 1&ndash;4", table_cell), Paragraph("Load logging, as-built verification, method statements, shutdown schedule", table_cell)],
        [Paragraph("2. TIA-942-C Design Certification", table_cell_bold), Paragraph("Wk 3&ndash;10", table_cell), Paragraph("Consultant audit, certifying body submission, closure of design gaps", table_cell)],
        [Paragraph("3. Equipment Procurement", table_cell_bold), Paragraph("Wk 3&ndash;14", table_cell), Paragraph("UPS, in-row units, CPCB IV+ DG sets, dry-type transformers manufacturing", table_cell)],
        [Paragraph("4. HT Works & DISCOM Approvals", table_cell_bold), Paragraph("Wk 6&ndash;16", table_cell), Paragraph("Two transformers, HT panel, dual HT cables, CEIG statutory clearance", table_cell)],
        [Paragraph("5. Outdoor & Yard Works", table_cell_bold), Paragraph("Wk 10&ndash;16", table_cell), Paragraph("DG erection, 48h bulk fuel tank, PESO licensing, condenser platforms", table_cell)],
        [Paragraph("6. B-Path Power Cutover", table_cell_bold), Paragraph("Wk 14&ndash;17", table_cell), Paragraph("B-side UPS, batteries & panels commissioned while A-path carries load", table_cell)],
        [Paragraph("7. A-Path Power Cutover", table_cell_bold), Paragraph("Wk 17&ndash;20", table_cell), Paragraph("A-side cutover executed seamlessly with B-side fully energized", table_cell)],
        [Paragraph("8. Cooling & Rack Migration", table_cell_bold), Paragraph("Wk 16&ndash;22", table_cell), Paragraph("In-row coolers and server racks migrated row-by-row with portable cooling", table_cell)],
        [Paragraph("9. Fire, DCIM & Security", table_cell_bold), Paragraph("Wk 18&ndash;22", table_cell), Paragraph("STQC CCTV swap, rack RFID strips, DCIM integration, glass partition", table_cell)],
        [Paragraph("10. Testing & Handover (IST)", table_cell_bold), Paragraph("Wk 22&ndash;24", table_cell), Paragraph("Integrated Systems Testing with load banks, black building test, training", table_cell)],
        [Paragraph("11. TIA Facility Certification", table_cell_bold), Paragraph("Wk 24&ndash;28", table_cell), Paragraph("Certifying body site audit, witnessed load-bank tests, official certificate", table_cell)]
    ]
    t_sched = Table(sched_data, colWidths=[130, 50, 342])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sched)
    story.append(Spacer(1, 10))

    story.append(Paragraph("10  Budgetary Commercial Offer", sec_title_style))
    story.append(Paragraph("Summary of turnkey capital expenditure and 5-year cost of ownership in Rs.  Lakhs (ex-GST):", body_style))
    story.append(Spacer(1, 4))

    capex_summary_data = [
        [Paragraph("<b>Subsystem / Scope Head</b>", table_hdr), Paragraph("<b>Amount (Rs.  Lakhs)</b>", ParagraphStyle('R', parent=table_hdr, alignment=2))],
        [Paragraph("Power Infrastructure (UPS, Li-Ion, TTA Panels, PDUs, Cabling, DG, 48h Fuel)", table_cell), Paragraph(f"Rs.  {capex_power:,.2f}", table_cell_right)],
        [Paragraph("Precision Cooling (In-row inverter DX, condensers, piping, containment)", table_cell), Paragraph(f"Rs.  {capex_cooling:,.2f}", table_cell_right)],
        [Paragraph("Racks and Airflow Containment Infrastructure", table_cell), Paragraph(f"Rs.  {capex_racks:,.2f}", table_cell_right)],
        [Paragraph("Fire Detection & Clean Agent Gas Suppression (FK-5-1-12, VESDA)", table_cell), Paragraph(f"Rs.  {capex_fire:,.2f}", table_cell_right)],
        [Paragraph("BMS, DCIM Software Suite, U-Position RFID Asset Tracking", table_cell), Paragraph(f"Rs.  {capex_dcim:,.2f}", table_cell_right)],
        [Paragraph("Physical Security, Rack Locks & Cameras, Fire-Rated Glass Partition", table_cell), Paragraph(f"Rs.  {capex_sec:,.2f}", table_cell_right)],
        [Paragraph("Engineering Services, Migration, Project Management & IST", table_cell), Paragraph(f"Rs.  {capex_services:,.2f}", table_cell_right)],
        [Paragraph("HT & Transformer Works (2 &times; Transformers, 11 kV Panel, DISCOM charges)", table_cell), Paragraph(f"Rs.  {capex_ht:,.2f}", table_cell_right)],
        [Paragraph("ANSI/TIA-942-C Rated-3 Certification (Consultancy, Audits, Gap Closure)", table_cell), Paragraph(f"Rs.  {capex_cert:,.2f}", table_cell_right)],
        [Paragraph("<b>TOTAL CAPITAL EXPENDITURE (CAPEX)</b>", table_cell_bold), Paragraph(f"<b>Rs.  {total_capex_lakhs:,.2f}</b>", table_cell_right_bold)]
    ]
    t_capex = Table(capex_summary_data, colWidths=[382, 140])
    t_capex.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_capex)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 12: 5-YEAR SPEND PROFILE, CAMC, MANAGED O&M & ASSUMPTIONS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5-Year Total Cost of Ownership (TCO) Spend Profile", subsec_title_style))
    story.append(Spacer(1, 4))

    tco_data = [
        [Paragraph("<b>Lifecycle Component</b>", table_hdr), Paragraph("<b>Amount (Rs.  Lakhs)</b>", ParagraphStyle('R', parent=table_hdr, alignment=2))],
        [Paragraph("CAPEX (inclusive of 3-Year Comprehensive Warranty)", table_cell_bold), Paragraph(f"Rs.  {total_capex_lakhs:,.2f}", table_cell_right_bold)],
        [Paragraph("Comprehensive AMC (CAMC) &ndash; Year 4", table_cell), Paragraph(f"Rs.  {camc_y4_lakhs:,.2f}", table_cell_right)],
        [Paragraph("Comprehensive AMC (CAMC) &ndash; Year 5 (5% escalation)", table_cell), Paragraph(f"Rs.  {camc_y5_lakhs:,.2f}", table_cell_right)],
        [Paragraph("24&times;7 Managed O&M Manpower &ndash; Year 1 (15 personnel)", table_cell), Paragraph(f"Rs.  {om_y1_lakhs:,.2f}", table_cell_right)],
        [Paragraph("24&times;7 Managed O&M Manpower &ndash; Year 2", table_cell), Paragraph(f"Rs.  {om_y2_lakhs:,.2f}", table_cell_right)],
        [Paragraph("24&times;7 Managed O&M Manpower &ndash; Year 3", table_cell), Paragraph(f"Rs.  {om_y3_lakhs:,.2f}", table_cell_right)],
        [Paragraph("24&times;7 Managed O&M Manpower &ndash; Year 4", table_cell), Paragraph(f"Rs.  {om_y4_lakhs:,.2f}", table_cell_right)],
        [Paragraph("24&times;7 Managed O&M Manpower &ndash; Year 5", table_cell), Paragraph(f"Rs.  {om_y5_lakhs:,.2f}", table_cell_right)],
        [Paragraph("<b>TOTAL 5-YEAR TCO (ex-GST)</b>", table_cell_bold), Paragraph(f"<b>Rs.  {total_5yr_lakhs:,.2f}</b>", table_cell_right_bold)],
        [Paragraph("Applicable GST @ 18%", table_cell), Paragraph(f"Rs.  {gst_lakhs:,.2f}", table_cell_right)],
        [Paragraph("<b>TOTAL 5-YEAR TCO (INCL. 18% GST)</b>", table_cell_bold), Paragraph(f"<b>Rs.  {total_incl_gst_lakhs:,.2f} (Rs. {total_incl_gst_cr:0.2f} Cr)</b>", table_cell_right_bold)]
    ]
    t_tco = Table(tco_data, colWidths=[382, 140])
    t_tco.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BACKGROUND', (0,9), (-1,9), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (0,11), (-1,11), colors.HexColor('#DBEAFE')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_tco)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Managed O&M Manpower Structure (24&times;7, On-Site, 15 Persons)", subsec_title_style))
    story.append(Spacer(1, 4))

    om_staff_data = [
        [Paragraph("<b>Role Description</b>", table_hdr), Paragraph("<b>Shift Coverage</b>", table_hdr), Paragraph("<b>Heads</b>", table_hdr), Paragraph("<b>Monthly Cost / Head (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2))],
        [Paragraph("Facility / Site Manager (DC Operations Lead)", table_cell_bold), Paragraph("General shift, 6 days", table_cell), Paragraph("1", table_cell), Paragraph("1,40,000", table_cell_right)],
        [Paragraph("Electrical Shift Engineer (UPS, LT, DG)", table_cell_bold), Paragraph("24&times;7 &ndash; 3 shifts + reliever", table_cell), Paragraph("4", table_cell), Paragraph("60,000", table_cell_right)],
        [Paragraph("HVAC / Mechanical Shift Technician", table_cell_bold), Paragraph("24&times;7 &ndash; 3 shifts + reliever", table_cell), Paragraph("4", table_cell), Paragraph("45,000", table_cell_right)],
        [Paragraph("BMS / DCIM / NOC Operator", table_cell_bold), Paragraph("24&times;7 &ndash; 3 shifts + reliever", table_cell), Paragraph("4", table_cell), Paragraph("42,000", table_cell_right)],
        [Paragraph("DG & Electrical Technician", table_cell_bold), Paragraph("General shift", table_cell), Paragraph("1", table_cell), Paragraph("35,000", table_cell_right)],
        [Paragraph("Fire, Safety & Security Technician", table_cell_bold), Paragraph("General shift", table_cell), Paragraph("1", table_cell), Paragraph("35,000", table_cell_right)],
        [Paragraph("<b>Total On-Site Operations Team</b>", table_cell_bold), Paragraph("<b>Continuous 24&times;7 Uptime Support</b>", table_cell_bold), Paragraph("<b>15</b>", table_cell_bold), Paragraph("<b>100% SLA Guarantee</b>", table_cell_right_bold)]
    ]
    t_om = Table(om_staff_data, colWidths=[172, 160, 50, 140])
    t_om.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_om)
    story.append(Spacer(1, 8))

    story.append(Paragraph("11  Assumptions and Exclusions", sec_title_style))
    p_assump = [
        f"<b>Assumptions:</b> (1) All {racks} racks engineered for {kw_per_rack:g} kW each. (2) Existing room and slab structure verified for 1,500 kg racks. (3) Yard space available for 2 &times; transformers and 8 kL bulk fuel tank. (4) 48h fuel autonomy complies with PESO licensing. (5) 3-year warranty included on all EPC equipment. (6) Offer validity: 90 calendar days."
    ]
    p_excl = [
        "<b>Exclusions:</b> (1) Passive structured network cabling (to be planned separately by client). (2) Major civil building alterations beyond transformer and fuel yard. (3) Active IT servers, storage, and networking switches. (4) Diesel consumption after commercial handover. (5) Statutory DISCOM and CEIG charges billed at actuals."
    ]
    for p in p_assump + p_excl:
        story.append(Paragraph(p, body_style))
        story.append(Spacer(1, 2))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 13: ANNEXURE A – ITEM-WISE BILL OF QUANTITIES (BOQ) - PART 1
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Annexure A &ndash; Item-wise Bill of Quantities", sec_title_style))
    story.append(Paragraph("Supply, installation, testing and commissioning with 3-year comprehensive warranty. Amounts in Rs. , ex-GST.", body_style))
    story.append(Spacer(1, 4))

    boq_headers = [Paragraph("<b>Sl.</b>", table_hdr), Paragraph("<b>Description & Technical Specification</b>", table_hdr), Paragraph("<b>UoM</b>", table_hdr), Paragraph("<b>Qty</b>", table_hdr), Paragraph("<b>Unit Rate (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)), Paragraph("<b>Amount (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)), Paragraph("<b>Disposition</b>", table_hdr)]

    boq_items_part1 = [
        # Package A: Power
        ("A1", f"Modular online double-conversion UPS, {ups_frame_kw} kW per side, hot-swappable 30 kW power modules, N+1 redundancy", "No.", "2", f"{int(6720000*scale):,}", f"{int(13440000*scale):,}", "Replace"),
        ("A2", f"Battery bank &ndash; Lithium-Ion (LFP) cabinets with integrated BMS, 15 min backup at {ups_frame_kw} kW, DC breaker", "Set", "2", f"{int(6720000*scale):,}", f"{int(13440000*scale):,}", "Replace"),
        ("A3", "Main LT panel &ndash; TTA (type-tested to IEC 61439-1/2), Form 4b, two transformer ACB incomers, DG incomer, bus-coupler", "Lot", "1", f"{int(3584000*scale):,}", f"{int(3584000*scale):,}", "Replace"),
        ("A4", "UPS input and output distribution panels for A and B paths (2N) &ndash; TTA to IEC 61439, Form 4b", "No.", "2", f"{int(1260000*scale):,}", f"{int(2520000*scale):,}", "Replace"),
        ("A5", "Floor-mounted Remote Power Panels (RPP), A and B feeds per row &ndash; TTA to IEC 61439 with branch monitoring", "No.", "4", f"{int(756000*scale):,}", f"{int(3024000*scale):,}", "Replace"),
        ("A6", "Intelligent 3-phase rack PDUs, 32 A, metered-by-outlet, network managed (2 per rack, A/B dual feed)", "No.", str(racks * 2), f"{int(161000):,}", f"{int(racks*2*161000):,}", "Replace"),
        ("A7", "Rack-mount automatic transfer switch (ATS) for single-corded network equipment", "No.", "4", "1,19,000", "4,76,000", "New"),
        ("A8", "LT power cabling (Cu armoured), cable trays, glands, lugs and terminations for upgraded power chain", "Lot", "1", f"{int(4480000*scale):,}", f"{int(4480000*scale):,}", "Upgrade"),
        ("A9", "Earthing system upgrade &ndash; dedicated clean IT earth pits, equipotential copper bonding grid", "Lot", "1", f"{int(630000*scale):,}", f"{int(630000*scale):,}", "Upgrade"),
        ("A10", f"Diesel generator set {dg_kva} kVA, CPCB IV+ compliant, with acoustic enclosure (N+1 standby power)", "No.", "2", f"{int(10080000*scale):,}", f"{int(20160000*scale):,}", "Replace"),
        ("A11", "DG synchronising and AMF panel &ndash; TTA to IEC 61439, with automated load management", "Lot", "1", f"{int(2352000*scale):,}", f"{int(2352000*scale):,}", "Replace"),
        ("A12", "Fuel system for 48-hour autonomy at full load &ndash; bulk storage tank (~8 kL), leak detection, transfer pumps, PESO", "Lot", "1", f"{int(2940000*scale):,}", f"{int(2940000*scale):,}", "Upgrade/New"),
        ("A13", "LED lighting with occupancy sensors for white space, UPS and plant rooms", "Lot", "1", "7,00,000", "7,00,000", "Replace"),
        # Package B: Cooling
        ("B1", f"In-row precision cooling, DX air-cooled, {cooling_tr:g} TR nominal, inverter compressor, EC fans, outdoor condenser (N+2)", "No.", "10", f"{int(2030000*scale):,}", f"{int(20300000*scale):,}", "Replace"),
        ("B2", "Refrigerant piping, insulation, condenser mounting structures, condensate drainage lines", "Lot", "1", f"{int(1960000*scale):,}", f"{int(1960000*scale):,}", "New"),
        ("B3", "Hot-aisle containment &ndash; roof panels, sliding glass doors, blanking panels, sealing (per row)", "Row", "2", f"{int(1190000*scale):,}", f"{int(2380000*scale):,}", "New/Upgrade"),
        ("B4", "Precision cooling for UPS and battery room, approx. 25 kW (N+1 redundant)", "No.", "2", "12,60,000", "25,20,000", "Upgrade")
    ]

    table_data_p1 = [boq_headers]
    for row in boq_items_part1:
        table_data_p1.append([
            Paragraph(row[0], table_cell_bold),
            Paragraph(row[1], table_cell),
            Paragraph(row[2], table_cell),
            Paragraph(row[3], table_cell),
            Paragraph(row[4], table_cell_right),
            Paragraph(row[5], table_cell_right_bold),
            Paragraph(row[6], table_cell)
        ])
    t_boq_p1 = Table(table_data_p1, colWidths=[24, 218, 26, 24, 70, 85, 75])
    t_boq_p1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_boq_p1)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 14: ANNEXURE A – ITEM-WISE BILL OF QUANTITIES (BOQ) - PART 2
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Annexure A &ndash; Item-wise Bill of Quantities (Continued)", sec_title_style))
    story.append(Spacer(1, 4))

    boq_items_part2 = [
        # Package C: Racks
        ("C1", "Server racks 47U, 800 W &times; 1200 D, perforated doors, 1500 kg static load, vertical cable managers", "No.", str(racks), f"{int(224000):,}", f"{int(racks*224000):,}", "Replace"),
        ("C2", "Network racks &ndash; retained; additional vertical cable managers and accessories", "No.", "4", "63,000", "2,52,000", "No Change"),
        ("C3", "Airflow management &ndash; blanking panels, brush grommets, cable-entry seals", "Lot", "1", "3,50,000", "3,50,000", "New"),
        # Package D: Fire
        ("D1", "Clean-agent suppression re-engineering &ndash; quantity recalculation, cylinder hydro-test/refill, nozzle relocation", "Lot", "1", "12,60,000", "12,60,000", "Refurbish"),
        ("D2", "Aspirating smoke detection (VESDA LaserPlus) upgrade for room and underfloor zones", "Lot", "1", "9,80,000", "9,80,000", "Upgrade"),
        ("D3", "Li-ion battery room &ndash; thermal off-gas detection and dedicated suppression system", "Lot", "1", "9,10,000", "9,10,000", "New"),
        ("D4", "Fire alarm panel integration with BMS, DG and HVAC shutdown interlocks", "Lot", "1", "3,50,000", "3,50,000", "Upgrade"),
        # Package E: BMS & DCIM
        ("E1", "DCIM core platform &ndash; real-time monitoring of power chain to outlet level, cooling, alarms, dashboards", "Lot", "1", f"{int(2520000*scale):,}", f"{int(2520000*scale):,}", "Upgrade/Replace"),
        ("E2", "Rack-level temperature/humidity sensors and door contacts", "Set", str(racks), "35,000", f"{int(racks*35000):,}", "New"),
        ("E3", "BMS controllers, gateways and integration of DG, LT, UPS, cooling, FAS, WLD", "Lot", "1", "12,60,000", "12,60,000", "Upgrade"),
        ("E4", "DCIM advanced modules &ndash; capacity planning, asset lifecycle, work orders, 3D visualization, PUE", "Lot", "1", "30,80,000", "30,80,000", "New"),
        ("E5", "DCIM servers in high availability (2 nos) with OS and database licenses", "Lot", "1", "12,60,000", "12,60,000", "New"),
        ("E6", "Asset tracking &ndash; U-position RFID sensor strips per rack (47U), with rack controller", "Set", str(racks), "77,000", f"{int(racks*77000):,}", "New"),
        ("E7", "Asset tracking tags for IT equipment (RFID / U-sensor tags)", "No.", "600", "1,000", "6,00,000", "New"),
        ("E8", "PUE metering &ndash; revenue-grade energy meters at incomer, UPS, cooling, and rack PDUs (ISO 30134-2)", "Lot", "1", "8,40,000", "8,40,000", "New"),
        # Package F: Security
        ("F1", "IP CCTV cameras, STQC ER-certified, non-Chinese origin (replacement of existing units)", "No.", "32", "31,000", "9,92,000", "Replace"),
        ("F2", "NVR / VMS with 90-day recording storage, STQC ER-certified", "Lot", "1", "6,30,000", "6,30,000", "Replace"),
        ("F3", "Intelligent rack handle locks, front and rear, with card + PIN / biometric dual authentication", "No.", str(racks * 2), "53,000", f"{int(racks*2*53000):,}", "New"),
        ("F4", "Rack-mounted IP cameras, front and rear of each rack, event-triggered capture; STQC ER-certified", "No.", str(racks * 2), "36,000", f"{int(racks*2*36000):,}", "New"),
        ("F5", "Fire-rated (EI 60) glass partition at data centre entrance connecting NOC room with access door", "Lot", "1", "17,50,000", "17,50,000", "New")
    ]

    table_data_p2 = [boq_headers]
    for row in boq_items_part2:
        table_data_p2.append([
            Paragraph(row[0], table_cell_bold),
            Paragraph(row[1], table_cell),
            Paragraph(row[2], table_cell),
            Paragraph(row[3], table_cell),
            Paragraph(row[4], table_cell_right),
            Paragraph(row[5], table_cell_right_bold),
            Paragraph(row[6], table_cell)
        ])
    t_boq_p2 = Table(table_data_p2, colWidths=[24, 218, 26, 24, 70, 85, 75])
    t_boq_p2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_boq_p2)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 15: ANNEXURE A (PART 3) SERVICES, HT & TIA-942-C + CAPEX TOTAL
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Annexure A &ndash; Item-wise Bill of Quantities (Services & HT)", sec_title_style))
    story.append(Spacer(1, 4))

    boq_items_part3 = [
        # Package G: Services
        ("G1", "Decommissioning, dismantling and e-waste compliant disposal of replaced equipment", "Lot", "1", "5,60,000", "5,60,000", "Service"),
        ("G2", "Live migration services &ndash; temporary power/cooling, phased cut-over, rack-by-rack support", "Lot", "1", f"{int(2520000*scale):,}", f"{int(2520000*scale):,}", "Service"),
        ("G3", "Detailed design, engineering, project management and as-built documentation", "Lot", "1", f"{int(2100000*scale):,}", f"{int(2100000*scale):,}", "Service"),
        ("G4", "Installation, testing and commissioning including Integrated Systems Testing (IST) with load banks", "Lot", "1", f"{int(2240000*scale):,}", f"{int(2240000*scale):,}", "Service"),
        # Package H: HT Works
        ("H1", f"11 kV / 433 V dry-type low-loss transformer, {tx_kva} kVA (BIS/BEE high-efficiency), with enclosure", "No.", "2", f"{int(4928000*scale):,}", f"{int(9856000*scale):,}", "New/Replace"),
        ("H2", "11 kV HT VCB panel &ndash; type-tested switchgear to IEC 62271-200, incomer and two transformer feeders", "Lot", "1", f"{int(5964000*scale):,}", f"{int(5964000*scale):,}", "New/Replace"),
        ("H3", "HT cabling (XLPE) &ndash; two independent cable runs from 11 kV supply, terminations, trenching", "Lot", "1", f"{int(5040000*scale):,}", f"{int(5040000*scale):,}", "New"),
        ("H4", "LT bus-duct / cabling from each transformer to the main LT panel (two runs)", "Lot", "1", f"{int(3500000*scale):,}", f"{int(3500000*scale):,}", "New"),
        ("H5", "Transformer yard civil works for two transformers &ndash; plinths, fencing, oil-pit and earthing", "Lot", "1", f"{int(3360000*scale):,}", f"{int(3360000*scale):,}", "New"),
        ("H6", "DISCOM liaison, Electrical Inspector (CEIG) approvals and statutory documentation", "Lot", "1", "21,00,000", "21,00,000", "Service"),
        ("H7", "DISCOM sanctioned-load enhancement charges &ndash; provisional, payable at actuals", "Lot", "1", "63,00,000", "63,00,000", "Provisional"),
        # Package J: TIA-942-C Certification
        ("J1", "TIA-942-C certification consultancy &ndash; gap analysis, design review and submission documentation", "Lot", "1", "56,00,000", "56,00,000", "Service"),
        ("J2", "ANSI/TIA-942-C Rated-3 certification of design documents &ndash; accredited certifying body fee", "Lot", "1", "84,00,000", "84,00,000", "Certification"),
        ("J3", "ANSI/TIA-942-C Rated-3 certification of constructed facility &ndash; accredited body audit & travel", "Lot", "1", "1,26,00,000", "1,26,00,000", "Certification"),
        ("J4", "Gap-closure works identified during design certification review (provisional contingency)", "Lot", "1", "70,00,000", "70,00,000", "Provisional")
    ]

    table_data_p3 = [boq_headers]
    for row in boq_items_part3:
        table_data_p3.append([
            Paragraph(row[0], table_cell_bold),
            Paragraph(row[1], table_cell),
            Paragraph(row[2], table_cell),
            Paragraph(row[3], table_cell),
            Paragraph(row[4], table_cell_right),
            Paragraph(row[5], table_cell_right_bold),
            Paragraph(row[6], table_cell)
        ])
    # Add Total Row
    table_data_p3.append([
        Paragraph("<b>TOTAL</b>", table_cell_bold),
        Paragraph("<b>TOTAL CAPITAL EXPENDITURE (CAPEX ex-GST)</b>", table_cell_bold),
        Paragraph("-", table_cell),
        Paragraph("-", table_cell),
        Paragraph("-", table_cell),
        Paragraph(f"<b>Rs.  {total_capex_lakhs * 100000:,.0f}</b>", ParagraphStyle('R', parent=table_cell_bold, alignment=2, textColor=colors.HexColor('#0F3870'))),
        Paragraph("<b>Turnkey EPC</b>", table_cell_bold)
    ])

    t_boq_p3 = Table(table_data_p3, colWidths=[24, 218, 26, 24, 70, 85, 75])
    t_boq_p3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#0F3870')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_boq_p3)
    story.append(Spacer(1, 8))

    prov_p = (
        "<i>Note: Quantities marked 'subject to survey' and provisional items (DISCOM load enhancement charges, certifying-body travel, "
        "and gap-closure contingencies) will be firmed up after joint site inspection and billed at actuals where stated.</i>"
    )
    story.append(Paragraph(prov_p, body_style))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 16: ANNEXURE B – CAMC BREAK-UP, YEARS 4 AND 5
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Annexure B &ndash; CAMC Break-up, Years 4 and 5", sec_title_style))
    story.append(Paragraph("Comprehensive AMC after initial 3-year warranty, including preventive & breakdown maintenance and all spares. Year 5 escalated by 5%.", body_style))
    story.append(Spacer(1, 4))

    camc_headers = [Paragraph("<b>Equipment Category</b>", table_hdr), Paragraph("<b>Equipment Value (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)), Paragraph("<b>Rate</b>", table_hdr), Paragraph("<b>Year 4 (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)), Paragraph("<b>Year 5 (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2))]

    camc_items = [
        ("Modular Online 2N UPS System", f"{int(13440000*scale):,}", "7%", f"{int(940800*scale):,}", f"{int(987840*scale):,}"),
        ("Lithium-Ion (LFP) Battery Cabinets", f"{int(13440000*scale):,}", "3%", f"{int(403200*scale):,}", f"{int(423360*scale):,}"),
        ("Main LT Switchboard (TTA Form 4b)", f"{int(3584000*scale):,}", "5%", f"{int(179200*scale):,}", f"{int(188160*scale):,}"),
        ("UPS I/O Panels & RPPs", f"{int(5544000*scale):,}", "5%", f"{int(277200*scale):,}", f"{int(291060*scale):,}"),
        ("Intelligent Rack PDUs & ATS", f"{int(6272000*scale):,}", "5%", f"{int(313600*scale):,}", f"{int(329280*scale):,}"),
        ("CPCB IV+ DG Power Generation System", f"{int(20160000*scale):,}", "6%", f"{int(1209600*scale):,}", f"{int(1270080*scale):,}"),
        ("DG AMF & Fuel System", f"{int(5292000*scale):,}", "4%", f"{int(205800*scale):,}", f"{int(216090*scale):,}"),
        ("In-Row Precision Cooling & Condensers", f"{int(20300000*scale):,}", "8%", f"{int(1624000*scale):,}", f"{int(1705200*scale):,}"),
        ("UPS Room Precision Cooling", f"{int(2520000*scale):,}", "8%", f"{int(201600*scale):,}", f"{int(211680*scale):,}"),
        ("Clean Agent Fire Suppression System", f"{int(1260000*scale):,}", "6%", f"{int(75600*scale):,}", f"{int(79380*scale):,}"),
        ("VESDA Aspirating Smoke Detection", f"{int(980000*scale):,}", "6%", f"{int(58800*scale):,}", f"{int(61740*scale):,}"),
        ("DCIM Platform & Servers", f"{int(6860000*scale):,}", "10%", f"{int(686000*scale):,}", f"{int(720300*scale):,}"),
        ("U-Position RFID Asset Tracking", f"{int(2364000*scale):,}", "8%", f"{int(189120*scale):,}", f"{int(198576*scale):,}"),
        ("STQC ER CCTV & NVR System", f"{int(1622000*scale):,}", "8%", f"{int(129760*scale):,}", f"{int(136248*scale):,}"),
        ("Intelligent Rack Handle Locks & Cameras", f"{int(3906000*scale):,}", "8%", f"{int(312480*scale):,}", f"{int(328104*scale):,}"),
        ("Access Control, WLD & Rodent Repellent", f"{int(1372000*scale):,}", "8%", f"{int(109760*scale):,}", f"{int(115248*scale):,}"),
        ("Dry-Type Low-Loss Transformers (2 nos)", f"{int(9856000*scale):,}", "3%", f"{int(295680*scale):,}", f"{int(310464*scale):,}"),
        ("11 kV HT VCB Panel", f"{int(5964000*scale):,}", "4%", f"{int(238560*scale):,}", f"{int(250488*scale):,}")
    ]

    table_data_camc = [camc_headers]
    for row in camc_items:
        table_data_camc.append([
            Paragraph(row[0], table_cell),
            Paragraph(row[1], table_cell_right),
            Paragraph(row[2], table_cell),
            Paragraph(row[3], table_cell_right),
            Paragraph(row[4], table_cell_right)
        ])
    # Total CAMC Row
    table_data_camc.append([
        Paragraph("<b>TOTAL CAMC (ex-GST)</b>", table_cell_bold),
        Paragraph("-", table_cell_right),
        Paragraph("<b>Blended</b>", table_cell_bold),
        Paragraph(f"<b>Rs.  {camc_y4_lakhs * 100000:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>Rs.  {camc_y5_lakhs * 100000:,.0f}</b>", table_cell_right_bold)
    ])

    t_camc = Table(table_data_camc, colWidths=[182, 110, 50, 90, 90])
    t_camc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#0F3870')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_camc)
    story.append(Spacer(1, 8))

    camc_note = (
        f"<b>CAMC Summary:</b> Total 2-Year Comprehensive AMC (Years 4 and 5) = <b>Rs.  {total_camc_lakhs:,.2f} Lakhs (Rs. {total_camc_cr:0.2f} Cr)</b>. "
        f"Passive elements, civil works, structured cabling, and TIA-942 certification fees carry zero CAMC liability. All genuine OEM spares included."
    )
    story.append(Paragraph(camc_note, body_style))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 17: ANNEXURE C – MANAGED O&M SERVICES 5-YEAR BREAK-UP
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Annexure C &ndash; Managed O&M Services, 5-Year Break-up", sec_title_style))
    story.append(Paragraph("24&times;7 on-site operations and maintenance by 15 certified engineering personnel. Monthly cost is all-inclusive of PF, ESI, bonus, and statutory compliance. 6% annual escalation from Year 2.", body_style))
    story.append(Spacer(1, 4))

    om_headers = [
        Paragraph("<b>Role</b>", table_hdr),
        Paragraph("<b>Shift Coverage</b>", table_hdr),
        Paragraph("<b>Qty</b>", table_hdr),
        Paragraph("<b>Year 1 (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)),
        Paragraph("<b>Year 2 (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)),
        Paragraph("<b>Year 3 (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)),
        Paragraph("<b>Year 4 (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2)),
        Paragraph("<b>Year 5 (Rs. )</b>", ParagraphStyle('R', parent=table_hdr, alignment=2))
    ]

    roles_info = [
        ("Facility / Site Manager", "General shift, 6 days", 1, 140000),
        ("Electrical Shift Engineer", "24x7 &ndash; 3 shifts + reliever", 4, 60000),
        ("HVAC / Mechanical Tech", "24x7 &ndash; 3 shifts + reliever", 4, 45000),
        ("BMS / DCIM / NOC Operator", "24x7 &ndash; 3 shifts + reliever", 4, 42000),
        ("DG & Electrical Tech", "General shift", 1, 35000),
        ("Fire & Security Tech", "General shift", 1, 35000),
    ]

    table_data_om = [om_headers]
    subtotal_y = [0.0]*5
    for title, cov, heads, rate in roles_info:
        y1 = heads * rate * 12
        y2 = round(y1 * 1.06)
        y3 = round(y2 * 1.06)
        y4 = round(y3 * 1.06)
        y5 = round(y4 * 1.06)
        subtotal_y[0] += y1
        subtotal_y[1] += y2
        subtotal_y[2] += y3
        subtotal_y[3] += y4
        subtotal_y[4] += y5
        table_data_om.append([
            Paragraph(title, table_cell_bold),
            Paragraph(cov, table_cell),
            Paragraph(str(heads), table_cell),
            Paragraph(f"{y1:,.0f}", table_cell_right),
            Paragraph(f"{y2:,.0f}", table_cell_right),
            Paragraph(f"{y3:,.0f}", table_cell_right),
            Paragraph(f"{y4:,.0f}", table_cell_right),
            Paragraph(f"{y5:,.0f}", table_cell_right)
        ])

    # Manpower Subtotal
    table_data_om.append([
        Paragraph("<b>Manpower Subtotal</b>", table_cell_bold),
        Paragraph("<b>15 Personnel</b>", table_cell_bold),
        Paragraph("<b>15</b>", table_cell_bold),
        Paragraph(f"<b>{subtotal_y[0]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{subtotal_y[1]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{subtotal_y[2]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{subtotal_y[3]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{subtotal_y[4]:,.0f}</b>", table_cell_right_bold)
    ])

    # 10% Service Charge
    sc_y = [round(s * 0.10) for s in subtotal_y]
    table_data_om.append([
        Paragraph("Service Charge (10%)", table_cell),
        Paragraph("Corporate PMO & QHSE", table_cell),
        Paragraph("-", table_cell),
        Paragraph(f"{sc_y[0]:,.0f}", table_cell_right),
        Paragraph(f"{sc_y[1]:,.0f}", table_cell_right),
        Paragraph(f"{sc_y[2]:,.0f}", table_cell_right),
        Paragraph(f"{sc_y[3]:,.0f}", table_cell_right),
        Paragraph(f"{sc_y[4]:,.0f}", table_cell_right)
    ])

    # Tools, PPE & Consumables
    tools_y1 = 300000
    tools_y = [round(tools_y1 * (1.06 ** i)) for i in range(5)]
    table_data_om.append([
        Paragraph("Tools, Consumables & PPE", table_cell),
        Paragraph("Fluke testers, safety gear", table_cell),
        Paragraph("-", table_cell),
        Paragraph(f"{tools_y[0]:,.0f}", table_cell_right),
        Paragraph(f"{tools_y[1]:,.0f}", table_cell_right),
        Paragraph(f"{tools_y[2]:,.0f}", table_cell_right),
        Paragraph(f"{tools_y[3]:,.0f}", table_cell_right),
        Paragraph(f"{tools_y[4]:,.0f}", table_cell_right)
    ])

    # Total O&M Row
    total_om_per_year = [round(subtotal_y[i] + sc_y[i] + tools_y[i]) for i in range(5)]
    total_om_5yr_sum = sum(total_om_per_year)
    table_data_om.append([
        Paragraph("<b>TOTAL O&M (ex-GST)</b>", table_cell_bold),
        Paragraph("<b>Full Turnkey Facility Care</b>", table_cell_bold),
        Paragraph("-", table_cell),
        Paragraph(f"<b>{total_om_per_year[0]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{total_om_per_year[1]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{total_om_per_year[2]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{total_om_per_year[3]:,.0f}</b>", table_cell_right_bold),
        Paragraph(f"<b>{total_om_per_year[4]:,.0f}</b>", table_cell_right_bold)
    ])

    t_om_detail = Table(table_data_om, colWidths=[122, 120, 24, 51, 51, 51, 51, 52])
    t_om_detail.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F3870')),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEBELOW', (0,7), (-1,7), 1, colors.HexColor('#94A3B8')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#0F3870')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_om_detail)
    story.append(Spacer(1, 10))

    final_note = (
        f"<b>Five-Year Managed O&M Total: Rs.  {total_om_5yr_sum:,.0f} (Rs. {total_om_5yr_sum/10000000:0.2f} Cr) ex-GST.</b> "
        f"Scope covers 24&times;7 round-the-clock power and thermal operations, preventive maintenance coordination, emergency rapid response, "
        f"uptime tracking, monthly SLA governance, and live PUE reporting. Certified OEM spares are provided under equipment warranty (Years 1&ndash;3) "
        f"and Comprehensive AMC (Years 4&ndash;5)."
    )
    story.append(Paragraph(final_note, body_style))

    # Build PDF with two-pass canvas
    doc.build(story, canvasmaker=FormalProposalCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
