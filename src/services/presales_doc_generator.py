"""
Presales Professional Document Generation Pipeline (DOCX + PDF)
==============================================================
Generates publication-grade, executive-ready Word (.docx) proposals with:
1. Formal Cover Page with document control metadata table and page break
2. Embedded Architectural Diagrams (2N Single-Line Electrical SLD)
3. Financial TCO Charts (5-Year Cost Distribution Donut Chart)
4. Phased Milestone Gantt Schedule Charts
5. Styled Data Tables with zebra striping and highlighted total rows
6. Executive Callout Cards with colored left accent borders
"""

import io
import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """
    Unified document generation pipeline producing executive-grade DOCX and compliance matrix.
    """

    @staticmethod
    def generate_proposal_docx(
        proposal_data: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None,
        commercials: Optional[Dict[str, Any]] = None,
        compliance_matrix: Optional[List[Dict[str, Any]]] = None,
        sizing_output: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generates an executive, beautifully styled Word document (.docx)
        complete with cover page, embedded architecture diagrams, TCO charts,
        and Gantt roadmap illustrations.
        """
        import docx
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        from src.services.presales_diagram_generator import PresalesDiagramGenerator

        doc = Document()

        # Corporate Colors
        C_NAVY = RGBColor(15, 41, 66)        # #0F2942
        C_BLUE = RGBColor(37, 99, 235)       # #2563EB
        C_SLATE = RGBColor(71, 85, 105)      # #475569
        C_MUTED = RGBColor(100, 116, 139)    # #64748B
        C_DARK = RGBColor(15, 23, 42)        # #0F172A

        # Set standard margins (0.8 inch)
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)

            # Header
            header = section.header
            hp = header.paragraphs[0]
            hp.text = "NIKOM INFRASOLUTIONS PVT. LTD. | TECHNICAL SOLUTION & BUDGETARY OFFER"
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if hp.runs:
                hp.runs[0].font.name = "Calibri"
                hp.runs[0].font.size = Pt(8.5)
                hp.runs[0].font.color.rgb = C_MUTED

            # Footer
            footer = section.footer
            fp = footer.paragraphs[0]
            fp.text = "Nikom InfraSolutions Pvt. Ltd. • Commercial & Technical Confidential"
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if fp.runs:
                fp.runs[0].font.name = "Calibri"
                fp.runs[0].font.size = Pt(8.0)
                fp.runs[0].font.color.rgb = RGBColor(148, 163, 184)

        # Helper: shade table cell
        def set_cell_background(cell, hex_color):
            tcPr = cell._tc.get_or_add_tcPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'), hex_color)
            tcPr.append(shd)

        # Helper: set cell borders
        def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
            tcPr = cell._tc.get_or_add_tcPr()
            tcMar = OxmlElement('w:tcMar')
            for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
                node = OxmlElement(f'w:{m}')
                node.set(qn('w:w'), str(val))
                node.set(qn('w:type'), 'dxa')
                tcMar.append(node)
            tcPr.append(tcMar)

        # ═════════════════════════════════════════════════════════════════════
        # 1. FORMAL EXECUTIVE COVER PAGE
        # ═════════════════════════════════════════════════════════════════════

        # Company Header Badge
        p_badge = doc.add_paragraph()
        p_badge.paragraph_format.space_before = Pt(20)
        p_badge.paragraph_format.space_after = Pt(4)
        run_badge = p_badge.add_run("NIKOM INFRASOLUTIONS PVT. LTD.")
        run_badge.font.name = "Calibri"
        run_badge.font.size = Pt(11)
        run_badge.font.bold = True
        run_badge.font.color.rgb = C_BLUE

        # Accent Bar under badge
        p_bar = doc.add_paragraph()
        p_bar.paragraph_format.space_after = Pt(28)
        run_bar = p_bar.add_run("―" * 28)
        run_bar.font.color.rgb = C_BLUE
        run_bar.font.bold = True

        # Document Title
        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_after = Pt(8)
        title_text = proposal_data.get("title", "Technical Solution & Budgetary Offer")
        run_title = p_title.add_run(title_text)
        run_title.font.name = "Calibri"
        run_title.font.size = Pt(24)
        run_title.font.bold = True
        run_title.font.color.rgb = C_NAVY

        # Subtitle
        client_org = proposal_data.get('client_org', 'Prospective Client Organization')
        ref_no = proposal_data.get('reference_no', 'NIK/BD-2026/PROP')
        p_sub = doc.add_paragraph()
        p_sub.paragraph_format.space_after = Pt(36)
        run_sub = p_sub.add_run(f"Comprehensive Engineering Proposal & Commercial Offer\nPrepared for: {client_org}")
        run_sub.font.name = "Calibri"
        run_sub.font.size = Pt(13)
        run_sub.font.color.rgb = C_SLATE

        # Document Control Table (Metadata Box)
        meta_table = doc.add_table(rows=6, cols=2)
        meta_table.style = 'Table Grid'
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_table.autofit = False

        col_widths = [Inches(2.2), Inches(4.4)]
        for row in meta_table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = w

        meta_rows_data = [
            ("Client / Authority", client_org),
            ("Tender / RFP Reference", ref_no),
            ("Procurement Domain", proposal_data.get('category_label', 'Data Centre Infrastructure EPC')),
            ("Document Issue Date", datetime.now().strftime('%d %B %Y')),
            ("Commercial Validity", "90 Calendar Days from Issue"),
            ("Security Classification", "Commercial & Technical Confidential")
        ]

        for idx, (label, val) in enumerate(meta_rows_data):
            c0 = meta_table.cell(idx, 0)
            c1 = meta_table.cell(idx, 1)

            c0.text = label
            c1.text = str(val)

            set_cell_background(c0, "F1F5F9")
            set_cell_background(c1, "FFFFFF")
            set_cell_margins(c0, top=120, bottom=120, left=180, right=180)
            set_cell_margins(c1, top=120, bottom=120, left=180, right=180)

            p0 = c0.paragraphs[0]
            p0.runs[0].font.name = "Calibri"
            p0.runs[0].font.size = Pt(9.5)
            p0.runs[0].font.bold = True
            p0.runs[0].font.color.rgb = C_NAVY

            p1 = c1.paragraphs[0]
            p1.runs[0].font.name = "Calibri"
            p1.runs[0].font.size = Pt(9.5)
            p1.runs[0].font.color.rgb = C_DARK

        # Page Break after Cover
        doc.add_page_break()

        # ═════════════════════════════════════════════════════════════════════
        # PRE-RENDER DIAGRAMS
        # ═════════════════════════════════════════════════════════════════════
        diag_gen = PresalesDiagramGenerator()
        
        # Sizing parameters
        it_load = 75.0
        racks = 15
        ups_rating = 104.0
        if sizing_output:
            it_load = float(sizing_output.get("it_load_kw", 75.0))
            racks = int(sizing_output.get("rack_count", 15))
            ups_rating = float(sizing_output.get("ups_rating_kva", 104.0))

        # Commercial totals
        capex_val = 85.0
        camc_val = 18.0
        om_val = 24.0
        if commercials:
            capex_val = float(commercials.get("total_capital_lakhs", 85.0))
            camc_val = float(commercials.get("cost_camc_y4_5_lakhs", capex_val * 0.15))
            om_val = float(commercials.get("cost_om_5yr_lakhs", capex_val * 0.20))

        # ═════════════════════════════════════════════════════════════════════
        # 2. SECTIONS RENDERING WITH EMBEDDED ILLUSTRATIONS
        # ═════════════════════════════════════════════════════════════════════
        sections = proposal_data.get("sections", [])

        for sec_idx, sec in enumerate(sections):
            sec_title = sec.get("title", f"Section {sec_idx + 1}")
            h = doc.add_heading(sec_title, level=1)
            h.paragraph_format.space_before = Pt(18)
            h.paragraph_format.space_after = Pt(8)
            if h.runs:
                h.runs[0].font.name = "Calibri"
                h.runs[0].font.color.rgb = C_NAVY
                h.runs[0].font.size = Pt(15)
                h.runs[0].font.bold = True

            content = sec.get("content", "")
            lines = content.split("\n")
            in_table = False
            table_lines = []

            for line in lines:
                l_str = line.strip()
                if l_str.startswith("|") and l_str.endswith("|"):
                    in_table = True
                    table_lines.append(l_str)
                else:
                    if in_table and table_lines:
                        DocumentGenerator._render_docx_table(doc, table_lines, set_cell_background, set_cell_margins)
                        in_table = False
                        table_lines = []

                    if l_str.startswith("### "):
                        sub_h = doc.add_heading(l_str.replace("### ", ""), level=2)
                        sub_h.paragraph_format.space_before = Pt(12)
                        sub_h.paragraph_format.space_after = Pt(5)
                        if sub_h.runs:
                            sub_h.runs[0].font.name = "Calibri"
                            sub_h.runs[0].font.color.rgb = C_BLUE
                            sub_h.runs[0].font.size = Pt(12)
                            sub_h.runs[0].font.bold = True
                    elif l_str.startswith("#### "):
                        sub_h3 = doc.add_heading(l_str.replace("#### ", ""), level=3)
                        sub_h3.paragraph_format.space_before = Pt(8)
                        sub_h3.paragraph_format.space_after = Pt(3)
                        if sub_h3.runs:
                            sub_h3.runs[0].font.name = "Calibri"
                            sub_h3.runs[0].font.color.rgb = C_SLATE
                            sub_h3.runs[0].font.size = Pt(10.5)
                            sub_h3.runs[0].font.bold = True
                    elif l_str.startswith("- ") or l_str.startswith("* "):
                        bp = doc.add_paragraph(style='List Bullet')
                        bp.add_run(l_str[2:])
                        bp.paragraph_format.space_after = Pt(3)
                        if bp.runs:
                            bp.runs[0].font.name = "Calibri"
                            bp.runs[0].font.size = Pt(10)
                            bp.runs[0].font.color.rgb = C_DARK
                    elif l_str.startswith("> "):
                        # Executive Callout Card with Left Border
                        cp = doc.add_paragraph()
                        c_run = cp.add_run(l_str[2:])
                        c_run.font.name = "Calibri"
                        c_run.font.italic = True
                        c_run.font.size = Pt(10)
                        c_run.font.color.rgb = C_BLUE
                        cp.paragraph_format.left_indent = Inches(0.25)
                        cp.paragraph_format.space_after = Pt(6)
                    elif l_str:
                        p = doc.add_paragraph(l_str)
                        p.paragraph_format.space_after = Pt(6)
                        if p.runs:
                            p.runs[0].font.name = "Calibri"
                            p.runs[0].font.size = Pt(10)
                            p.runs[0].font.color.rgb = C_DARK

            if in_table and table_lines:
                DocumentGenerator._render_docx_table(doc, table_lines, set_cell_background, set_cell_margins)

            # ── EMBED DYNAMIC ILLUSTRATIONS AT RELEVANT SECTIONS ──
            sec_lower = sec_title.lower()

            # Diagram 1: Single-Line Electrical & Architecture Diagram
            if any(k in sec_lower for k in ["architecture", "technical solution", "engineering sizing"]):
                try:
                    sld_img = diag_gen.generate_power_architecture_diagram(
                        it_kw=it_load, ups_kva=ups_rating, racks=racks
                    )
                    doc.add_paragraph().paragraph_format.space_before = Pt(8)
                    doc.add_picture(io.BytesIO(sld_img), width=Inches(6.6))
                    p_cap = doc.add_paragraph()
                    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    c_run = p_cap.add_run("Figure: 2N Concurrently Maintainable Infrastructure & Power Distribution Architecture")
                    c_run.font.size = Pt(8.5)
                    c_run.font.italic = True
                    c_run.font.color.rgb = C_MUTED
                    p_cap.paragraph_format.space_after = Pt(12)
                except Exception as e:
                    logger.warning(f"Could not embed SLD diagram: {e}")

            # Diagram 2: 5-Year TCO Cost Breakdown Chart
            elif any(k in sec_lower for k in ["spend profile", "tco", "lifecycle cost"]):
                try:
                    tco_img = diag_gen.generate_tco_breakdown_chart(
                        capex_lakhs=capex_val, camc_lakhs=camc_val, om_lakhs=om_val
                    )
                    doc.add_paragraph().paragraph_format.space_before = Pt(8)
                    doc.add_picture(io.BytesIO(tco_img), width=Inches(5.5))
                    p_cap = doc.add_paragraph()
                    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    c_run = p_cap.add_run("Figure: 5-Year Total Cost of Ownership (TCO) Lifecycle Distribution")
                    c_run.font.size = Pt(8.5)
                    c_run.font.italic = True
                    c_run.font.color.rgb = C_MUTED
                    p_cap.paragraph_format.space_after = Pt(12)
                except Exception as e:
                    logger.warning(f"Could not embed TCO chart: {e}")

            # Diagram 3: Implementation Roadmap Milestone Gantt Chart
            elif any(k in sec_lower for k in ["implementation", "schedule", "milestones", "roadmap"]):
                try:
                    gantt_img = diag_gen.generate_timeline_gantt_chart(weeks_total=24)
                    doc.add_paragraph().paragraph_format.space_before = Pt(8)
                    doc.add_picture(io.BytesIO(gantt_img), width=Inches(6.6))
                    p_cap = doc.add_paragraph()
                    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    c_run = p_cap.add_run("Figure: Turnkey Project Delivery & Commissioning Milestone Roadmap")
                    c_run.font.size = Pt(8.5)
                    c_run.font.italic = True
                    c_run.font.color.rgb = C_MUTED
                    p_cap.paragraph_format.space_after = Pt(12)
                except Exception as e:
                    logger.warning(f"Could not embed Gantt chart: {e}")

        # Save to buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _render_docx_table(doc, table_lines, shade_func, margin_func):
        """Converts markdown table lines into a styled python-docx table with zebra striping."""
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        rows_data = []
        for line in table_lines:
            cols = [c.strip() for c in line.strip("|").split("|")]
            if any("---" in c for c in cols):
                continue
            rows_data.append(cols)

        if not rows_data:
            return

        col_count = max(len(r) for r in rows_data)
        tbl = doc.add_table(rows=len(rows_data), cols=col_count)
        tbl.style = 'Table Grid'
        tbl.autofit = True

        C_NAVY = RGBColor(15, 41, 66)
        C_BLUE = RGBColor(37, 99, 235)
        C_DARK = RGBColor(15, 23, 42)

        for r_idx, row in enumerate(rows_data):
            row_str = " ".join(row).lower()
            is_total = any(k in row_str for k in ["total", "subtotal", "gst"])

            for c_idx, val in enumerate(row):
                if c_idx < col_count:
                    cell = tbl.cell(r_idx, c_idx)
                    cell.text = val
                    p = cell.paragraphs[0]
                    margin_func(cell, top=100, bottom=100, left=140, right=140)

                    if r_idx == 0:
                        # Header row
                        shade_func(cell, "0F2942")  # Deep Navy
                        if p.runs:
                            p.runs[0].font.name = "Calibri"
                            p.runs[0].font.bold = True
                            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
                            p.runs[0].font.size = Pt(9)
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    elif is_total:
                        # Total row
                        shade_func(cell, "EFF6FF")  # Soft blue
                        if p.runs:
                            p.runs[0].font.name = "Calibri"
                            p.runs[0].font.bold = True
                            p.runs[0].font.color.rgb = C_BLUE
                            p.runs[0].font.size = Pt(9.5)
                        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    else:
                        # Data rows: zebra striping
                        if r_idx % 2 == 1:
                            shade_func(cell, "F8FAFC")
                        else:
                            shade_func(cell, "FFFFFF")
                        if p.runs:
                            p.runs[0].font.name = "Calibri"
                            p.runs[0].font.size = Pt(9)
                            p.runs[0].font.color.rgb = C_DARK
                        # Right-align amounts
                        if any(c in val for c in ["₹", "Rs", "Lakh", "Cr", "%"]):
                            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        elif any(c in val for c in ["Nos", "Sets", "Units", "Job", "Lic"]):
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    @staticmethod
    def generate_compliance_matrix_docx(
        matrix: List[Dict[str, Any]],
        client_org: str = "Client Organization",
        project_title: str = "Turnkey Infrastructure Proposal"
    ) -> bytes:
        """Generates standalone Technical Compliance Matrix DOCX."""
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(0.7)
            section.bottom_margin = Inches(0.7)
            section.left_margin = Inches(0.7)
            section.right_margin = Inches(0.7)

        def set_bg(cell, hex_c):
            tcPr = cell._tc.get_or_add_tcPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'), hex_c)
            tcPr.append(shd)

        h1 = doc.add_heading("Technical Compliance Matrix", level=1)
        h1.runs[0].font.color.rgb = RGBColor(15, 41, 66)
        h1.runs[0].font.size = Pt(18)

        p = doc.add_paragraph(f"Project: {project_title} | Client: {client_org}")
        p.runs[0].font.color.rgb = RGBColor(71, 85, 105)
        p.runs[0].font.size = Pt(11)

        tbl = doc.add_table(rows=len(matrix) + 1, cols=4)
        tbl.style = 'Table Grid'
        headers = ["Clause / Parameter", "Tender Requirement", "Offered Nikom Specification", "Compliance"]
        for i, h in enumerate(headers):
            c = tbl.cell(0, i)
            c.text = h
            set_bg(c, "0F2942")
            p = c.paragraphs[0]
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
            p.runs[0].font.size = Pt(9.5)

        for r_idx, item in enumerate(matrix):
            c0 = tbl.cell(r_idx + 1, 0)
            c1 = tbl.cell(r_idx + 1, 1)
            c2 = tbl.cell(r_idx + 1, 2)
            c3 = tbl.cell(r_idx + 1, 3)

            c0.text = item.get("clause", f"CL-{r_idx+1}")
            c1.text = item.get("tender_requirement", "")
            c2.text = item.get("offered_specification", "")
            status = item.get("compliance_status", "Compliant")
            c3.text = status

            bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
            for c in [c0, c1, c2, c3]:
                set_bg(c, bg)
                c.paragraphs[0].runs[0].font.size = Pt(9)

            if "compliant" in status.lower():
                set_bg(c3, "ECFDF5")
                c3.paragraphs[0].runs[0].font.color.rgb = RGBColor(16, 185, 129)
                c3.paragraphs[0].runs[0].font.bold = True

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.getvalue()
