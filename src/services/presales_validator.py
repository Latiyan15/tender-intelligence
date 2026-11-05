"""
Presales Independent Quality Control & Validation System
========================================================
Inspects generated proposals across 5 Quality Pillars:
1. Requirement Alignment
2. Technical Integrity
3. Company Integrity
4. Commercial Integrity
5. Document Quality

Assigns findings with severity: CRITICAL, HIGH, MEDIUM, LOW.
Any CRITICAL error blocks approval gate. Computes an overall Quality Score (0–100%).
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ProposalValidator:
    """
    Independent validation engine inspecting proposal drafts prior to human sign-off.
    """

    def validate_proposal(
        self,
        project_data: Dict[str, Any],
        requirements: Dict[str, Any],
        proposal_content: Dict[str, Any],
        commercials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Runs comprehensive programmatic validation across the 5 quality pillars.
        """
        findings = []

        # 1. PILLAR: REQUIREMENT ALIGNMENT
        self._check_requirement_alignment(requirements, proposal_content, findings)

        # 2. PILLAR: TECHNICAL INTEGRITY
        self._check_technical_integrity(requirements, proposal_content, findings)

        # 3. PILLAR: COMPANY INTEGRITY
        self._check_company_integrity(proposal_content, findings)

        # 4. PILLAR: COMMERCIAL INTEGRITY
        self._check_commercial_integrity(commercials, proposal_content, findings)

        # 5. PILLAR: DOCUMENT QUALITY
        self._check_document_quality(proposal_content, findings)

        # Score & Gate Status
        critical_count = len([f for f in findings if f["severity"] == "CRITICAL"])
        high_count = len([f for f in findings if f["severity"] == "HIGH"])
        medium_count = len([f for f in findings if f["severity"] == "MEDIUM"])
        low_count = len([f for f in findings if f["severity"] == "LOW"])

        # Quality Score Calculation
        deductions = (critical_count * 30) + (high_count * 15) + (medium_count * 5) + (low_count * 2)
        quality_score = max(0, min(100, 100 - deductions))

        if critical_count > 0:
            gate_status = "BLOCKED"
            recommendation = f"Approval BLOCKED by {critical_count} critical finding(s). Must be resolved prior to client submission."
        elif high_count > 0:
            gate_status = "WARNINGS"
            recommendation = f"Proposal approved with {high_count} advisory warning(s). Review recommended."
        else:
            gate_status = "PASSED"
            recommendation = "Proposal passed all automated quality control checks. Ready for sales director sign-off."

        return {
            "validation_timestamp": "now",
            "quality_score": quality_score,
            "gate_status": gate_status,
            "recommendation": recommendation,
            "findings_summary": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
                "total": len(findings)
            },
            "findings": findings
        }

    def _check_requirement_alignment(self, requirements, proposal, findings):
        client = requirements.get("client_details", {})
        client_name = client.get("client_org", "")
        full_text = proposal.get("full_markdown", "")

        if not client_name or client_name == "Prospective Client Organization":
            findings.append({
                "pillar": "Requirement Alignment",
                "severity": "HIGH",
                "item": "Generic Client Organization",
                "details": "Client organization name is set to generic placeholder. Confirm exact client/authority entity."
            })

        # Check if mandatory scope items are present
        sow_items = requirements.get("scope_of_work", [])
        for item in sow_items[:10]:
            desc = item.get("description", "")
            # check key words
            key_words = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', desc) if w.lower() not in ["with", "from", "that", "this", "have", "been", "shall", "will"]]
            if key_words and not any(kw.lower() in full_text.lower() for kw in key_words[:3]):
                findings.append({
                    "pillar": "Requirement Alignment",
                    "severity": "MEDIUM",
                    "item": "Unaddressed Scope Keyword",
                    "details": f"Scope item '{desc[:60]}...' may not be explicitly detailed in technical solution."
                })

    def _check_technical_integrity(self, requirements, proposal, findings):
        tech = requirements.get("technical_specifications", {})
        full_text = proposal.get("full_markdown", "")

        # Check for ungrounded capacity claims
        if tech.get("it_load_kw") and f"{int(tech['it_load_kw'])} kW" not in full_text:
            findings.append({
                "pillar": "Technical Integrity",
                "severity": "HIGH",
                "item": "Capacity Discrepancy",
                "details": f"Specified IT load {tech.get('it_load_kw')} kW does not match narrative text."
            })

        # Check for units consistency (kW, kVA, TR)
        if "kva" in full_text.lower() and "pf" not in full_text.lower() and "power factor" not in full_text.lower():
            findings.append({
                "pillar": "Technical Integrity",
                "severity": "LOW",
                "item": "Missing Power Factor Specification",
                "details": "kVA ratings are specified without explicitly citing design power factor (recommend 0.90 or 0.80 PF)."
            })

    def _check_company_integrity(self, proposal, findings):
        full_text = proposal.get("full_markdown", "")
        # Verify Nikom identity
        if "Nikom InfraSolutions" not in full_text:
            findings.append({
                "pillar": "Company Integrity",
                "severity": "CRITICAL",
                "item": "Company Identity Missing",
                "details": "Proposal header or narrative is missing official 'Nikom InfraSolutions Pvt. Ltd.' corporate entity reference."
            })

        # Verify no fake certifications
        if "tier v" in full_text.lower():
            findings.append({
                "pillar": "Company Integrity",
                "severity": "CRITICAL",
                "item": "Invalid Tier V Standard Claimed",
                "details": "Uptime / TIA standards only define up to Tier IV / Rated-4. 'Tier V' is an invalid claim."
            })

    def _check_commercial_integrity(self, commercials, proposal, findings):
        capex_l = commercials.get("total_capex_lakhs", 0.0)
        gst_l = commercials.get("gst_amount_lakhs", 0.0)
        tot_incl = round(commercials.get("total_capex_incl_gst_cr", 0.0) * 100.0, 2)
        expected_incl = round((capex_l + gst_l) / 100.0, 2)

        # Mathematical reconciliation check
        if commercials.get("total_capex_cr", 0.0) > 0:
            diff = abs(commercials.get("total_capex_incl_gst_cr", 0.0) - expected_incl)
            if diff > 0.05:
                findings.append({
                    "pillar": "Commercial Integrity",
                    "severity": "CRITICAL",
                    "item": "Commercial Subtotal Mismatch",
                    "details": f"Total CAPEX incl. GST (₹ {commercials.get('total_capex_incl_gst_cr')} Cr) does not reconcile with CAPEX (₹ {commercials.get('total_capex_cr')} Cr) + 18% GST (₹ {gst_l/100:.2f} Cr)."
                })

        # Check for unpriced placeholders
        if commercials.get("has_unpriced_placeholders"):
            findings.append({
                "pillar": "Commercial Integrity",
                "severity": "HIGH",
                "item": "Unquoted BOQ Rates Detected",
                "details": f"{commercials.get('missing_rate_items_count')} BOQ line item(s) are marked as '[Rate TBD - Vendor Quote Needed]'. Vendor quotes required prior to commercial binding offer."
            })

    def _check_document_quality(self, proposal, findings):
        full_text = proposal.get("full_markdown", "")

        # Check for leftover template variables like {{client}} or [INSERT]
        leftover_matches = re.findall(r'(\{\{[^}]+\}\}|\[INSERT[^\]]*\]|<TODO[^>]*>)', full_text, re.I)
        if leftover_matches:
            findings.append({
                "pillar": "Document Quality",
                "severity": "CRITICAL",
                "item": "Unresolved Template Placeholders",
                "details": f"Detected unresolved template tags in document: {', '.join(leftover_matches[:3])}."
            })

        # Check for currency formatting
        if "Rs." in full_text or "INR" in full_text:
            findings.append({
                "pillar": "Document Quality",
                "severity": "LOW",
                "item": "Currency Formatting Consistency",
                "details": "Recommend standardizing currency symbol to '₹' throughout all narrative text and tables."
            })
