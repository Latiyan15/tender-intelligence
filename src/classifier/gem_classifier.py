"""
Classifies GeM bids into Nikom's 8 business groups and assigns roles.
"""

import re
from typing import Tuple


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

    return "1 Best fit – cooling & power", "Direct bidder"


def is_nikom_relevant(title: str, scope: str = "") -> bool:
    """Check if a GeM bid falls within Nikom's business domains at all."""
    text = f"{title} {scope}".lower()
    relevance_patterns = [
        r"ups\b", r"precision\s+a", r"chiller", r"hvac",
        r"cooling", r"dg\s+set", r"diesel\s+gen", r"genset",
        r"data\s+cent", r"server\s+room", r"smart\s+rack",
        r"structured\s+cabl", r"fire\s+detect", r"fire\s+alarm",
        r"fire\s+suppress", r"fire\s+hydrant", r"hpc\b",
        r"gpu\s+cluster", r"vrf\b", r"vrv\b", r"ductable",
        r"air\s*condition", r"ahu\b", r"busduct", r"transformer",
        r"lt\s+panel", r"generator", r"cleanroom",
        r"network\s+rack", r"server\s+rack",
        r"bms\b", r"building\s+management",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in relevance_patterns)
