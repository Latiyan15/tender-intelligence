"""
Classifies GeM bids into Nikom's 8 business groups and assigns roles.
Includes a three-layer relevance scoring system that correlates context
to filter out noise from ambiguous keywords.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Relevance scoring data structures
# ---------------------------------------------------------------------------

class RelevanceVerdict(Enum):
    PASS = "pass"
    BORDERLINE = "borderline"
    REJECT = "reject"


@dataclass
class RelevanceResult:
    verdict: RelevanceVerdict
    score: float
    matched_signals: List[str] = field(default_factory=list)
    reject_reasons: List[str] = field(default_factory=list)
    group_hint: Optional[str] = None


@dataclass
class _WeakKW:
    pattern: "re.Pattern"
    base_score: float
    boosts: List["re.Pattern"]
    rejects: List["re.Pattern"]
    group_hint: str


# ---------------------------------------------------------------------------
# Layer 1: Negative context — fast reject even when a positive keyword matches
# ---------------------------------------------------------------------------

_NEGATIVE_CONTEXTS = [re.compile(p, re.IGNORECASE) for p in [
    # Courier / logistics (UPS brand confusion)
    r"\b(?:courier|parcel|delivery|logistics|postal|shipping|consignment|freight\s+forward)\b",
    # Food / dairy / pharma cooling
    r"\b(?:kitchen|food\s+process|dairy|milk\s+chiller|cold\s+chain|pharma(?:ceut)?|brewery|carcass|mortuary|fish\s+chiller)\b",
    # Medical / hospital equipment
    r"\b(?:hospital\s+bed|operation\s+theatre|surgical|ambulance|oxygen\s+generator|medical\s+gas|blood\s+bank)\b",
    # Residential / comfort cooling
    r"\b(?:split\s+a/?c|window\s+a/?c|split\s+air\s*condition|window\s+air\s*condition|residential\s+quarter|staff\s+quarter|domestic\s+ups|home\s+ups|solar\s+ups)\b",
    # Automotive / agricultural
    r"\b(?:automotive|vehicle\s+hiring|car\s+rental|tractor|agricultural|engine\s+oil|motor\s+pump\s+set|dewatering\s+pump)\b",
    # Signal / instrument / specialty generators
    r"\b(?:signal\s+generator|function\s+generator|ozone\s+generator|oxygen\s+generator|nitrogen\s+generator|hydrogen\s+generator)\b",
    # Laboratory / test equipment
    r"\b(?:laboratory\s+equipment|lab\s+equipment|testing\s+machine|universal\s+testing)\b",
    # Civil / road construction
    r"\b(?:road\s+construct|highway|bridge\s+construct|culvert|earthwork|dredging|masonry|plastering|whitewash)\b",
    # Manpower / housekeeping services
    r"\b(?:data\s+entry\s+operator|security\s+guard|safai|sweeper|housekeeping|canteen\s+service|catering|mess\s+service)\b",
    # Office supplies
    r"\b(?:stationery|calendar\s+print|uniform\s+supply|steel\s+almirah|wooden\s+chair)\b",
    # Transformer oil / petroleum (not electrical infra)
    r"\b(?:transformer\s+oil|oil\s+filtration|oil\s+bdv|ignition\s+transformer|furnace\s+transformer|pole\s+mounted\s+transformer)\b",
]]

# ---------------------------------------------------------------------------
# Layer 2: Strong patterns — high-specificity terms that pass with score 1.0
# ---------------------------------------------------------------------------

_STRONG_PATTERNS = [(re.compile(p, re.IGNORECASE), hint) for p, hint in [
    # Precision cooling
    (r"precision\s+air\s*condition", "1 Best fit – cooling & power"),
    (r"precision\s+a/?c\b", "1 Best fit – cooling & power"),
    (r"precision\s+cooling", "1 Best fit – cooling & power"),
    (r"\bcrac\b", "1 Best fit – cooling & power"),
    (r"\bcrah\b", "1 Best fit – cooling & power"),
    # Data centre context
    (r"data\s+cent(?:re|er)\s+(?:cool|power|infra)", "1 Best fit – cooling & power"),
    (r"(?:cool|power|infra).*data\s+cent(?:re|er)", "1 Best fit – cooling & power"),
    (r"mini\s+data\s+cent", "1 Best fit – cooling & power"),
    (r"server\s+room\s+(?:cool|power|infra|revamp)", "1 Best fit – cooling & power"),
    # Chilled water / large chillers
    (r"chilled[\s-]*water\s+(?:plant|system|hvac|piping)", "1 Best fit – cooling & power"),
    (r"(?:screw|centrifugal|scroll)\s+chiller", "1 Best fit – cooling & power"),
    (r"chiller\s+plant", "1 Best fit – cooling & power"),
    (r"cooling\s+tower", "1 Best fit – cooling & power"),
    # Online / modular UPS
    (r"online\s+ups", "6 UPS / DG / electrical"),
    (r"modular\s+ups", "6 UPS / DG / electrical"),
    (r"\bups\b.*\d+\s*kva", "6 UPS / DG / electrical"),
    (r"\d+\s*kva\b.*\bups\b", "6 UPS / DG / electrical"),
    (r"ups\s+(?:system|batter(?:y|ies))", "6 UPS / DG / electrical"),
    # DG set / genset
    (r"(?:diesel|dg)\s+(?:gen|set)", "6 UPS / DG / electrical"),
    (r"\bdg\s+set\b", "6 UPS / DG / electrical"),
    (r"\bgenset\b", "6 UPS / DG / electrical"),
    (r"generator\s+set", "6 UPS / DG / electrical"),
    # Structured cabling / racks
    (r"structured\s+cabl", "8 Racks & cabling"),
    (r"server\s+rack", "8 Racks & cabling"),
    (r"network\s+rack", "8 Racks & cabling"),
    (r"smart\s+rack", "8 Racks & cabling"),
    (r"(?:42u|24u)\s+rack", "8 Racks & cabling"),
    # Fire detection / suppression
    (r"fire\s+detect", "7 Fire detection AMC"),
    (r"fire\s+alarm", "7 Fire detection AMC"),
    (r"fire\s+suppress", "7 Fire detection AMC"),
    (r"fire\s+hydrant", "7 Fire detection AMC"),
    (r"novec\s+1230", "7 Fire detection AMC"),
    (r"\bvesda\b", "7 Fire detection AMC"),
    # HPC
    (r"\bhpc\b", "3 HPC – partner only"),
    (r"gpu\s+(?:cluster|compute)", "3 HPC – partner only"),
    (r"supercomput", "3 HPC – partner only"),
    # VRF / VRV / ductable
    (r"\bvrv\b", "5 HVAC & VRF supply / install"),
    (r"ductable\s+a/?c", "5 HVAC & VRF supply / install"),
    # Cleanroom
    (r"cleanroom", "5 HVAC & VRF supply / install"),
    # Busduct
    (r"bus\s*duct", "6 UPS / DG / electrical"),
    # Data centre AMC
    (r"(?:amc|camc|cmc)\s+(?:of\s+)?data\s+cent", "4 Chiller / HVAC O&M & AMC"),
    (r"data\s+cent(?:re|er)\s+(?:amc|camc|cmc)", "4 Chiller / HVAC O&M & AMC"),
]]

# ---------------------------------------------------------------------------
# Layer 3: Weak keywords — ambiguous terms that need corroborating context
# ---------------------------------------------------------------------------

def _compile_list(patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns]

_WEAK_KEYWORDS = [
    _WeakKW(
        pattern=re.compile(r"\bups\b", re.IGNORECASE),
        base_score=0.3,
        boosts=_compile_list([
            r"\bkva\b", r"\bonline\b", r"\bbatter(?:y|ies)\b", r"\bpower\b",
            r"data\s+cent", r"server\s+room", r"\bphase\b", r"\binverter\b",
            r"\brectifier\b", r"\bmodular\b", r"\bbackup\b",
            r"\bschneider\b", r"\bvertiv\b", r"\beaten\b", r"\bapc\b",
        ]),
        rejects=_compile_list([
            r"\bcourier\b", r"\bdelivery\b", r"\bexpress\b", r"\bparcel\b",
            r"\btraffic\b", r"\bsolar\b", r"\bhome\b", r"\bdomestic\b",
            r"\b600\s*va\b", r"\b800\s*va\b",
        ]),
        group_hint="6 UPS / DG / electrical",
    ),
    _WeakKW(
        pattern=re.compile(r"\bgenerator\b", re.IGNORECASE),
        base_score=0.2,
        boosts=_compile_list([
            r"\bkva\b", r"\bdiesel\b", r"\bstandby\b", r"\bbackup\b",
            r"\bacoustic\b", r"\bamf\b", r"\bsync\b", r"\bcpcb\b",
            r"data\s+cent", r"server\s+room",
            r"\bcummins\b", r"\bkirloskar\b",
        ]),
        rejects=_compile_list([
            r"\bsignal\b", r"\bozone\b", r"\boxygen\b", r"\bnitrogen\b",
            r"\bhydrogen\b", r"\bfunction\b", r"\blaboratory\b",
            r"\bsteam\b", r"\bportable\b",
        ]),
        group_hint="6 UPS / DG / electrical",
    ),
    _WeakKW(
        pattern=re.compile(r"\bcooling\b", re.IGNORECASE),
        base_score=0.25,
        boosts=_compile_list([
            r"data\s+cent", r"server\s+room", r"\bprecision\b", r"\bchiller\b",
            r"\bhvac\b", r"\brack\b", r"\bin[\s-]*row\b", r"\bcontainment\b",
            r"\btr\b", r"\bton\b", r"\btower\b",
        ]),
        rejects=_compile_list([
            r"\bkitchen\b", r"\bfood\b", r"\bdairy\b", r"\bpharm",
            r"\bengine\b", r"\bautomot", r"\bindustrial\s+process\b",
            r"\bcold\s+chain\b", r"\bcold\s+storage\b",
        ]),
        group_hint="1 Best fit – cooling & power",
    ),
    _WeakKW(
        pattern=re.compile(r"\btransformer\b", re.IGNORECASE),
        base_score=0.2,
        boosts=_compile_list([
            r"\bisolation\b", r"\bdry[\s-]*type\b", r"\bresin\s+cast\b",
            r"data\s+cent", r"server\s+room", r"\bsubstation\b",
            r"\b(?:lt|ht)\s+panel\b", r"\belectrical\s+panel\b",
            r"\bstep[\s-]*down\b", r"\bk[\s-]*factor\b",
        ]),
        rejects=_compile_list([
            r"\btransformer\s+oil\b", r"\boil\s+(?:filtration|bdv|testing)\b",
            r"\bignition\b", r"\bfurnace\b", r"\bpole\s+mounted\b",
            r"\bdistribution\s+transformer\b", r"\brural\b",
            r"\bpump\s+set\b", r"\btubewell\b", r"\bwelding\b",
            r"\binstrument\b",
        ]),
        group_hint="6 UPS / DG / electrical",
    ),
    _WeakKW(
        pattern=re.compile(r"air\s*condition", re.IGNORECASE),
        base_score=0.3,
        boosts=_compile_list([
            r"\bprecision\b", r"\bductable\b", r"\bvrf\b", r"\bvrv\b",
            r"\bhvac\b", r"data\s+cent", r"server\s+room",
            r"\bsitc\b", r"\bahu\b", r"\bchiller\b",
            r"\bcommission\b", r"\berection\b",
        ]),
        rejects=_compile_list([
            r"\bsplit\b", r"\bwindow\b", r"\bresidential\b",
            r"\bdomestic\b", r"\bhome\b", r"\bwall\s+mounted\b",
            r"\broom\s+air\b(?!.*server)", r"\bportable\b",
        ]),
        group_hint="5 HVAC & VRF supply / install",
    ),
    _WeakKW(
        pattern=re.compile(r"\bchiller\b", re.IGNORECASE),
        base_score=0.4,
        boosts=_compile_list([
            r"\btr\b", r"\bton\b", r"\bchilled\s+water\b", r"\bhvac\b",
            r"\bscrew\b", r"\bcentrifugal\b", r"\bscroll\b", r"\bplant\b",
            r"data\s+cent", r"server\s+room", r"\bcooling\s+tower\b",
        ]),
        rejects=_compile_list([
            r"\bmilk\b", r"\bdairy\b", r"\bdrinking\b", r"\bcarcass\b",
            r"\bmortuary\b", r"\bfish\b", r"\bbrewery\b", r"\bmeat\b",
        ]),
        group_hint="1 Best fit – cooling & power",
    ),
    _WeakKW(
        pattern=re.compile(r"\bhvac\b", re.IGNORECASE),
        base_score=0.4,
        boosts=_compile_list([
            r"data\s+cent", r"server\s+room", r"\bprecision\b", r"\bchiller\b",
            r"\bclean\s*room\b", r"\bcommand\s+cent", r"\bnoc\b",
            r"\btier\s+(?:iii|iv|3|4)\b", r"\bductable\b",
            r"\bsitc\b", r"\bcommission\b",
        ]),
        rejects=_compile_list([
            r"\bsplit\s+a/?c\b", r"\bwindow\s+a/?c\b", r"\bresidential\b",
            r"\bstaff\s+quarter\b", r"\bhostel\b", r"\bhospital\s+ward\b",
            r"\bpassenger\s+coach\b", r"\bbarrack\b", r"\bmess\s+hall\b",
        ]),
        group_hint="5 HVAC & VRF supply / install",
    ),
    _WeakKW(
        pattern=re.compile(r"\b(?:lt|ht)\s+panel\b", re.IGNORECASE),
        base_score=0.35,
        boosts=_compile_list([
            r"data\s+cent", r"server\s+room", r"\bups\b", r"\bsubstation\b",
            r"\btransformer\b", r"\belectrical\b", r"\bbus\s*duct\b",
        ]),
        rejects=_compile_list([
            r"\brural\b", r"\bpump\s+house\b", r"\btubewell\b",
            r"\bagricult\b", r"\birrigation\b",
        ]),
        group_hint="6 UPS / DG / electrical",
    ),
    _WeakKW(
        pattern=re.compile(r"\bbms\b", re.IGNORECASE),
        base_score=0.25,
        boosts=_compile_list([
            r"\bbuilding\s+management\b", r"data\s+cent", r"server\s+room",
            r"\bautomation\b", r"\bscada\b", r"\bhvac\b", r"\bibms\b",
            r"\bmonitoring\b", r"\bsensor\b",
        ]),
        rejects=_compile_list([
            r"\bbattery\s+management\b", r"\bcollege\b", r"\bcourse\b",
            r"\bbiomedical\b",
        ]),
        group_hint="1 Best fit – cooling & power",
    ),
    _WeakKW(
        pattern=re.compile(r"\bvrf\b", re.IGNORECASE),
        base_score=0.5,
        boosts=_compile_list([
            r"\bsystem\b", r"\bunit\b", r"\boutdoor\b", r"\bindoor\b",
            r"\bcopper\s+pip\b", r"\binstall\b",
        ]),
        rejects=[],
        group_hint="5 HVAC & VRF supply / install",
    ),
    _WeakKW(
        pattern=re.compile(r"\bahu\b", re.IGNORECASE),
        base_score=0.45,
        boosts=_compile_list([
            r"\bhvac\b", r"\bductable\b", r"\bclean\s*room\b",
            r"data\s+cent", r"server\s+room", r"\bchiller\b",
        ]),
        rejects=[],
        group_hint="5 HVAC & VRF supply / install",
    ),
    _WeakKW(
        pattern=re.compile(r"\bbuilding\s+management\b", re.IGNORECASE),
        base_score=0.45,
        boosts=_compile_list([
            r"data\s+cent", r"server\s+room", r"\bautomation\b",
            r"\bscada\b", r"\bsensor\b", r"\bhvac\b",
        ]),
        rejects=[],
        group_hint="1 Best fit – cooling & power",
    ),
]

# Buyer organizations that frequently procure DC / IT infrastructure
_BUYER_BOOSTS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bnic\b", r"national\s+informatics",
    r"\bc[\-\s]*dac\b", r"\bc[\-\s]*dot\b",
    r"\bdrdo\b", r"\bongc\b", r"\biocl\b", r"indian\s+oil",
    r"\baai\b", r"airports?\s+authority", r"\bcris\b",
    r"\bntpc\b", r"\bnhpc\b", r"power\s+grid",
    r"\b(?:iit|nit)\b", r"\bnatgrid\b",
    r"\b(?:pnb|sbi|rbi|boi)\b",
    r"\brailtel\b", r"\bbsnl\b", r"\bmtnl\b",
    r"(?:ministry|dept).*(?:electron|informat|telecom|defence)",
]]


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def score_nikom_relevance(
    title: str,
    scope: str = "",
    issuing_org: str = "",
) -> RelevanceResult:
    """Score a GeM bid for relevance to Nikom's business domains.

    Three layers evaluated in order:
      1. Negative context rejection (fast reject even if positive keywords present)
      2. Strong pattern matching (unambiguous terms pass with score=1.0)
      3. Context-gated scoring for ambiguous terms (boost/reject context)
    """
    text = f"{title} {scope}".lower().strip()
    signals: List[str] = []
    rejects: List[str] = []

    # Layer 1: Negative context
    for neg_re in _NEGATIVE_CONTEXTS:
        if neg_re.search(text):
            has_strong_override = any(sp.search(text) for sp, _ in _STRONG_PATTERNS)
            if not has_strong_override:
                rejects.append(neg_re.pattern)
                return RelevanceResult(
                    verdict=RelevanceVerdict.REJECT, score=0.0,
                    matched_signals=signals, reject_reasons=rejects,
                )

    # Layer 2: Strong patterns
    for strong_re, group_hint in _STRONG_PATTERNS:
        if strong_re.search(text):
            signals.append(strong_re.pattern)
            return RelevanceResult(
                verdict=RelevanceVerdict.PASS, score=1.0,
                matched_signals=signals, group_hint=group_hint,
            )

    # Layer 3: Context-gated scoring
    best_score = 0.0
    best_hint = None

    for wk in _WEAK_KEYWORDS:
        if not wk.pattern.search(text):
            continue

        score = wk.base_score
        signals.append(wk.pattern.pattern)

        rejected = False
        for rej_re in wk.rejects:
            if rej_re.search(text):
                score -= 0.3
                rejects.append(rej_re.pattern)
                if score < 0.0:
                    rejected = True
                    break
        if rejected:
            continue

        for boost_re in wk.boosts:
            if boost_re.search(text):
                score += 0.15
                signals.append(boost_re.pattern)

        score = min(score, 1.0)
        if score > best_score:
            best_score = score
            best_hint = wk.group_hint

    # Buyer organization boost
    if issuing_org:
        org_lower = issuing_org.lower()
        for org_re in _BUYER_BOOSTS:
            if org_re.search(org_lower):
                best_score = min(best_score + 0.15, 1.0)
                signals.append(f"buyer:{org_re.pattern}")
                break

    if best_score >= 0.5:
        verdict = RelevanceVerdict.PASS
    elif best_score >= 0.3:
        verdict = RelevanceVerdict.BORDERLINE
    else:
        verdict = RelevanceVerdict.REJECT

    return RelevanceResult(
        verdict=verdict, score=best_score,
        matched_signals=signals, reject_reasons=rejects,
        group_hint=best_hint,
    )


# Each group: (group_label, nikom_role, keywords_must_match, keywords_exclude)
# Order matters — first match wins, so more specific groups come first.
GROUP_RULES = [
    # Group 7: Fire detection AMC — very specific, check early
    {
        "label": "7 Fire detection AMC",
        "role": "Direct bidder",
        "match_any": [
            r"fire\s+detect", r"fire\s+alarm", r"fire\s+hydrant",
            r"fire\s+sprinkler", r"fire\s+suppress", r"fire\s+fight",
            r"fire\s+extinguish",
            r"(?:amc|cmc|camc|o\s*&?\s*m).*fire",
            r"fire.*(?:amc|cmc|camc|o\s*&?\s*m)",
        ],
        "exclude": [],
    },
    # Group 3: HPC — partner only
    {
        "label": "3 HPC – partner only",
        "role": "Site-prep / power / cooling partner to IT bidder",
        "match_any": [
            r"\bhpc\b", r"high\s*performance\s*comput",
            r"gpu\s+compute", r"gpu\s+cluster",
            r"cpu[\s-]*gpu.*cluster", r"lustre\s+storage",
            r"supercomput",
        ],
        "exclude": [],
    },
    # Group 4: Chiller / HVAC O&M & AMC — maintenance/repair contracts
    {
        "label": "4 Chiller / HVAC O&M & AMC",
        "role": "Direct bidder",
        "match_any": [
            r"\b(?:amc|cmc|camc|comprehensive\s+(?:annual\s+)?maintenance)\b.*(?:hvac|chiller|air\s*condition|precision\s+a/?c|vrf|vrv|cooling)",
            r"(?:hvac|chiller|air\s*condition|precision\s+a/?c|vrf|vrv|cooling).*\b(?:amc|cmc|camc|comprehensive\s+(?:annual\s+)?maintenance)\b",
            r"\bo\s*&\s*m\b\s+(?:of\s+)?(?:hvac|chiller|air\s*condition|cooling|precision)",
            r"(?:hvac|chiller|air\s*condition|cooling|precision).*\bo\s*&\s*m\b",
            r"(?:repair|overhaul|servicing).*(?:chiller|precision\s+a/?c|hvac|air\s*condition)",
            r"(?:chiller|precision\s+a/?c|hvac|air\s*condition).*(?:repair|overhaul|servicing)",
            r"\bmaintenance\b.*(?:chiller|hvac|air\s*condition|precision|cooling\s+plant)",
            r"\boperation\b.*\bmaintenance\b.*(?:hvac|chiller|cooling)",
        ],
        "exclude": [],
    },
    # Group 1: Best fit — cooling & power (supply of major DC equipment)
    # Checked BEFORE Groups 5 and 6 so large chilled-water plants and
    # comprehensive UPS AMC land here, matching the user's own categorization.
    {
        "label": "1 Best fit – cooling & power",
        "role": "Direct bidder",
        "match_any": [
            r"precision\s+air\s*condition", r"precision\s+a/?c",
            r"(?:data\s+cent(?:re|er)|server\s+room).*(?:cool|power|infra)",
            r"(?:cool|power|infra).*(?:data\s+cent(?:re|er)|server\s+room)",
            r"mini\s+data\s+cent",
            r"integrated.*cooling\s+solution",
            r"(?:chilled[\s-]*water|water[\s-]*cooled).*(?:chiller|plant|system|hvac|piping)",
            r"chilled[\s-]*water\s+(?:hvac|plant)",
            r"(?:screw|centrifugal|scroll)\s+chiller",
            r"(?:100|150|200|250|300|400|500|600)\s*tr\b.*chiller",
            r"chiller\s+(?:plant|package|system)",
            r"cooling\s+(?:system|solution|tower|plant)",
            r"comprehensive\s+amc.*(?:ups|online\s+ups)",
            r"(?:comprehensive|manpower).*(?:cmc|ups|precision)",
            r"(?:cmc|amc).*(?:ups\s+system|precision\s+air)",
        ],
        "exclude": [
            r"(?:amc|cmc|camc|o\s*&?\s*m|repair|overhaul|maintenance).*(?:hvac(?!\s*plant)|(?<!precision\s)air\s*condition(?!er))",
        ],
    },
    # Group 8: Racks & cabling — checked before Group 2 so "server + smart rack" lands here
    {
        "label": "8 Racks & cabling",
        "role": "Direct bidder",
        "match_any": [
            r"structured\s+cabl", r"server\s+rack", r"network\s+rack",
            r"smart\s+rack.*server", r"server.*smart\s+rack",
            r"rack.*cable", r"cable.*rack",
            r"lan\s+cabl", r"fibre?\s+cabl",
        ],
        "exclude": [],
    },
    # Group 2: Quick win — simpler / smaller items
    {
        "label": "2 Quick win",
        "role": "Direct bidder",
        "match_any": [
            r"smart\s+rack",
            r"compact.*(?:chiller|water\s+chiller)",
            r"industrial\s+chiller",
            r"\b(?:5|7\.?5|10|15)\s*tr\b.*(?:chiller|water\s+chiller)",
            r"chiller\s+(?:5|7\.?5|10|15)\s*ton",
            r"(?:centrifugal|screw)\s+chiller\b(?!.*(?:plant|package|system|\bamc\b|repair|\d{3}\s*tr))",
        ],
        "exclude": [
            r"\b(?:amc|cmc|camc)\b",
            r"\bo\s*&\s*m\b",
            r"\b(?:repair|overhaul|maintenance)\b",
            r"(?:100|150|200|250|300|400|500|600)\s*tr\b",
        ],
    },
    # Group 5: HVAC & VRF supply / install (new installation, not maintenance)
    {
        "label": "5 HVAC & VRF supply / install",
        "role": "Direct bidder",
        "match_any": [
            r"(?:sitc|supply.*install|erection.*commission).*(?:hvac|vrf|vrv|ductable|ducted|air\s*condition|chiller|ahu|cleanroom)",
            r"(?:hvac|vrf|vrv|ductable|ducted).*(?:sitc|supply.*install|erection.*commission)",
            r"execution.*hvac\s+work",
            r"hvac.*(?:works?|system)",
            r"(?:vrf|vrv)\s+(?:systems?|units?|outdoor|indoor)",
            r"(?:vrf|vrv)\b.*(?:compensat|copper\s+pip|install)",
            r"ductable\s+a/?c",
            r"cleanroom.*(?:hvac|panel|facility)",
            r"modular\s+cleanroom",
        ],
        "exclude": [
            r"\b(?:amc|cmc|camc)\b",
            r"\bo\s*&\s*m\b",
            r"\b(?:repair|overhaul|maintenance)\b",
            r"chilled[\s-]*water",
        ],
    },
    # Group 6: UPS / DG / electrical
    {
        "label": "6 UPS / DG / electrical",
        "role": "Direct bidder",
        "match_any": [
            r"\bups\b.*\d+\s*kva",
            r"\d+\s*kva\b.*\bups\b",
            r"(?:online\s+)?ups\b(?!.*(?:chiller|hvac|precision|cooling))",
            r"\bups\s+(?:system|battery|batteries)",
            r"(?:diesel|dg)\s+(?:gen|set)", r"\bdg\s+set",
            r"generator\s+set", r"\bgenset\b",
            r"(?:amc|cmc).*(?:dg\s+set|generator)",
            r"(?:dg\s+set|generator).*(?:amc|cmc)",
            r"busduct", r"bus\s*duct",
            r"batter(?:y|ies).*ups", r"ups.*batter(?:y|ies)",
            r"(?:lt|ht)\s+panel", r"transformer",
            r"\bkva\b.*(?:dg|generator)",
            r"(?:dg|generator).*\bkva\b",
            r"rental.*(?:dg|generator)",
        ],
        "exclude": [
            r"comprehensive\s+amc.*ups",
            r"(?:manpower|\bcmc\b).*(?:ups\s+system|precision)",
        ],
    },
]


def classify_bid(title: str, scope: str = "") -> Tuple[str, str]:
    """
    Classify a GeM bid into one of Nikom's 8 groups.

    Returns (group_label, nikom_role).
    Falls back to "1 Best fit – cooling & power" / "Direct bidder" if
    the bid matched Nikom keywords but no specific group.
    """
    text = f"{title} {scope}".lower().strip()

    for rule in GROUP_RULES:
        excluded = False
        for exc_pattern in rule["exclude"]:
            if re.search(exc_pattern, text, re.IGNORECASE):
                excluded = True
                break
        if excluded:
            continue

        for pattern in rule["match_any"]:
            if re.search(pattern, text, re.IGNORECASE):
                role = rule["role"]
                if rule["label"] == "8 Racks & cabling" and re.search(r"server", text, re.I):
                    role = "Rack portion / partner with server OEM"
                return rule["label"], role

    return "0 Unclassified", "Review needed"


def is_nikom_relevant(title: str, scope: str = "", issuing_org: str = "") -> bool:
    """Check if a GeM bid falls within Nikom's business domains.

    Uses the three-layer relevance scoring system. Returns True for PASS
    and BORDERLINE verdicts (borderline bids get LLM triage downstream).
    """
    result = score_nikom_relevance(title, scope, issuing_org)
    return result.verdict != RelevanceVerdict.REJECT
