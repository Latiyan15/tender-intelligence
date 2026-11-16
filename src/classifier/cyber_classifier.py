"""
Classifies GeM bids into cyber-security groups and assigns roles.

Mirrors the three-layer relevance scoring in ``gem_classifier`` (negative
context rejection -> strong patterns -> context-gated weak keywords) but with
a cyber-security taxonomy seeded from ``config/keywords.yaml`` Tier A and
hardened against the classic cyber false-positives (physical security,
financial "security deposit", System-on-Chip "SoC", DLP projectors, civil
"penetration test", etc.).
"""

import re
from typing import List, Optional, Tuple

# Reuse the shared scoring primitives from the DC classifier.
from src.classifier.gem_classifier import (
    RelevanceVerdict,
    RelevanceResult,
    _WeakKW,
    _compile_list,
)


# ---------------------------------------------------------------------------
# Layer 1: Negative context — fast reject even when a cyber keyword matches
# ---------------------------------------------------------------------------

_CYBER_NEGATIVE_CONTEXTS = [re.compile(p, re.IGNORECASE) for p in [
    # Physical security manpower (the #1 noise source for "security")
    r"\b(?:security\s+guard|guard\s+service|gunman|armed\s+guard|security\s+personnel|bouncer|watch\s*man|patrolling\s+service)\b",
    r"\b(?:housekeeping|safai|sweeper|canteen\s+service|catering|mess\s+service|manpower\s+supply)\b",
    # Physical access-control hardware (not logical/network access)
    r"\b(?:boom\s+barrier|tripod\s+turnstile|flap\s+barrier|spike\s+barrier|road\s+blocker|bollard)\b",
    # Fire fighting (physical) — "firewall" confusion with fire safety
    r"\b(?:fire\s+fight\w*|fire\s+tender|fire\s+brigade|fire\s+engines?)\b",
    r"\b(?:brick|masonry|rcc)\s+fire\s*wall\b",
    r"\bfire\s*wall\b.*\b(?:brick|masonry|rcc|partition|plaster|construct)\b",
    # Unrelated "security" phrases
    r"\b(?:food\s+security|social\s+security|national\s+food|security\s+deposit\s+refund)\b",
    r"\bsoil\s+organic\s+carbon\b",
    # Civil / soil penetration testing (not pentest)
    r"\b(?:soil|concrete|standard\s+cone|spt)\s+penetration\s+test",
    r"\bpenetration\s+test\w*\b.*\b(?:soil|concrete|cone|spt|plate\s+load|geotech)\b",
    # Clearly non-IT domains
    r"\b(?:road\s+construct|highway|culvert|earthwork|masonry|plastering|whitewash)\b",
    r"\b(?:tractor|agricultural|irrigation|tubewell|dewatering\s+pump)\b",
]]

# ---------------------------------------------------------------------------
# Layer 2: Strong patterns — unambiguous cyber terms that pass with score 1.0
# ---------------------------------------------------------------------------

_CYBER_STRONG_PATTERNS = [(re.compile(p, re.IGNORECASE), hint) for p, hint in [
    # SOC / SIEM / monitoring
    (r"\bsiem\b", "1 SOC / SIEM / monitoring"),
    (r"security\s+information\s+and\s+event", "1 SOC / SIEM / monitoring"),
    (r"security\s+operations?\s+cent(?:re|er)", "1 SOC / SIEM / monitoring"),
    (r"managed\s+detection\s+and\s+response", "1 SOC / SIEM / monitoring"),
    (r"\bmdr\b", "1 SOC / SIEM / monitoring"),
    (r"\bxdr\b", "3 Endpoint & threat defense"),
    # Network security
    (r"next[\s-]*gen(?:eration)?\s+firewall", "2 Network security (firewall / WAF)"),
    (r"\bngfw\b", "2 Network security (firewall / WAF)"),
    (r"web\s+application\s+firewall", "2 Network security (firewall / WAF)"),
    (r"\bwaf\b", "2 Network security (firewall / WAF)"),
    (r"unified\s+threat\s+management", "2 Network security (firewall / WAF)"),
    (r"\bd?dos\s+(?:protection|mitigation)", "2 Network security (firewall / WAF)"),
    (r"anti[\s-]*ddos", "2 Network security (firewall / WAF)"),
    (r"intrusion\s+(?:prevention|detection)\s+system", "2 Network security (firewall / WAF)"),
    (r"secure\s+web\s+gateway", "2 Network security (firewall / WAF)"),
    # Endpoint & threat defense
    (r"endpoint\s+detection\s+and\s+response", "3 Endpoint & threat defense"),
    (r"\bedr\b", "3 Endpoint & threat defense"),
    (r"endpoint\s+(?:security|protection)", "3 Endpoint & threat defense"),
    (r"anti[\s-]*virus", "3 Endpoint & threat defense"),
    (r"anti[\s-]*malware", "3 Endpoint & threat defense"),
    (r"anti[\s-]*ransomware", "3 Endpoint & threat defense"),
    (r"threat\s+intelligence", "3 Endpoint & threat defense"),
    (r"zero[\s-]*day\s+protection", "3 Endpoint & threat defense"),
    # Identity & access
    (r"identity\s+and\s+access\s+management", "4 Identity & access (IAM / PAM)"),
    (r"privileged\s+access\s+management", "4 Identity & access (IAM / PAM)"),
    (r"multi[\s-]*factor\s+authentication", "4 Identity & access (IAM / PAM)"),
    (r"zero\s+trust(?:\s+network\s+access)?", "4 Identity & access (IAM / PAM)"),
    (r"\bztna\b", "4 Identity & access (IAM / PAM)"),
    # Data security & encryption
    (r"data\s+(?:loss|leakage)\s+prevention", "5 Data security & encryption"),
    (r"hardware\s+security\s+module", "5 Data security & encryption"),
    # VAPT / audit / compliance
    (r"\bvapt\b", "6 VAPT / audit / compliance"),
    (r"vulnerability\s+assessment", "6 VAPT / audit / compliance"),
    (r"penetration\s+test\w*", "6 VAPT / audit / compliance"),
    (r"cyber\s*security\s+audit", "6 VAPT / audit / compliance"),
    (r"\bcyber\s+audit\b", "6 VAPT / audit / compliance"),
    (r"cert[\s-]*in\b", "6 VAPT / audit / compliance"),
    (r"iso\s*27001", "6 VAPT / audit / compliance"),
    (r"\bisms\b", "6 VAPT / audit / compliance"),
    # General cyber
    (r"cyber\s*security", "6 VAPT / audit / compliance"),
    (r"cyber[\s-]security", "6 VAPT / audit / compliance"),
    (r"information\s+security\s+(?:management|solution|service|audit|policy)", "6 VAPT / audit / compliance"),
]]

# ---------------------------------------------------------------------------
# Layer 3: Weak keywords — ambiguous terms that need corroborating context
# ---------------------------------------------------------------------------

_CYBER_WEAK_KEYWORDS = [
    _WeakKW(
        pattern=re.compile(r"\bfirewall\b|\bfirewalls\b", re.IGNORECASE),
        base_score=0.5,
        boosts=_compile_list([
            r"\bnetwork\b", r"\bcyber\b", r"\bsecurity\b", r"\bappliance\b",
            r"\bperimeter\b", r"\bgateway\b", r"\butm\b", r"\bthroughput\b",
            r"\bpalo\s*alto\b", r"\bfortinet\b", r"\bfortigate\b", r"\bcheck\s*point\b",
            r"\bsophos\b", r"\bcisco\b", r"\bjuniper\b", r"\bsonicwall\b",
        ]),
        rejects=_compile_list([
            r"\bbrick\b", r"\bmasonry\b", r"\brcc\b", r"\bpartition\s+wall\b",
            r"\bplaster\b", r"\bcivil\s+work\b",
        ]),
        group_hint="2 Network security (firewall / WAF)",
    ),
    _WeakKW(
        pattern=re.compile(r"\bsoc\b", re.IGNORECASE),
        base_score=0.3,
        boosts=_compile_list([
            r"\bsecurity\b", r"\bcyber\b", r"\bincident\b", r"\bthreat\b",
            r"\bmonitor\w*\b", r"\bsiem\b", r"\boperations?\s+cent", r"\banalyst\b",
        ]),
        rejects=_compile_list([
            r"\bcommittee\b", r"\bdrainage\b", r"\bhousing\b", r"\bresidential\b",
            r"\bsoccer\b", r"\bsociety\b", r"\bsoil\s+organic\b",
            r"\bstate\s+of\s+charge\b", r"\bsystem[\s-]*on[\s-]*chip\b",
        ]),
        group_hint="1 SOC / SIEM / monitoring",
    ),
    _WeakKW(
        pattern=re.compile(r"\bsoar\b", re.IGNORECASE),
        base_score=0.3,
        boosts=_compile_list([
            r"\bsecurity\b", r"\borchestrat\w*\b", r"\bautomation\b",
            r"\bresponse\b", r"\bplaybook\b", r"\bsiem\b", r"\bincident\b",
        ]),
        rejects=_compile_list([
            r"\bprice\w*\b", r"\bcost\b", r"\binflation\b", r"\btemperature\b",
            r"\bheight\b", r"\beagle\b", r"\bballoon\b",
        ]),
        group_hint="1 SOC / SIEM / monitoring",
    ),
    _WeakKW(
        pattern=re.compile(r"\bsecurity\b", re.IGNORECASE),
        base_score=0.2,
        boosts=_compile_list([
            r"\bcyber\b", r"\bnetwork\b", r"\binformation\b", r"\bdata\b",
            r"\bfirewall\b", r"\bendpoint\b", r"\bthreat\b", r"\bsoc\b",
            r"\bsiem\b", r"\bit\s+security\b", r"\bapplication\s+security\b",
            r"\bweb\s+security\b", r"\bemail\s+security\b",
        ]),
        rejects=_compile_list([
            r"\bguard\b", r"\bdeposit\b", r"\bpersonnel\b", r"\bphysical\b",
            r"\bcctv\b", r"\bsurveillance\b", r"\bfood\b", r"\bsocial\b",
            r"\bfencing\b", r"\bpatrol\w*\b", r"\bman\s*power\b",
        ]),
        group_hint="6 VAPT / audit / compliance",
    ),
    _WeakKW(
        pattern=re.compile(r"\baudit\b", re.IGNORECASE),
        base_score=0.15,
        boosts=_compile_list([
            r"\bsecurity\b", r"\bcyber\b", r"\binformation\s+security\b",
            r"\bvapt\b", r"\biso\s*27001\b", r"\bvulnerability\b",
            r"\bcompliance\b", r"\bisms\b", r"\bnetwork\b",
        ]),
        rejects=_compile_list([
            r"\bfinancial\b", r"\bstatutory\b", r"\benergy\s+audit\b",
            r"\bwater\s+audit\b", r"\bgreen\s+audit\b", r"\bsafety\s+audit\b",
            r"\bfire\s+audit\b", r"\bstock\s+audit\b", r"\baccount\w*\b",
            r"\benvironment\w*\b",
        ]),
        group_hint="6 VAPT / audit / compliance",
    ),
    _WeakKW(
        pattern=re.compile(r"\bendpoint\b", re.IGNORECASE),
        base_score=0.4,
        boosts=_compile_list([
            r"\bsecurity\b", r"\bprotection\b", r"\bedr\b", r"\bantivirus\b",
            r"\bdetection\b", r"\bmalware\b", r"\bdevice\s+control\b",
        ]),
        rejects=_compile_list([
            r"\bapi\s+endpoint\b", r"\brest\s+endpoint\b", r"\burl\s+endpoint\b",
        ]),
        group_hint="3 Endpoint & threat defense",
    ),
    _WeakKW(
        pattern=re.compile(r"\bmonitoring\b", re.IGNORECASE),
        base_score=0.2,
        boosts=_compile_list([
            r"\bsecurity\b", r"\bthreat\b", r"\bnetwork\b", r"\bsoc\b",
            r"\bsiem\b", r"\blog\b", r"\bevent\b", r"\bcyber\b", r"\bintrusion\b",
        ]),
        rejects=_compile_list([
            r"\benvironment\w*\b", r"\bhealth\b", r"\bpatient\b", r"\bwater\b",
            r"\bair\s+quality\b", r"\bpollution\b", r"\bweather\b",
            r"\bstructural\b", r"\bvital\s+sign\b", r"\bcctv\b",
        ]),
        group_hint="1 SOC / SIEM / monitoring",
    ),
    _WeakKW(
        pattern=re.compile(r"\bvpn\b", re.IGNORECASE),
        base_score=0.5,
        boosts=_compile_list([
            r"\bgateway\b", r"\bsite[\s-]*to[\s-]*site\b", r"\bssl\b",
            r"\bipsec\b", r"\btunnel\b", r"\bfirewall\b", r"\bremote\s+access\b",
        ]),
        rejects=[],
        group_hint="2 Network security (firewall / WAF)",
    ),
    _WeakKW(
        pattern=re.compile(r"\bencryption\b", re.IGNORECASE),
        base_score=0.4,
        boosts=_compile_list([
            r"\bdata\b", r"\baes\b", r"\bdisk\b", r"\bfile\b", r"\bsecurity\b",
            r"\bkey\s+management\b", r"\bend[\s-]*to[\s-]*end\b", r"\bcrypto\w*\b",
        ]),
        rejects=[],
        group_hint="5 Data security & encryption",
    ),
    _WeakKW(
        pattern=re.compile(r"\bips\b|\bids\b", re.IGNORECASE),
        base_score=0.3,
        boosts=_compile_list([
            r"\bintrusion\b", r"\bprevention\b", r"\bdetection\b", r"\bnetwork\b",
            r"\bsignature\b", r"\bfirewall\b", r"\bsecurity\b",
        ]),
        rejects=_compile_list([
            r"\binches\s+per\s+second\b", r"\bdisplay\b", r"\bpanel\b",
            r"\bips\s+lcd\b", r"\bmonitor\s+ips\b",
        ]),
        group_hint="2 Network security (firewall / WAF)",
    ),
    _WeakKW(
        pattern=re.compile(r"\bpam\b", re.IGNORECASE),
        base_score=0.35,
        boosts=_compile_list([
            r"\bprivileged\b", r"\baccess\b", r"\bidentity\b", r"\bcredential\b",
            r"\bvault\b", r"\bcyberark\b", r"\bbeyondtrust\b", r"\bsession\b",
        ]),
        rejects=[],
        group_hint="4 Identity & access (IAM / PAM)",
    ),
    _WeakKW(
        pattern=re.compile(r"\biam\b", re.IGNORECASE),
        base_score=0.35,
        boosts=_compile_list([
            r"\bidentity\b", r"\baccess\s+management\b", r"\bprovisioning\b",
            r"\bsso\b", r"\bauthentication\b", r"\bdirectory\b",
        ]),
        rejects=[],
        group_hint="4 Identity & access (IAM / PAM)",
    ),
    _WeakKW(
        pattern=re.compile(r"\butm\b", re.IGNORECASE),
        base_score=0.35,
        boosts=_compile_list([
            r"\bfirewall\b", r"\bthreat\b", r"\bgateway\b", r"\bsecurity\b",
            r"\bunified\b", r"\bappliance\b",
        ]),
        rejects=_compile_list([
            r"\bcoordinate\b", r"\bzone\s+\d", r"\beasting\b", r"\bnorthing\b",
            r"\bprojection\b", r"\bgrid\s+reference\b",
        ]),
        group_hint="2 Network security (firewall / WAF)",
    ),
    _WeakKW(
        pattern=re.compile(r"\bdlp\b", re.IGNORECASE),
        base_score=0.35,
        boosts=_compile_list([
            r"\bdata\s+loss\b", r"\bleakage\b", r"\bprevention\b", r"\bsecurity\b",
            r"\bendpoint\b", r"\bemail\b", r"\bexfiltrat\w*\b",
        ]),
        rejects=_compile_list([
            r"\bprojector\b", r"\bprojection\b", r"\blumens?\b", r"\blamp\b",
            r"\bdisplay\b", r"\blight\s+process\w*\b",
        ]),
        group_hint="5 Data security & encryption",
    ),
    _WeakKW(
        pattern=re.compile(r"\bhsm\b", re.IGNORECASE),
        base_score=0.4,
        boosts=_compile_list([
            r"\bhardware\s+security\b", r"\bkey\b", r"\bencryption\b",
            r"\bcrypto\w*\b", r"\bpki\b", r"\bsign\w*\b",
        ]),
        rejects=[],
        group_hint="5 Data security & encryption",
    ),
    _WeakKW(
        pattern=re.compile(r"access\s+control", re.IGNORECASE),
        base_score=0.2,
        boosts=_compile_list([
            r"\bidentity\b", r"\biam\b", r"\bpam\b", r"\blogical\b",
            r"\bprivileged\b", r"\brole[\s-]*based\b", r"\brbac\b", r"\bnetwork\b",
        ]),
        rejects=_compile_list([
            r"\bdoor\b", r"\bboom\s+barrier\b", r"\bturnstile\b", r"\bgate\b",
            r"\bbiometric\s+attendance\b", r"\bphysical\b", r"\bflap\s+barrier\b",
            r"\bparking\b", r"\bentry\s+exit\b",
        ]),
        group_hint="4 Identity & access (IAM / PAM)",
    ),
    _WeakKW(
        pattern=re.compile(r"\bnac\b", re.IGNORECASE),
        base_score=0.35,
        boosts=_compile_list([
            r"\bnetwork\s+access\s+control\b", r"\b802\.1x?\b", r"\bposture\b",
            r"\bendpoint\b", r"\bsecurity\b",
        ]),
        rejects=[],
        group_hint="2 Network security (firewall / WAF)",
    ),
    _WeakKW(
        pattern=re.compile(r"\bthreat\b", re.IGNORECASE),
        base_score=0.2,
        boosts=_compile_list([
            r"\bcyber\b", r"\bsecurity\b", r"\bintelligence\b", r"\bdetection\b",
            r"\badvanced\s+persistent\b", r"\bmalware\b", r"\bactor\b", r"\bhunting\b",
        ]),
        rejects=_compile_list([
            r"\bbomb\b", r"\bbird\b", r"\bpest\b", r"\blife\s+threat\b",
        ]),
        group_hint="3 Endpoint & threat defense",
    ),
]

# Buyer organizations that frequently procure cyber-security
_CYBER_BUYER_BOOSTS = [re.compile(p, re.IGNORECASE) for p in [
    r"\bnic\b", r"national\s+informatics",
    r"\bc[\-\s]*dac\b", r"\bc[\-\s]*dot\b", r"\bcert[\-\s]*in\b",
    r"\bdrdo\b", r"\bnciipc\b", r"\bnatgrid\b",
    r"\b(?:police|cyber\s+cell|cyber\s+crime)\b",
    r"ministry\s+of\s+home", r"home\s+(?:affairs|department)",
    r"\b(?:income\s+tax|gst|cbdt|cbic)\b",
    r"\buidai\b", r"\bnpci\b", r"\brbi\b", r"\bsebi\b",
    r"\b(?:pnb|sbi|boi|bank\s+of)\b",
    r"\b(?:iit|nit|iiit)\b",
    r"\bbsnl\b", r"\brailtel\b", r"\bnpcil\b",
    r"(?:ministry|dept).*(?:electron|informat|telecom|defence|finance)",
]]


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def score_cyber_relevance(
    title: str,
    scope: str = "",
    issuing_org: str = "",
) -> RelevanceResult:
    """Score a GeM bid for relevance to cyber-security domains.

    Same three-layer evaluation and thresholds as ``score_nikom_relevance``:
      1. Negative context rejection (fast reject even if cyber keywords present)
      2. Strong pattern matching (unambiguous terms pass with score=1.0)
      3. Context-gated scoring for ambiguous terms (boost/reject context)
    """
    text = f"{title} {scope}".lower().strip()
    signals: List[str] = []
    rejects: List[str] = []

    # Layer 1: Negative context — always reject, no strong-pattern override
    for neg_re in _CYBER_NEGATIVE_CONTEXTS:
        if neg_re.search(text):
            rejects.append(neg_re.pattern)
            return RelevanceResult(
                verdict=RelevanceVerdict.REJECT, score=0.0,
                matched_signals=signals, reject_reasons=rejects,
            )

    # Layer 2: Strong patterns
    for strong_re, group_hint in _CYBER_STRONG_PATTERNS:
        if strong_re.search(text):
            signals.append(strong_re.pattern)
            return RelevanceResult(
                verdict=RelevanceVerdict.PASS, score=1.0,
                matched_signals=signals, group_hint=group_hint,
            )

    # Layer 3: Context-gated scoring
    best_score = 0.0
    best_hint = None

    for wk in _CYBER_WEAK_KEYWORDS:
        if not wk.pattern.search(text):
            continue

        score = wk.base_score
        signals.append(wk.pattern.pattern)

        rejected = False
        for rej_re in wk.rejects:
            if rej_re.search(text):
                score -= 0.3
                rejects.append(rej_re.pattern)
                if score <= 0.0:
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
        for org_re in _CYBER_BUYER_BOOSTS:
            if org_re.search(org_lower):
                best_score = min(best_score + 0.15, 1.0)
                signals.append(f"buyer:{org_re.pattern}")
                break

    if best_score >= 0.6:
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


# Each group: (group_label, role, keywords_must_match, keywords_exclude)
# Order matters — first match wins, so more specific groups come first.
CYBER_GROUP_RULES = [
    # Group 6: VAPT / audit / compliance — specific services, check early
    {
        "label": "6 VAPT / audit / compliance",
        "role": "Services partner",
        "match_any": [
            r"\bvapt\b", r"vulnerability\s+assessment", r"penetration\s+test\w*",
            r"cyber\s*security\s+audit", r"\bcyber\s+audit\b",
            r"information\s+security\s+audit", r"\biso\s*27001\b",
            r"cert[\s-]*in\b", r"\bisms\b", r"security\s+posture\s+assessment",
        ],
        "exclude": [],
    },
    # Group 1: SOC / SIEM / monitoring
    {
        "label": "1 SOC / SIEM / monitoring",
        "role": "Direct bidder",
        "match_any": [
            r"\bsiem\b", r"security\s+information\s+and\s+event",
            r"security\s+operations?\s+cent", r"\bsoc\b",
            r"\bsoar\b", r"managed\s+detection", r"\bmdr\b",
            r"security\s+monitoring", r"incident\s+response",
            r"log\s+(?:management|correlation|monitor)",
        ],
        "exclude": [],
    },
    # Group 4: Identity & access
    {
        "label": "4 Identity & access (IAM / PAM)",
        "role": "Reseller / OEM partner",
        "match_any": [
            r"identity\s+and\s+access\s+management", r"\biam\b",
            r"privileged\s+access\s+management", r"\bpam\b",
            r"multi[\s-]*factor\s+authentication", r"\bmfa\b",
            r"single\s+sign[\s-]*on", r"\bsso\b",
            r"zero\s+trust", r"\bztna\b", r"identity\s+management",
        ],
        "exclude": [],
    },
    # Group 3: Endpoint & threat defense
    {
        "label": "3 Endpoint & threat defense",
        "role": "Reseller / OEM partner",
        "match_any": [
            r"endpoint\s+detection", r"\bedr\b", r"\bxdr\b",
            r"endpoint\s+(?:security|protection)", r"anti[\s-]*virus",
            r"anti[\s-]*malware", r"anti[\s-]*ransomware",
            r"threat\s+intelligence", r"zero[\s-]*day",
            r"vulnerability\s+management", r"patch\s+management",
        ],
        "exclude": [],
    },
    # Group 2: Network security
    {
        "label": "2 Network security (firewall / WAF)",
        "role": "Reseller / OEM partner",
        "match_any": [
            r"next[\s-]*gen(?:eration)?\s+firewall", r"\bngfw\b",
            r"web\s+application\s+firewall", r"\bwaf\b",
            r"\bfirewall\b", r"unified\s+threat\s+management", r"\butm\b",
            r"d?dos\s+(?:protection|mitigation)", r"anti[\s-]*ddos",
            r"intrusion\s+(?:prevention|detection)", r"\bips\b", r"\bids\b",
            r"secure\s+web\s+gateway", r"\bvpn\b", r"network\s+access\s+control",
            r"\bnac\b",
        ],
        "exclude": [],
    },
    # Group 5: Data security & encryption
    {
        "label": "5 Data security & encryption",
        "role": "Reseller / OEM partner",
        "match_any": [
            r"data\s+(?:loss|leakage)\s+prevention", r"\bdlp\b",
            r"encryption", r"hardware\s+security\s+module", r"\bhsm\b",
            r"\bpki\b", r"digital\s+signature\s+certificate",
        ],
        "exclude": [],
    },
    # Group 7: Managed security services / AMC (catch-all for service contracts)
    {
        "label": "7 Managed security services",
        "role": "Services partner",
        "match_any": [
            r"managed\s+security\s+service", r"\bmssp\b",
            r"security\s+as\s+a\s+service", r"soc\s+as\s+a\s+service",
            r"(?:amc|camc|cmc|comprehensive\s+(?:annual\s+)?maintenance).*(?:firewall|security|siem|endpoint|cyber)",
            r"(?:firewall|security|siem|endpoint|cyber).*(?:amc|camc|cmc)",
            r"cyber\s*security", r"information\s+security",
        ],
        "exclude": [],
    },
]


def classify_cyber_bid(title: str, scope: str = "") -> Tuple[str, str]:
    """
    Classify a GeM bid into one of the cyber-security groups.

    Returns (group_label, role). Falls back to ("0 Unclassified",
    "Review needed") when no group rule matches.
    """
    text = f"{title} {scope}".lower().strip()

    for rule in CYBER_GROUP_RULES:
        excluded = False
        for exc_pattern in rule["exclude"]:
            if re.search(exc_pattern, text, re.IGNORECASE):
                excluded = True
                break
        if excluded:
            continue

        for pattern in rule["match_any"]:
            if re.search(pattern, text, re.IGNORECASE):
                return rule["label"], rule["role"]

    return "0 Unclassified", "Review needed"


def is_cyber_relevant(title: str, scope: str = "", issuing_org: str = "") -> bool:
    """Return True for PASS or BORDERLINE verdicts (REJECT dropped)."""
    result = score_cyber_relevance(title, scope, issuing_org)
    return result.verdict != RelevanceVerdict.REJECT
