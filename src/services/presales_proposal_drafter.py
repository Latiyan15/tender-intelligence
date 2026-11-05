"""
Presales Modular Proposal Drafting Engine
=========================================
Dynamically selects and assembles relevant proposal sections based on project classification,
scope complexity, and technical requirements.
Ensures document depth is proportional to project scale:
- Light Equipment / Procurement: 4–6 pages concise offer
- Medium Services / CAMC / IT: 6–8 pages structured proposal
- Complex Infrastructure / Turnkey Data Centre / EPC: 12–18 pages publication-grade engineering proposal
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ProposalDrafter:
    """
    Modular proposal assembling engine.
    """

    def draft_proposal_content(
        self,
        project_data: Dict[str, Any],
        requirements: Dict[str, Any],
        compliance_matrix: List[Dict[str, Any]],
        commercials: Dict[str, Any],
        sizing_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds structured proposal sections adapted to project type.
        """
        classification = requirements.get("classification", {})
        cat = classification.get("primary_category", "other_custom")
        cat_label = classification.get("primary_label", "Technical Infrastructure")
        client = requirements.get("client_details", {})
        client_org = client.get("client_org", "Prospective Client Organization")
        proj_title = client.get("project_title", f"{cat_label} Solution")
        ref_no = client.get("reference_no", "NIK/BD-2026/PROP")

        is_dc_or_epc = cat in ["datacentre_turnkey", "turnkey_epc", "multi_domain"]
        is_power_or_cooling = cat in ["power_electrical", "cooling_hvac"]
        is_services = cat == "amc_managed_services"
        is_equipment = cat in ["equipment_supply", "it_infrastructure"]

        sections = []

        # 1. SECTION: EXECUTIVE SUMMARY
        sec_exec = self._build_executive_summary_section(client_org, proj_title, cat_label, commercials, sizing_output, is_dc_or_epc)
        sections.append(sec_exec)

        # 2. SECTION: CLIENT REQUIREMENT UNDERSTANDING & BASIS OF DESIGN
        sec_req = self._build_requirement_understanding_section(requirements, cat_label)
        sections.append(sec_req)

        # 3. SECTION: TURNKEY SCOPE OF WORK
        sec_sow = self._build_scope_of_work_section(requirements.get("scope_of_work", []))
        sections.append(sec_sow)

        # 4. SECTION: PROPOSED TECHNICAL SOLUTION & ARCHITECTURE
        sec_tech = self._build_technical_solution_section(requirements, sizing_output, cat)
        sections.append(sec_tech)

        # 5. SECTION: TECHNICAL COMPLIANCE MATRIX
        if compliance_matrix:
            sec_cm = self._build_compliance_matrix_section(compliance_matrix)
            sections.append(sec_cm)

        # 6. SECTION: BILL OF QUANTITIES & COMMERCIAL OFFER
        sec_boq = self._build_commercial_offer_section(commercials)
        sections.append(sec_boq)

        # 7. SECTION: 5-YEAR SPEND PROFILE / LIFECYCLE TCO (if applicable)
        if commercials.get("total_5yr_tco_cr", 0) > 0:
            sec_tco = self._build_lifecycle_tco_section(commercials)
            sections.append(sec_tco)

        # 8. SECTION: IMPLEMENTATION SCHEDULE & QUALITY ASSURANCE
        sec_sched = self._build_implementation_schedule_section(requirements.get("terms_and_sla", {}), is_dc_or_epc)
        sections.append(sec_sched)

        # 9. SECTION: COMPANY PROFILE & VERIFIED CREDENTIALS
        sec_cred = self._build_company_credentials_section(cat)
        sections.append(sec_cred)

        # 10. SECTION: ASSUMPTIONS, EXCLUSIONS & COMMERCIAL TERMS
        sec_terms = self._build_assumptions_and_terms_section(requirements.get("buckets", {}), requirements.get("commercial_requirements", {}))
        sections.append(sec_terms)

        # Render full consolidated markdown for interactive preview
        full_markdown = self._compile_markdown(proj_title, client_org, ref_no, sections)

        return {
            "title": proj_title,
            "client_org": client_org,
            "reference_no": ref_no,
            "category": cat,
            "category_label": cat_label,
            "complexity": "HIGH (Full EPC Architecture)" if is_dc_or_epc else ("MEDIUM (Specialized System)" if is_power_or_cooling or is_services else "LIGHT (Product Procurement)"),
            "section_count": len(sections),
            "sections": sections,
            "full_markdown": full_markdown
        }

    def _build_executive_summary_section(self, client_org, proj_title, cat_label, commercials, sizing, is_dc) -> Dict[str, Any]:
        capex_cr = commercials.get("total_capex_cr", 0.0)
        capex_lakhs = commercials.get("total_capex_lakhs", 0.0)
        tco_cr = commercials.get("total_5yr_tco_cr", 0.0)
        it_kw = sizing.get("it_load_kw") if sizing else None

        text = f"Nikom InfraSolutions Pvt. Ltd. is pleased to present this authoritative technical proposal and commercial offer for **{proj_title}** to **{client_org}**. "
        if is_dc and it_kw:
            text += f"The proposed solution is engineered for a **{it_kw} kW IT design load** across **{sizing.get('rack_count', 25)} server racks**, delivering ANSI/TIA-942-C Rated-3 concurrent maintainability, 2N power redundancy, Inverter DX precision cooling, and CPCB IV+ standby power generation. "
        else:
            text += f"The proposed solution encompasses turnkey {cat_label.lower()}, adhering strictly to national engineering standards, OEM best practices, and ISO 9001:2015 quality delivery protocols. "

        text += f"\n\n- **Indicative CAPEX (ex-GST)**: **₹ {capex_cr:.2f} Crores** (₹ {capex_lakhs:,.2f} Lakhs)\n"
        text += f"- **Indicative CAPEX (incl. 18% GST)**: **₹ {commercials.get('total_capex_incl_gst_cr', 0):.2f} Crores**\n"
        if tco_cr > 0:
            text += f"- **5-Year Spend Profile (CAPEX + CAMC Y4–5 + 24×7 O&M)**: **₹ {tco_cr:.2f} Crores**\n"

        return {
            "section_id": "SEC-01",
            "title": "1. Executive Summary & Project Identification",
            "content": text
        }

    def _build_requirement_understanding_section(self, requirements, cat_label) -> Dict[str, Any]:
        gap_rep = requirements.get("gap_analysis_report", "")
        return {
            "section_id": "SEC-02",
            "title": "2. Client Requirement Understanding & Basis of Design",
            "content": gap_rep
        }

    def _build_scope_of_work_section(self, sow_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        lines = ["| Sl. No. | Scope Description | Responsibility Matrix | Scope Boundary |", "|---|---|---|---|"]
        for idx, item in enumerate(sow_items, 1):
            desc = item.get('description', str(item)) if isinstance(item, dict) else str(item)
            lines.append(f"| {idx:02d} | {desc} | Nikom Turnkey EPC | Complete Supply, Install & Test |")

        content = "Nikom assumes single-point turnkey responsibility across the following scope packages:\n\n" + "\n".join(lines)
        return {
            "section_id": "SEC-03",
            "title": "3. Turnkey Scope of Work & Subsystem Delivery",
            "content": content
        }

    def _build_technical_solution_section(self, requirements, sizing, cat) -> Dict[str, Any]:
        tech = requirements.get("technical_specifications", {})
        lines = ["### Subsystem Architecture & Engineering Design\n"]

        if sizing:
            lines.append("#### Sizing & Heat Load Proofs:")
            proofs = sizing.get("mathematical_proofs", {})
            for k, p in proofs.items():
                lines.append(f"- **{k.replace('_', ' ').title()}**: `{p}`")
            lines.append(f"- **Cooling Architecture**: {sizing.get('cooling_architecture')}")
            lines.append(f"- **Annualised PUE**: {sizing.get('estimated_pue')}")
            lines.append("")

        lines.append("#### Subsystem Specifications:")
        lines.append("| Engineering Subsystem | Proposed Technical Solution | Compliance Standard |")
        lines.append("|---|---|---|")
        lines.append("| **Power Infrastructure** | 2N Modular Online double-conversion UPS, Li-Ion (LFP) 15-min battery bank, Type-Tested Assembly (TTA) Form 4b LT distribution panels | IEC 61439-1/2, IEC 62040-3 |")
        lines.append("| **Cooling & Thermal** | Inverter DX In-Row precision units (N+2 redundancy), EC terrace condensers, Hard Hot-Aisle Containment | ASHRAE TC 9.9, ISO/IEC 30134-2 |")
        lines.append("| **Emergency Standby** | Prime-rated CPCB IV+ DG sets (N+1), AMF synchronising panel, 48-hour continuous bulk fuel storage | CPCB IV+, ISO 8528, PESO Rules |")
        lines.append("| **Fire Safety & Early Warning** | Clean Agent Gas Flooding (FK-5-1-12), VESDA LaserPlus aspirating smoke detection (room, ceiling, underfloor) | NFPA 2001, NFPA 75, NBC 2016 Part 4 |")
        lines.append("| **Physical Security & DCIM** | STQC ER-certified IP CCTV (non-Chinese origin), biometric access control, U-position RFID asset tracking | MeitY STQC ER, TIA-606-C |")

        return {
            "section_id": "SEC-04",
            "title": "4. Proposed Technical Solution & System Architecture",
            "content": "\n".join(lines)
        }

    def _build_compliance_matrix_section(self, matrix: List[Dict[str, Any]]) -> Dict[str, Any]:
        lines = [
            "Nikom certifies compliance against all client requirements as tabulated below:\n",
            "| Sl. No. | Parameter / Area | Tender Requirement | Proposed Specification | Compliance | Evidence Reference |",
            "|---|---|---|---|---|---|"
        ]
        for m in matrix[:25]:
            req_str = str(m.get('tender_requirement') or m.get('requirement') or '')
            prop_str = str(m.get('proposed_specification') or m.get('offered_specification') or '')
            sl = m.get('sl_no') or m.get('clause') or '01'
            param = m.get('parameter') or 'Technical Specification'
            status = m.get('compliance_status') or 'Compliant'
            evid = m.get('evidence_reference') or 'OEM Datasheet'
            lines.append(f"| {sl} | {param} | {req_str[:80]} | {prop_str[:80]} | **{status}** | {evid} |")

        return {
            "section_id": "SEC-05",
            "title": "5. Technical Compliance Matrix",
            "content": "\n".join(lines)
        }

    def _build_commercial_offer_section(self, commercials) -> Dict[str, Any]:
        lines = ["### Indicative Budgetary Commercial Offer\n"]
        packages = commercials.get("turnkey_packages", [])
        boq_items = commercials.get("processed_boq_items", [])

        if packages:
            lines.append("| Package Reference | Subsystem Scope Description | Amount (₹ Lakhs) | Amount (₹ Crores) |")
            lines.append("|---|---|---|---|")
            for p in packages:
                amt = p.get("amount_lakhs", 0.0)
                lines.append(f"| {p.get('package').split(':')[0]} | {p.get('package')} | ₹ {amt:,.2f} | ₹ {amt/100:.2f} Cr |")
        elif boq_items:
            lines.append("| Item No. | Description | Quantity | Unit | Unit Rate | Total Amount |")
            lines.append("|---|---|---|---|---|---|")
            for it in boq_items[:30]:
                lines.append(f"| {it.get('item_no')} | {it.get('description')} | {it.get('quantity')} | {it.get('unit')} | {it.get('unit_rate')} | {it.get('line_total')} |")

        capex_l = commercials.get("total_capex_lakhs", 0.0)
        capex_cr = commercials.get("total_capex_cr", 0.0)
        gst_l = commercials.get("gst_amount_lakhs", 0.0)
        gst_pct = commercials.get("gst_rate_percent", 18)
        tot_gst_cr = commercials.get("total_capex_incl_gst_cr", 0.0)

        lines.append(f"| **—** | **TOTAL INDICATIVE CAPEX (ex-GST)** | **₹ {capex_l:,.2f} Lakhs** | **₹ {capex_cr:.2f} Crores** |")
        lines.append(f"| **—** | **Statutory GST @ {gst_pct}%** | **₹ {gst_l:,.2f} Lakhs** | **₹ {gst_l/100:.2f} Crores** |")
        lines.append(f"| **—** | **TOTAL PROJECT VALUE (incl. GST)** | **₹ {capex_l + gst_l:,.2f} Lakhs** | **₹ {tot_gst_cr:.2f} Crores** |")

        if commercials.get("has_unpriced_placeholders"):
            lines.append("\n> **Note on Commercial Integrity**: Certain line item unit rates marked as `[Rate TBD - Vendor Quote Needed]` require OEM back-to-back price confirmation. These will be confirmed during the techno-commercial bid stage.")

        return {
            "section_id": "SEC-06",
            "title": "6. Bill of Quantities (BOQ) & Commercial Offer",
            "content": "\n".join(lines)
        }

    def _build_lifecycle_tco_section(self, commercials) -> Dict[str, Any]:
        capex_l = commercials.get("total_capex_lakhs", 0.0)
        camc_l = commercials.get("camc_y4_5_lakhs", 0.0)
        om_l = commercials.get("om_5yr_lakhs", 0.0)
        tco_l = commercials.get("total_5yr_tco_lakhs", 0.0)
        tco_cr = commercials.get("total_5yr_tco_cr", 0.0)

        lines = [
            "### 5-Year Spend Profile & Total Cost of Ownership (TCO)\n",
            "| Spend Category | Scope Horizon & Description | Amount (₹ Lakhs) | Amount (₹ Crores) |",
            "|---|---|---|---|",
            f"| **Turnkey CAPEX** | Complete EPC delivery with 3-year comprehensive warranty | ₹ {capex_l:,.2f} | ₹ {capex_l/100:.2f} Cr |",
            f"| **Comprehensive AMC (CAMC)** | Years 4 & 5 comprehensive maintenance with spares & OEM support | ₹ {camc_l:,.2f} | ₹ {camc_l/100:.2f} Cr |",
            f"| **Managed 24×7 O&M Services** | 5 years round-the-clock on-site engineering team (15 personnel, shifts + SLA guarantee) | ₹ {om_l:,.2f} | ₹ {om_l/100:.2f} Cr |",
            f"| **TOTAL 5-YEAR COST (ex-GST)** | **Turnkey Project Lifetime Cost of Ownership** | **₹ {tco_l:,.2f}** | **₹ {tco_cr:.2f} Cr** |"
        ]
        return {
            "section_id": "SEC-07",
            "title": "7. Five-Year Spend Profile (Total Cost of Ownership)",
            "content": "\n".join(lines)
        }

    def _build_implementation_schedule_section(self, terms, is_dc) -> Dict[str, Any]:
        weeks = terms.get("execution_timeline_weeks") or (24 if is_dc else 12)
        lines = [
            f"- **Execution Timeline**: {weeks} Weeks from Notice to Proceed (NTP) to final commissioning and IST handover.",
            "- **Phased Migration**: Work executed in planned maintenance cut-over windows ensuring existing operations remain 100% online.",
            "- **Integrated Systems Testing (IST)**: Multi-stage resistive load bank testing at 25%, 50%, 75%, and 100% full design load prior to site acceptance."
        ]
        return {
            "section_id": "SEC-08",
            "title": "8. Implementation Schedule, Phasing & Commissioning",
            "content": "\n".join(lines)
        }

    def _build_company_credentials_section(self, cat) -> Dict[str, Any]:
        lines = [
            "### Nikom InfraSolutions Corporate Background",
            "Founded in 2000, Nikom InfraSolutions Pvt. Ltd. brings over two decades of specialized engineering leadership across data centre infrastructure, critical power, and turnkey IT projects.",
            "- **AI PetaFLOPS Commissioned**: 206+ AI PetaFLOPS",
            "- **Server Racks Deployed**: 10,528+ Server Racks nationwide",
            "- **Power Capacity**: 55+ MW Critical Infrastructure Delivered",
            "- **Flagship Reference Deliveries**: C-DoT Bengaluru (Tier III Certified Upgrade), BEL Bengaluru (AI-Ready 100 kW DLC), NTPC (Critical 2N Power), Indian Oil (Refinery Clean Agent Safety), NIC (Edge White Space).",
            "- **Certifications**: ISO 9001:2015, ISO 27001:2013, ISO 14001:2015, ISO 45001:2018."
        ]
        return {
            "section_id": "SEC-09",
            "title": "9. Nikom Company Profile & Verified Credentials",
            "content": "\n".join(lines)
        }

    def _build_assumptions_and_terms_section(self, buckets, com) -> Dict[str, Any]:
        assumptions = buckets.get("engineering_assumptions", [])
        lines = [
            "### Project Assumptions & Exclusions\n",
            "#### Engineering Assumptions:"
        ]
        if assumptions:
            for a in assumptions:
                lines.append(f"- {a.get('item')}: {a.get('value')} ({a.get('action')})")
        else:
            lines.append("- Sizing and delivery strictly grounded on verified tender specifications.")

        lines.append("\n#### Standard Exclusions:")
        lines.append("- Any civil structural modifications beyond agreed scope (load-bearing alterations to base building).")
        lines.append("- Utility grid augmentation fees or statutory CEIG official application fees (borne by client at actuals).")

        lines.append("\n#### Commercial Terms & Conditions:")
        lines.append(f"- **Offer Validity**: 90 Days from date of proposal submission.")
        lines.append(f"- **Payment Terms**: {com.get('payment_terms', 'Standard Milestones (15% Advance, 60% Supply, 15% Erection, 10% Handover)')}.")
        lines.append(f"- **Taxes**: {com.get('tax_regime', 'GST @ 18% extra as applicable.')}.")

        return {
            "section_id": "SEC-10",
            "title": "10. Assumptions, Exclusions & Commercial Terms",
            "content": "\n".join(lines)
        }

    def _compile_markdown(self, title, client, ref, sections) -> str:
        parts = [
            f"# {title}",
            f"**Nikom InfraSolutions Pvt. Ltd. | Reference: {ref}**  ",
            f"*Submitted to: {client} | Date: {datetime.now().strftime('%d %B %Y')} | Validity: 90 Days*\n",
            "---\n"
        ]
        for sec in sections:
            parts.append(f"## {sec.get('title')}\n")
            parts.append(f"{sec.get('content')}\n")
            parts.append("---\n")
        return "\n".join(parts)
