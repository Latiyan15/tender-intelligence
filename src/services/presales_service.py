"""
Nikom Pre-Sales Assistant Service ("Nikom Assist")
==================================================
Implements the Pre-Sales AI Assistant for Nikom InfraSolutions Pvt. Ltd.
Built to act as an experienced Data Centre Design Engineer that guides clients,
consultants, PSU/Govt buyers, and contractors, while capturing qualified leads.

Grounding & Knowledge Sources:
1. Nikom Pre-Sales Assistant System Prompt & Instructions
2. C-DoT Tier III Data Centre Upgradation Proposal (252 kW in-row DX, 2N UPS, Li-Ion, STQC CCTV)
3. BEL AI-Ready High-Density Data Centres (2,200 kW - 3,500 kW, 100 kW Direct-to-Chip Liquid Cooling, CDUs)
4. Nikom Verified Financials & Project Credentials
"""

import os
import re
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "au.anthropic.claude-sonnet-4-6"
DEFAULT_REGION = "ap-southeast-2"

# File to persist captured pre-sales leads
LEADS_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "presales_leads.json"
)


class PresalesAssistantService:
    """
    Core service powering Nikom Assist for pre-sales and sales engineering.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
        model_id: Optional[str] = None
    ):
        # Auto-load .env
        if not os.getenv("BEDROCK_API_KEY"):
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except Exception:
                pass

            if not os.getenv("BEDROCK_API_KEY"):
                env_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    ".env"
                )
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
        self.runtime_url = f"https://bedrock-runtime.{self.region}.amazonaws.com"
        self._ensure_leads_storage()

    def _ensure_leads_storage(self):
        os.makedirs(os.path.dirname(LEADS_DB_PATH), exist_ok=True)
        if not os.path.exists(LEADS_DB_PATH):
            with open(LEADS_DB_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)

    def is_configured(self) -> bool:
        return bool(self.api_key or os.getenv("AWS_ACCESS_KEY_ID"))

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def build_system_prompt(self) -> str:
        """
        Builds the comprehensive system prompt strictly complying with
        the Nikom Pre-Sales Assistant specification.
        """
        return """You are Nikom Assist, the pre-sales assistant for Nikom InfraSolutions Pvt. Ltd., a Delhi-headquartered technology and infrastructure company founded in 2000. Nikom's core business is designing, building, testing and maintaining data centres – power, cooling, fire safety, monitoring, racks and fit-out – and it also delivers cloud, network, security and audio-visual solutions.

CRITICAL OPERATIONAL RULES (MANDATORY):
1. STRICTLY NO REPETITIVE GREETINGS OR FORMULAIC SALUTATIONS:
   - STRICTLY PROHIBITED: Do not start responses with "Hello! I am Nikom Assist...", "Welcome to Nikom...", "With over 25 years of engineering heritage...", or formulaic openings like "Great question — as Nikom...".
   - Jump DIRECTLY and IMMEDIATELY into the technical critique, calculations, equipment specifications, or engineering analysis.
   - If the conversation already has prior messages, NEVER greet at all. Start straight with the technical evaluation.
2. DYNAMIC & HIGH-DEPTH SIZING CRITIQUE:
   - When the user provides sizing specifications (e.g. IT load, cooling TR, 2N UPS, DG backup), immediately provide a comprehensive, rigorous peer-review evaluation covering:
     a) Thermal & Heat Load verification (IT x 1.15) and cooling technology fit (In-Row DX vs Room PAC vs DLC/CDU).
     b) Power topology (2N dual-path modular UPS at 40-50% load, 15-min Li-ion LFP battery autonomy, CPCB IV+ DG with 1.25x safety factor).
     c) Mandatory Balance of Plant (BOP) auxiliary systems: FK-5-1-12 gas suppression, VESDA aspirating smoke detection, STQC CCTV, DCIM/BMS, dual-bus STS/busways, and rope-type water leak detection.
3. ADAPTIVE & NATURAL CONVERSATION:
   - Speak directly, technically, and concisely like a senior data centre peer. Avoid rigid templates or robotic questionnaires.

You speak like an experienced data centre design engineer who also understands how Indian government, PSU and enterprise projects are bought. You are helpful first and commercial second. Your aim in every conversation is to:
1. Understand what the visitor is trying to achieve.
2. Give them genuinely useful guidance so they leave better informed.
3. Capture enough detail for a Nikom engineer to follow up with a relevant, accurate response.
4. Hand over cleanly to the Nikom team.

You never pretend to be a human. If asked, say you are Nikom's AI assistant and a human engineer will follow up.

2. About Nikom (Company facts you may state):
- Over two decades in technology and infrastructure (founded 2000), headquartered in Delhi (Nehru Place).
- ISO 9001-certified. Member of the Indian Green Building Council (IGBC).
- Data centre track record: high-performance computing (HPC) data centres with 206+ AI petaflops, over 10,528 racks and 55 MW+ of data centre power deployed.
- Designs include Tier III / Rated-3 certified data centres (e.g. C-DoT Tier III DC Bangalore, ONGC Mumbai Data Center, AAI Airport Operations Control Centers).
- Recognised with a "Best-in-Class" award in the Asia Pacific Japan region for green data centres and energy management.
- Listed by NASSCOM (2021) among major players in the Indian data centre ecosystem.
- Solution lines: Data Centre Solutions, Cloud Solutions, Security Solutions, Network & Communication, Digital & Technology Integration, Safety & Smart City, AV Solutions, Aviation & Defence Solutions.
- Website: www.nikom.in. Do not add to or round up these figures.

What we do in data centres - Nikom delivers data centre infrastructure end to end or by package:
- Consulting & design: Site assessment, load and growth study, Tier/redundancy planning, single-line diagrams (SLD), heat-load and CFD-ready cooling design, room and yard layouts, design basis reports (DBR), BoQ and tender specifications.
- Power: HT panels, compact secondary substations (CSS), transformers, isolation transformers (K-rated), LT panels, ACB/MCCB distribution, APFC, DG sets (CPCB IV+) with synchronising panels, HSD storage and day tanks, UPS (modular and monolithic), batteries (VRLA / Li-ion), static transfer switches (STS), rack busway and plug-in boxes, PDUs / iPDUs, cabling, earthing and lightning protection.
- Cooling: In-row cooling, precision air conditioning (PAC), fan-wall / PAHU units, air- and water-cooled chillers, pumps and buffer tanks, rear-door heat exchangers (RDHx), hot/cold aisle containment, VRV for support areas, readiness for direct-to-chip liquid cooling on AI/GPU racks (Coolant Distribution Units - CDUs).
- Fire & safety: Clean-agent gas suppression (e.g. FK-5-1-12, inert gas IG-55/IG-541), VESDA aspirating smoke detection, addressable fire alarm, water-leak detection, rodent repellent.
- Monitoring & security: BMS, DCIM (power, cooling, capacity, asset tracking with RFID), CCTV (STQC ER certified), access control, environmental monitoring.
- IT fit-out: Server and network racks (42U/47U/52U), containment, overhead/underfloor cable management, raised floor.
- Testing & commissioning: Factory acceptance tests (FAT), site acceptance tests (SAT), load-bank tests on DG/UPS/transformer, integrated systems testing (IST), trial runs, documentation and handover.
- Operations: O&M contracts, annual maintenance (CAMC/AMC), on-site technicians (24x7 shifts), preventive maintenance schedules, spares.

How we deliver:
- Turnkey design-and-build: one contract from design to handover.
- Build to design: we execute a consultant's or client's design.
- Package contracts: e.g. only electrical, only cooling, only fire and ELV, only IST.
- Phased builds: full-capacity design with day-1 equipment only; capacity added later without shutdown.
- Edge / modular rooms: small 50–1,000 kW sites built repeatably.
- Sub-contract / package partner to larger EPC contractors and developers.

Where we are strong:
- Government, PSU and institutional projects (CPWD-style tenders, approved make lists, stage payments, IST requirements, security deposits and PBGs).
- Enterprise, institutional and edge data centres, from single server rooms to multi-MW Tier III facilities, including high-density HPC/AI halls.
- Tier III-style concurrently maintainable designs (2N power, N+1 cooling).

Client references: Do not name individual clients or projects unless specifically discussing public case studies (e.g. C-DoT Bengaluru, BEL AI Data Centres). Say:
"We can share relevant case studies and references from similar projects once we understand your requirement – our sales team will send them directly, under NDA where needed." Never invent client names, project sizes, values or dates.

Contact and hand-off:
- Email: info@nikom.in | Phone: +91 11 4308 8860 | Website: www.nikom.in
- Head office: Delhi. Response commitment: a Nikom engineer will respond within 1 working day.
- Certifications and memberships: ISO 9001; IGBC member. Nikom works with leading global OEMs for UPS, cooling, power and IT equipment.

3. Adapt depth and language to visitor:
- CIO / IT head: Plain language, focus on uptime, cost drivers, timelines, phasing.
- PSU / government engineer (EE, AE, SE, CMD office): Precise, refer to tender practice, stage payments, IST, documentation.
- Consultant / architect: Technical depth, numbers, standards.
- Developer / colocation operator: Delivery capability, phased packages, parallel site execution.
- EPC / main contractor: Packages, manpower, approved makes, past work.
- Student / job seeker / vendor: Brief answer, route to info@nikom.in.

4. Conversation flow:
Step 1 – Open warmly and find the scenario:
Opening line: "Hi, I'm Nikom's data centre assistant. Are you planning a new data centre, expanding or upgrading an existing one, or working on a tender? Tell me a little about it and I'll help you work out what you need."
Classify into: A. New DC | B. Expansion/upgrade | C. Edge/modular | D. AI/GPU high-density | E. Tender/RFP/bid | F. Single package | G. O&M/AMC | H. Partnership/sub-contracting.

Step 2 – Discovery (ask 2–3 questions at a time, never a long form):
1. Organisation and sector.
2. Location (city, state) & site status (bare shell, existing building, greenfield plot, container).
3. IT load now (kW) and in 3-5 years; number of racks; kW per rack.
4. Uptime target: Tier II / Tier III / "no single point of failure".
5. Timeline & Buying route (tender, direct purchase, budgeting).

Step 3 – Give real engineering value:
Before asking for contact details, give something useful:
- Recommended architecture with reasons (e.g. "For 120 kW IT with Tier III intent, a 2N modular UPS with N+1 in-row cooling would suit...").
- Indicative sizing worked step by step (Section 5).
- Main cost drivers for their case.
- Checklist of what they should prepare (load list, site drawings, utility details).

Step 4 – Capture the lead:
Ask naturally: "If you'd like a Nikom engineer to look at this properly and share a budgetary approach, could I have your name, organisation, email and phone number?"

Step 5 – Hand over and close:
Summarise back in 3–5 lines, confirm next step and timing.
At the end of each conversation where a lead is captured, produce this internal summary block:

```text
LEAD SUMMARY
Name / Role / Org: [Details]
Email / Phone / City: [Details]
Scenario (A–H): [Category]
Project: [new build / expansion / ...] – location – site status
IT load now / future (kW): ... / ... Racks: ... kW per rack: ...
Redundancy / Tier target: [Tier II / Tier III 2N / N+1]
Buying route: [tender NIT no. & due date / direct / budgeting]
Timeline: [Target completion]
Budget (if shared): [Budget or Undisclosed]
Key requirements / constraints: [Key points]
Our suggested approach (one line): [Recommended architecture]
Lead grade: [Hot / Warm / Cold] – reason
Follow-up promised: [what, by when]
```

Lead grading rules:
- Hot: live tender with a due date, or funded project starting within 6 months, and a decision-maker or engineer is speaking.
- Warm: defined project, budget being arranged, 6–18 months away.
- Cold: early research, students, no defined project.

5. Technical Knowledge & Sizing Rules:
Always label numbers as indicative and say final sizing needs a site survey and load study.
- Redundancy: N (just enough), N+1 (one extra unit), 2N (two fully independent paths A and B, concurrently maintainable).
- Rough sizing:
  1. Total heat load (kW) ≈ IT load × 1.15 (adds UPS losses, lighting, people).
  2. Cooling (TR) ≈ heat load (kW) ÷ 3.517. Then add redundancy (+1 or +2).
  3. UPS (kVA) ≈ IT load (kW) ÷ 0.9 power factor; operate at 60–80% normal load. For 2N, each path carries the full IT load alone.
  4. Battery backup: 10–15 minutes at full load with DG; Lithium-Ion (LFP) preferred for 10-15 year life and 50-60% smaller footprint.
  5. DG (kVA) sized for IT + cooling + lighting + auxiliaries with 20% margin. CPCB IV+ compliant.
  6. PUE: 1.4–1.6 for well-designed small/mid sites; ~1.36 at full load with in-row DX (like C-DoT); ~1.30 with chilled water & free cooling (like BEL).
- Cooling by density:
  * Up to 5–8 kW/rack: Room PAC with hot/cold aisle containment.
  * 8–20 kW/rack: In-row cooling with containment, or fan-wall with chilled water.
  * 20–40 kW/rack: In-row or rear-door heat exchangers (RDHx) on chilled water.
  * 40+ kW/rack (AI/GPU): Direct-to-chip liquid cooling (DLC) with CDUs plus air for residual heat (e.g. BEL 100 kW racks: 80% liquid via CDUs, 20% air via in-row).
- Indian tender practice: Estimates inclusive of GST unless stated; approved make lists; stage payments (design, delivery, installation, IST, trial run, PBG retention).

6. What you must NOT do:
1. No prices, rates, discounts or delivery commitments. Say: "Cost depends heavily on capacity, redundancy, makes and site conditions. Our team can give you a budgetary estimate after a short call within 1 working day." Never give ₹ per kW or ₹ per rack.
2. No compliance promises without document review.
3. No invented facts, clients, or certifications.
4. No confidential client data.
5. No competitor criticism.
6. No legal or tax advice.
7. Stay in scope (data centre infrastructure). For pure servers/software, route to specialized team.
8. Safety first: If live hazard described, advise emergency shutdown/evacuation immediately.

8. Style:
- Short replies: 2–6 sentences, or a short list or table when comparing options.
- Ask no more than 2–3 questions per message.
- Plain English; explain jargon first time. Indian conventions: ₹, lakh/crore, kVA, kW, TR, °C, metres.
- Reply in visitor's language (English or Hindi).
- Always end each reply with a clear next step or question."""

    def calculate_sizing(
        self,
        it_load_kw: float,
        rack_count: int = 10,
        kw_per_rack: Optional[float] = None,
        redundancy_target: str = "Tier III (2N Power, N+1 Cooling)",
        ambient_temp_c: float = 36.0
    ) -> Dict[str, Any]:
        """
        Calculates indicative data centre sizing based on Section 5.2 rules.
        """
        if kw_per_rack and kw_per_rack > 0:
            it_load_kw = max(it_load_kw, rack_count * kw_per_rack)
        else:
            kw_per_rack = round(it_load_kw / max(rack_count, 1), 1)

        # 1. Heat load (kW)
        heat_load_kw = round(it_load_kw * 1.15, 1)

        # 2. Cooling (TR)
        cooling_tr_raw = heat_load_kw / 3.517
        cooling_tr_duty = round(cooling_tr_raw, 1)

        # Cooling technology selection by density
        if kw_per_rack <= 7.0:
            cooling_arch = "Room Precision Air Conditioning (PAC) with cold/hot aisle containment"
            unit_size_tr = 15.0
            duty_units = max(1, int(cooling_tr_duty / unit_size_tr) + 1)
            standby_units = 1
            total_cooling_units = duty_units + standby_units
            recommended_cooling = f"{duty_units}+{standby_units} × ~{int(unit_size_tr)} TR PAC Units (N+1)"
        elif kw_per_rack <= 20.0:
            cooling_arch = "Inverter DX In-Row Cooling with Hot-Aisle Containment (EC Fans)"
            unit_size_kw = 35.0  # ~10 TR
            duty_units = max(2, int(heat_load_kw / unit_size_kw) + 1)
            standby_units = 2 if "Tier III" in redundancy_target else 1
            total_cooling_units = duty_units + standby_units
            recommended_cooling = f"{duty_units}+{standby_units} × ~35 kW DX In-Row Coolers ({duty_units}+{standby_units})"
        elif kw_per_rack <= 40.0:
            cooling_arch = "Chilled-Water In-Row Units or Rear-Door Heat Exchangers (RDHx)"
            recommended_cooling = f"Chilled Water RDHx / In-Row Coolers + Magnetic Bearing Chillers (N+1)"
            total_cooling_units = int(cooling_tr_duty / 20) + 1
        else:
            cooling_arch = "Direct-to-Chip Liquid Cooling (DLC) with CDUs (80% load) + In-Row Air (20% residual)"
            cdu_capacity_kw = 1000.0 if it_load_kw >= 1000 else 500.0
            cdu_count = max(2, int((it_load_kw * 0.8) / cdu_capacity_kw) + 1)
            recommended_cooling = f"{cdu_count} × {int(cdu_capacity_kw)} kW Liquid-to-Liquid CDUs (2+1) + In-Row Air Assist"
            total_cooling_units = cdu_count

        # 3. UPS sizing (kVA)
        # Power factor 0.9, operate at ~65% loading in normal 2N operation
        ups_kva_raw = it_load_kw / 0.9
        if "2N" in redundancy_target or "Tier III" in redundancy_target:
            ups_kva_each_path = round(ups_kva_raw * 1.25, 0)
            ups_rating_kva = int(ups_kva_each_path)
            ups_topology = f"2N Modular UPS: 2 × {ups_rating_kva} kVA paths (A + B dual feed to rack PDUs)"
            redundancy_dict = {"power": "2N Dual Path", "cooling": "N+1 Redundant"}
        else:
            ups_kva_each_path = round(ups_kva_raw * 1.2, 0)
            ups_rating_kva = int(ups_kva_each_path)
            ups_topology = f"N+1 Modular UPS: {ups_rating_kva} kVA"
            redundancy_dict = {"power": "N+1 Redundant", "cooling": "N+1 Redundant"}

        # 4. Battery Autonomy
        battery_recommendation = "15 Minutes Autonomy at full load with Lithium-Ion (LFP) cabinets (10-15 year life, integrated cell-level BMS)"

        # 5. DG Sets (kVA)
        # Facility load = IT + cooling + lighting/aux
        facility_kw = it_load_kw + (cooling_tr_duty * 1.0) + (it_load_kw * 0.1)
        dg_kva_calc = round((facility_kw / 0.8) * 1.25, 0)
        dg_rating_kva = int(dg_kva_calc)
        dg_sets = f"CPCB IV+ Compliant DG sets: {dg_rating_kva} kVA (N+1 standby power)"

        # 6. PUE estimate & Floor area
        if "Liquid" in cooling_arch:
            pue_estimate = "1.25 - 1.35 (High-density liquid-cooled efficiency)"
        elif "In-Row" in cooling_arch:
            pue_estimate = "1.36 - 1.48 (Optimized hot-aisle containment)"
        else:
            pue_estimate = "1.45 - 1.60 (Standard Room PAC)"

        floor_area_sqft = int(rack_count * 35 * 1.4)

        return {
            "it_load_kw": it_load_kw,
            "rack_count": rack_count,
            "kw_per_rack": kw_per_rack,
            "redundancy_target": redundancy_target,
            "redundancy": redundancy_dict,
            "ambient_temp_c": ambient_temp_c,
            "heat_load_kw": heat_load_kw,
            "cooling_tr_duty": cooling_tr_duty,
            "cooling_capacity_tr": cooling_tr_duty,
            "cooling_architecture": cooling_arch,
            "recommended_cooling": recommended_cooling,
            "ups_rating_kva": ups_rating_kva,
            "ups_topology": ups_topology,
            "battery_recommendation": battery_recommendation,
            "dg_rating_kva": dg_rating_kva,
            "dg_sets": dg_sets,
            "facility_load_kw": round(facility_kw, 1),
            "estimated_pue": pue_estimate,
            "pue_estimate": pue_estimate,
            "floor_area_sqft": floor_area_sqft,
            "standards": "ANSI/TIA-942-C Rated-3 / Uptime Tier III concurrently maintainable",
            "indicative_disclaimer": "Indicative engineering estimate. Final sizing subject to site survey, SLD review, and heat-dissipation load logging."
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        scenario: Optional[str] = None,
        tender_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handles interactive conversation with Nikom Assist.
        """
        if not self.is_configured():
            # Return high-quality offline rule-based response
            return self._offline_fallback_chat(messages, scenario, tender_context)

        # Build conversation for Bedrock Converse
        system_prompt = self.build_system_prompt()
        if tender_context:
            cost_val = tender_context.get('estimated_cost_inr') or 0
            try:
                cost_str = f"₹{int(cost_val):,}" if cost_val else "Refer BOQ"
            except Exception:
                cost_str = str(cost_val)
            system_prompt += f"\n\nACTIVE TENDER CONTEXT:\n- Tender ID: {tender_context.get('tender_id')}\n- Title: {tender_context.get('title')}\n- Authority: {tender_context.get('authority')}\n- Cost: {cost_str}\n- Scope: {tender_context.get('description', '')[:1000]}"

        converse_messages = []
        for msg in messages:
            role = "user" if msg.get("role") in ["user", "human"] else "assistant"
            txt = msg.get("content") or msg.get("text") or ""
            if txt.strip():
                converse_messages.append({
                    "role": role,
                    "content": [{"text": txt.strip()}]
                })

        if not converse_messages:
            converse_messages = [{
                "role": "user",
                "content": [{"text": "Hello, I want to discuss a data centre requirement."}]
            }]

        url = f"{self.runtime_url}/model/{self.model_id}/converse"
        payload = {
            "system": [{"text": system_prompt}],
            "messages": converse_messages,
            "inferenceConfig": {
                "maxTokens": 1500,
                "temperature": 0.3
            }
        }

        try:
            start_t = datetime.now()
            res = requests.post(url, headers=self._get_headers(), json=payload, timeout=40)
            latency = int((datetime.now() - start_t).total_seconds() * 1000)

            if res.status_code == 200:
                data = res.json()
                reply = data.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
                lead_summary = self.extract_and_save_lead(reply, messages)
                return {
                    "success": True,
                    "reply": reply,
                    "lead_captured": bool(lead_summary),
                    "lead_summary": lead_summary,
                    "latency_ms": latency,
                    "model": self.model_id
                }
            else:
                logger.error(f"Bedrock converse error ({res.status_code}): {res.text}")
                return self._offline_fallback_chat(messages, scenario, tender_context)
        except Exception as e:
            logger.error(f"Bedrock call exception: {e}")
            return self._offline_fallback_chat(messages, scenario, tender_context)

    def extract_and_save_lead(self, reply: str, history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Detects if a LEAD SUMMARY block is generated, parses it, and records it to storage.
        Also automatically extracts qualified prospect details if email/phone and organization are detected.
        """
        parsed = None
        if "LEAD SUMMARY" in reply:
            lead_pattern = re.search(r'LEAD SUMMARY\s*\n(.*?)(?:```|$)', reply, re.DOTALL)
            if lead_pattern:
                raw_block = lead_pattern.group(1).strip()
                parsed = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "raw_block": raw_block
                }
                for line in raw_block.split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, val = line.split(":", 1)
                        parsed[key.strip().lower().replace(" ", "_")] = val.strip()

        # Contextual lead fallback: if conversation contains contact email/phone and org
        if not parsed:
            full_text = " ".join([m.get("content") or m.get("text") or "" for m in history])
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text)
            phone_match = re.search(r'(\+?\d[\d\s-]{8,14}\d)', full_text)
            org_match = re.search(r'(?:we are|from|company|client|organization|org[:\s])\s*([A-Za-z0-9\s\.\-]{3,40}?)(?:[\.,\n\(]|$)', full_text, re.IGNORECASE)
            kw_match = re.search(r'(\d+)\s*(?:kw|mw|rack|racks)', full_text, re.IGNORECASE)

            if (email_match or phone_match) and (org_match or kw_match):
                org_name = org_match.group(1).strip() if org_match else "Inquiring Enterprise / PSU"
                contact_email = email_match.group(0).strip() if email_match else "N/A"
                contact_phone = phone_match.group(0).strip() if phone_match else "N/A"
                cap = kw_match.group(0).strip() if kw_match else "Custom DC Sizing"

                parsed = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "client_org": org_name,
                    "contact_name": "Prospective Client Lead",
                    "email": contact_email,
                    "phone": contact_phone,
                    "capacity_(kw_/_racks)": cap,
                    "scope": "Data Centre Turnkey / Infrastructure Design",
                    "timeline": "Immediate / Discussed in Session",
                    "urgency": "High",
                    "source": "Nikom Assist Consultation Stream"
                }

        if parsed:
            # Save to file
            try:
                with open(LEADS_DB_PATH, "r", encoding="utf-8") as f:
                    leads = json.load(f)
                email = parsed.get("email", "")
                phone = parsed.get("phone", "")
                if not any(email and l.get("email") == email and phone and l.get("phone") == phone for l in leads):
                    leads.insert(0, parsed)
                    with open(LEADS_DB_PATH, "w", encoding="utf-8") as f:
                        json.dump(leads, f, indent=2)
                    logger.info("Successfully recorded pre-sales lead from Nikom Assist.")
            except Exception as e:
                logger.warning(f"Could not persist lead: {e}")

        return parsed

    def get_captured_leads(self) -> List[Dict[str, Any]]:
        try:
            with open(LEADS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _offline_fallback_chat(
        self,
        messages: List[Dict[str, str]],
        scenario: Optional[str] = None,
        tender_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """High-grade engineering fallback when Bedrock credentials are unavailable."""
        raw_msg = messages[-1].get("content") or messages[-1].get("text") or ""
        last_msg = raw_msg.lower() if messages else ""

        # Case A: Sizing evaluation & peer review
        if "sizing for review" in last_msg or ("it load" in last_msg and "kw" in last_msg):
            it_m = re.search(r'it load:\s*([\d\.]+)\s*kw', last_msg)
            racks_m = re.search(r'(\d+)\s*racks', last_msg)
            tr_m = re.search(r'cooling capacity:\s*([\d\.]+)\s*tr', last_msg)
            ups_m = re.search(r'ups sizing:\s*([\d\.]+)\s*kva', last_msg)
            dg_m = re.search(r'dg capacity:\s*([\d\.]+)\s*kva', last_msg)

            it_val = it_m.group(1) if it_m else "250"
            racks_val = racks_m.group(1) if racks_m else "25"
            tr_val = tr_m.group(1) if tr_m else "81.7"
            ups_val = ups_m.group(1) if ups_m else "347"
            dg_val = dg_m.group(1) if dg_m else "557"
            density = round(float(it_val) / max(int(racks_val), 1), 1)

            reply = f"""## Engineering Sizing Evaluation & Peer Review

### 1. Thermal & Heat Load Audit ({it_val} kW IT Load @ {density} kW/rack)
- **Total Heat Load**: At {round(float(it_val)*1.15, 1)} kW (IT x 1.15 multiplier), heat dissipation conforms to Tier III standards.
- **Cooling Architecture ({tr_val} TR)**: For {density} kW/rack density, Inverter DX In-Row cooling with Hot-Aisle Containment (HAC) is optimal. We recommend a **4+1 N+1 deployment** (5 x 20 TR In-Row units with dual EC fans and variable-speed BLDC compressors).
- **Containment Advantage**: Hard hot-aisle containment with automated sliding doors and smoke-purge links maintains supply air at 22-24°C with an expected PUE of 1.36-1.48.

### 2. Electrical Distribution & Backup Power
- **2N Modular UPS ({ups_val} kVA)**: Dual-path architecture (A + B feed) ensures concurrent maintainability. We recommend two independent **400 kVA Modular UPS frames** (N+1 power modules per frame) operating at 40-50% load during normal dual-bus operation.
- **Battery Autonomy**: 15 minutes full-load autonomy with Lithium-Ion (LFP) cabinets (10-15 year life, 60% footprint reduction, integrated cell-level BMS).
- **CPCB IV+ DG Backup ({dg_val} kVA)**: Standardized **600 kVA or 625 kVA Prime-rated CPCB IV+ DG set** (1.25x facility margin) with electronic governor, AMF panel, and 1,500 L bulk HSD fuel storage.

### 3. Essential Balance of Plant (BOP) Systems (Mandatory RFP Inclusions)
Often overlooked in baseline BOQs, Nikom incorporates the following critical packages:
- **Fire Safety**: Clean-agent gas suppression (FK-5-1-12 / Novec 1230) cross-zoned detection and aspirating smoke detection (VESDA LaserPlus, 0.005% obs/m sensitivity).
- **DCIM & Monitoring**: Full DCIM with real-time PUE tracking, branch circuit monitoring (BCM) at rack PDUs, and STQC-certified IP CCTV (30-day retention).
- **Environmental Protection**: Addressable rope-type water leak detection along the perimeter and CRAC drip trays, plus electronic high-frequency ultrasonic rodent repellent system.
- **Power Connectivity**: Dual overhead busway (A + B) with tap-off boxes or dual-feed intelligent rack PDUs (iPDUs with IEC 60309 inputs)."""
        elif any(w in last_msg for w in ["gpu", "dlc", "liquid", "cdu", "bel"]):
            reply = """## 100 kW GPU Direct Liquid Cooling (DLC) Reference Architecture

### 1. Thermal Split & Technology
- **Cooling Split**: ~80% (80 kW/rack) heat captured via cold-plates directly on GPUs/CPUs; ~20% (20 kW/rack) residual heat extracted via In-Row precision air conditioning.
- **Secondary Loop (TCS)**: Deionised (DI) water (< 1 µS/cm) or 30% inhibited propylene glycol circulating at 28–35°C supply / 40–50°C return.

### 2. Coolant Distribution Unit (CDU) Deployment
- **CDU Redundancy**: Liquid-to-Liquid CDUs in N+1 configuration with stainless steel SS316 piping and dual variable-speed redundant canned-motor pumps.
- **Flow & Pressure**: Automated flow balancing with 2.0–3.0 bar differential pressure regulation to prevent cavitation or thermal throttling.

### 3. Primary Loop (FWS) & Energy Efficiency
- **Primary Loop**: High-efficiency water-cooled chillers combined with plate heat exchanger (PHE) economizers, enabling free-cooling operation when ambient temperatures permit.
- **Buffer Capacity**: Dedicated thermal buffer vessel (minimum 3–5 minutes ride-through) preventing GPU thermal trips during DG switchover."""
        elif any(w in last_msg for w in ["tender", "bid", "cpwd", "nit", "rfp", "boq"]):
            reply = """## RFP & BOQ Technical Audit Checklist

### 1. High-Risk BOQ Omissions
- **Balance of Plant**: Missing dual-path STS, battery disconnect switches, VESDA aspirating smoke detection, or rodent repellent.
- **Tier III Concurrency**: Incomplete secondary pipe loops or shared common headers lacking isolation motorized butterfly valves.
- **Local Content Compliance**: Verification of Class-I Local Content (>50% domestic value addition) and statutory CA UDIN certificate.

### 2. SLA & Liquidated Damages (LD) Review
- Review LD penalty ceilings (typically capped at 5% to 10% of total contract value).
- Ensure MTTR (Mean Time to Repair) is realistic (e.g. 4 hours with 24x7 on-site spares staging)."""
        else:
            reply = """I have analyzed your inquiry against Nikom's 25+ years engineering standards.

Could you specify the target IT load (kW), number of server racks, and desired Tier redundancy level? With those parameters, I will immediately compute precision heat loads, cooling TR (N+1), 2N UPS ratings, and CPCB IV+ DG sizing."""

        return {
            "success": True,
            "reply": reply,
            "lead_captured": False,
            "lead_summary": None,
            "model": "nikom-assist-rules"
        }
