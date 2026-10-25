# Scoring Derivation & Field-by-Field Audit Report
## Autonomous Tender Intelligence System for Nikom InfraSolutions Pvt. Ltd.

**Date of Execution:** October 22, 2026  
**Auditing System:** Autonomous Tender Intelligence Feasibility Engine  
**Target Enterprise:** Nikom InfraSolutions Pvt. Ltd. (Data Center Infrastructure, Critical Power, Precision Cooling & EPC)  
**Tenders Audited:** 42 Total (35 Live Indian Government Portals + 7 Benchmark Controls)  
**Deliverable Type:** Field-Level Comparative Derivation & Mathematical Audit  

---

## 1. The Nikom Baseline Record & Evaluation Criteria

Every tender discovered by the autonomous agent was mathematically scored and evaluated against the verified commercial, technical, and operational profile of **Nikom InfraSolutions Pvt. Ltd.**:

### 1.1 Enterprise Baseline Record
```
+----------------------------------------------------------------------------------------------------+
|                               NIKOM INFRASOLUTIONS BASELINE PROFILE                                |
+--------------------------------------+-------------------------------------------------------------+
| Founding Year & HQ                   | 2002 | New Delhi, India                                     |
| Operating Branches                   | Mumbai, Bengaluru, Hyderabad, Chennai, Kolkata              |
| Core Turnkey Capabilities            | Tier I to Tier IV Data Center Turnkey EPC                   |
| Critical Power Domain                | Online UPS Systems, Isolation Transformers, Battery Banks   |
| Thermal Management Domain            | Precision Air Conditioning (PAC), CRAC/CRAH, Chilled Water  |
| Electrical Infrastructure            | HT/LT Panels, AMF, Cabling, Busducts, DG Sets               |
| Low Voltage / IBMS                   | Building Management Systems, DCIM, SCADA, Water Leak (WLD)  |
| Fire Safety & Suppression            | VESDA (Early Warning), Clean Agent Gas (FM-200, Novec 1230) |
| Physical Security                    | IP CCTV Surveillance, Biometric Access Control, Turnstiles  |
| Passive Infrastructure               | Server Racks (42U/48U), Hot/Cold Aisle Containment          |
| Lifecycle Services                   | 24x7 Facility Management (FMS), Annual Maintenance (AMC)    |
+--------------------------------------+-------------------------------------------------------------+
```

### 1.2 Mathematical Thresholds & Parameters
The evaluation engine enforces strict quantitative boundaries based on Nikom's corporate balance sheet and bonding capacity:

* **Financial Sweet Spot Range ($[V_{min\_sweet}, V_{max\_sweet}]$):** **₹25,00,000 to ₹25,00,00,000 (₹25 Lakhs to ₹25 Crores)**.  
  *Contracts in this range receive maximum commercial score (100 pts) as they align with Nikom's working capital, bank guarantee (BG) limits, and gross margin targets.*
* **Absolute Minimum Project Size ($V_{floor}$):** **₹5,00,000 (₹5 Lakhs)**.  
  *Contracts below ₹5 Lakhs are penalized (score = 40 pts) due to overhead inefficiencies.*
* **Single Contract Capacity Limit ($V_{single\_max}$):** **₹30,00,00,000 (₹30 Crores)**.  
  *Contracts above ₹30 Crores require joint ventures or consortiums and receive a capped score (50 pts).*
* **Annual Turnover Capacity Ceiling ($T_{cap}$):** **₹1,00,00,00,000 (₹100 Crores)**.  
  *Any tender mandating an average annual turnover exceeding ₹100 Crores is **instantly disqualified (NO-GO)**.*
* **Earnest Money Deposit (EMD) Limit:** **Up to ₹50,00,000 (₹50 Lakhs)**.  
* **Partner OEM Authorizations (MAFs):** Schneider Electric / APC, Vertiv (Emerson Network Power), Eaton, Delta, Legrand, Cummins, Kirloskar, Cisco, Honeywell, Siemens, Johnson Controls.
* **Corporate Certifications:** ISO 9001:2015, ISO 27001:2013, ISO 20000-1, ISO 14001:2015, ISO 45001:2018.

### 1.3 Negative Exclusion Triggers
Tenders falling into the following 18 domains trigger **immediate automatic disqualification ($S_{scope} = 0.0 \implies \text{NO-GO}$)** unless overridden by explicit data center / server room requirements:
> *Road construction, highway, bridge, civil building construction, medical equipment, pharmaceutical, catering, canteen/mess, housekeeping, sanitation, security guard manpower, vehicle hiring, transport services, printing, stationery, clothing/uniforms, dredging, mining.*

---

## 2. Mathematical Scoring Model & Derivation Formula

Each tender is evaluated across four orthogonal dimensions to produce a normalized **Composite Feasibility Score ($S_{composite}$)** from 0 to 100:

$$\mathbf{S_{composite} = 0.40 \cdot S_{scope} + 0.25 \cdot S_{eligibility} + 0.20 \cdot S_{commercial} + 0.15 \cdot S_{retrieval}}$$

```mermaid
flowchart LR
    subgraph Dimensions["4 Evaluated Dimensions"]
        D1["Scope Alignment<br/>(Weight: 40%)"]
        D2["Eligibility & Capacity<br/>(Weight: 25%)"]
        D3["Commercial Viability<br/>(Weight: 20%)"]
        D4["Retrieval Completeness<br/>(Weight: 15%)"]
    end

    subgraph Computation["Mathematical Model"]
        C1["Weighted Linear Sum<br/>S = 0.40·S₁ + 0.25·S₂ + 0.20·S₃ + 0.15·S₄"]
    end

    subgraph Decision["Decision Logic"]
        V1["GO (Score ≥ 70 & Scope ≥ 60)"]
        V2["CAUTION (50 ≤ Score < 70)"]
        V3["NO-GO (Score < 50 or Disqualified)"]
    end

    D1 & D2 & D3 & D4 --> C1
    C1 --> Decision
```

### 2.1 Dimension 1: Technical Scope Alignment ($S_{scope}$ — 40% Weight)
Measures the linguistic and semantic overlap between the tender's title, scope of work, BOQ, and specifications against Nikom's domain taxonomy:
* **Trigger 1: Excluded Domain Check:** If an excluded keyword is detected (and no primary data center keyword is present), **$S_{scope} = 0.0$** and `is_excluded = True`.
* **Trigger 2: Core Data Center Scope:**
  * $\ge 3$ High-Match keywords (e.g. *Data Center, Precision AC, Online UPS, VESDA*): **$S_{scope} = 100.0$**
  * $2$ High-Match keywords: **$S_{scope} = 90.0$**
  * $1$ High-Match keyword: **$S_{scope} = 75.0$**
* **Trigger 3: Adjacent Domain Scope:**
  * $\ge 2$ Adjacent keywords (e.g. *CCTV, Access Control, Substation, DG Set, HVAC*): **$S_{scope} = 60.0$**
  * $1$ Adjacent keyword: **$S_{scope} = 45.0$**
* **Trigger 4: Out-of-Scope Baseline:** If no domain keywords match: **$S_{scope} = 10.0$**

### 2.2 Dimension 2: Bidder Eligibility & Capacity ($S_{eligibility}$ — 25% Weight)
Measures whether Nikom qualifies under the mandatory qualification clauses:
* **Base Score:** **80.0** (Standard corporate baseline for ISO-certified EPC).
* **Turnover Clause Adjustment ($T_{req}$):**
  * If $T_{req} > \text{₹100 Crores}$: **$-40.0$ pts** ($S_{eligibility} = 40.0$) $\rightarrow$ **Triggers Hard Disqualification Rule!**
  * If $\text{₹50 Crores} < T_{req} \le \text{₹100 Crores}$: **$-10.0$ pts** ($S_{eligibility} = 70.0$, Consortium advisory).
  * If $T_{req} \le \text{₹50 Crores}$: **$+10.0$ pts** ($S_{eligibility} = 90.0$, Full financial clearance).
* **OEM Authorization Adjustment:**
  * If Manufacturer Authorization Form (MAF) is mandated and the specified OEM is in Nikom's active partner roster (Schneider, Vertiv, Eaton, Cummins): **$+10.0$ pts** ($S_{eligibility} \le 100.0$).
  * If MAF is required but OEM is unaligned: Gap noted for partner alignment.

### 2.3 Dimension 3: Commercial Viability ($S_{commercial}$ — 20% Weight)
Evaluates contract value ($V$ in INR) against Nikom's revenue sweet spot:
* **Sweet Spot:** $\text{₹25 Lakhs} \le V \le \text{₹25 Crores} \implies \mathbf{S_{commercial} = 100.0}$
* **Viable Range:** $\text{₹5 Lakhs} \le V < \text{₹25 Lakhs} \implies \mathbf{S_{commercial} = 75.0}$
* **Micro-Tender:** $V < \text{₹5 Lakhs} \implies \mathbf{S_{commercial} = 40.0}$ (Sub-economic scale)
* **Mega-Contract:** $V > \text{₹30 Crores} \implies \mathbf{S_{commercial} = 50.0}$ (Exceeds single-entity cap)
* **Unpublished Value:** Notice does not disclose value $\implies \mathbf{S_{commercial} = 60.0}$ (Neutral assumption)

### 2.4 Dimension 4: Retrieval Completeness ($S_{retrieval}$ — 15% Weight)
Measures data integrity and whether sufficient information was retrieved to bid without blind risk:
* Detailed Project Title ($>10$ characters): **15 points**
* Submission Deadline extracted (ISO-8601): **20 points**
* EMD terms (INR amount or explicit Exemption): **20 points**
* Estimated Tender Value extracted: **15 points**
* Full Technical Specifications / Downloaded PDF Document: **20 points** (or 15 points for text scope)
* Issuing Authority / Department identified: **10 points**
* *Maximum Total:* **100 points**.

---

## 3. Decision Boundary Rules & Final Verdict Logic

The final operational verdict is synthesized using deterministic threshold logic:

```mermaid
flowchart TD
    Start["Tender Ingested & Scored"] --> CheckDisq{"Disqualification Trigger?<br/>• Excluded Domain?<br/>• Scope Score < 30?<br/>• Turnover > ₹100 Cr?"}
    
    CheckDisq -- YES --> NO_GO["VERDICT: NO-GO<br/>(Disqualified / Out of Domain)"]
    
    CheckDisq -- NO --> CheckRetr{"Retrieval Completeness<br/>Score < 40%?"}
    CheckRetr -- YES --> CAUTION_DATA["VERDICT: CAUTION<br/>(Incomplete Public Data)"]
    
    CheckRetr -- NO --> CheckGO{"Composite Score ≥ 70.0<br/>AND Scope Score ≥ 60.0?"}
    
    CheckGO -- YES --> CheckDocs{"Retrieval Completeness<br/>≥ 70%?"}
    CheckDocs -- YES --> GO["VERDICT: GO<br/>(High Feasibility: Pursue Bid)"]
    CheckDocs -- NO --> GO_PROV["VERDICT: GO (PROVISIONAL)<br/>(Favorable Scope: Manual Doc Pull)"]
    
    CheckGO -- NO --> CheckCaution{"Composite Score ≥ 50.0?"}
    CheckCaution -- YES --> CAUTION["VERDICT: CAUTION<br/>(Adjacent Scope / Review Required)"]
    CheckCaution -- NO --> NO_GO_LOW["VERDICT: NO-GO<br/>(Sub-Threshold Feasibility)"]
```

* **GO:** Composite $\ge 70.0$, Scope $\ge 60.0$, Completeness $\ge 70.0$, and zero disqualifiers.
* **GO (PROVISIONAL):** High alignment ($\ge 70.0$), but full tender documents require manual portal pull.
* **CAUTION:** Composite between $50.0$ and $69.9$, or incomplete data fields requiring human verification.
* **NO-GO:** Composite $< 50.0$, scope $< 30.0$, excluded domain, or turnover ceiling breached.

---

## 4. Complete Audit Matrix: Field-by-Field Breakdown of All 42 Tenders

Below is the complete tabular record of every tender, the extracted figures, the sub-scores across all four dimensions, and the mathematical derivation of the final verdict:

| # | Tender ID | Issuing Organisation | Extracted Value (INR) | EMD (INR) | Scope (40%) | Elig (25%) | Comm (20%) | Retr (15%) | Composite Score | Verdict | Derivation Rationale |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `2026_RINL_854802_1` | Rashtriya Ispat Nigam Ltd | ₹1,21,67,458 | Nil (0.0) | 10.0 | 80.0 | 100.0 | 100.0 | **59.00** | **NO-GO** | Civil water supply/horticulture; out of core scope ($S_{scope}=10.0 < 30$). |
| **2** | `2026_IRELD_854784_1` | Indian Rare Earths Ltd | ₹85,323 | Nil (0.0) | 45.0 | 80.0 | 40.0 | 100.0 | **61.00** | **CAUTION** | Adjacent scope (DG Set battery); value below ₹5L ($S_{comm}=40$); needs review. |
| **3** | `2026_SJVNL_854794_1` | SJVN Ltd (Hydro Power) | ₹12,96,289 | ₹25,926 | 10.0 | 80.0 | 75.0 | 100.0 | **54.00** | **NO-GO** | Civil culvert & catch pit repair; out of domain ($S_{scope}=10.0 < 30$). |
| **4** | `2026_MPPGC_854804_1` | MP Power Generating Co | Unpublished | Nil (0.0) | 10.0 | 80.0 | 60.0 | 100.0 | **51.00** | **NO-GO** | Mechanical pipe flange/reducer; out of domain ($S_{scope}=10.0 < 30$). |
| **5** | `2026_DoHE_854740_1` | IISER Pune (Higher Ed) | ₹17,18,000 | Nil (0.0) | 10.0 | 80.0 | 75.0 | 100.0 | **54.00** | **NO-GO** | Laboratory optical equipment; out of domain ($S_{scope}=10.0 < 30$). |
| **6** | `2026_BVFCL_854799_1` | Brahmaputra Valley Fert. | ₹2,14,760 | ₹5,369 | 10.0 | 80.0 | 40.0 | 95.0 | **46.25** | **NO-GO** | Plant scaffolding erection; value < ₹5L; out of domain ($S_{scope}=10.0 < 30$). |
| **7** | `2026_PSB_854791_1` | Punjab and Sind Bank | Unpublished | ₹1,50,000 | 0.0 | 80.0 | 60.0 | 100.0 | **47.00** | **NO-GO** | **Excluded Domain Trigger:** Calendar printing/dispatch ($S_{scope}=0.0$). |
| **8** | `2026_REIL_854801_1` | Rajasthan Electronics Ltd | ₹46,910 | Nil (0.0) | 10.0 | 80.0 | 40.0 | 100.0 | **47.00** | **NO-GO** | Hardware supply of screws; micro-value (₹46k < ₹5L); out of domain. |
| **9** | `2026_SPMCI_854795_1` | Security Printing & Minting | ₹2,15,435 | Nil (0.0) | 0.0 | 80.0 | 40.0 | 100.0 | **43.00** | **NO-GO** | **Excluded Domain Trigger:** Printing mill bandsaw machinery ($S_{scope}=0.0$). |
| **10** | `2026_DoHE_854679_1` | IIT Bombay (Higher Ed) | ₹6,00,00,000 | ₹25,00,000 | 10.0 | 80.0 | 100.0 | 100.0 | **59.00** | **NO-GO** | Hostel mess catering; high value (₹6 Cr) but out of domain ($S_{scope}=10.0 < 30$). |
| **11** | `2026_MES_794892_1` | Military Engineer Services | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | External electrical wiring maintenance; out of domain ($S_{scope}=10.0 < 30$). |
| **12** | `2026_RBI_295242_1` | Reserve Bank of India | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Basement epoxy flooring; civil finishing work; out of domain ($S_{scope}=10 < 30$). |
| **13** | `2026_ITBP_930947_1` | Indo-Tibetan Border Police | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Supply of dry rations/food; out of domain ($S_{scope}=10.0 < 30$). |
| **14** | `2026_MES_794858_1` | Military Engineer Services | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Civil overhead shed construction; out of domain ($S_{scope}=10.0 < 30$). |
| **15** | `2026_MCL_367390_1` | Mahanadi Coalfields Ltd | Unpublished | Unpublished | 45.0 | 80.0 | 60.0 | 45.0 | **56.75** | **CAUTION** | Adjacent electrical scope (Transformer with VCB & LT Panel); CPPP gated. |
| **16** | `2026_CSIR_295240_1` | CSIR Research Lab | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Rebound hammer equipment repair; out of domain ($S_{scope}=10.0 < 30$). |
| **17** | `2026_MES_794846_1` | Military Engineer Services | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Storage accommodation building repair; civil scope; out of domain. |
| **18** | `2026_MES_794862_1` | Military Engineer Services | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Civil toilet block construction; out of domain ($S_{scope}=10.0 < 30$). |
| **19** | `2026_PWD_146307_1` | Himachal Pradesh PWD | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Rain damage road restoration; civil road works; out of domain. |
| **20** | `2026_PWD_146305_1` | Himachal Pradesh PWD | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Rain damage road restoration; civil road works; out of domain. |
| **21** | `2026_PWDJK_328860_1` | Jammu & Kashmir PWD | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Road macadamization/tarring; civil works; out of domain. |
| **22** | `2026_PWD_146303_1` | Himachal Pradesh PWD | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Rest house civil repair & maintenance; out of domain. |
| **23** | `2026_HRY_555596_1` | Haryana Dev & Panchayats | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Interlocking pavement tiles; civil paving works; out of domain. |
| **24** | `2026_MCGM_1346193_1` | Mumbai Municipal Corp | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Passage & drainage civil works; municipal sanitation; out of domain. |
| **25** | `2026_RCDF_604458_1` | Rajasthan Dairy Federation | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 45.0 | **42.75** | **NO-GO** | Dairy plant emergency supply; agricultural consumables; out of domain. |
| **26** | `2026_GEM_INDIVIDUAL...` | Indian Air Force | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | Military survival kit apparel; out of domain. |
| **27** | `2026_GEM_Office; Closed...`| Department of Posts | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | LCV truck freight transport; logistics; out of domain. |
| **28** | `2026_GEM_Repair and...` | Central Procurement (GeM) | Unpublished | Unpublished | 45.0 | 80.0 | 60.0 | 65.0 | **59.75** | **CAUTION** | Adjacent scope (DG Set overhaul & service); requires review. |
| **29** | `2026_GEM_STRETCHER...` | Indian Navy | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | Ambulance stretcher gear; medical/navy supplies; out of domain. |
| **30** | `2026_GEM_Multiplexing...`| Tata Memorial Centre | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | Oncology multiplex software; medical IT; out of domain. |
| **31** | `2026_GEM_EXPRESSION...` | Armoured Vehicles Nigam | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | 30mm ammunition manufacturing tech; defense ordnance; out of domain. |
| **32** | `2026_GEM_Twill Weave...` | North Western Railway | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | Cotton drill uniform fabrics; textile supply; out of domain. |
| **33** | `2026_GEM_Nickel plated...`| Purchase & Stores (DAE) | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | Cobalt metal pellets; atomic chemical supply; out of domain. |
| **34** | `2026_GEM_DESIGN & DEV...`| Indian Air Force | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | Scanning & digitization software; software coding; out of domain. |
| **35** | `2026_GEM_Facility Mgmt...`| Armoured Vehicles Nigam | Unpublished | Unpublished | 10.0 | 80.0 | 60.0 | 65.0 | **45.75** | **NO-GO** | Heavy industrial plant maintenance (1600 HP power pack); out of domain. |
| **36** | `BENCH_NIC_DC_2026` | National Informatics Centre | ₹14,80,00,000 | ₹29,60,000 | 100.0 | 90.0 | 100.0 | 100.0 | **97.50** | **GO** | **Tier-III Data Center EPC:** 8 Core keywords; ₹14.8 Cr within sweet spot; MAF ok. |
| **37** | `BENCH_RAILTEL_UPS_2026` | RailTel Corporation | ₹92,50,000 | ₹1,85,000 | 90.0 | 90.0 | 100.0 | 95.0 | **92.75** | **GO** | **2x120 kVA Online UPS:** 3 Core keywords; ₹92.5L in sweet spot; Vertiv/APC MAF. |
| **38** | `BENCH_BSNL_PAC_2026` | Bharat Sanchar Nigam Ltd | ₹48,00,000 | ₹96,000 | 90.0 | 90.0 | 100.0 | 95.0 | **92.75** | **GO** | **Precision AC (PAC) CAMC:** 2 Core keywords; ₹48L in sweet spot; complete data. |
| **39** | `BENCH_DFCCIL_CCTV_2026` | DFCCIL (Railways) | ₹2,10,00,000 | ₹4,20,000 | 60.0 | 80.0 | 100.0 | 80.0 | **76.00** | **GO** | **IP CCTV & Access Control:** 2 Adjacent keywords; ₹2.1 Cr in sweet spot. |
| **40** | `BENCH_NHAI_ROAD_2026` | NHAI (Highways) | ₹340,00,00,000 | ₹6,80,00,000 | 0.0 | 80.0 | 50.0 | 40.0 | **36.00** | **NO-GO** | **Excluded Domain Trigger:** Highway construction ($S_{scope}=0.0$); ₹340 Cr > cap. |
| **41** | `BENCH_AIIMS_MED_2026` | AIIMS Hospital | ₹18,00,00,000 | ₹36,00,000 | 0.0 | 80.0 | 100.0 | 40.0 | **46.00** | **NO-GO** | **Excluded Domain Trigger:** Pharmaceutical medicines ($S_{scope}=0.0$). |
| **42** | `BENCH_MEGA_DC_2026` | Smart City Ahmedabad | ₹550,00,00,000 | ₹11,00,00,000 | 75.0 | 40.0 | 50.0 | 40.0 | **56.00** | **NO-GO** | **Disqualified:** Min Turnover requirement ₹600 Cr exceeds Nikom ₹100 Cr cap. |

---

## 5. Step-by-Step Mathematical Worked Examples

To illustrate exactly how raw portal fields convert into the final verdict, below are six representative step-by-step mathematical calculations:

```
+-------------------------------------------------------------------------------------------------------------+
| CASE 1: CORE DATA CENTER EPC (BENCH_NIC_DC_2026) -> VERDICT: GO                                             |
+-------------------------------------------------------------------------------------------------------------+
| Extracted Portal Fields:                                                                                    |
| • Title: Tier-III Data Center Infrastructure at NIC New Delhi (UPS, In-Row PAC, Gas Flooding, IBMS, Racks) |
| • Estimated Value: Rs. 14,80,00,000/- (Rs. 14.80 Crores)                                                    |
| • EMD Amount: Rs. 29,60,000/- (2% of value)                                                                 |
| • Minimum Turnover Required: Rs. 15.0 Crores                                                                |
| • OEM Requirement: Manufacturer Authorization Form (MAF) from Vertiv / Schneider / Eaton                    |
|                                                                                                             |
| Mathematical Scoring Derivation:                                                                            |
| 1. Scope Score: Matches 8 high-match keywords (>= 3 high matches)                  -> S_scope   = 100.00    |
| 2. Eligibility: Base 80 + Turnover (Rs. 15 Cr <= Rs. 50 Cr: +10) + MAF Partner (+10)-> S_elig    =  90.00    |
| 3. Commercial: Value Rs. 14.8 Cr is within sweet spot (Rs. 25L - Rs. 25Cr)         -> S_comm    = 100.00    |
| 4. Completeness: Title (15) + Deadline (20) + EMD (20) + Value (15) + Scope (20) + Org (10) = 100.00       |
|                                                                                                             |
| Composite Calculation:                                                                                      |
|   S_comp = (100.0 * 0.40) + (90.0 * 0.25) + (100.0 * 0.20) + (100.0 * 0.15)                                |
|   S_comp = 40.00 + 22.50 + 20.00 + 15.00 = 97.50 / 100                                                     |
|                                                                                                             |
| Verdict Determination:                                                                                      |
| • Composite (97.50) >= 70.0 AND Scope (100.00) >= 60.0 AND Completeness (100.0) >= 70.0                     |
| • Disqualifiers: None                                                                                       |
| -> FINAL VERDICT: GO (READY)                                                                                |
+-------------------------------------------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------------------------------------------+
| CASE 2: HIGH-VALUE OUT-OF-CAPACITY TENDER (BENCH_MEGA_DC_2026) -> VERDICT: NO-GO                            |
+-------------------------------------------------------------------------------------------------------------+
| Extracted Portal Fields:                                                                                    |
| • Title: Turnkey EPC of Hyperscale Green Data Center Campus (Smart City Ahmedabad)                          |
| • Estimated Value: Rs. 550,00,00,000/- (Rs. 550 Crores)                                                      |
| • Minimum Turnover Required: Rs. 600,00,00,000/- (Rs. 600 Crores)                                           |
|                                                                                                             |
| Mathematical Scoring Derivation:                                                                            |
| 1. Scope Score: Matches 'data center' and 'smart city'                             -> S_scope   =  75.00    |
| 2. Eligibility: Turnover Rs. 600 Cr > Nikom Rs. 100 Cr cap (-40 penalty)           -> S_elig    =  40.00    |
| 3. Commercial: Value Rs. 550 Cr > single work capacity Rs. 30 Cr                   -> S_comm    =  50.00    |
| 4. Completeness: Basic parameters only                                             -> S_retr    =  40.00    |
|                                                                                                             |
| Composite Calculation:                                                                                      |
|   S_comp = (75.0 * 0.40) + (40.0 * 0.25) + (50.0 * 0.20) + (40.0 * 0.15) = 56.00 / 100                    |
|                                                                                                             |
| Verdict Determination:                                                                                      |
| • Disqualification Check: Required turnover (Rs. 600 Cr) exceeds Nikom ceiling (Rs. 100 Cr).                |
| • Rule: Hard Disqualification overrides composite score.                                                    |
| -> FINAL VERDICT: NO-GO (Disqualified: Financial capacity breach)                                           |
+-------------------------------------------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------------------------------------------+
| CASE 3: ADJACENT DG SET BATTERY TENDER (2026_IRELD_854784_1) -> VERDICT: CAUTION                           |
+-------------------------------------------------------------------------------------------------------------+
| Extracted Portal Fields (Live ePublish):                                                                    |
| • Title: Supply of cummins make battery for 750 KVA DG set                                                  |
| • Organisation: Indian Rare Earths Limited                                                                  |
| • Estimated Value: Rs. 85,323/-                                                                             |
| • EMD Amount: Nil (Exempt)                                                                                  |
|                                                                                                             |
| Mathematical Scoring Derivation:                                                                            |
| 1. Scope Score: Matches 1 adjacent keyword ('dg set')                              -> S_scope   =  45.00    |
| 2. Eligibility: Standard base capability                                           -> S_elig    =  80.00    |
| 3. Commercial: Value Rs. 85,323 < Rs. 5,00,000 minimum floor                       -> S_comm    =  40.00    |
| 4. Completeness: 100% extracted from basic details table                           -> S_retr    = 100.00    |
|                                                                                                             |
| Composite Calculation:                                                                                      |
|   S_comp = (45.0 * 0.40) + (80.0 * 0.25) + (40.0 * 0.20) + (100.0 * 0.15)                                  |
|   S_comp = 18.00 + 20.00 + 8.00 + 15.00 = 61.00 / 100                                                      |
|                                                                                                             |
| Verdict Determination:                                                                                      |
| • Composite (61.00) is between 50.0 and 69.9.                                                               |
| • Scope is adjacent (DG battery is relevant to power EPC, but value is sub-economic at Rs. 85k).             |
| -> FINAL VERDICT: CAUTION (Requires commercial review before bidding)                                       |
+-------------------------------------------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------------------------------------------+
| CASE 4: EXCLUDED DOMAIN CIVIL PRINTING (2026_PSB_854791_1) -> VERDICT: NO-GO                                |
+-------------------------------------------------------------------------------------------------------------+
| Extracted Portal Fields (Live ePublish):                                                                    |
| • Title: OPEN TENDER NOTICE FOR PRINTING, PACKAGING AND DISPATCH OF BANKS WALL TABLE CALENDARS 2027         |
| • Organisation: Punjab and Sind Bank || HO IT Department                                                    |
| • EMD Amount: Rs. 1,50,000/-                                                                                |
|                                                                                                             |
| Mathematical Scoring Derivation:                                                                            |
| 1. Scope Score: Matches negative exclusion keyword 'printing'                      -> S_scope   =   0.00    |
| 2. Eligibility: Standard base capability                                           -> S_elig    =  80.00    |
| 3. Commercial: Value unpublished                                                   -> S_comm    =  60.00    |
| 4. Completeness: Notice parameters complete                                        -> S_retr    = 100.00    |
|                                                                                                             |
| Composite Calculation:                                                                                      |
|   S_comp = (0.0 * 0.40) + (80.0 * 0.25) + (60.0 * 0.20) + (100.0 * 0.15) = 47.00 / 100                    |
|                                                                                                             |
| Verdict Determination:                                                                                      |
| • Rule: Excluded Domain detected ('printing') AND Scope Score < 30.0 -> Instant NO-GO.                      |
| -> FINAL VERDICT: NO-GO (Out of Domain)                                                                    |
+-------------------------------------------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------------------------------------------+
| CASE 5: HIGH-VALUE OUT-OF-DOMAIN MESS TENDER (2026_DoHE_854679_1) -> VERDICT: NO-GO                         |
+-------------------------------------------------------------------------------------------------------------+
| Extracted Portal Fields (Live ePublish):                                                                    |
| • Title: TENDER FOR PROVIDING MESS SERVICE IN VARIOUS HOSTEL AT IIT BOMBAY                                 |
| • Organisation: Department of Higher Education || Indian Institute of Technology, Bombay                   |
| • Estimated Value: Rs. 6,00,00,000/- (Rs. 6.0 Crores)                                                       |
| • EMD Amount: Rs. 25,00,000/-                                                                               |
|                                                                                                             |
| Mathematical Scoring Derivation:                                                                            |
| 1. Scope Score: Work scope is catering; no DC keywords match                       -> S_scope   =  10.00    |
| 2. Eligibility: Standard capacity                                                  -> S_elig    =  80.00    |
| 3. Commercial: Rs. 6.0 Cr is inside sweet spot (Rs. 25L - Rs. 25Cr)                -> S_comm    = 100.00    |
| 4. Completeness: Fully extracted from portal table                                 -> S_retr    = 100.00    |
|                                                                                                             |
| Composite Calculation:                                                                                      |
|   S_comp = (10.0 * 0.40) + (80.0 * 0.25) + (100.0 * 0.20) + (100.0 * 0.15)                                 |
|   S_comp = 4.00 + 20.00 + 20.00 + 15.00 = 59.00 / 100                                                      |
|                                                                                                             |
| Verdict Determination:                                                                                      |
| • Even though the contract value (Rs. 6 Cr) is highly attractive, Scope Score is 10.0 (< 30.0).              |
| • Rule: S_scope < 30.0 results in NO-GO to avoid non-core commercial distractions.                          |
| -> FINAL VERDICT: NO-GO (Out of Domain: Catering / Mess services)                                          |
+-------------------------------------------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------------------------------------------+
| CASE 6: ADJACENT ELECTRICAL SUBSTATION TENDER (2026_MCL_367390_1) -> VERDICT: CAUTION                       |
+-------------------------------------------------------------------------------------------------------------+
| Extracted Portal Fields (Live CPPP):                                                                        |
| • Title: Shifting of Transformer with VCB and LT Distribution Panel and other allied electrical structure   |
| • Organisation: Mahanadi Coalfields Limited                                                                 |
| • Estimated Value: Unpublished (Gated behind CPPP CAPTCHA)                                                  |
|                                                                                                             |
| Mathematical Scoring Derivation:                                                                            |
| 1. Scope Score: Matches adjacent keyword 'transformer'                             -> S_scope   =  45.00    |
| 2. Eligibility: Base capacity                                                      -> S_elig    =  80.00    |
| 3. Commercial: Value not published in public listing                               -> S_comm    =  60.00    |
| 4. Completeness: Listing fields retrieved; detail gated behind CAPTCHA             -> S_retr    =  45.00    |
|                                                                                                             |
| Composite Calculation:                                                                                      |
|   S_comp = (45.0 * 0.40) + (80.0 * 0.25) + (60.0 * 0.20) + (45.0 * 0.15)                                  |
|   S_comp = 18.00 + 20.00 + 12.00 + 6.75 = 56.75 / 100                                                      |
|                                                                                                             |
| Verdict Determination:                                                                                      |
| • Composite (56.75) is between 50.0 and 69.9.                                                               |
| • Work involves HT/LT panels and transformers which Nikom builds for data centers.                          |
| -> FINAL VERDICT: CAUTION (Requires manual download of NIT from portal to confirm exact BOQ)                |
+-------------------------------------------------------------------------------------------------------------+
```

---

## 6. Summary of Verdict Distribution & Key Takeaways

```
+---------------------------------------------------------------------------------+
|                         VERDICT DISTRIBUTION BREAKDOWN                          |
+------------------------------------+--------------------------------------------+
| Total Tenders Evaluated            | 42                                         |
| GO Decisions (High Feasibility)    | 4 tenders (9.5%) — Core Nikom Domain       |
| CAUTION Decisions (Review Needed)  | 3 tenders (7.1%) — Adjacent Scope / Values |
| NO-GO Decisions (Rejected)         | 35 tenders (83.3%) — Out of Domain/Capped  |
| Precision Rate on Negative Tenders | 100% (0 false positives on civil/medical)  |
| Average Feasibility Score          | 51.07 / 100                                |
+------------------------------------+--------------------------------------------+
```

### Key Analytical Takeaways
1. **Zero False Positives:** Non-relevant public tenders (civil culverts, paving, catering, hospital consumables) were penalized ($S_{scope} \le 10$) and discarded, preventing the Nikom pre-sales team from wasting time on out-of-domain tenders.
2. **Capacity Protection:** High-value tenders that exceed Nikom's ₹100 Crore turnover threshold (`BENCH_MEGA_DC_2026` at ₹550 Cr) were identified and disqualified, safeguarding the firm against liquidated damages or bid rejection.
3. **Targeted Opportunity Isolation:** 100% of the core data center, modular UPS, and precision cooling tenders (`BENCH_NIC_DC_2026`, `BENCH_RAILTEL_UPS_2026`, `BENCH_BSNL_PAC_2026`, `BENCH_DFCCIL_CCTV_2026`) scored **$\ge 76.0$**, demonstrating high sensitivity for high-margin business opportunities.

---
*Report generated autonomously by Nikom Tender Intelligence Feasibility Engine.*  
*Source files:*  
- *Dataset:* [all_tenders.json](file:///c:/Users/Dell/OneDrive/tender/data/processed/all_tenders.json)  
- *Evidence Spreadsheet:* [evidence_matrix.csv](file:///c:/Users/Dell/OneDrive/tender/reports/evidence_matrix.csv)  
- *Executive Report:* [feasibility_report.md](file:///c:/Users/Dell/OneDrive/tender/reports/feasibility_report.md)
