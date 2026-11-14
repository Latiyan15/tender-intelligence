"""
LLM-powered bid enrichment using Google Gemini Flash.
Extracts structured fields (est. value, EMD, experience, turnover, remarks)
from GeM bid detail page text.

Uses Gemini 2.0 Flash free tier (15 RPM, 1500 RPD, 1M TPM).
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"

EXTRACTION_PROMPT = """You are analyzing a Government e-Marketplace (GeM) bid for Nikom InfraSolutions.
Extract the following fields from the bid detail page text below. Return ONLY valid JSON.

BID: {bid_number}
TITLE: {title}
BUYER: {buyer}

DETAIL PAGE TEXT:
{page_text}

Extract and return this JSON (use null for fields you cannot find):
{{
  "estimated_value_lakh": <number in Rs lakhs, or null>,
  "emd_lakh": <number in Rs lakhs, or null>,
  "experience_years": <number of years of past experience required, or null>,
  "min_turnover_lakh": <minimum average annual turnover in Rs lakhs, or null>,
  "remarks": "<concise 1-3 sentence summary of key bid terms: warranty period, delivery timeline, bid type (single/two-packet), reverse auction status, bid opening date, buyer contact info, site visit requirements, any special conditions. Keep under 200 chars.>"
}}"""


class BidEnrichmentService:
    """Extract structured bid fields using Google Gemini Flash."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._model = None

        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _get_model(self):
        if self._model is None and self.api_key:
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _call_gemini(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.0,
    ) -> Optional[str]:
        """Call Gemini API. Returns response text or None on failure."""
        model = self._get_model()
        if not model:
            logger.warning("Gemini not configured (no GEMINI_API_KEY)")
            return None

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
            return None

    def extract_bid_fields(
        self,
        bid_number: str,
        title: str,
        buyer: str,
        page_text: str,
    ) -> Dict[str, Any]:
        """Send detail page text to Gemini for structured field extraction.

        Returns dict with keys: estimated_value_lakh, emd_lakh, experience_years,
        min_turnover_lakh, remarks. Empty dict on failure.
        """
        if not page_text:
            return {}

        prompt = EXTRACTION_PROMPT.format(
            bid_number=bid_number,
            title=title[:200],
            buyer=buyer[:100],
            page_text=page_text[:12000],
        )

        raw = self._call_gemini(prompt, max_tokens=500, temperature=0.0)

        if not raw:
            return {}

        try:
            m = re.search(r'\{[\s\S]*\}', raw)
            if m:
                parsed = json.loads(m.group(0))
                logger.info(
                    f"Gemini extracted: est_value={parsed.get('estimated_value_lakh')}, "
                    f"emd={parsed.get('emd_lakh')}, "
                    f"exp={parsed.get('experience_years')} yrs, "
                    f"turnover={parsed.get('min_turnover_lakh')}"
                )
                return parsed
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse Gemini response for {bid_number}: {e}")

        return {}

    def check_bid_relevance(
        self,
        title: str,
        buyer: str,
        page_text: str,
    ) -> bool:
        """Quick binary relevance check for borderline bids.

        Uses minimal tokens for cost efficiency. Returns True on failure
        (false negatives are worse than false positives).
        """
        if not page_text:
            return True

        prompt = (
            "You are filtering Government e-Marketplace (GeM) bids for "
            "Nikom InfraSolutions, a company that works in: data centre cooling, "
            "precision air conditioning, HVAC for server rooms / clean rooms, "
            "online UPS / DG sets / electrical infrastructure, fire detection AMC, "
            "server racks & structured cabling, and HPC site-prep.\n\n"
            f"BID TITLE: {title[:200]}\n"
            f"BUYER: {buyer[:100]}\n\n"
            f"DETAIL PAGE TEXT (excerpt):\n{page_text[:3000]}\n\n"
            "Is this bid relevant to Nikom's business domains listed above? "
            "Reply with ONLY \"YES\" or \"NO\"."
        )

        raw = self._call_gemini(prompt, max_tokens=10, temperature=0.0)

        if not raw:
            return True

        verdict = "YES" in raw.upper()
        logger.info(f"Relevance check for '{title[:50]}': {raw.strip()}")
        return verdict
