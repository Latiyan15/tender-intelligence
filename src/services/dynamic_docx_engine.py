"""
Dynamic Markdown-to-DOCX Engine
===============================
Converts arbitrary proposal Markdown into publication-grade,
executive Microsoft Word (.docx) documents matching Nikom's corporate standards.

Features:
- Geometric Minimalist Cover Page with Submission Metadata Table
- Executive Metric / Callout Boxes with Left Accent Border
- Formatted Headings with Nikom Navy (#0F2942) and Cyan (#0284C7)
- Styled Data & BOQ Tables with Zebra Striping and Total Highlights
- Authorized Signatory block at document end
"""

import io
import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from src.services.deliverable_cleaner import clean_deliverable_markdown

logger = logging.getLogger(__name__)

# Corporate Colors
C_NAVY = RGBColor(15, 41, 66)       # #0F2942 Primary
C_BLUE = RGBColor(37, 99, 235)      # #2563EB Primary Accent
C_CYAN = RGBColor(2, 132, 199)      # #0284C7 Secondary Accent
C_SLATE = RGBColor(71, 85, 105)     # #475569 Body Slate
C_DARK = RGBColor(30, 41, 59)       # #1E293B Dark Text
C_MUTED = RGBColor(100, 116, 139)   # #64748B Muted


def _set_cell_background(cell, hex_color: str):
    """Sets background shading of a docx table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def _set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell padding (in dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


class DynamicMarkdownDocxEngine:
    """Converts arbitrary proposal markdown into a styled .docx proposal."""

    def build_docx(self, markdown_text: str, project_meta: Optional[Dict[str, Any]] = None) -> bytes:
        project_meta = project_meta or {}
        cleaned = clean_deliverable_markdown(markdown_text)

        doc = Document()

        # Set 0.75-inch margins
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        title = project_meta.get("title") or "Technical Solution & Budgetary Commercial Offer"
        client_org = project_meta.get("client_org") or "Client / Buyer Authority"

        # Check for title in markdown if not provided
        lines = cleaned.split('\n')
        for line in lines[:8]:
            s = line.strip()
            if s.startswith('# '):
                title = s[2:].strip()
                if ":" in title and not project_meta.get("client_org"):
                    parts = title.split(":", 1)
                    title = parts[0].strip()
                    client_org = parts[1].strip()
                break

        # ── 1. COVER PAGE ───────────────────────────────────────────────────
        self._build_cover_page(doc, title, client_org)

        # ── 2. BODY CONTENT ─────────────────────────────────────────────────
        i = 0
        in_table = False
        table_lines = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Table detection
            if stripped.startswith('|') and stripped.endswith('|'):
                in_table = True
                table_lines.append(stripped)
                i += 1
                continue
            elif in_table:
                self._render_table(doc, table_lines)
                in_table = False
                table_lines = []

            # Blank lines
            if not stripped:
                i += 1
                continue

            # Skip top-level H1 (already rendered on cover page)
            if stripped.startswith('# '):
                i += 1
                continue

            # Horizontal rule
            if re.match(r'^(\-{3,}|\*{3,}|_{3,})$', stripped):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                # Bottom border line
                pBorder = OxmlElement('w:pBdr')
                bottom = OxmlElement('w:bottom')
                bottom.set(qn('w:val'), 'single')
                bottom.set(qn('w:sz'), '6')
                bottom.set(qn('w:space'), '1')
                bottom.set(qn('w:color'), 'CBD5E1')
                pBorder.append(bottom)
                p._p.get_or_add_pPr().append(pBorder)
                i += 1
                continue

            # Blockquote (> ...)
            if stripped.startswith('>'):
                callout_text = stripped.lstrip('> *').strip()
                self._render_callout(doc, callout_text)
                i += 1
                continue

            # Section headings
            if stripped.startswith('## '):
                h = doc.add_heading(level=1)
                h.paragraph_format.space_before = Pt(16)
                h.paragraph_format.space_after = Pt(6)
                h.paragraph_format.keep_with_next = True
                run = h.add_run(stripped[3:].strip())
                run.font.name = "Calibri"
                run.font.size = Pt(15)
                run.font.bold = True
                run.font.color.rgb = C_NAVY
                i += 1
                continue
            elif stripped.startswith('### '):
                h = doc.add_heading(level=2)
                h.paragraph_format.space_before = Pt(12)
                h.paragraph_format.space_after = Pt(4)
                h.paragraph_format.keep_with_next = True
                run = h.add_run(stripped[4:].strip())
                run.font.name = "Calibri"
                run.font.size = Pt(12.5)
                run.font.bold = True
                run.font.color.rgb = C_CYAN
                i += 1
                continue
            elif stripped.startswith('#### '):
                h = doc.add_heading(level=3)
                h.paragraph_format.space_before = Pt(8)
                h.paragraph_format.space_after = Pt(3)
                h.paragraph_format.keep_with_next = True
                run = h.add_run(stripped[5:].strip())
                run.font.name = "Calibri"
                run.font.size = Pt(11)
                run.font.bold = True
                run.font.color.rgb = C_DARK
                i += 1
                continue

            # Unordered lists (- , * , • )
            if re.match(r'^[\-\*\•]\s+', stripped):
                bullet_content = re.sub(r'^[\-\*\•]\s+', '', stripped)
                p = doc.add_paragraph(style='List Bullet')
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(3)
                self._add_formatted_runs(p, bullet_content)
                i += 1
                continue

            # Numbered lists (1. , 2. )
            if re.match(r'^\d+\.\s+', stripped):
                num_content = re.sub(r'^\d+\.\s+', '', stripped)
                p = doc.add_paragraph(style='List Number')
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(3)
                self._add_formatted_runs(p, num_content)
                i += 1
                continue

            # Standard paragraph
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(5)
            p.paragraph_format.line_spacing = 1.15
            self._add_formatted_runs(p, stripped)
            i += 1

        # Flush any trailing table
        if in_table and table_lines:
            self._render_table(doc, table_lines)

        # ── 3. AUTHORIZED SIGNATORY BLOCK ──────────────────────────────────
        self._build_signatory_block(doc)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.getvalue()

    def _build_cover_page(self, doc: Document, title: str, client_org: str):
        """Renders an authoritative corporate cover page."""
        # Top badge
        p_badge = doc.add_paragraph()
        p_badge.paragraph_format.space_before = Pt(40)
        p_badge.paragraph_format.space_after = Pt(4)
        run_badge = p_badge.add_run("NIKOM INFRASOLUTIONS PVT. LTD.")
        run_badge.font.name = "Calibri"
        run_badge.font.size = Pt(11)
        run_badge.font.bold = True
        run_badge.font.color.rgb = C_CYAN

        # Subtitle
        p_sub = doc.add_paragraph()
        p_sub.paragraph_format.space_after = Pt(16)
        r_sub = p_sub.add_run("PRE-SALES & MISSION-CRITICAL SOLUTIONS ENGINEERING DESK")
        r_sub.font.name = "Calibri"
        r_sub.font.size = Pt(9)
        r_sub.font.bold = True
        r_sub.font.color.rgb = C_MUTED

        # Main Title
        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_after = Pt(8)
        r_title = p_title.add_run(title)
        r_title.font.name = "Calibri"
        r_title.font.size = Pt(24)
        r_title.font.bold = True
        r_title.font.color.rgb = C_NAVY

        # Sub-heading
        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.space_after = Pt(120)
        r_desc = p_desc.add_run(f"Comprehensive Technical Architecture, Engineering Sizing & Budgetary Commercial Offer\nPrepared Exclusively for: {client_org}")
        r_desc.font.name = "Calibri"
        r_desc.font.size = Pt(11)
        r_desc.font.color.rgb = C_SLATE

        # Metadata Table
        meta_data = [
            ("SUBMITTED TO:", client_org),
            ("SUBMITTED BY:", "Nikom InfraSolutions Pvt. Ltd. • Turnkey Solutions Engineering"),
            ("DATE:", datetime.now().strftime("%d %B %Y")),
            ("DOCUMENT CLASSIFICATION:", "Official Tender Deliverable • Commercial & Technical Confidential"),
            ("AUTHORIZED CONTACT:", "B.S Kiran Kumar • Director, Solutions Engineering • tenders@nikom.in")
        ]

        table = doc.add_table(rows=len(meta_data), cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        col_widths = [Inches(2.2), Inches(4.8)]

        for r_idx, (lbl, val) in enumerate(meta_data):
            row = table.rows[r_idx]
            cell_lbl, cell_val = row.cells[0], row.cells[1]

            cell_lbl.width = col_widths[0]
            cell_val.width = col_widths[1]

            _set_cell_background(cell_lbl, "F1F5F9")
            _set_cell_background(cell_val, "F8FAFC")
            _set_cell_margins(cell_lbl, top=80, bottom=80, left=120, right=120)
            _set_cell_margins(cell_val, top=80, bottom=80, left=120, right=120)

            p0 = cell_lbl.paragraphs[0]
            p0.paragraph_format.space_before = Pt(2)
            p0.paragraph_format.space_after = Pt(2)
            r0 = p0.add_run(lbl)
            r0.font.name = "Calibri"
            r0.font.bold = True
            r0.font.size = Pt(8.5)
            r0.font.color.rgb = C_NAVY

            p1 = cell_val.paragraphs[0]
            p1.paragraph_format.space_before = Pt(2)
            p1.paragraph_format.space_after = Pt(2)
            r1 = p1.add_run(val)
            r1.font.name = "Calibri"
            r1.font.size = Pt(8.5)
            r1.font.color.rgb = C_DARK

        doc.add_page_break()

    def _render_callout(self, doc: Document, text: str):
        """Renders an executive callout box."""
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Inches(7.0)
        _set_cell_background(cell, "F8FAFC")
        _set_cell_margins(cell, top=100, bottom=100, left=160, right=140)

        # Left blue border
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        left = OxmlElement('w:left')
        left.set(qn('w:val'), 'single')
        left.set(qn('w:sz'), '24')  # 3pt
        left.set(qn('w:color'), '0284C7')
        tcBorders.append(left)
        for b_name in ['top', 'bottom', 'right']:
            b = OxmlElement(f'w:{b_name}')
            b.set(qn('w:val'), 'none')
            tcBorders.append(b)
        tcPr.append(tcBorders)

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        self._add_formatted_runs(p, text)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def _render_table(self, doc: Document, table_lines: List[str]):
        """Parses markdown table lines and renders a styled docx table."""
        if len(table_lines) < 2:
            return

        headers = [c.strip() for c in table_lines[0].split('|')[1:-1]]
        data_rows = []
        for line in table_lines[1:]:
            if re.match(r'^\s*\|?\s*[\:\-\|\s]+\s*\|?\s*$', line):
                continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                data_rows.append(cells)

        if not headers or not data_rows:
            return

        num_cols = len(headers)
        tbl = doc.add_table(rows=len(data_rows) + 1, cols=num_cols)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = True

        # Header Row
        for col_idx, h_text in enumerate(headers):
            cell = tbl.cell(0, col_idx)
            _set_cell_background(cell, "0F2942")
            _set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            clean_h = re.sub(r'\*\*([^*]+)\*\*', r'\1', h_text)
            r = p.add_run(clean_h)
            r.font.name = "Calibri"
            r.font.bold = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(255, 255, 255)
            if col_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif any(w in clean_h.lower() for w in ['amount', 'price', 'rate', 'cost', 'total', '₹', 'rs']):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        # Data Rows
        for r_idx, row_cells in enumerate(data_rows):
            is_total_row = any(
                w in ' '.join(row_cells).lower()
                for w in ['total', 'subtotal', 'gst @', 'grand total']
            )

            for col_idx in range(num_cols):
                cell = tbl.cell(r_idx + 1, col_idx)
                val = row_cells[col_idx] if col_idx < len(row_cells) else ""
                clean_val = re.sub(r'\*\*([^*]+)\*\*', r'\1', val)

                # Shading
                if is_total_row:
                    _set_cell_background(cell, "EFF6FF")  # Soft blue highlight
                elif r_idx % 2 == 1:
                    _set_cell_background(cell, "F8FAFC")
                else:
                    _set_cell_background(cell, "FFFFFF")

                _set_cell_margins(cell, top=70, bottom=70, left=90, right=90)

                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                r = p.add_run(clean_val)
                r.font.name = "Calibri"
                r.font.size = Pt(8.5)

                if is_total_row:
                    r.font.bold = True
                    r.font.color.rgb = C_BLUE
                else:
                    r.font.color.rgb = C_DARK

                # Alignment
                if any(c in clean_val for c in ['₹', 'Rs.', 'Lakh', 'Cr']) or re.match(r'^\s*[\d,.]+\s*$', clean_val):
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif clean_val.lower() in ['compliant', 'conforming', 'yes', 'verified']:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r.font.color.rgb = RGBColor(16, 185, 129)
                    r.font.bold = True
                elif col_idx == 0 and len(clean_val) <= 4:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    def _build_signatory_block(self, doc: Document):
        """Appends the official Nikom authorized signatory block."""
        tbl = doc.add_table(rows=1, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False

        c0, c1 = tbl.cell(0, 0), tbl.cell(0, 1)
        c0.width = Inches(3.5)
        c1.width = Inches(3.5)

        for c in [c0, c1]:
            _set_cell_background(c, "F8FAFC")
            _set_cell_margins(c, top=100, bottom=100, left=140, right=140)

        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run("SUBMITTED ON BEHALF OF:\n")
        r0.font.bold = True
        r0.font.size = Pt(8.5)
        r0.font.color.rgb = C_NAVY

        r0_body = p0.add_run("Nikom InfraSolutions Pvt. Ltd.\nE-48/3, Okhla Industrial Area Phase-II, New Delhi — 110020\nCIN: U72900DL2000PTC105284 • GSTIN: 07AAACN1234F1Z1")
        r0_body.font.size = Pt(8)
        r0_body.font.color.rgb = C_SLATE

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(2)
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run("AUTHORIZED SIGNATORY:\n\n____________________________________\n")
        r1.font.bold = True
        r1.font.size = Pt(8.5)
        r1.font.color.rgb = C_NAVY

        r1_body = p1.add_run("B.S Kiran Kumar • Director, Solutions Engineering\nEmail: tenders@nikom.in • Web: www.nikom.in")
        r1_body.font.size = Pt(8)
        r1_body.font.color.rgb = C_SLATE

    def _add_formatted_runs(self, paragraph, text: str):
        """Parses inline bold (**text**) and renders runs."""
        parts = re.split(r'(\*\*[^*]+\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                r = paragraph.add_run(part[2:-2])
                r.font.name = "Calibri"
                r.font.bold = True
                r.font.size = Pt(9.5)
                r.font.color.rgb = C_DARK
            elif part:
                r = paragraph.add_run(part)
                r.font.name = "Calibri"
                r.font.size = Pt(9.5)
                r.font.color.rgb = C_SLATE


dynamic_docx_engine = DynamicMarkdownDocxEngine()

