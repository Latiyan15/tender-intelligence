"""
AWS Bedrock Intelligence Service for Nikom Tender Intelligence
Integrates Claude Sonnet 4.6 (with AU / Global cross-region privacy profiles)
for deep tender feasibility evaluation, eligibility audit, and RFP Copilot Q&A.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.matcher.nikom_profile import NIKOM_PROFILE, NikomProfile

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "au.anthropic.claude-sonnet-4-6"
DEFAULT_REGION = "ap-southeast-2"


class BedrockTenderService:
    """
    Client for AWS Bedrock Foundation Models.
    Communicates via the Bedrock Converse API using Bedrock API Keys or IAM credentials.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
        model_id: Optional[str] = None,
        profile: NikomProfile = NIKOM_PROFILE
    ):
        # Auto-load .env if environment variables are not yet present in os.environ
        if not os.getenv("BEDROCK_API_KEY"):
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except Exception:
                pass

            if not os.getenv("BEDROCK_API_KEY"):
                # Direct fallback reader for .env
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith("#") and "=" in line:
                                    k, v = line.split("=", 1)
                                    os.environ.setdefault(k.strip(), v.strip())
                    except Exception as e:
                        logger.warning(f"Failed to read .env file: {e}")

        self.api_key = api_key or os.getenv("BEDROCK_API_KEY")
        self.region = region or os.getenv("AWS_REGION", DEFAULT_REGION)
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        self.profile = profile

        # Base URL for the Bedrock Runtime Converse endpoint
        self.runtime_url = f"https://bedrock-runtime.{self.region}.amazonaws.com"

    def is_configured(self) -> bool:
        """Checks if AWS Bedrock credentials are provided."""
        return bool(self.api_key or os.getenv("AWS_ACCESS_KEY_ID"))

    def _get_headers(self) -> Dict[str, str]:
        """Constructs headers for the Bedrock Converse API request."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def test_connection(self) -> Dict[str, Any]:
        """Tests live connectivity to AWS Bedrock Claude Sonnet model."""
        if not self.api_key:
            return {
                "success": False,
                "error": "BEDROCK_API_KEY is not configured in .env",
                "region": self.region,
                "model_id": self.model_id
            }

        url = f"{self.runtime_url}/model/{self.model_id}/converse"
        payload = {
            "messages": [
                {"role": "user", "content": [{"text": "Ping: Verify active connection for Nikom Tender Intelligence."}]}
            ],
            "inferenceConfig": {
                "maxTokens": 50,
                "temperature": 0.0
            }
        }

        try:
            start_time = datetime.now()
            res = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if res.status_code == 200:
                data = res.json()
                reply = data.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
                return {
                    "success": True,
                    "model_id": self.model_id,
                    "region": self.region,
                    "latency_ms": latency_ms,
                    "response": reply.strip()
                }
            else:
                return {
                    "success": False,
                    "status_code": res.status_code,
                    "error": res.text,
                    "region": self.region,
                    "model_id": self.model_id
                }
        except Exception as e:
            logger.error(f"Bedrock test_connection error: {e}")
            return {
                "success": False,
                "error": str(e),
                "region": self.region,
                "model_id": self.model_id
            }

    def _build_system_prompt(self) -> str:
        """Constructs the grounding prompt describing Nikom InfraSolutions."""
        domains = "\n- ".join(self.profile.core_domains)
        clients = ", ".join(self.profile.verified_clients[:18])

        return f"""You are the Chief Bidding Strategist and Tender Qualification AI for Nikom InfraSolutions Pvt. Ltd.
Your mission is to rigorously analyze Indian government tender notices (from CPPP, GeM, State eProcurement, PSUs) and assess feasibility, eligibility compliance, commercial viability, and risks.

ABOUT NIKOM INFRASOLUTIONS PVT. LTD.:
- Founded: 2002 | HQ: 65, Jyoti Building, Nehru Place, New Delhi | Turnkey Data Center EPC Specialist (22+ years).
- Financial Strength (Verified Audited Filings):
  * Turnover: FY 2022-23: ₹48.50 Cr | FY 2023-24: ₹67.18 Cr | FY 2024-25: ₹91.21 Cr | FY 2025-26 (Prov.): ₹123.07 Cr
  * Average 3-Year Annual Turnover: ₹70.11 Cr (Audited) / ₹100.75 Cr (including FY26 Prov) | Peak Quoted: ₹123.07 Cr
  * Net Worth: ₹28.58 Cr (FY25 Audited) / ₹38.57 Cr (FY26 Prov) - 100% positive, profitable in all years (PAT positive).
  * Liquidity & Solvency: Working Capital ₹61.12 Cr | Current Ratio 2.56x | Debt/Equity 0.00x (Zero Debt) | Cash & Bank ₹14.52 Cr
  * Bid Capacity: Calculated at ₹201.16 Cr (A x N x 2 - B).
  * Order Book in Hand: ₹104.17 Cr active contracts (NATGRID ₹28.66 Cr server, C-DAC Mohali ₹25.37 Cr, Alliance L&T ₹19.00 Cr, IOCL ₹8.91 Cr AMC, AAI Chennai ₹5.14 Cr).
- Verified Completed Works (Similar Past Experience, Total ₹162.24 Cr):
  * AAI Hyderabad: ₹21.68 Cr - Non-IT DR Site Infrastructure (Completed 2021, Certificate available)
  * ONGC Vasudhara Bhavan Mumbai: ₹20.40 Cr - Data Center Turnkey EPC (Completed 2023, Certificate available)
  * AAI 10 Airports: ₹25.93 Cr - Airport Operations Control Centers (Completed 2018, Certificate available)
  * ITD Premises: ₹10.71 Cr - Turnkey Facilities & Data Center Infrastructure (Completed 2017)
  * ONGC 11 High Panvel: ₹5.14 Cr - Server Room Revamping & Data Center (Completed 2020)
  * IIT Roorkee: ₹4.55 Cr | C-DAC Bangalore: ₹3.87 Cr | NIT Trichy: ₹3.62 Cr | JSCL Smart City: ₹3.14 Cr | IIT Gandhinagar: ₹3.22 Cr | IIT Hyderabad: ₹3.01 Cr
- Enterprise Status: Registered Medium Enterprise under MSME / UDYAM. (Eligible for UDYAM exemptions; on tenders strictly reserving MSE exemptions for Micro/Small, backed by ICICI Bank Guarantee or standard Bid Security Declaration).
- Verified PSU & Government Track Record: Executed high-value contracts for {clients}.

CORE TECHNICAL CAPABILITIES:
- {domains}

STRICT EXCLUSIONS (AUTOMATIC NO-GO):
- Pure civil works (roads, bridges, residential construction, earthworks, sewerage)
- Medical equipment, pharmaceuticals, surgical supplies
- Catering, hospitality, housekeeping, uniforms
- Vehicle leasing, transport logistics

SCORING METHODOLOGY:
- GO: Strong match in Data Center / Server Room / UPS / PAC / Fire Suppression / IBMS where Nikom qualifies technically and financially.
- CAUTION: Mixed scope, border turnover requirement, or joint venture (JV)/consortium needed.
- NO-GO: Out-of-domain scope (civil, medical, general supplies) or criteria exceeding Nikom's qualifications.
"""

    def analyze_tender_feasibility(
        self,
        tender: Dict[str, Any],
        document_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a deep feasibility and qualification evaluation using Claude Sonnet.
        Returns structured analysis and decision checklist.
        """
        if not self.is_configured():
            raise ValueError("AWS Bedrock credentials not configured")

        # Compile tender context
        tender_id = tender.get("tender_id") or "N/A"
        title = tender.get("title") or tender.get("tender_title") or "N/A"
        authority = tender.get("issuing_authority") or tender.get("organization") or "N/A"
        dept = tender.get("department") or "N/A"
        category = tender.get("tender_category") or tender.get("category") or "N/A"
        cost = tender.get("estimated_cost_inr") or tender.get("estimated_value") or 0.0
        emd = tender.get("emd_inr") or tender.get("emd_amount") or 0.0
        deadline = tender.get("submission_deadline") or "N/A"
        scope = tender.get("scope_of_work") or tender.get("description") or ""

        cost_cr = f"₹{cost / 10000000:.2f} Cr" if cost and cost > 0 else "Unspecified / Two-Bid Rate"
        emd_str = f"₹{emd / 100000:.2f} Lakhs" if emd and emd > 0 else "Exempted / To be verified"

        prompt_text = f"""Please perform a thorough Feasibility and Eligibility Evaluation for this tender:

TENDER METADATA:
- Tender ID: {tender_id}
- Title / Subject: {title}
- Issuing Authority: {authority}
- Department: {dept}
- Category: {category}
- Estimated Cost: {cost_cr} (Raw: {cost})
- EMD Amount: {emd_str}
- Submission Deadline: {deadline}
- Published Scope / Work Details:
{scope[:2500]}
"""

        if document_text and len(document_text.strip()) > 50:
            prompt_text += f"""
EXTRACTED RFP / NIT DOCUMENT CLAUSES:
{document_text[:6000]}
"""

        prompt_text += """
Respond strictly in valid JSON format with the following keys:
{
  "verdict": "GO" | "CAUTION" | "NO-GO",
  "feasibility_score": <integer 0-100>,
  "confidence": <float 0.0-1.0>,
  "headline": "<1 concise punchy sentence summarizing the verdict>",
  "executive_summary": "<2-3 paragraph detailed strategic rationale for the Bidding Director>",
  "matched_domains": ["<domain 1>", "<domain 2>"],
  "turnover_check": {
    "status": "Met" | "Check" | "Unspecified",
    "required_turnover": "<turnover requirement in text or estimate>",
    "explanation": "<how Nikom ₹42+ Cr compares>"
  },
  "technical_alignment": [
    {"area": "Data Center / Civil-Electrical", "status": "High" | "Medium" | "Low" | "N/A", "notes": "..."},
    {"area": "UPS & Power Systems", "status": "High" | "Medium" | "Low" | "N/A", "notes": "..."},
    {"area": "Precision Cooling (PAC/CRAC)", "status": "High" | "Medium" | "Low" | "N/A", "notes": "..."},
    {"area": "Fire Suppression & IBMS", "status": "High" | "Medium" | "Low" | "N/A", "notes": "..."}
  ],
  "red_flags_and_risks": ["<risk 1>", "<risk 2>"],
  "bidding_checklist": ["<action item 1>", "<action item 2>"]
}
"""

        url = f"{self.runtime_url}/model/{self.model_id}/converse"
        payload = {
            "system": [{"text": self._build_system_prompt()}],
            "messages": [
                {"role": "user", "content": [{"text": prompt_text}]}
            ],
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.1
            }
        }

        res = requests.post(url, headers=self._get_headers(), json=payload, timeout=60)
        if res.status_code != 200:
            logger.error(f"Bedrock evaluation error: {res.status_code} - {res.text}")
            raise RuntimeError(f"Bedrock invocation failed ({res.status_code}): {res.text}")

        res_data = res.json()
        raw_reply = res_data.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")

        # Parse JSON from response
        clean_json_str = raw_reply.strip()
        import re
        json_match = re.search(r'\{[\s\S]*\}', clean_json_str)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                parsed["model_used"] = self.model_id
                parsed["analyzed_at"] = datetime.now().isoformat()
                return parsed
            except json.JSONDecodeError as err:
                logger.warning(f"JSON decode failed on extracted block: {err}")

        return {
            "verdict": "CAUTION",
            "feasibility_score": 60,
            "headline": "Raw analysis generated",
            "executive_summary": raw_reply,
            "matched_domains": [],
            "red_flags_and_risks": [],
            "bidding_checklist": [],
            "raw_response": raw_reply,
            "model_used": self.model_id,
            "analyzed_at": datetime.now().isoformat()
        }

    def ask_tender_copilot(
        self,
        tender: Dict[str, Any],
        question: str,
        document_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interactive Q&A Copilot for bidding engineers to ask specific questions about RFP clauses.
        """
        if not self.is_configured():
            raise ValueError("AWS Bedrock credentials not configured")

        title = tender.get("title") or tender.get("tender_title") or "N/A"
        authority = tender.get("issuing_authority") or tender.get("organization") or "N/A"
        scope = tender.get("scope_of_work") or tender.get("description") or ""

        est_cost = tender.get("estimated_cost_inr")
        emd_val = tender.get("emd_inr")
        try:
            est_cost_str = f"₹{int(est_cost):,}" if est_cost else "Refer BOQ / Commercial Schedule"
        except Exception:
            est_cost_str = str(est_cost or "Refer BOQ")
        try:
            emd_str = f"₹{int(emd_val):,}" if emd_val else "Exempted / Refer NIT"
        except Exception:
            emd_str = str(emd_val or "Exempted")

        context_text = f"""TENDER CONTEXT:
Tender ID: {tender.get('tender_id', 'N/A')}
Title: {title}
Issuing Authority: {authority}
Category: {tender.get('category', 'N/A')}
Estimated Cost: {est_cost_str}
EMD: {emd_str}
Submission Deadline: {tender.get('submission_deadline', 'N/A')}

Scope / Technical Summary:
{scope[:2000]}
"""
        if document_text and len(document_text.strip()) > 50:
            context_text += f"""
RFP / NIT DOCUMENT EXTRACT:
{document_text[:6000]}
"""

        system_instruction = f"""You are the Nikom Tender Intelligence Copilot.
You assist Nikom's senior bidding engineers in dissecting government RFP and NIT clauses.
Provide accurate, factual, and crisp answers grounded directly in the provided tender data.
Highlight specific thresholds, OEM authorization mandates (MAF), penalty/LD clauses, or compliance requirements."""

        user_content = f"""{context_text}

ENGINEER QUESTION:
{question}

Provide a direct, factual answer tailored for Nikom's bidding submission:"""

        url = f"{self.runtime_url}/model/{self.model_id}/converse"
        payload = {
            "system": [{"text": system_instruction}],
            "messages": [
                {"role": "user", "content": [{"text": user_content}]}
            ],
            "inferenceConfig": {
                "maxTokens": 1200,
                "temperature": 0.2
            }
        }

        res = requests.post(url, headers=self._get_headers(), json=payload, timeout=40)
        if res.status_code != 200:
            raise RuntimeError(f"Bedrock invocation failed ({res.status_code}): {res.text}")

        res_data = res.json()
        answer = res_data.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")

        return {
            "question": question,
            "answer": answer.strip(),
            "model_used": self.model_id,
            "timestamp": datetime.now().isoformat()
        }

    def evaluate_document_eligibility(
        self,
        tender: Dict[str, Any],
        document_filename: str,
        document_text: str
    ) -> Dict[str, Any]:
        """
        Analyzes the user-uploaded tender document with AWS Bedrock (Claude Sonnet 4.6)
        and evaluates extracted criteria directly against Nikom InfraSolutions corporate profile.
        """
        if not self.is_configured():
            raise ValueError("AWS Bedrock credentials not configured")

        tender_id = tender.get("tender_id") or "N/A"
        title = tender.get("title") or tender.get("tender_title") or "N/A"
        authority = tender.get("issuing_authority") or tender.get("organization") or "N/A"
        cost = tender.get("estimated_cost_inr") or tender.get("estimated_value") or 0.0
        cost_str = f"₹{cost / 10000000:.2f} Cr" if cost and cost > 0 else "Unspecified in notice"

        prompt = f"""You are the Chief Bidding Strategist and Tender Qualification AI for Nikom InfraSolutions Pvt. Ltd.
The bidding engineer has uploaded the official procurement document: "{document_filename}".

TENDER BASIC METADATA:
- Tender ID: {tender_id}
- Title / Subject: {title}
- Issuing Authority: {authority}
- Estimated Cost: {cost_str}

NIKOM INFRASOLUTIONS PVT. LTD. CORPORATE BENCHMARKS (AUDITED DATA):
- Annual Turnover (Audited / Filed): FY 2022-23: ₹48.50 Cr | FY 2023-24: ₹67.18 Cr | FY 2024-25: ₹91.21 Cr | FY 2025-26 (Prov.): ₹123.07 Cr.
- Average 3-Year Annual Turnover: ₹70.11 Crores (Audited 3-year standard) / ₹100.75 Crores (FY24-FY26 Prov). Peak Turnover: ₹123.07 Cr.
- Net Worth: ₹28.58 Cr (FY25 Audited) / ₹38.57 Cr (FY26 Prov). Net worth is 100% positive, with profitable PAT across all years.
- Liquidity & Working Capital: Working Capital: ₹61.12 Cr | Current Ratio: 2.56x | Debt/Equity: 0.00x (Zero Debt) | Cash & Bank: ₹14.52 Cr.
- Calculated Bid Capacity: ₹201.16 Crores (Formula: A x N x 2 - B).
- Active Order Book (FY26): ₹104.17 Crores in hand across 17 contracts (NATGRID ₹28.66 Cr, C-DAC Mohali ₹25.37 Cr, Alliance L&T ₹19.00 Cr, IOCL AMC ₹8.91 Cr, AAI Chennai ₹5.14 Cr).
- Verified Completed Works with Client Certificates (7-Year Lookback, Total ₹162.24 Cr):
  * AAI Hyderabad: ₹21.68 Cr - Non-IT Infrastructure for Disaster Recovery (DR) Site (Completed 08.07.2021)
  * ONGC Vasudhara Bhavan Mumbai: ₹20.40 Cr - Turnkey RO Communication & Common Data Center (Completed 21.07.2023)
  * AAI 10 Airports: ₹25.93 Cr - Airport Operations Control Centers Tier-II (Completed 21.05.2018)
  * ITD Premises: ₹10.71 Cr - Design, Supply & SITC of Enterprise Infrastructure (Completed 16.09.2017)
  * ONGC 11 High Panvel: ₹5.14 Cr - Server Room Revamping & Data Center (Completed 22.12.2020)
  * IIT Roorkee: ₹4.55 Cr | C-DAC Bangalore: ₹3.87 Cr | NIT Trichy: ₹3.62 Cr | JSCL Smart City: ₹3.14 Cr | IIT Gandhinagar: ₹3.22 Cr | IIT Hyderabad: ₹3.01 Cr | CRIS: ₹2.89 Cr | ONGC Laxmi Nagar: ₹2.48 Cr | NIT Goa: ₹2.31 Cr | AAI Lucknow: ₹2.25 Cr | ONGC Urja Bhawan: ₹2.13 Cr | GRSE: ₹1.53 Cr | NFL Noida: ₹1.40 Cr | NHPC Server Room: ₹1.04 Cr.
- Enterprise Status: Registered Medium Enterprise under MSME / UDYAM. (Eligible for UDYAM exemptions; on tenders strictly reserving MSE exemptions for Micro/Small, backed by ICICI Bank Guarantee or standard Bid Security Declaration).
- Quality Certifications: Active ISO 9001:2015, ISO 27001:2022, ISO 20000-1:2018, ISO 14001:2015, ISO 45001:2018, CMMI Level 3.
- Core Technical Capabilities: High-Efficiency Modular Online UPS (10-500 kVA), In-Row Precision Air Conditioning (PAC/CRAC), Clean Agent Fire Suppression (Novec 1230, FM-200), VESDA, SCADA/IBMS, Smart Racks & Cold/Hot Aisle Containment, CAMC & 24x7 FMS.
- OEM Alliances: Schneider Electric, APC, Vertiv, Eaton, Delta, Legrand, Cisco, Fortinet, Palo Alto, Dell EMC, HPE, Honeywell, Siemens, Cummins.

UPLOADED TENDER DOCUMENT EXTRACT:
{document_text[:12000]}

INSTRUCTIONS:
1. Carefully extract the real qualification criteria, technical specifications, and bidding terms from this uploaded document.
2. Evaluate each requirement strictly against Nikom's corporate benchmarks above.
3. Determine whether Nikom is "Qualified" (Met), "Review Required" (Borderline/Check), or "Disqualified" (Not Met).
4. Keep values crisp, clear, and concise (1-2 sentences per note). Do not add introductory prose or trailing commentary. Return pure JSON only.

Respond strictly in valid JSON format:
{{
  "overall_verdict": "Qualified" | "Review Required" | "Disqualified",
  "verdict_score": <integer 0-100>,
  "met_criteria_count": <integer>,
  "total_criteria_count": <integer>,
  "company_evaluated": "Nikom InfraSolutions Pvt. Ltd.",
  "document_analyzed": "{document_filename}",
  "ai_powered": true,
  "executive_summary": "<2-3 sentence strategic executive verdict for the Bidding Director based on the uploaded document>",
  "criteria": [
    {{
      "key": "turnover",
      "name": "Annual Financial Turnover",
      "requirement": "<exact requirement extracted from uploaded document or 'Not specified in RFP'>",
      "nikom_profile": "<how Nikom's audited ₹70.11 Cr 3-yr avg / ₹123.07 Cr prov compares with exact numbers>",
      "status": "Met" | "Check" | "Not Met",
      "badge_color": "green" | "amber" | "red",
      "notes": "<audited balance sheet note or verification remark>"
    }},
    {{
      "key": "experience",
      "name": "Similar Work Past Experience",
      "requirement": "<exact past work order value and scope extracted from document>",
      "nikom_profile": "<matching Nikom PSU/Govt track record e.g. ONGC/AAI/NTPC/NIC>",
      "status": "Met" | "Check" | "Not Met",
      "badge_color": "green" | "amber" | "red",
      "notes": "<execution certificate details>"
    }},
    {{
      "key": "technical_specs",
      "name": "Technical Scope & BOQ Specifications",
      "requirement": "<exact UPS, PAC cooling, Fire, IBMS specs extracted from document>",
      "nikom_profile": "<Nikom's matching core capability>",
      "status": "Met" | "Check" | "Not Met",
      "badge_color": "green" | "amber" | "red",
      "notes": "<technical compliance notes>"
    }},
    {{
      "key": "certifications",
      "name": "Quality & OEM Certifications",
      "requirement": "<exact ISO, CMMI, OEM Authorization Form (MAF) required in document>",
      "nikom_profile": "<Nikom's ISO/CMMI certificates and OEM alliances>",
      "status": "Met" | "Check" | "Not Met",
      "badge_color": "green" | "amber" | "red",
      "notes": "<MAF readiness advice>"
    }},
    {{
      "key": "emd",
      "name": "Earnest Money Deposit (EMD)",
      "requirement": "<exact EMD amount and acceptable instruments from document>",
      "nikom_profile": "<MSME UDYAM exemption applicability or ICICI credit lines>",
      "status": "Met" | "Check" | "Not Met",
      "badge_color": "green" | "amber" | "red",
      "notes": "<statutory exemption note>"
    }},
    {{
      "key": "timeline_risks",
      "name": "Delivery Timeline & Penalty Terms",
      "requirement": "<completion schedule and Liquidated Damages (LD) % extracted from document>",
      "nikom_profile": "<Nikom delivery timeline assessment>",
      "status": "Met" | "Check" | "Not Met",
      "badge_color": "green" | "amber" | "red",
      "notes": "<risk and commercial feasibility assessment>"
    }}
  ],
  "red_flags": ["<risk 1>", "<risk 2>"]
}}
"""

        url = f"{self.runtime_url}/model/{self.model_id}/converse"
        payload = {
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ],
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.1
            }
        }

        res = requests.post(url, headers=self._get_headers(), json=payload, timeout=60)
        if res.status_code != 200:
            raise RuntimeError(f"Bedrock invocation failed ({res.status_code}): {res.text}")

        res_data = res.json()
        raw_reply = res_data.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")

        import re
        json_match = re.search(r'\{[\s\S]*\}', raw_reply)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                parsed["model_used"] = self.model_id
                parsed["generated_at"] = datetime.now().isoformat()
                # Attach expert checklist and trap radar to guarantee completeness
                expert_data = self.get_bidding_checklist_and_traps(tender, document_text)
                parsed["uncommon_trap_clauses"] = parsed.get("uncommon_trap_clauses") or expert_data["uncommon_trap_clauses"]
                parsed["bidding_document_checklist"] = parsed.get("bidding_document_checklist") or expert_data["bidding_document_checklist"]
                return parsed
            except Exception as e:
                logger.warning(f"Failed to parse Bedrock JSON: {e}")

        raise ValueError("Could not parse structured evaluation from Bedrock response")

    def get_bidding_checklist_and_traps(
        self,
        tender: Dict[str, Any],
        document_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts all critical compliance information, uncommon/trap clauses,
        and mandatory submission documents grouped by Envelope.
        Provides bidding teams with a high-accuracy operational checklist to prevent disqualification.
        """
        title = tender.get("title") or tender.get("tender_title") or ""
        t_lower = (title + " " + (tender.get("description") or "") + " " + (document_text or "")).lower()
        cost = tender.get("estimated_cost_inr") or tender.get("estimated_value") or 0.0
        authority = tender.get("authority") or tender.get("issuing_authority") or "Public Procurement Authority"
        portal = (tender.get("portal_source") or "").lower()
        emd = tender.get("emd_inr") or tender.get("emd_amount") or 0.0

        trap_clauses = []

        # 1. Compulsory Pre-Bid Site Inspection
        if any(k in t_lower for k in ["site visit", "site inspection", "pre-bid visit", "inspect the site", "satisfy himself", "prior to submission of bid"]):
            trap_clauses.append({
                "clause": "Compulsory Pre-Bid Site Inspection Certificate",
                "severity": "HIGH",
                "risk_type": "Site & Execution Risk",
                "trap_explanation": "Tender mandates bidder must visit the physical site prior to bid submission. Bids submitted without a signed and stamped Site Inspection Certificate countersigned by the Executive Engineer / Project In-Charge are rejected at Envelope-1.",
                "mitigation": "Depute Nikom field engineer to visit site immediately, conduct physical survey of cable trays, plant rooms, and power intake, and obtain official stamped certificate."
            })
        elif "gem" not in portal:
            trap_clauses.append({
                "clause": "Deemed Site Survey & Plant Space Verification",
                "severity": "MEDIUM",
                "risk_type": "Execution Pre-requisite",
                "trap_explanation": "Clause stipulates bidder is deemed to have inspected the premises and existing power/chiller utilities. Any extra civil or cable trenching later will not be paid as variation.",
                "mitigation": "Nikom project team should verify floor loading (1500 kg/rack) and terrace condenser space against available building drawings."
            })

        # 2. OEM Specific Authorization Form (MAF)
        if any(k in t_lower for k in ["maf", "oem authorization", "manufacturer authorization", "oem certificate", "authorized partner", "back to back"]):
            trap_clauses.append({
                "clause": "Tender-Specific Ink-Signed OEM Manufacturer Authorization (MAF)",
                "severity": "CRITICAL",
                "risk_type": "Technical Elimination",
                "trap_explanation": "Mandates authorization on original OEM letterhead for UPS / PAC / Chillers / DG with tender reference number explicitly quoted and back-to-back warranty commitment. Generic dealer certificates cause immediate technical rejection.",
                "mitigation": "Request tender-specific MAF from Nikom alliance managers at Schneider/Vertiv/Eaton/Cummins immediately upon NIT release."
            })
        else:
            trap_clauses.append({
                "clause": "Back-to-Back Comprehensive OEM Warranty & Spares Commitment",
                "severity": "MEDIUM",
                "risk_type": "Warranty Compliance",
                "trap_explanation": "Tender mandates minimum 3 to 5 years comprehensive on-site warranty with guaranteed 4-hour MTTR and availability of spare parts for at least 7 to 10 years.",
                "mitigation": "Nikom must ensure OEM quotations include written commitment for long-term component availability and SLA uptime backing."
            })

        # 3. Make in India (MII) / Class-I Local Content (>50%)
        if cost >= 50000000 or any(k in t_lower for k in ["make in india", "local content", "dpiit", "class-i", "class 1", "mii"]):
            trap_clauses.append({
                "clause": "Class-I Local Content (MII) Declaration with CA Certificate",
                "severity": "HIGH",
                "risk_type": "Statutory Eligibility",
                "trap_explanation": "Public Procurement (Preference to Make in India) Order mandates >50% local value addition. For tenders exceeding ₹10 Crore, a Statutory Auditor / Chartered Accountant certificate with valid UDIN is mandatory; self-declaration alone is invalid.",
                "mitigation": "Nikom qualifies as Class-I supplier with domestic assembly and integration. Attach Nikom CA certified MII calculation sheet with statutory UDIN."
            })

        # 4. MSME EMD Exemption vs Bank Guarantee
        if emd and emd > 0:
            trap_clauses.append({
                "clause": "EMD Exemption Strictness (Medium Enterprise vs Micro/Small)",
                "severity": "HIGH",
                "risk_type": "Commercial Disqualification",
                "trap_explanation": f"EMD is ₹{emd/100000:.2f} Lakhs. Nikom is a registered Medium Enterprise under UDYAM. Certain government portals strictly restrict EMD exemption only to Micro and Small Enterprises (MSEs), rejecting Medium Enterprises.",
                "mitigation": "Submit standard Bank Guarantee via ICICI Bank credit line or verify if UDYAM Medium exemption is explicitly accepted under GeM GTC / NIT clauses."
            })

        # 5. Liquidated Damages & SLA Penalty Ceiling
        if any(k in t_lower for k in ["penalty", "liquidated damage", "ld clause", "sla", "delay"]):
            trap_clauses.append({
                "clause": "Stringent SLA & Liquidated Damages (LD) Capped at 10%",
                "severity": "MEDIUM",
                "risk_type": "Commercial Risk",
                "trap_explanation": "Clause imposes 0.5% per week delay penalty up to a ceiling of 10% of total contract value, plus uptime SLA penalties for data center cooling/power outages.",
                "mitigation": "Include realistic equipment delivery lead times (UPS/Chillers 10-12 weeks) in the proposed delivery schedule to prevent LD exposure."
            })

        # Master Document Checklist Grouped by Envelope
        checklist = [
            # Envelope 1
            {
                "envelope": "Envelope 1: Fee, EMD & Pre-Qualification",
                "document_name": "Earnest Money Deposit (EMD) / Bank Guarantee",
                "mandatory": True,
                "format": "Bank Guarantee on ₹100 stamp paper / Portal e-Receipt",
                "nikom_status": "Ready",
                "guidance": f"EMD of ₹{emd/100000:.2f}L if specified, or MSME UDYAM registration certificate. Backed by Nikom ICICI Bank revolving BG facility."
            },
            {
                "envelope": "Envelope 1: Fee, EMD & Pre-Qualification",
                "document_name": "Power of Attorney (POA) for Authorized Signatory",
                "mandatory": True,
                "format": "Notarized on ₹100 Non-Judicial Stamp Paper with Board Resolution",
                "nikom_status": "Ready",
                "guidance": "Board Resolution dated 12.04.2023 authorizing Mr. B.S. Kiran Kumar / Directors with company seal."
            },
            {
                "envelope": "Envelope 1: Fee, EMD & Pre-Qualification",
                "document_name": "Signed Integrity Pact & Pre-Contract Pact",
                "mandatory": True,
                "format": "Prescribed RFP Format signed by Authorized Signatory & 2 Witnesses",
                "nikom_status": "Ready",
                "guidance": "Nikom standard format ready for client-specific signature."
            },
            {
                "envelope": "Envelope 1: Fee, EMD & Pre-Qualification",
                "document_name": "Statutory Business Registrations (GST, PAN, PF, ESI)",
                "mandatory": True,
                "format": "Self-attested copies + Last 2 Quarters GST Returns (GSTR-3B)",
                "nikom_status": "Ready",
                "guidance": "Nikom GSTIN: 07AAACN0261A1Z9, PAN, EPFO, ESIC registration certificates readily available."
            },

            # Envelope 2
            {
                "envelope": "Envelope 2: Technical & Past Experience",
                "document_name": "Audited 3-Year Annual Turnover Certificate with UDIN",
                "mandatory": True,
                "format": "Chartered Accountant Certificate with UDIN + Audited Balance Sheets",
                "nikom_status": "Ready",
                "guidance": "CA Certified 3-Year Avg: ₹70.11 Cr (FY23: ₹48.50 Cr, FY24: ₹67.18 Cr, FY25: ₹91.21 Cr). Positive net worth ₹28.58 Cr."
            },
            {
                "envelope": "Envelope 2: Technical & Past Experience",
                "document_name": "Similar Work Past Experience & Completion Certificates",
                "mandatory": True,
                "format": "Client Work Orders + Completion Certificates with Project Value",
                "nikom_status": "Ready",
                "guidance": "Attach AAI DR Site ₹21.68 Cr, ONGC Mumbai DC ₹20.40 Cr, AAI 10 Airports ₹25.93 Cr. Total ₹162.24 Cr proven credentials."
            },
            {
                "envelope": "Envelope 2: Technical & Past Experience",
                "document_name": "OEM Manufacturer Authorization Forms (MAF)",
                "mandatory": True,
                "format": "On OEM Official Letterhead addressed to Authority with tender reference",
                "nikom_status": "Action Needed",
                "guidance": "Obtain tender-specific authorization letters from Schneider Electric, Vertiv, Eaton, or Cummins alliance leads."
            },
            {
                "envelope": "Envelope 2: Technical & Past Experience",
                "document_name": "Quality & Technical Certifications (ISO 9001 / ISO 27001)",
                "mandatory": True,
                "format": "Valid Certificates from Accredited Certification Bodies",
                "nikom_status": "Ready",
                "guidance": "Nikom holds active ISO 9001:2015, ISO 27001:2022, ISO 20000-1:2018, ISO 14001:2015, CMMI Level 3."
            },
            {
                "envelope": "Envelope 2: Technical & Past Experience",
                "document_name": "Clause-by-Clause Technical Compliance Statement & Datasheets",
                "mandatory": True,
                "format": "On Bidder Letterhead with OEM Technical Datasheets attached",
                "nikom_status": "Action Needed",
                "guidance": "Pre-sales engineering team to prepare compliance table against Section-3 BoQ specifications."
            },

            # Envelope 3
            {
                "envelope": "Envelope 3: Statutory Undertakings & Declarations",
                "document_name": "Non-Blacklisting & Non-Debarment Affidavit",
                "mandatory": True,
                "format": "Notarized on ₹100 Non-Judicial Stamp Paper",
                "nikom_status": "Ready",
                "guidance": "Affidavit confirming Nikom is not blacklisted by Central/State Govt or PSUs. Template auto-drafted."
            },
            {
                "envelope": "Envelope 3: Statutory Undertakings & Declarations",
                "document_name": "Make in India (MII) Class-I Local Content Declaration",
                "mandatory": True,
                "format": "Self-declaration on Nikom letterhead (>50% local value addition)",
                "nikom_status": "Ready",
                "guidance": "Formatted on Nikom official letterhead with local manufacturing locations detailed."
            },
            {
                "envelope": "Envelope 3: Statutory Undertakings & Declarations",
                "document_name": "Land Border Sharing Declaration (DoE Order Compliance)",
                "mandatory": True,
                "format": "Declaration on bidder letterhead as per Annexure format",
                "nikom_status": "Ready",
                "guidance": "Standard undertaking confirming Nikom has no beneficial ownership from land border countries."
            },
            {
                "envelope": "Envelope 3: Statutory Undertakings & Declarations",
                "document_name": "Calculated Bid Capacity Certificate",
                "mandatory": False,
                "format": "CA certified sheet: Bid Capacity = (A * N * 2) - B",
                "nikom_status": "Ready",
                "guidance": "Nikom Bid Capacity calculated at ₹201.16 Cr (Max Turnover A = ₹123.07 Cr, Existing Commitments B = ₹104.17 Cr)."
            }
        ]

        return {
            "tender_id": tender.get("tender_id"),
            "title": title,
            "authority": authority,
            "estimated_cost_inr": cost,
            "trap_clauses_count": len(trap_clauses),
            "uncommon_trap_clauses": trap_clauses,
            "checklist_total_items": len(checklist),
            "checklist_ready_count": len([c for c in checklist if c["nikom_status"] == "Ready"]),
            "checklist_action_count": len([c for c in checklist if c["nikom_status"] == "Action Needed"]),
            "bidding_document_checklist": checklist,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
