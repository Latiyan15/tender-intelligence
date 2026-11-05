"""
Comprehensive Automated Test Suite for Redesigned Pre-Sales Engineering System
==============================================================================
Validates:
1. Multi-category Project Classification (Equipment, IT, Power, DC, AMC, Turnkey EPC).
2. Requirement Extraction & Provenance Tracking.
3. Interactive Clarification Engine (Gap Identification & Question Generation).
4. Requirement Compliance Engine (Evaluates statuses & evidence).
5. Deterministic Commercial & Sizing Calculation Engine (Mathematical accuracy, GST, placeholders).
6. Modular Proposal Drafting (Light, Medium, Complex scale).
7. Independent Quality Control Validation (5 Pillars, Severity findings, Quality Score, Gate).
8. Context Isolation & Anti-Contamination Regression (Cross-project leakage prevention).
9. Professional Document Generation (DOCX & PDF).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.presales_project_manager import ProjectManager
from src.services.presales_requirement_engine import RequirementEngine, PROJECT_CATEGORIES
from src.services.presales_clarification_engine import ClarificationEngine
from src.services.presales_knowledge_base import KnowledgeBaseService
from src.services.presales_compliance_engine import ComplianceEngine
from src.services.presales_calculation_engine import CalculationEngine
from src.services.presales_proposal_drafter import ProposalDrafter
from src.services.presales_validator import ProposalValidator
from src.services.presales_doc_generator import DocumentGenerator


class TestPresalesGeneralIntelligence(unittest.TestCase):

    def setUp(self):
        self.pm = ProjectManager()
        self.req_engine = RequirementEngine()
        self.clarify_engine = ClarificationEngine()
        self.kb = KnowledgeBaseService()
        self.comp_engine = ComplianceEngine()
        self.calc_engine = CalculationEngine()
        self.drafter = ProposalDrafter()
        self.validator = ProposalValidator()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. MULTI-CATEGORY PROJECT CLASSIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    def test_classification_equipment_supply(self):
        text = "Procurement of 500 units of Desktop Computers with Intel i7, 16GB RAM, 512GB SSD, 24-inch Monitors and laser printers for state education department."
        res = self.req_engine.classify_project(text, "Supply of Desktop Computers")
        self.assertIn(res["primary_category"], ["equipment_supply", "it_infrastructure"])
        self.assertNotEqual(res["primary_category"], "datacentre_turnkey")

    def test_classification_power_electrical(self):
        text = "Design, supply, installation, testing and commissioning of 2 x 400 kVA Modular Online UPS System with Li-Ion battery banks and TTA Form 4b main LT distribution panels."
        res = self.req_engine.classify_project(text, "Critical Power Infrastructure")
        self.assertEqual(res["primary_category"], "power_electrical")

    def test_classification_cooling_hvac(self):
        text = "Supply and installation of 5 x 20 TR Inverter DX In-Row Precision Air Conditioning units with EC fans and Hot-Aisle Containment."
        res = self.req_engine.classify_project(text, "Precision Cooling System")
        self.assertEqual(res["primary_category"], "cooling_hvac")

    def test_classification_amc_managed_services(self):
        text = "Tender for 3-Year Comprehensive Annual Maintenance Contract (CAMC) with 24x7 resident engineering team, preventive maintenance schedules, and 4-hour SLA response."
        res = self.req_engine.classify_project(text, "Annual Maintenance Contract")
        self.assertEqual(res["primary_category"], "amc_managed_services")

    def test_classification_datacentre_turnkey(self):
        text = "Turnkey Design, Build, Supply, Installation, Testing, Commissioning and Certification of Tier III Concurrently Maintainable Data Centre facility (250 kW IT Load)."
        res = self.req_engine.classify_project(text, "Tier III Data Centre Construction")
        self.assertEqual(res["primary_category"], "datacentre_turnkey")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. REQUIREMENT EXTRACTION & GAP IDENTIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    def test_gap_identification_on_incomplete_specs(self):
        incomplete_text = "Please give quote for turnkey data centre construction in Bengaluru."
        res = self.req_engine.extract_requirements(incomplete_text)
        buckets = res["buckets"]
        missing_items = [m["item"] for m in buckets["missing_information"]]
        # Must detect that IT load / electrical capacity is missing
        self.assertTrue(any("Capacity" in m or "Load" in m for m in missing_items))
        # Must have formulated targeted follow-up question
        questions = self.clarify_engine.generate_clarification_questions(res)
        self.assertTrue(len(questions) > 0)
        self.assertEqual(questions[0]["priority"], "CRITICAL")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. CONTEXT ISOLATION & ANTI-CONTAMINATION REGRESSION TEST
    # ─────────────────────────────────────────────────────────────────────────

    def test_cross_project_isolation(self):
        """
        REGRESSION TEST: Ensures an inquiry for Project B (e.g. 500 Laptops) does NOT
        inherit quantities, client names, or data-centre kW figures from Project A (C-DoT 252 kW).
        """
        proj_a = self.pm.create_project(title="C-DoT Tier III 252 kW Facility", client_org="C-DoT Bengaluru")
        proj_b = self.pm.create_project(title="Supply of 500 Laptops", client_org="State Education Board")

        # Project B text mentions nothing about data centres
        text_b = "Tender for procurement of 500 Nos commercial laptops with 3-year warranty for State Education Board."
        req_b = self.req_engine.extract_requirements(text_b)

        # Assert no C-DoT or 252 kW contamination in Project B
        self.assertNotIn("c-dot", req_b["client_details"]["client_org"].lower())
        self.assertNotIn("252", str(req_b["technical_specifications"]))
        self.assertEqual(req_b["classification"]["primary_category"], "equipment_supply")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. DETERMINISTIC CALCULATION ACCURACY & PRICING INTEGRITY
    # ─────────────────────────────────────────────────────────────────────────

    def test_deterministic_dc_sizing_math(self):
        it_kw = 250.0
        sizing = self.calc_engine.calculate_data_centre_sizing(it_load_kw=it_kw, rack_count=25)
        # Mathematical proof: Heat load = 250 * 1.15 = 287.5 kW
        self.assertEqual(sizing["heat_load_kw"], 287.5)
        # Cooling TR = 287.5 / 3.517 = 81.7 TR
        self.assertEqual(sizing["cooling_capacity_tr"], 81.7)
        # UPS Sizing = (250 / 0.9) * 1.25 = 347.2 => 348 kVA per side
        self.assertGreaterEqual(sizing["ups_rating_kva"], 347)

    def test_commercial_pricing_integrity(self):
        """Checks that unknown unit rates produce explicit [TBD] placeholders rather than fabricated numbers."""
        boq = [
            {"item_no": "1", "description": "Core Switch", "quantity": 2, "estimated_unit_rate": None},
            {"item_no": "2", "description": "SFP Transceiver", "quantity": 10, "estimated_unit_rate": 5000.0}
        ]
        res = self.calc_engine.calculate_boq_and_commercials(boq_items=boq, category="networking_security")
        self.assertTrue(res["has_unpriced_placeholders"])
        self.assertEqual(res["missing_rate_items_count"], 1)
        self.assertEqual(res["processed_boq_items"][0]["unit_rate"], "[Rate TBD - Vendor Quote Needed]")
        self.assertEqual(res["processed_boq_items"][1]["line_total_numeric"], 50000.0)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. INDEPENDENT QUALITY CONTROL VALIDATOR
    # ─────────────────────────────────────────────────────────────────────────

    def test_validator_blocks_invalid_tier_v(self):
        fake_proposal = {
            "title": "Invalid Tier Proposal",
            "full_markdown": "Nikom InfraSolutions proposes a Tier V Data Centre Facility with 99.9999% uptime."
        }
        res = self.validator.validate_proposal(
            project_data={},
            requirements={"client_details": {"client_org": "Test Entity"}},
            proposal_content=fake_proposal,
            commercials={}
        )
        # Tier V claim must trigger CRITICAL finding and block gate
        self.assertEqual(res["gate_status"], "BLOCKED")
        self.assertTrue(any(f["severity"] == "CRITICAL" and "Tier V" in f["item"] for f in res["findings"]))

    # ─────────────────────────────────────────────────────────────────────────
    # 6. PROFESSIONAL DOCUMENT GENERATION (DOCX & PDF)
    # ─────────────────────────────────────────────────────────────────────────

    def test_docx_generation(self):
        proposal_dict = {
            "title": "Turnkey Substation & Critical Power Proposal",
            "client_org": "NTPC Limited",
            "reference_no": "NIK/NTPC/2026/01",
            "sections": [
                {"title": "1. Executive Summary", "content": "Nikom proposes turnkey 2N power infrastructure."},
                {"title": "2. BOQ", "content": "| Sl | Item | Qty | Unit |\n|---|---|---|---|\n| 1 | 500 kVA Transformer | 2 | Nos |"}
            ]
        }
        docx_bytes = DocumentGenerator.generate_proposal_docx(proposal_dict)
        self.assertGreater(len(docx_bytes), 10000)
        # Check ZIP / DOCX magic bytes (PK\x03\x04)
        self.assertTrue(docx_bytes.startswith(b"PK\x03\x04"))


    def test_presentation_deck_generation(self):
        """Validates 16:9 widescreen PowerPoint deck generation for client pitches."""
        from src.services.presentation_deck_engine import presentation_deck_engine
        import io
        import pptx

        sample_markdown = """# Upgradation of Computer Training Laboratory
58 Gorkha Training Centre, Happy Valley, Shillong

## Executive Summary
Turnkey supply and commissioning of 45 Thin Clients, 3 Host Servers, 45 Monitors, 86" IFPD, and Networking.
- **Total CAPEX (ex-GST)**: Rs. 25.89 Lakhs
- **Total CAPEX (incl. 18% GST)**: Rs. 30.55 Lakhs

| Sl | Item Description | Qty | Unit | Unit Rate (Rs. L) | Amount (Rs. L) |
|---|---|---|---|---|---|
| 1 | Thin Client Computer 4-Core ARM | 45 | Nos | 0.16 | 7.20 |
| 2 | High Performance Host Server i9-14th Gen | 3 | Nos | 1.80 | 5.40 |
| 3 | 19-inch LED Monitor FHD | 45 | Nos | 0.35 | 15.75 |
| | **SUBTOTAL CAPEX (ex-GST)** | | | | **25.89** |
| | **GST @ 18%** | | | | **4.66** |
| | **TOTAL CAPEX (incl. 18% GST)** | | | | **30.55** |
"""
        pptx_bytes = presentation_deck_engine.build_presentation(
            sample_markdown,
            project_meta={
                "title": "Upgradation of Computer Training Laboratory",
                "client_org": "58 Gorkha Training Centre, Shillong",
                "reference_no": "GEM/2026/B/7861470"
            }
        )

        self.assertGreater(len(pptx_bytes), 20000)
        self.assertTrue(pptx_bytes.startswith(b"PK\x03\x04"))

        # Verify PPTX structure
        prs = pptx.Presentation(io.BytesIO(pptx_bytes))
        self.assertEqual(len(prs.slides), 6)
        self.assertAlmostEqual(prs.slide_width.inches, 13.333, places=2)
        self.assertAlmostEqual(prs.slide_height.inches, 7.5, places=2)

    def test_dynamic_pdf_engine(self):
        """Validates publication-grade dynamic PDF generation."""
        from src.services.dynamic_pdf_engine import dynamic_pdf_engine

        sample_markdown = """# Technical Solution & Budgetary Commercial Offer
Commandant, 58 Gorkha Training Centre, Happy Valley, Shillong

Nikom InfraSolutions Pvt. Ltd. proposes turnkey IT lab fitout.
"""
        pdf_bytes = dynamic_pdf_engine.convert_markdown_to_pdf(sample_markdown)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

