"""
Nikom Presales Diagram & Visual Illustration Generator
======================================================
Produces high-resolution, vector-crisp diagrams, architectural flowcharts,
and financial charts for inclusion in proposals and presentation decks.

Illustrations generated:
1. Power & Infrastructure Single-Line Architecture (2N Dual Feed SLD)
2. 5-Year Total Cost of Ownership (TCO) Donut & Spend Profile Chart
3. Implementation Milestone Gantt Schedule Chart
4. Executive 4-KPI Metric Dashboard Banner
"""

import io
import logging
from typing import Dict, Any, List, Optional
import matplotlib
matplotlib.use('Agg')  # Headless backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Arrow

logger = logging.getLogger(__name__)

# Corporate Color Palette
NAVY = "#0F2942"
NAVY_DARK = "#091B2E"
BLUE = "#2563EB"
BLUE_LIGHT = "#60A5FA"
CYAN = "#06B6D4"
TEAL = "#14B8A6"
GREEN = "#10B981"
AMBER = "#F59E0B"
SLATE_BG = "#F8FAFC"
SLATE_BORDER = "#CBD5E1"
DARK_TEXT = "#0F172A"
MUTED_TEXT = "#64748B"


class PresalesDiagramGenerator:
    """
    Renders professional vector/PNG illustrations for proposal documents.
    """

    @staticmethod
    def generate_power_architecture_diagram(
        it_kw: float = 75.0,
        ups_kva: float = 104.0,
        racks: int = 15,
        redundancy: str = "2N Dual Path"
    ) -> bytes:
        """
        Draws a clean, publication-grade Single-Line Architecture Diagram (SLD)
        showing Utility Grid -> Dual Transformers -> Dual 2N UPS -> Dual Bus -> Racks.
        """
        fig, ax = plt.subplots(figsize=(10, 4.2), dpi=200)
        ax.set_facecolor(SLATE_BG)
        fig.patch.set_facecolor(SLATE_BG)

        # Remove axes
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 4.2)
        ax.axis('off')

        def draw_box(x, y, w, h, label, sublabel="", color=NAVY, text_color="white"):
            box = FancyBboxPatch(
                (x, y), w, h,
                boxstyle="round,pad=0.08,rounding_size=0.12",
                facecolor=color, edgecolor=SLATE_BORDER, linewidth=1.2
            )
            ax.add_patch(box)
            ax.text(x + w / 2, y + h / 2 + (0.08 if sublabel else 0), label,
                    color=text_color, fontsize=9.5, fontweight='bold',
                    ha='center', va='center', fontfamily='sans-serif')
            if sublabel:
                ax.text(x + w / 2, y + h / 2 - 0.12, sublabel,
                        color="#94A3B8" if text_color == "white" else MUTED_TEXT,
                        fontsize=7.5, ha='center', va='center', fontfamily='sans-serif')

        def draw_line(x1, y1, x2, y2, color=BLUE, style='-', width=2.0):
            ax.plot([x1, x2], [y1, y2], color=color, linestyle=style, linewidth=width, zorder=1)

        # 1. Utility Input & Standby DG
        draw_box(0.3, 2.7, 1.6, 0.9, "11 kV Utility Grid", "State Electricity Board", color=NAVY)
        draw_box(0.3, 0.7, 1.6, 0.9, "Standby DG Sets", "CPCB IV+ Compliant", color="#1E3A8A")

        # 2. Main HT / AMF Switchboard
        draw_box(2.4, 1.7, 1.5, 1.0, "Main Switchboard", "Dual Source AMF / ATS", color=NAVY)

        draw_line(1.9, 3.15, 2.4, 2.4, color=BLUE, width=2.2)
        draw_line(1.9, 1.15, 2.4, 2.0, color="#F59E0B", style='--', width=2.2)

        # 3. Dual UPS Paths (2N Architecture)
        # Path A (Top)
        draw_box(4.5, 2.6, 1.9, 1.1, f"UPS Path A ({int(ups_kva)} kVA)", "Modular Li-Ion (LFP) Bank", color=BLUE)
        # Path B (Bottom)
        draw_box(4.5, 0.7, 1.9, 1.1, f"UPS Path B ({int(ups_kva)} kVA)", "Modular Li-Ion (LFP) Bank", color=TEAL)

        # Feeds from Switchboard
        draw_line(3.9, 2.4, 4.5, 3.15, color=BLUE, width=2.2)
        draw_line(3.9, 2.0, 4.5, 1.25, color=TEAL, width=2.2)

        # 4. Dual Distribution Panels (PDU A and PDU B)
        draw_box(7.0, 2.7, 1.3, 0.9, "PDU Feed A", "Dual 32A Busway", color=NAVY_DARK)
        draw_box(7.0, 0.8, 1.3, 0.9, "PDU Feed B", "Dual 32A Busway", color=NAVY_DARK)

        draw_line(6.4, 3.15, 7.0, 3.15, color=BLUE, width=2.2)
        draw_line(6.4, 1.25, 7.0, 1.25, color=TEAL, width=2.2)

        # 5. Server Racks White Space (Final Load)
        draw_box(8.7, 1.2, 1.1, 2.0, f"Server Racks\n({racks} Racks)", f"{it_kw} kW IT Load\nA+B iPDUs", color="#047857")

        draw_line(8.3, 3.15, 8.7, 2.5, color=BLUE, width=2.2)
        draw_line(8.3, 1.25, 8.7, 1.9, color=TEAL, width=2.2)

        # Title Header Banner inside plot
        ax.text(0.3, 3.9, f"ELECTRICAL 2N CONCURRENTLY MAINTAINABLE ARCHITECTURE (IT LOAD: {it_kw} kW)",
                fontsize=10.5, fontweight='bold', color=NAVY, fontfamily='sans-serif')
        ax.text(0.3, 3.7, f"Standards: ANSI/TIA-942-C Rated-3 • Dual Feed (Path A + Path B) • 15-Min LFP Autonomy",
                fontsize=8.0, color=MUTED_TEXT, fontfamily='sans-serif')

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=200, facecolor=SLATE_BG)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    @staticmethod
    def generate_tco_breakdown_chart(
        capex_lakhs: float = 85.0,
        camc_lakhs: float = 18.0,
        om_lakhs: float = 24.0
    ) -> bytes:
        """
        Draws a modern financial donut chart showing 5-Year Cost of Ownership (TCO).
        """
        fig, ax = plt.subplots(figsize=(7, 3.8), dpi=200)
        ax.set_facecolor(SLATE_BG)
        fig.patch.set_facecolor(SLATE_BG)

        total = capex_lakhs + camc_lakhs + om_lakhs
        values = [capex_lakhs, camc_lakhs, om_lakhs]
        labels = [
            f"Turnkey CAPEX\n₹ {capex_lakhs:.1f}L ({capex_lakhs/total*100:.0f}%)",
            f"Comprehensive AMC\n₹ {camc_lakhs:.1f}L ({camc_lakhs/total*100:.0f}%)",
            f"24×7 Managed O&M\n₹ {om_lakhs:.1f}L ({om_lakhs/total*100:.0f}%)"
        ]
        colors = [BLUE, CYAN, TEAL]

        wedges, texts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            startangle=140,
            textprops={'fontsize': 8.5, 'color': DARK_TEXT, 'fontfamily': 'sans-serif'},
            wedgeprops={'width': 0.45, 'edgecolor': 'white', 'linewidth': 2}
        )

        # Center summary badge
        ax.text(0, 0.08, "5-YEAR TCO", ha='center', va='center',
                fontsize=9.0, fontweight='bold', color=MUTED_TEXT)
        ax.text(0, -0.12, f"₹ {total/100:.2f} Cr", ha='center', va='center',
                fontsize=14.0, fontweight='bold', color=NAVY)

        ax.set_title("5-Year Total Cost of Ownership (TCO) Distribution",
                     fontsize=11.5, fontweight='bold', color=NAVY, pad=15)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=200, facecolor=SLATE_BG)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    @staticmethod
    def generate_timeline_gantt_chart(weeks_total: int = 24) -> bytes:
        """
        Draws a milestone Gantt chart for the turnkey delivery timeline.
        """
        fig, ax = plt.subplots(figsize=(10, 3.8), dpi=200)
        ax.set_facecolor(SLATE_BG)
        fig.patch.set_facecolor(SLATE_BG)

        tasks = [
            ("Detailed Engineering & Site Survey", 0, 4, BLUE),
            ("OEM Procurement & Equipment Dispatch", 3, 10, CYAN),
            ("Civil, Raised Floor & White Space Fit-Out", 8, 14, TEAL),
            ("Electrical & 2N Modular UPS Installation", 12, 18, NAVY),
            ("Precision Cooling & Containment", 14, 20, "#6366F1"),
            ("IST Load Bank Testing & Commissioning", 18, 23, GREEN),
            ("Handover & SLA Sign-Off", 22, 24, AMBER)
        ]

        y_positions = list(range(len(tasks)))
        y_positions.reverse()

        for idx, (task_name, start, end, color) in enumerate(tasks):
            y = y_positions[idx]
            duration = end - start
            bar = ax.barh(y, duration, left=start, height=0.55,
                          color=color, edgecolor='none', zorder=2)
            # Add week text inside or beside bar
            ax.text(start + duration / 2, y, f"{duration} wks",
                    ha='center', va='center', color='white',
                    fontsize=8.0, fontweight='bold')

        ax.set_yticks(y_positions)
        ax.set_yticklabels([t[0] for t in tasks], fontsize=8.5, color=DARK_TEXT)
        ax.set_xlabel("Project Timeline (Weeks from Purchase Order)", fontsize=9.0, color=MUTED_TEXT)
        ax.set_xlim(0, max(weeks_total, 24))
        ax.grid(axis='x', linestyle='--', alpha=0.5, color=SLATE_BORDER)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(SLATE_BORDER)
        ax.spines['bottom'].set_color(SLATE_BORDER)

        ax.set_title("Turnkey Execution Roadmap & Milestone Schedule",
                     fontsize=11.5, fontweight='bold', color=NAVY, pad=15)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=200, facecolor=SLATE_BG)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

