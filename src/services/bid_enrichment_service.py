"""
LLM-powered bid enrichment using AWS Bedrock Claude.
Extracts structured fields (est. value, EMD, experience, turnover, remarks)
from GeM bid detail page text.

Supports two auth paths:
  1. boto3 (AWS CLI profile / IAM credentials) — for local development
  2. Bearer token via BEDROCK_API_KEY env var — for CI / GitHub Actions
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

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
        self.api_key = os.getenv("BEDROCK_API_KEY")
        self.runtime_url = f"https://bedrock-runtime.{self.region}.amazonaws.com"
        self._boto_client = None
        self._boto_tested = False

    def _get_boto_client(self):
        """Try to get a boto3 Bedrock client (for local dev with AWS profile)."""
        if self._boto_tested:
            return self._boto_client
        self._boto_tested = True
        try:
            import boto3
            profile = os.getenv("AWS_PROFILE", "tender")
            try:
                self._boto_client = boto3.Session(
                    profile_name=profile, region_name=self.region
                ).client("bedrock-runtime")
            except Exception:
                self._boto_client = boto3.Session(
                    region_name=self.region
                ).client("bedrock-runtime")
            # Validate credentials with a no-op — boto3 creates clients lazily
            self._boto_client.meta.region_name
            return self._boto_client
        except Exception as e:
            logger.debug(f"boto3 client init failed (will use API key): {e}")
            self._boto_client = None
            return None

    def is_configured(self) -> bool:
        return self._get_boto_client() is not None or bool(self.api_key)

    def _call_bedrock(
        self,
        messages: List[Dict],
        max_tokens: int = 500,
        temperature: float = 0.0,
    ) -> Optional[str]:
        """Call Bedrock Converse API. Returns the response text or None on failure.

        Path A: boto3 client.converse() (AWS CLI / IAM credentials)
        Path B: Raw HTTP POST with Bearer token (BEDROCK_API_KEY)
        """
        # Path A: boto3
        boto_client = self._get_boto_client()
        if boto_client:
            try:
                res = boto_client.converse(
                    modelId=self.model_id,
                    messages=messages,
                    inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
                )
                return (
                    res.get("output", {})
                    .get("message", {})
                    .get("content", [{}])[0]
                    .get("text", "")
                )
            except Exception as e:
                logger.info(f"boto3 converse failed, trying API key fallback: {e}")

        # Path B: Bearer token
        if not self.api_key:
            logger.warning("No Bedrock credentials available (no boto3 and no BEDROCK_API_KEY)")
            return None

        url = f"{self.runtime_url}/model/{self.model_id}/converse"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return (
                    data.get("output", {})
                    .get("message", {})
                    .get("content", [{}])[0]
                    .get("text", "")
                )
            else:
                logger.warning(
                    f"Bedrock API returned {res.status_code}: {res.text[:200]}"
                )
                return None
        except Exception as e:
            logger.warning(f"Bedrock API request failed: {e}")
            return None

    def extract_bid_fields(
        self,
        bid_number: str,
        title: str,
        buyer: str,
        page_text: str,
    ) -> Dict[str, Any]:
        """Send detail page text to Claude for structured field extraction.

        Returns dict with keys: estimated_value_lakh, emd_lakh, experience_years,
        min_turnover_lakh, remarks. Empty dict on failure.
        """
        if not page_text:
            return {}

        prompt = EXTRACTION_PROMPT.format(
            bid_number=bid_number,
            title=title[:200],
            buyer=buyer[:100],
            page_text=page_text[:8000],
        )

        messages = [{"role": "user", "content": [{"text": prompt}]}]
        raw = self._call_bedrock(messages, max_tokens=500, temperature=0.0)

        if not raw:
            return {}

        try:
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
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse Bedrock response for {bid_number}: {e}")

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

        messages = [{"role": "user", "content": [{"text": prompt}]}]
        raw = self._call_bedrock(messages, max_tokens=10, temperature=0.0)

        if not raw:
            return True

        verdict = "YES" in raw.upper()
        logger.info(f"Relevance check for '{title[:50]}': {raw.strip()}")
        return verdict
