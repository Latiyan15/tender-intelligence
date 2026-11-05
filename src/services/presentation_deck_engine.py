"""
Nikom Presentation Deck Engine v2
==================================
A professional, fully dynamic PPTX generator that accepts Claude-designed
slide specifications and renders them into executive-grade presentation decks.

Every slide is dynamic — no hardcoded content. Claude decides what goes on each slide.

Supports slide layouts:
  cover, executive_summary, content, two_column, table, comparison,
  architecture, timeline, credentials, closing
"""

import re
import io
import logging
from typing import List, Dict, Any, Optional, Tuple
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

logger = logging.getLogger(__name__)

# ─── Corporate Color Palette ────────────────────────────────────────────────
NAVY        = RGBColor(0x0F, 0x29, 0x42)
NAVY_DARK   = RGBColor(0x09, 0x1B, 0x2E)
BLUE        = RGBColor(0x25, 0x63, 0xEB)
BLUE_LIGHT  = RGBColor(0x3B, 0x82, 0xF6)
CYAN        = RGBColor(0x06, 0xB6, 0xD4)
TEAL        = RGBColor(0x14, 0xB8, 0xA6)
GREEN       = RGBColor(0x10, 0xB9, 0x81)
AMBER       = RGBColor(0xF5, 0x9E, 0x0B)
CORAL       = RGBColor(0xEF, 0x44, 0x44)
PURPLE      = RGBColor(0x7C, 0x3A, 0xED)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
NEAR_WHITE  = RGBColor(0xF8, 0xFA, 0xFC)
SLATE_50    = RGBColor(0xF1, 0xF5, 0xF9)
SLATE_100   = RGBColor(0xE2, 0xE8, 0xF0)
SLATE_200   = RGBColor(0xCB, 0xD5, 0xE1)
SLATE_300   = RGBColor(0x94, 0xA3, 0xB8)
SLATE_500   = RGBColor(0x64, 0x74, 0x8B)
SLATE_700   = RGBColor(0x33, 0x41, 0x55)
DARK        = RGBColor(0x0F, 0x17, 0x2A)
DARK_TEXT   = RGBColor(0x1E, 0x29, 0x3B)

# Accent color pool for variety
ACCENT_COLORS = [BLUE, CYAN, TEAL, GREEN, PURPLE, AMBER]

# ─── Typography ──────────────────────────────────────────────────────────────
FONT_PRIMARY   = "Calibri"
FONT_HEADING   = "Calibri"
FONT_MONO      = "Consolas"

# ─── Slide dimensions (16:9) ────────────────────────────────────────────────
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _hex_to_rgb(hex_str: str) -> RGBColor:
    """Convert '#RRGGBB' to RGBColor."""
    h = hex_str.lstrip('#')
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _add_rounded_rect(slide, left, top, width, height, fill_color, border_color=None, border_width=Pt(0.75)):
    """Add a rounded rectangle shape with optional border."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = border_width
    else:
        shape.line.fill.background()
    # Adjust corner radius
    try:
        shape.adjustments[0] = 0.06
    except Exception:
        pass
    return shape


def _add_rect(slide, left, top, width, height, fill_color):
    """Add a plain rectangle shape."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape


def _add_text_box(slide, left, top, width, height, text, font_size=Pt(12),
                  font_color=DARK_TEXT, bold=False, italic=False,
                  alignment=PP_ALIGN.LEFT, font_name=FONT_PRIMARY,
                  anchor=MSO_ANCHOR.TOP, line_spacing=1.15):
    """Add a text box with consistent styling."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = False
    try:
        tf.paragraphs[0].space_before = Pt(0)
        tf.paragraphs[0].space_after = Pt(0)
    except Exception:
        pass
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = font_size
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.font.italic = italic
    p.font.name = font_name
    p.alignment = alignment
    p.line_spacing = Pt(int(font_size.pt * line_spacing)) if hasattr(font_size, 'pt') else None
    try:
        txBox.text_frame.paragraphs[0].space_before = Pt(0)
    except Exception:
        pass
    return txBox


def _add_multiline_text(slide, left, top, width, height, lines: List[Dict],
                        anchor=MSO_ANCHOR.TOP):
    """Add a text box with multiple formatted paragraphs.
    lines: [{"text": "...", "size": Pt(12), "color": DARK, "bold": False, "bullet": False, "spacing_after": Pt(4)}]
    """
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = False

    for i, line_spec in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        text = line_spec.get("text", "")
        if line_spec.get("bullet"):
            text = f"•  {text}"

        p.text = text
        p.font.size = line_spec.get("size", Pt(11))
        p.font.color.rgb = line_spec.get("color", DARK_TEXT)
        p.font.bold = line_spec.get("bold", False)
        p.font.italic = line_spec.get("italic", False)
        p.font.name = line_spec.get("font", FONT_PRIMARY)
        p.alignment = line_spec.get("align", PP_ALIGN.LEFT)
        p.space_after = line_spec.get("spacing_after", Pt(4))
        p.space_before = line_spec.get("spacing_before", Pt(0))

    return txBox


def _add_slide_number(slide, slide_num: int, total: int):
    """Add slide number to bottom-right."""
    _add_text_box(
        slide,
        left=SLIDE_W - Inches(1.2),
        top=SLIDE_H - Inches(0.45),
        width=Inches(1.0),
        height=Inches(0.3),
        text=f"{slide_num} / {total}",
        font_size=Pt(8),
        font_color=SLATE_300,
        alignment=PP_ALIGN.RIGHT
    )


def _add_brand_footer(slide, slide_num: int, total: int):
    """Add consistent branded footer bar to a slide."""
    # Thin line
    _add_rect(slide, Inches(0.6), SLIDE_H - Inches(0.55), SLIDE_W - Inches(1.2), Pt(0.75), SLATE_200)
    # Company name
    _add_text_box(
        slide,
        left=Inches(0.6),
        top=SLIDE_H - Inches(0.48),
        width=Inches(6),
        height=Inches(0.35),
        text="Nikom InfraSolutions Pvt. Ltd.  •  Commercial & Technical Confidential",
        font_size=Pt(7.5),
        font_color=SLATE_300,
        alignment=PP_ALIGN.LEFT
    )
    _add_slide_number(slide, slide_num, total)


# ═══════════════════════════════════════════════════════════════════════════════
#  SLIDE RENDERERS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_cover(prs, spec: Dict, total_slides: int):
    """Render an executive cover slide with full-bleed navy background."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Full navy background
    _add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, NAVY)

    # Blue accent bar (left edge)
    _add_rect(slide, 0, 0, Inches(0.12), SLIDE_H, BLUE)

    # Company badge
    _add_text_box(
        slide, Inches(0.8), Inches(0.6), Inches(8), Inches(0.5),
        "NIKOM INFRASOLUTIONS PVT. LTD.",
        font_size=Pt(11), font_color=SLATE_300, bold=True,
        font_name=FONT_HEADING
    )

    # Decorative line under badge
    _add_rect(slide, Inches(0.8), Inches(1.15), Inches(2.5), Pt(2.5), BLUE)

    # Main title
    title = spec.get("title", "Technical Solution & Budgetary Offer")
    _add_text_box(
        slide, Inches(0.8), Inches(1.6), Inches(11), Inches(1.8),
        title,
        font_size=Pt(32), font_color=WHITE, bold=True,
        font_name=FONT_HEADING, line_spacing=1.2
    )

    # Subtitle
    subtitle = spec.get("subtitle", "")
    if subtitle:
        _add_text_box(
            slide, Inches(0.8), Inches(3.4), Inches(10), Inches(0.7),
            subtitle,
            font_size=Pt(16), font_color=SLATE_200, italic=True
        )

    # Metadata card (bottom-left)
    meta_items = spec.get("metadata", [])
    if meta_items:
        card_top = Inches(4.5)
        _add_rounded_rect(slide, Inches(0.8), card_top, Inches(7), Inches(2.2),
                          NAVY_DARK, border_color=SLATE_700)
        lines = []
        for item in meta_items[:6]:
            label = item.get("label", "")
            value = item.get("value", "")
            lines.append({"text": f"{label}:  {value}", "size": Pt(11),
                          "color": SLATE_200, "bold": False, "spacing_after": Pt(6)})
        _add_multiline_text(slide, Inches(1.1), card_top + Inches(0.2),
                            Inches(6.5), Inches(1.9), lines)

    # Date (bottom-right)
    date_text = spec.get("date", "")
    if date_text:
        _add_text_box(
            slide, SLIDE_W - Inches(3.5), SLIDE_H - Inches(0.8),
            Inches(3), Inches(0.4),
            date_text,
            font_size=Pt(10), font_color=SLATE_300, alignment=PP_ALIGN.RIGHT
        )

    # Slide number
    _add_text_box(
        slide, SLIDE_W - Inches(1.2), SLIDE_H - Inches(0.45),
        Inches(1.0), Inches(0.3),
        f"1 / {total_slides}",
        font_size=Pt(8), font_color=SLATE_500, alignment=PP_ALIGN.RIGHT
    )


def _render_executive_summary(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render KPI dashboard + narrative summary slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    title = spec.get("title", "Executive Summary")
    _add_text_box(
        slide, Inches(0.6), Inches(0.3), Inches(10), Inches(0.5),
        title,
        font_size=Pt(22), font_color=NAVY, bold=True, font_name=FONT_HEADING
    )
    # Accent underline
    _add_rect(slide, Inches(0.6), Inches(0.85), Inches(1.5), Pt(3), BLUE)

    # KPI Cards
    kpis = spec.get("kpis", [])
    if kpis:
        card_count = min(len(kpis), 5)
        total_width = SLIDE_W - Inches(1.2)
        gap = Inches(0.15)
        card_w = (total_width - gap * (card_count - 1)) / card_count
        card_h = Inches(1.25)
        card_top = Inches(1.15)

        for i, kpi in enumerate(kpis[:card_count]):
            accent = ACCENT_COLORS[i % len(ACCENT_COLORS)]
            card_left = Inches(0.6) + i * (card_w + gap)

            # Card background
            _add_rounded_rect(slide, int(card_left), int(card_top), int(card_w), int(card_h),
                              NEAR_WHITE, border_color=SLATE_200)
            # Top accent bar
            _add_rect(slide, int(card_left), int(card_top), int(card_w), Pt(3.5), accent)

            # KPI value
            _add_text_box(
                slide, int(card_left) + Inches(0.15), int(card_top) + Inches(0.18),
                int(card_w) - Inches(0.3), Inches(0.5),
                str(kpi.get("value", "")),
                font_size=Pt(20), font_color=NAVY, bold=True,
                alignment=PP_ALIGN.CENTER
            )
            # KPI label
            _add_text_box(
                slide, int(card_left) + Inches(0.1), int(card_top) + Inches(0.72),
                int(card_w) - Inches(0.2), Inches(0.45),
                str(kpi.get("label", "")),
                font_size=Pt(8.5), font_color=SLATE_500,
                alignment=PP_ALIGN.CENTER
            )

    # Narrative section
    narrative_lines = spec.get("narrative", [])
    if narrative_lines:
        narr_top = Inches(2.7)
        # Left accent bar
        _add_rect(slide, Inches(0.6), narr_top, Pt(4), Inches(4.0), CYAN)

        lines = []
        for item in narrative_lines:
            if isinstance(item, str):
                lines.append({"text": item, "size": Pt(12), "color": DARK_TEXT,
                              "bullet": True, "spacing_after": Pt(8)})
            elif isinstance(item, dict):
                lines.append({
                    "text": item.get("text", ""),
                    "size": Pt(item.get("size", 12)),
                    "color": _hex_to_rgb(item["color"]) if "color" in item else DARK_TEXT,
                    "bold": item.get("bold", False),
                    "bullet": item.get("bullet", True),
                    "spacing_after": Pt(item.get("spacing", 8))
                })

        _add_multiline_text(slide, Inches(0.95), narr_top + Inches(0.1),
                            Inches(11.5), Inches(3.8), lines)

    _add_brand_footer(slide, slide_num, total_slides)


def _render_content(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render a standard content slide with title and bullet points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    title = spec.get("title", "")
    _add_text_box(
        slide, Inches(0.6), Inches(0.3), Inches(11), Inches(0.5),
        title,
        font_size=Pt(22), font_color=NAVY, bold=True, font_name=FONT_HEADING
    )
    _add_rect(slide, Inches(0.6), Inches(0.85), Inches(1.5), Pt(3), BLUE)

    subtitle = spec.get("subtitle", "")
    if subtitle:
        _add_text_box(
            slide, Inches(0.6), Inches(0.95), Inches(11), Inches(0.4),
            subtitle,
            font_size=Pt(12), font_color=SLATE_500, italic=True
        )

    # Content bullets
    bullets = spec.get("bullets", [])
    if bullets:
        lines = []
        for b in bullets:
            if isinstance(b, str):
                lines.append({"text": b, "size": Pt(13), "color": DARK_TEXT,
                              "bullet": True, "spacing_after": Pt(10)})
            elif isinstance(b, dict):
                # Heading bullet
                if b.get("heading"):
                    lines.append({"text": b["heading"], "size": Pt(14), "color": NAVY,
                                  "bold": True, "spacing_after": Pt(3), "spacing_before": Pt(12)})
                if b.get("text"):
                    lines.append({"text": b["text"], "size": Pt(12), "color": DARK_TEXT,
                                  "bullet": True, "spacing_after": Pt(8)})

        content_top = Inches(1.4) if not subtitle else Inches(1.55)
        _add_multiline_text(slide, Inches(0.8), content_top,
                            Inches(11.5), Inches(5.2), lines)

    # Optional callout box
    callout = spec.get("callout", "")
    if callout:
        callout_top = SLIDE_H - Inches(1.6)
        _add_rounded_rect(slide, Inches(0.6), callout_top,
                          SLIDE_W - Inches(1.2), Inches(0.85),
                          SLATE_50, border_color=BLUE_LIGHT)
        _add_rect(slide, Inches(0.6), callout_top, Pt(4), Inches(0.85), BLUE)
        _add_text_box(
            slide, Inches(0.95), callout_top + Inches(0.12),
            SLIDE_W - Inches(1.8), Inches(0.6),
            callout,
            font_size=Pt(11), font_color=DARK_TEXT, italic=True
        )

    _add_brand_footer(slide, slide_num, total_slides)


def _render_two_column(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render a two-column layout with cards."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    title = spec.get("title", "")
    _add_text_box(
        slide, Inches(0.6), Inches(0.3), Inches(11), Inches(0.5),
        title,
        font_size=Pt(22), font_color=NAVY, bold=True, font_name=FONT_HEADING
    )
    _add_rect(slide, Inches(0.6), Inches(0.85), Inches(1.5), Pt(3), BLUE)

    left_col = spec.get("left", {})
    right_col = spec.get("right", {})
    col_w = Inches(5.85)
    col_h = Inches(5.3)
    col_top = Inches(1.2)

    for idx, col_spec in enumerate([left_col, right_col]):
        col_left = Inches(0.6) if idx == 0 else Inches(6.85)
        accent = ACCENT_COLORS[idx % len(ACCENT_COLORS)]

        # Column card
        _add_rounded_rect(slide, col_left, col_top, col_w, col_h,
                          NEAR_WHITE, border_color=SLATE_200)
        # Accent top bar
        _add_rect(slide, col_left, col_top, col_w, Pt(4), accent)

        # Column heading
        col_title = col_spec.get("title", "")
        _add_text_box(
            slide, col_left + Inches(0.2), col_top + Inches(0.2),
            col_w - Inches(0.4), Inches(0.4),
            col_title,
            font_size=Pt(15), font_color=NAVY, bold=True
        )

        # Column bullets
        col_bullets = col_spec.get("bullets", [])
        lines = []
        for b in col_bullets:
            if isinstance(b, str):
                lines.append({"text": b, "size": Pt(11), "color": DARK_TEXT,
                              "bullet": True, "spacing_after": Pt(6)})
            elif isinstance(b, dict):
                lines.append({
                    "text": b.get("text", ""),
                    "size": Pt(b.get("size", 11)),
                    "color": DARK_TEXT,
                    "bold": b.get("bold", False),
                    "bullet": True,
                    "spacing_after": Pt(6)
                })

        if lines:
            _add_multiline_text(slide, col_left + Inches(0.2), col_top + Inches(0.7),
                                col_w - Inches(0.4), col_h - Inches(0.9), lines)

    _add_brand_footer(slide, slide_num, total_slides)


def _render_table(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render a professional data table slide (BOQ, compliance matrix, etc.)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    title = spec.get("title", "")
    _add_text_box(
        slide, Inches(0.6), Inches(0.3), Inches(11), Inches(0.5),
        title,
        font_size=Pt(22), font_color=NAVY, bold=True, font_name=FONT_HEADING
    )
    _add_rect(slide, Inches(0.6), Inches(0.85), Inches(1.5), Pt(3), BLUE)

    headers = spec.get("headers", [])
    rows = spec.get("rows", [])

    if not headers or not rows:
        _add_text_box(
            slide, Inches(0.8), Inches(2), Inches(11), Inches(1),
            "No table data provided.",
            font_size=Pt(14), font_color=SLATE_500, italic=True
        )
        _add_brand_footer(slide, slide_num, total_slides)
        return

    num_cols = len(headers)
    num_rows = min(len(rows), 14)  # Cap at 14 data rows per slide
    table_w = SLIDE_W - Inches(1.0)
    row_h = Inches(0.34)
    table_h = row_h * (num_rows + 1)
    table_left = Inches(0.5)
    table_top = Inches(1.15)

    tbl = slide.shapes.add_table(
        num_rows + 1, num_cols, table_left, table_top, int(table_w), int(table_h)
    ).table

    # Column widths - auto distribute but give more space to description columns
    for ci in range(num_cols):
        header_lower = headers[ci].lower()
        if any(w in header_lower for w in ["description", "scope", "item", "specification"]):
            tbl.columns[ci].width = int(table_w * 0.38)
        elif any(w in header_lower for w in ["amount", "total", "cost", "rate", "price"]):
            tbl.columns[ci].width = int(table_w * 0.14)
        elif any(w in header_lower for w in ["sl", "#", "no", "pkg"]):
            tbl.columns[ci].width = int(table_w * 0.06)
        elif any(w in header_lower for w in ["qty", "quantity", "unit"]):
            tbl.columns[ci].width = int(table_w * 0.07)

    # Style header row
    for ci, header in enumerate(headers):
        cell = tbl.cell(0, ci)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(9)
            p.font.bold = True
            p.font.color.rgb = WHITE
            p.font.name = FONT_PRIMARY
            p.alignment = PP_ALIGN.CENTER

    # Style data rows
    for ri, row in enumerate(rows[:num_rows]):
        is_total_row = False
        row_text = " ".join(str(c) for c in row).lower()
        if any(w in row_text for w in ["subtotal", "total", "grand total", "gst"]):
            is_total_row = True

        for ci in range(num_cols):
            cell = tbl.cell(ri + 1, ci)
            cell_val = str(row[ci]) if ci < len(row) else ""
            cell.text = cell_val.strip()

            # Background
            if is_total_row:
                cell.fill.solid()
                cell.fill.fore_color.rgb = SLATE_50
            elif ri % 2 == 1:
                cell.fill.solid()
                cell.fill.fore_color.rgb = NEAR_WHITE
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE

            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(8.5) if not is_total_row else Pt(9)
                p.font.bold = is_total_row
                p.font.color.rgb = BLUE if is_total_row else DARK_TEXT
                p.font.name = FONT_PRIMARY
                # Right-align amount columns
                header_lower = headers[ci].lower() if ci < len(headers) else ""
                if any(w in header_lower for w in ["amount", "total", "cost", "rate", "price"]):
                    p.alignment = PP_ALIGN.RIGHT
                elif any(w in header_lower for w in ["sl", "#", "qty", "unit", "no"]):
                    p.alignment = PP_ALIGN.CENTER
                else:
                    p.alignment = PP_ALIGN.LEFT

    # Table caption
    caption = spec.get("caption", "")
    if caption:
        _add_text_box(
            slide, Inches(0.6), table_top + table_h + Inches(0.15),
            Inches(11), Inches(0.35),
            caption,
            font_size=Pt(9), font_color=SLATE_500, italic=True
        )

    _add_brand_footer(slide, slide_num, total_slides)


def _render_comparison(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render a Before vs After or Option A vs Option B comparison slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    title = spec.get("title", "Comparison")
    _add_text_box(
        slide, Inches(0.6), Inches(0.3), Inches(11), Inches(0.5),
        title,
        font_size=Pt(22), font_color=NAVY, bold=True, font_name=FONT_HEADING
    )
    _add_rect(slide, Inches(0.6), Inches(0.85), Inches(1.5), Pt(3), BLUE)

    items = spec.get("items", [])
    count = min(len(items), 4)
    if count == 0:
        _add_brand_footer(slide, slide_num, total_slides)
        return

    total_w = SLIDE_W - Inches(1.2)
    gap = Inches(0.2)
    card_w = (total_w - gap * (count - 1)) / count
    card_h = Inches(5.3)
    card_top = Inches(1.2)

    for i, item in enumerate(items[:count]):
        accent = ACCENT_COLORS[i % len(ACCENT_COLORS)]
        card_left = Inches(0.6) + i * (card_w + gap)

        # Card
        _add_rounded_rect(slide, int(card_left), int(card_top), int(card_w), int(card_h),
                          WHITE, border_color=SLATE_200)

        # Header bar
        _add_rect(slide, int(card_left), int(card_top), int(card_w), Inches(0.5), accent)

        # Card title
        card_title = item.get("title", f"Option {i+1}")
        _add_text_box(
            slide, int(card_left) + Inches(0.15), int(card_top) + Inches(0.08),
            int(card_w) - Inches(0.3), Inches(0.35),
            card_title,
            font_size=Pt(13), font_color=WHITE, bold=True,
            alignment=PP_ALIGN.CENTER
        )

        # Card bullets
        bullets = item.get("bullets", [])
        lines = []
        for b in bullets:
            if isinstance(b, str):
                lines.append({"text": b, "size": Pt(10.5), "color": DARK_TEXT,
                              "bullet": True, "spacing_after": Pt(6)})
            elif isinstance(b, dict):
                lines.append({"text": b.get("text", ""), "size": Pt(b.get("size", 10.5)),
                              "color": DARK_TEXT, "bold": b.get("bold", False),
                              "bullet": True, "spacing_after": Pt(6)})

        if lines:
            _add_multiline_text(slide, int(card_left) + Inches(0.15),
                                int(card_top) + Inches(0.65),
                                int(card_w) - Inches(0.3), card_h - Inches(0.9), lines)

    _add_brand_footer(slide, slide_num, total_slides)


def _render_timeline(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render a horizontal timeline / roadmap slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    title = spec.get("title", "Implementation Roadmap")
    _add_text_box(
        slide, Inches(0.6), Inches(0.3), Inches(11), Inches(0.5),
        title,
        font_size=Pt(22), font_color=NAVY, bold=True, font_name=FONT_HEADING
    )
    _add_rect(slide, Inches(0.6), Inches(0.85), Inches(1.5), Pt(3), BLUE)

    phases = spec.get("phases", [])
    count = min(len(phases), 6)
    if count == 0:
        _add_brand_footer(slide, slide_num, total_slides)
        return

    # Timeline bar
    bar_top = Inches(2.0)
    bar_left = Inches(1.0)
    bar_right = SLIDE_W - Inches(1.0)
    bar_w = bar_right - bar_left
    _add_rect(slide, bar_left, bar_top + Inches(0.15), int(bar_w), Pt(4), BLUE)

    phase_w = bar_w / count
    for i, phase in enumerate(phases[:count]):
        accent = ACCENT_COLORS[i % len(ACCENT_COLORS)]
        cx = bar_left + phase_w * i + phase_w / 2

        # Circle marker
        circle_size = Inches(0.35)
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            int(cx - circle_size / 2), int(bar_top),
            int(circle_size), int(circle_size)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = accent
        circle.line.fill.background()

        # Phase label (above)
        phase_label = phase.get("label", f"Phase {i+1}")
        _add_text_box(
            slide, int(cx - Inches(1.2)), bar_top - Inches(0.65),
            Inches(2.4), Inches(0.5),
            phase_label,
            font_size=Pt(11), font_color=NAVY, bold=True,
            alignment=PP_ALIGN.CENTER
        )

        # Duration (small text above label)
        duration = phase.get("duration", "")
        if duration:
            _add_text_box(
                slide, int(cx - Inches(1)), bar_top - Inches(0.95),
                Inches(2), Inches(0.3),
                duration,
                font_size=Pt(8.5), font_color=accent, bold=True,
                alignment=PP_ALIGN.CENTER
            )

        # Details card below timeline
        details = phase.get("details", [])
        if details:
            card_top = bar_top + Inches(0.7)
            card_w_phase = phase_w - Inches(0.2)
            card_left = bar_left + phase_w * i + Inches(0.1)

            _add_rounded_rect(slide, int(card_left), int(card_top),
                              int(card_w_phase), Inches(3.5),
                              NEAR_WHITE, border_color=SLATE_200)
            _add_rect(slide, int(card_left), int(card_top),
                      int(card_w_phase), Pt(3), accent)

            lines = []
            for d in details[:8]:
                lines.append({"text": d, "size": Pt(9), "color": DARK_TEXT,
                              "bullet": True, "spacing_after": Pt(4)})
            _add_multiline_text(slide, int(card_left) + Inches(0.1),
                                int(card_top) + Inches(0.15),
                                int(card_w_phase) - Inches(0.2), Inches(3.2), lines)

    _add_brand_footer(slide, slide_num, total_slides)


def _render_credentials(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render company credentials / why-us slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    title = spec.get("title", "Nikom InfraSolutions — Verified Credentials")
    _add_text_box(
        slide, Inches(0.6), Inches(0.3), Inches(11), Inches(0.5),
        title,
        font_size=Pt(22), font_color=NAVY, bold=True, font_name=FONT_HEADING
    )
    _add_rect(slide, Inches(0.6), Inches(0.85), Inches(1.5), Pt(3), BLUE)

    cards = spec.get("cards", [])
    count = min(len(cards), 8)

    # Grid layout: 2 rows x 4 cols (or adjust)
    cols = min(count, 4)
    rows_count = (count + cols - 1) // cols
    card_gap = Inches(0.2)
    total_w = SLIDE_W - Inches(1.2)
    card_w = (total_w - card_gap * (cols - 1)) / cols
    card_h = Inches(2.2)

    for i, card in enumerate(cards[:count]):
        row = i // cols
        col = i % cols
        accent = ACCENT_COLORS[i % len(ACCENT_COLORS)]

        card_left = Inches(0.6) + col * (card_w + card_gap)
        card_top = Inches(1.2) + row * (card_h + card_gap)

        _add_rounded_rect(slide, int(card_left), int(card_top), int(card_w), int(card_h),
                          WHITE, border_color=SLATE_200)
        _add_rect(slide, int(card_left), int(card_top), int(card_w), Pt(4), accent)

        # Metric value
        metric = card.get("metric", "")
        _add_text_box(
            slide, int(card_left) + Inches(0.15), int(card_top) + Inches(0.2),
            int(card_w) - Inches(0.3), Inches(0.55),
            metric,
            font_size=Pt(22), font_color=NAVY, bold=True,
            alignment=PP_ALIGN.CENTER
        )

        # Label
        label = card.get("label", "")
        _add_text_box(
            slide, int(card_left) + Inches(0.1), int(card_top) + Inches(0.8),
            int(card_w) - Inches(0.2), Inches(0.35),
            label,
            font_size=Pt(10), font_color=SLATE_500, bold=True,
            alignment=PP_ALIGN.CENTER
        )

        # Description
        desc = card.get("description", "")
        if desc:
            _add_text_box(
                slide, int(card_left) + Inches(0.1), int(card_top) + Inches(1.2),
                int(card_w) - Inches(0.2), Inches(0.8),
                desc,
                font_size=Pt(8.5), font_color=SLATE_700,
                alignment=PP_ALIGN.CENTER
            )

    _add_brand_footer(slide, slide_num, total_slides)


def _render_closing(prs, spec: Dict, slide_num: int, total_slides: int):
    """Render a professional closing / thank-you slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Full navy background
    _add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, NAVY)
    _add_rect(slide, 0, 0, Inches(0.12), SLIDE_H, BLUE)

    # Thank you text
    heading = spec.get("heading", "Thank You")
    _add_text_box(
        slide, Inches(0.8), Inches(1.5), Inches(11), Inches(1.2),
        heading,
        font_size=Pt(40), font_color=WHITE, bold=True,
        font_name=FONT_HEADING, alignment=PP_ALIGN.LEFT
    )

    # Decorative line
    _add_rect(slide, Inches(0.8), Inches(3.0), Inches(3), Pt(3), BLUE)

    # Message
    message = spec.get("message", "We look forward to partnering with you on this project.")
    _add_text_box(
        slide, Inches(0.8), Inches(3.3), Inches(10), Inches(0.8),
        message,
        font_size=Pt(16), font_color=SLATE_200, italic=True
    )

    # Contact card
    contact_lines = spec.get("contact", [])
    if contact_lines:
        card_top = Inches(4.5)
        _add_rounded_rect(slide, Inches(0.8), card_top, Inches(6), Inches(2.2),
                          NAVY_DARK, border_color=SLATE_700)
        lines = []
        for cl in contact_lines:
            lines.append({"text": cl, "size": Pt(11), "color": SLATE_200,
                          "spacing_after": Pt(6)})
        _add_multiline_text(slide, Inches(1.1), card_top + Inches(0.2),
                            Inches(5.6), Inches(1.9), lines)

    _add_text_box(
        slide, SLIDE_W - Inches(1.2), SLIDE_H - Inches(0.45),
        Inches(1.0), Inches(0.3),
        f"{slide_num} / {total_slides}",
        font_size=Pt(8), font_color=SLATE_500, alignment=PP_ALIGN.RIGHT
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

LAYOUT_RENDERERS = {
    "cover": _render_cover,
    "executive_summary": _render_executive_summary,
    "content": _render_content,
    "two_column": _render_two_column,
    "table": _render_table,
    "comparison": _render_comparison,
    "timeline": _render_timeline,
    "credentials": _render_credentials,
    "closing": _render_closing,
}


class PresentationDeckEngine:
    """
    Renders Claude-designed slide specifications into professional PPTX decks.
    
    Usage:
        engine = PresentationDeckEngine()
        pptx_bytes = engine.build_from_slides(slides=[
            {"layout": "cover", "title": "...", "metadata": [...]},
            {"layout": "executive_summary", "kpis": [...], "narrative": [...]},
            {"layout": "table", "title": "BOQ", "headers": [...], "rows": [...]},
            ...
        ])
    """

    def build_from_slides(self, slides: List[Dict[str, Any]]) -> bytes:
        """Build a complete PPTX from a list of slide specifications."""
        prs = Presentation()
        prs.slide_width = SLIDE_W
        prs.slide_height = SLIDE_H

        total_slides = len(slides)

        for i, slide_spec in enumerate(slides):
            layout = slide_spec.get("layout", "content")
            renderer = LAYOUT_RENDERERS.get(layout)

            if renderer is None:
                logger.warning(f"Unknown slide layout '{layout}', falling back to content")
                renderer = _render_content

            try:
                if layout == "cover":
                    renderer(prs, slide_spec, total_slides)
                else:
                    renderer(prs, slide_spec, i + 1, total_slides)
            except Exception as e:
                logger.error(f"Error rendering slide {i+1} ({layout}): {e}", exc_info=True)
                # Add error placeholder slide
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                _add_text_box(slide, Inches(1), Inches(3), Inches(10), Inches(1),
                              f"Slide rendering error: {e}",
                              font_size=Pt(14), font_color=CORAL)

        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.read()

    def build_presentation(self, markdown: str, project_meta: Optional[Dict] = None) -> bytes:
        """
        Legacy compatibility: Builds a presentation from markdown text.
        Parses the markdown into slide specifications and renders them.
        """
        slides = self._parse_markdown_to_slides(markdown, project_meta or {})
        return self.build_from_slides(slides)

    def _parse_markdown_to_slides(self, markdown: str, meta: Dict) -> List[Dict]:
        """Convert markdown proposal text into slide specifications."""
        from src.services.deliverable_cleaner import clean_deliverable_markdown, extract_deliverable_kpis, CONVERSATIONAL_TRAILING_PATTERNS, CONVERSATIONAL_PREAMBLE_PATTERNS
        markdown = clean_deliverable_markdown(markdown)
        slides = []

        title = meta.get("title", "")
        client = meta.get("client_org", "")

        # Extract title from markdown H1
        h1_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        if h1_match and not title:
            title = h1_match.group(1).strip()
            # Try to split "Title: Client" patterns
            if ":" in title:
                parts = title.split(":", 1)
                if not client:
                    client = parts[1].strip()
                title = parts[0].strip()

        # Cover slide
        cover_meta = []
        if client:
            cover_meta.append({"label": "Client / Authority", "value": client})

        tender_match = re.search(r'(?:Tender|Bid|GEM|RA)[^:]*:\s*`?([^`\n]+)', markdown, re.I)
        if tender_match:
            cover_meta.append({"label": "Reference", "value": tender_match.group(1).strip()})

        cover_meta.append({"label": "Prepared By", "value": "Nikom InfraSolutions Pvt. Ltd."})
        cover_meta.append({"label": "Classification", "value": "Commercial & Technical Confidential"})

        slides.append({
            "layout": "cover",
            "title": title or "Technical Solution & Budgetary Offer",
            "subtitle": client,
            "metadata": cover_meta
        })

        # Extract KPIs for executive summary using deliverable cleaner
        kpis = extract_deliverable_kpis(markdown)

        # Extract narrative bullets from executive summary section
        narrative = []
        exec_match = re.search(r'(?:Executive Summary|Summary)(.*?)(?=\n##|\n---|\Z)', markdown, re.I | re.DOTALL)
        if exec_match:
            for line in exec_match.group(1).strip().split('\n'):
                line = line.strip().lstrip('- *•>')
                if line and len(line) > 10 and not line.startswith('|'):
                    narrative.append(re.sub(r'\*\*([^*]+)\*\*', r'\1', line))
                    if len(narrative) >= 5:
                        break

        if not narrative:
            narrative = [f"Turnkey technical solution for {client or 'the project'}."]

        slides.append({
            "layout": "executive_summary",
            "title": "Executive Summary",
            "kpis": kpis[:5],
            "narrative": narrative
        })

        # Parse sections into content slides
        sections = re.split(r'\n##\s+', markdown)
        for sec in sections[1:]:
            lines = sec.strip().split('\n')
            sec_title = lines[0].strip().rstrip('#').strip()

            # Skip if title is executive summary (already handled)
            if 'executive summary' in sec_title.lower():
                continue

            sec_body = '\n'.join(lines[1:]).strip()

            # Check if section has a table
            table_lines = [l for l in lines[1:] if l.strip().startswith('|')]
            if len(table_lines) >= 3:
                # Parse table
                headers = [c.strip() for c in table_lines[0].split('|')[1:-1]]
                rows = []
                for tl in table_lines[2:]:  # skip separator line
                    if '---' in tl:
                        continue
                    cells = [c.strip() for c in tl.split('|')[1:-1]]
                    if cells:
                        rows.append(cells)

                if headers and rows:
                    slides.append({
                        "layout": "table",
                        "title": sec_title,
                        "headers": headers,
                        "rows": rows
                    })
                    continue

            # Otherwise, render as content slide with bullets
            bullets = []
            for line in lines[1:]:
                line = line.strip()
                if not line or line.startswith('|') or line.startswith('---'):
                    continue
                if line.startswith('### '):
                    bullets.append({"heading": line.lstrip('# ').strip()})
                elif line.startswith('- ') or line.startswith('* '):
                    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', line.lstrip('- *'))
                    bullets.append(clean)
                elif line.startswith('> '):
                    pass  # skip blockquotes in bullets
                else:
                    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
                    if len(clean) > 5:
                        if not any(re.search(pat, clean, re.IGNORECASE) for pat in CONVERSATIONAL_TRAILING_PATTERNS + CONVERSATIONAL_PREAMBLE_PATTERNS):
                            bullets.append(clean)

            if bullets:
                slides.append({
                    "layout": "content",
                    "title": sec_title,
                    "bullets": bullets[:12]
                })

        # Closing slide
        slides.append({
            "layout": "closing",
            "heading": "Thank You",
            "message": f"We look forward to partnering with {client or 'you'} on this project.",
            "contact": [
                "Nikom InfraSolutions Pvt. Ltd.",
                "Corporate Office: New Delhi",
                "Email: bd@nikominfra.com",
                "Web: www.nikominfra.com"
            ]
        })

        return slides


# Module-level singleton for backward compatibility
presentation_deck_engine = PresentationDeckEngine()
