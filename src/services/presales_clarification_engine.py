"""
Presales Interactive Clarification & Q&A Engine
===============================================
Identifies missing information, unresolved technical assumptions, and conflicting clauses.
Generates prioritized, non-overwhelming follow-up questions grouped by discipline,
and processes user answers to update the project requirement state.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ClarificationEngine:
    """
    Manages interactive inquiry and gap resolution between the pre-sales agent and user.
    """

    def generate_clarification_questions(
        self,
        requirements: Dict[str, Any],
        max_questions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Produces a prioritized list of high-impact questions to clarify missing
        parameters or confirm critical assumptions before drafting.
        """
        questions = []
        buckets = requirements.get("buckets", {})
        missing = buckets.get("missing_information", [])
        assumptions = buckets.get("engineering_assumptions", [])
        conflicts = buckets.get("conflicting_information", [])
        classification = requirements.get("classification", {})
        cat = classification.get("primary_category", "other_custom")

        q_id = 1

        # Priority 1: Conflicting requirements (High Risk)
        for conf in conflicts:
            questions.append({
                "question_id": f"Q-{q_id:02d}",
                "category": "Technical Conflict",
                "priority": "HIGH",
                "question": f"Conflict Detected: {conf.get('conflict')} - Would you like us to proceed with the recommended resolution ({conf.get('reconciliation')})?",
                "context": "Conflicting tender clauses or specification discrepancy",
                "options": ["Approve Recommended Resolution", "Keep Stated Specification", "Provide Custom Input"],
                "status": "pending"
            })
            q_id += 1

        # Priority 2: Critical missing information
        for m in missing:
            if m.get("impact", "").upper() == "CRITICAL":
                questions.append({
                    "question_id": f"Q-{q_id:02d}",
                    "category": "Mandatory Requirement",
                    "priority": "CRITICAL",
                    "question": m.get("question", f"Please specify {m.get('item')}."),
                    "context": f"Missing critical parameter: {m.get('item')}",
                    "status": "pending"
                })
                q_id += 1

        # Priority 3: Non-critical missing information
        for m in missing:
            if m.get("impact", "").upper() != "CRITICAL":
                questions.append({
                    "question_id": f"Q-{q_id:02d}",
                    "category": "Scope & Sizing",
                    "priority": "MEDIUM",
                    "question": m.get("question", f"Please clarify {m.get('item')}."),
                    "context": f"Missing parameter: {m.get('item')}",
                    "status": "pending"
                })
                q_id += 1

        # Priority 4: Significant engineering assumptions requiring confirmation
        # Only ask if there is an actual critical gap or conflict, otherwise assumptions are accepted by default
        if len(missing) > 0 or len(conflicts) > 0:
            for a in assumptions:
                questions.append({
                    "question_id": f"Q-{q_id:02d}",
                    "category": "Engineering Assumption",
                    "priority": "MEDIUM",
                    "question": f"We have assumed {a.get('item')} is '{a.get('value')}'. Does this match your client's expectation?",
                    "context": a.get("action", "Default engineering assumption"),
                    "options": ["Confirm Assumption", "Modify Value"],
                    "status": "pending"
                })
                q_id += 1

        # Return grouped and capped to max_questions so the user is never overwhelmed
        return questions[:max_questions]

    def apply_user_answer(
        self,
        requirements: Dict[str, Any],
        question_id: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        Updates the requirement state when a user answers a question.
        Moves answered items from 'missing' or 'assumptions' into 'verified_facts'.
        """
        buckets = requirements.setdefault("buckets", {})
        verified = buckets.setdefault("verified_facts", [])
        missing = buckets.get("missing_information", [])
        assumptions = buckets.get("engineering_assumptions", [])

        # Find and resolve in missing
        updated_missing = []
        for m in missing:
            if question_id in m.get("question_id", "") or m.get("item", "").lower() in answer.lower():
                verified.append({
                    "item": m.get("item", "Clarified Parameter"),
                    "value": answer,
                    "confidence": "HIGH (User Confirmed)",
                    "resolved_via": question_id
                })
            else:
                updated_missing.append(m)
        buckets["missing_information"] = updated_missing

        # Also log in verified facts
        verified.append({
            "item": f"Clarification ({question_id})",
            "value": answer,
            "confidence": "HIGH",
            "source": "Sales Engineer Response"
        })

        return requirements
