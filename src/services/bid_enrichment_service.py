"""
LLM-powered bid enrichment using AWS Bedrock Claude.
Extracts structured fields (est. value, EMD, experience, turnover, remarks)
from GeM bid detail page text.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "au.anthropic.claude-sonnet-4-6"
DEFAULT_REGION = "ap-southeast-2"

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
    """Extract structured bid fields using AWS Bedrock Claude."""

    def __init__(self):
        self.model_id = os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        self.region = os.getenv("AWS_REGION", DEFAULT_REGION)
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3
            api_key = os.getenv("BEDROCK_API_KEY")
            if api_key:
                self._client = boto3.Session(region_name=self.region).client("bedrock-runtime")
            else:
                profile = os.getenv("AWS_PROFILE", "tender")
                try:
                    self._client = boto3.Session(profile_name=profile, region_name=self.region).client("bedrock-runtime")
                except Exception:
                    self._client = boto3.Session(region_name=self.region).client("bedrock-runtime")
            return self._client
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock client: {e}")
            return None

    def is_configured(self) -> bool:
        return self._get_client() is not None

    def extract_bid_fields(
        self,
        bid_number: str,
        title: str,
        buyer: str,
        page_text: str,
    ) -> Dict[str, Any]:
        """
        Send detail page text to Claude for structured field extraction.
        Returns dict with keys: estimated_value_lakh, emd_lakh, experience_years,
        min_turnover_lakh, remarks. Empty dict on failure.
        """
        client = self._get_client()
        if not client or not page_text:
            return {}

        prompt = EXTRACTION_PROMPT.format(
            bid_number=bid_number,
            title=title[:200],
            buyer=buyer[:100],
            page_text=page_text[:8000],
        )

        try:
            res = client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 500, "temperature": 0.0},
            )
            raw = res.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
            m = re.search(r'\{[\s\S]*\}', raw)
            if m:
                parsed = json.loads(m.group(0))
                logger.info(
                    f"Bedrock extracted: est_value={parsed.get('estimated_value_lakh')}, "
                    f"emd={parsed.get('emd_lakh')}, "
                    f"exp={parsed.get('experience_years')} yrs, "
                    f"turnover={parsed.get('min_turnover_lakh')}"
                )
                return parsed
        except Exception as e:
            logger.warning(f"Bedrock extraction failed for {bid_number}: {e}")

        return {}
