"""
Feasibility Engine Module
Compares extracted tender data against Nikom's business profile and capabilities.
Evaluates technical scope alignment, eligibility feasibility, commercial viability,
and retrieval completeness to deliver an automated GO / CAUTION / NO-GO verdict.
"""

import re
import logging
from typing import Dict, Any, List, Tuple
from src.models.tender import TenderRecord, ReadinessClassification, FieldStatus
from src.matcher.nikom_profile import NIKOM_PROFILE, NikomProfile

logger = logging.getLogger(__name__)


class FeasibilityEngine:
    """Evaluates tender records against Nikom InfraSolutions Pvt. Ltd. profile."""

    def __init__(self, profile: NikomProfile = NIKOM_PROFILE):
        self.profile = profile

    def evaluate_tender(self, tender: TenderRecord) -> Dict[str, Any]:
        """
        Comprehensive feasibility evaluation of a tender for Nikom.
        Returns detailed scoring breakdown, identified gaps, readiness classification, and verdict.
        """
        combined_text = self._build_searchable_corpus(tender)

        # 1. Scope / Domain Alignment (0 - 100)
        scope_score, matched_domains, is_excluded = self._score_scope_alignment(combined_text)

        # 2. Eligibility & Qualification Feasibility (0 - 100)
        eligibility_score, eligibility_gaps = self._score_eligibility(tender, combined_text)

        # 3. Commercial Viability (0 - 100)
        commercial_score, commercial_notes = self._score_commercial_viability(tender)

        # 4. Retrieval Completeness & Decision Readiness (0 - 100)
        retrieval_score, missing_fields = self._score_retrieval_completeness(tender)

        # Calculate weighted composite score
        # Scope is 40%, Eligibility is 25%, Commercial is 20%, Completeness is 15%
        composite_score = round(
            (scope_score * 0.40) +
            (eligibility_score * 0.25) +
            (commercial_score * 0.20) +
            (retrieval_score * 0.15),
            2
        )

        # Determine Verdict & Readiness
        verdict, readiness, verdict_reason = self._determine_verdict(
            composite_score=composite_score,
            scope_score=scope_score,
            is_excluded=is_excluded,
            eligibility_gaps=eligibility_gaps,
            missing_fields=missing_fields,
            retrieval_score=retrieval_score
        )

        # Update tender model state
        tender.readiness = readiness
        tender.readiness_gaps = eligibility_gaps + missing_fields
        tender.decision_notes = verdict_reason

        evaluation_result = {
            "tender_id": tender.tender_id,
            "title": tender.title,
            "verdict": verdict,  # "GO", "CAUTION", "NO-GO"
            "readiness": readiness.value,  # "READY", "PARTIALLY_READY", "NOT_READY"
            "composite_score": composite_score,
            "subscores": {
                "scope_alignment": scope_score,
                "eligibility_feasibility": eligibility_score,
                "commercial_viability": commercial_score,
                "retrieval_completeness": retrieval_score
            },
            "matched_domains": matched_domains,
            "is_excluded_domain": is_excluded,
            "eligibility_gaps": eligibility_gaps,
            "commercial_notes": commercial_notes,
            "missing_fields": missing_fields,
            "verdict_reason": verdict_reason
        }

        return evaluation_result

    def _build_searchable_corpus(self, tender: TenderRecord) -> str:
        """Combine all text snippets into a single searchable string."""
        parts = []
        if tender.title:
            parts.append(tender.title)
        if tender.department:
            parts.append(tender.department)
        if tender.issuing_organization:
            parts.append(tender.issuing_organization)
        if tender.scope_of_work and tender.scope_of_work.raw_text:
            parts.append(tender.scope_of_work.raw_text)

        for doc in tender.documents:
            if doc.extracted_text:
                parts.append(doc.extracted_text[:10000])

        return " ".join(parts).lower()

    def _score_scope_alignment(self, text: str) -> Tuple[float, List[str], bool]:
        """Score alignment against Nikom's core and adjacent domain keywords."""
        if not text:
            return 0.0, [], False

        # Check exclusions first
        for ex in self.profile.excluded_domains:
            if re.search(r'\b' + re.escape(ex) + r'\b', text):
                # Check if it also has strong DC keywords
                has_dc = any(k in text for k in ["data center", "datacenter", "server room", "precision air conditioning"])
                if not has_dc:
                    return 0.0, [f"Excluded domain detected: {ex}"], True

        matched = []
        high_matches = 0
        for kw in self.profile.high_match_keywords:
            if kw in text:
                high_matches += 1
                matched.append(kw)

        adjacent_matches = 0
        for kw in self.profile.adjacent_match_keywords:
            if kw in text:
                adjacent_matches += 1
                matched.append(kw)

        if high_matches >= 3:
            score = 100.0
        elif high_matches >= 2:
            score = 90.0
        elif high_matches == 1:
            score = 75.0
        elif adjacent_matches >= 2:
            score = 60.0
        elif adjacent_matches == 1:
            score = 45.0
        else:
            score = 10.0

        return score, matched[:8], False

    def _score_eligibility(self, tender: TenderRecord, text: str) -> Tuple[float, List[str]]:
        """Score bidder qualification criteria against Nikom capacity."""
        score = 80.0  # Base assumption of standard capacity
        gaps = []

        # Check turnover
        if tender.minimum_turnover and tender.minimum_turnover.normalized_value:
            req_turnover = float(tender.minimum_turnover.normalized_value)
            if req_turnover > self.profile.max_turnover_capacity_inr:
                score -= 40.0
                gaps.append(f"Turnover requirement (Rs. {req_turnover:,.0f}) exceeds Nikom capacity (Rs. {self.profile.max_turnover_capacity_inr:,.0f})")
            elif req_turnover > (self.profile.max_turnover_capacity_inr * 0.5):
                score -= 10.0
                gaps.append(f"High turnover requirement (Rs. {req_turnover:,.0f}) requires consortium / JV")
            else:
                score += 10.0

        # Check OEM requirement
        if tender.oem_requirements and tender.oem_requirements.normalized_value:
            # Check if partner OEMs are mentioned or allowed
            partner_found = any(oem.lower() in text for oem in self.profile.partner_oems)
            if partner_found:
                score += 10.0
            else:
                gaps.append("OEM Authorization / MAF required - need partner alignment (e.g. Schneider/Vertiv)")

        score = max(0.0, min(100.0, score))
        return score, gaps

    def _score_commercial_viability(self, tender: TenderRecord) -> Tuple[float, List[str]]:
        """Score estimated contract value against Nikom project sweet spot."""
        notes = []
        if not tender.estimated_value or not tender.estimated_value.normalized_value:
            notes.append("Estimated value not published in tender notice")
            return 60.0, notes

        val = float(tender.estimated_value.normalized_value)
        if self.profile.sweet_spot_min_inr <= val <= self.profile.sweet_spot_max_inr:
            score = 100.0
            notes.append(f"Optimal project size: Rs. {val:,.0f} (within sweet spot Rs. 25L - Rs. 25Cr)")
        elif val < self.profile.min_tender_value_inr:
            score = 40.0
            notes.append(f"Below minimum threshold: Rs. {val:,.0f} < Rs. 5L")
        elif val > self.profile.single_work_capacity_inr:
            score = 50.0
            notes.append(f"Exceeds single work capacity: Rs. {val:,.0f} > Rs. 30Cr (Requires consortium)")
        else:
            score = 75.0
            notes.append(f"Viable contract size: Rs. {val:,.0f}")

        return score, notes

    def _score_retrieval_completeness(self, tender: TenderRecord) -> Tuple[float, List[str]]:
        """Evaluate whether sufficient data was retrieved to make an informed bid decision."""
        missing = []
        points = 0

        # Title and reference
        if tender.title and len(tender.title) > 10:
            points += 15
        else:
            missing.append("Missing detailed title")

        # Submission deadline
        if tender.submission_deadline and tender.submission_deadline.status == FieldStatus.PRESENT_EXTRACTED:
            points += 20
        else:
            missing.append("Missing submission deadline")

        # Commercial terms (EMD / Value)
        if tender.emd_amount and tender.emd_amount.status == FieldStatus.PRESENT_EXTRACTED:
            points += 20
        else:
            missing.append("Missing EMD terms")

        if tender.estimated_value and tender.estimated_value.status == FieldStatus.PRESENT_EXTRACTED:
            points += 15
        else:
            missing.append("Missing estimated value")

        # Scope / Documents
        if tender.documents and any(d.downloaded for d in tender.documents):
            points += 20
        elif tender.scope_of_work and tender.scope_of_work.status == FieldStatus.PRESENT_EXTRACTED:
            points += 15
        else:
            missing.append("Missing tender specification document or full scope")

        # Issuing org
        if tender.issuing_organization:
            points += 10
        else:
            missing.append("Missing issuing authority")

        return float(min(100, points)), missing

    def _determine_verdict(
        self,
        composite_score: float,
        scope_score: float,
        is_excluded: bool,
        eligibility_gaps: List[str],
        missing_fields: List[str],
        retrieval_score: float
    ) -> Tuple[str, ReadinessClassification, str]:
        """Synthesize scores and conditions into GO / CAUTION / NO-GO verdict."""
        if is_excluded or scope_score < 30.0:
            return (
                "NO-GO",
                ReadinessClassification.READY,
                "Out of domain: Work scope does not match Nikom's core data center, power, cooling, or IT capabilities."
            )

        if any("exceeds Nikom capacity" in g for g in eligibility_gaps):
            return (
                "NO-GO",
                ReadinessClassification.READY,
                "Disqualified: Minimum financial turnover or capacity threshold exceeds Nikom parameters."
            )

        if retrieval_score < 40.0:
            return (
                "CAUTION",
                ReadinessClassification.NOT_READY,
                f"Incomplete Data: Insufficient public details retrieved to make a conclusive bid determination ({', '.join(missing_fields[:2])})."
            )

        if composite_score >= 70.0 and scope_score >= 60.0:
            if retrieval_score >= 70.0:
                return (
                    "GO",
                    ReadinessClassification.READY,
                    "High Feasibility: Strong technical scope alignment with Nikom capabilities, viable commercial size, and complete public tender specifications."
                )
            else:
                return (
                    "GO (PROVISIONAL)",
                    ReadinessClassification.PARTIALLY_READY,
                    "Favorable Scope: High business alignment, but full tender documents require manual portal download."
                )

        if composite_score >= 50.0:
            return (
                "CAUTION",
                ReadinessClassification.PARTIALLY_READY,
                f"Requires Review: Adjacent technical scope or qualification constraints ({'; '.join(eligibility_gaps or missing_fields[:2])})."
            )

        return (
            "NO-GO",
            ReadinessClassification.READY,
            "Low Feasibility: Composite technical and commercial score below viable bidding threshold."
        )
