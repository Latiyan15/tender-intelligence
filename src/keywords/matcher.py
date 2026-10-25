"""
Keyword Matching Engine for Tender Discovery
=============================================
Loads keyword configuration from YAML and performs tiered, contextual matching
against tender text. Supports word boundaries, phrase matching, negative filtering,
and configurable inclusion rules.

This engine determines *discovery category*, NOT suitability or fit scoring.
"""

import re
import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class KeywordMatch:
    """A single keyword match with evidence."""
    term: str
    tier: str                    # "A", "B", "C", "D"
    group: str                   # e.g. "power", "cooling", "facility_types"
    matched_text: str            # the exact text that matched
    snippet: str                 # surrounding context (up to 200 chars)
    position: int                # character offset in the source text
    source_field: str = ""       # which field the match came from (title, description, etc.)
    is_contextual: bool = False  # required context check to pass

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "tier": self.tier,
            "group": self.group,
            "matched_text": self.matched_text,
            "snippet": self.snippet,
            "position": self.position,
            "source_field": self.source_field,
            "is_contextual": self.is_contextual,
        }


@dataclass
class MatchResult:
    """Complete result of keyword matching for a tender."""
    tender_id: str
    qualified: bool = False
    primary_category: str = ""        # "direct" or "indirect_review"
    highest_tier: str = ""            # "A", "B", "C", "D", or ""
    matches: List[KeywordMatch] = field(default_factory=list)
    negative_hits: List[Dict[str, str]] = field(default_factory=list)
    disqualified_by_negative: bool = False
    uncertain: bool = False           # flagged for manual review
    tier_a_count: int = 0
    tier_b_count: int = 0
    tier_b_distinct_groups: int = 0
    tier_c_count: int = 0
    tier_c_has_dc_context: bool = False
    tier_d_count: int = 0
    inclusion_rule_applied: str = ""  # which rule caused qualification

    def to_dict(self) -> dict:
        return {
            "tender_id": self.tender_id,
            "qualified": self.qualified,
            "primary_category": self.primary_category,
            "highest_tier": self.highest_tier,
            "inclusion_rule_applied": self.inclusion_rule_applied,
            "tier_a_count": self.tier_a_count,
            "tier_b_count": self.tier_b_count,
            "tier_b_distinct_groups": self.tier_b_distinct_groups,
            "tier_c_count": self.tier_c_count,
            "tier_c_has_dc_context": self.tier_c_has_dc_context,
            "tier_d_count": self.tier_d_count,
            "disqualified_by_negative": self.disqualified_by_negative,
            "uncertain": self.uncertain,
            "matches": [m.to_dict() for m in self.matches],
            "negative_hits": self.negative_hits,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Keyword Matcher
# ──────────────────────────────────────────────────────────────────────────────

class KeywordMatcher:
    """
    Loads keyword rules from a YAML config and matches tender text
    against tiered keyword groups with contextual validation and
    negative filtering.
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config", "keywords.yaml"
            )
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._compiled_patterns: Dict[str, List[Tuple[re.Pattern, str, str]]] = {}
        self._negative_patterns: List[Tuple[re.Pattern, str]] = []
        self._soft_negative_patterns: List[Dict[str, Any]] = []
        self._contextual_rules: Dict[str, List[Dict[str, Any]]] = {}
        self._inclusion_rules: Dict[str, Any] = {}

        self._load_config()
        self._compile_patterns()

    def _load_config(self):
        """Load keyword configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded keyword config from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Keyword config not found: {self.config_path}")
            self.config = {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse keyword config: {e}")
            self.config = {}

    def _escape_for_regex(self, term: str) -> str:
        """Escape a keyword term for use in regex, preserving word boundaries."""
        escaped = re.escape(term)
        # Allow flexible whitespace matching
        escaped = escaped.replace(r"\ ", r"\s+")
        escaped = escaped.replace(r"\-", r"[-\s]?")
        return escaped

    def _build_word_boundary_pattern(self, term: str) -> re.Pattern:
        """Build a regex pattern with word boundaries for a keyword term."""
        escaped = self._escape_for_regex(term)
        # Use word boundaries for most terms
        pattern_str = r'(?<![a-zA-Z0-9])' + escaped + r'(?![a-zA-Z0-9])'
        return re.compile(pattern_str, re.IGNORECASE)

    def _compile_patterns(self):
        """Pre-compile regex patterns for all keyword tiers."""
        for tier_key in ["tier_a", "tier_b", "tier_c", "tier_d"]:
            tier_config = self.config.get(tier_key, {})
            tier_letter = tier_key[-1].upper()
            patterns = []

            groups = tier_config.get("groups", {})
            for group_name, terms in groups.items():
                if isinstance(terms, list):
                    for term in terms:
                        pat = self._build_word_boundary_pattern(term)
                        patterns.append((pat, term, group_name))

            self._compiled_patterns[tier_letter] = patterns

            # Compile contextual rules
            ctx_rules = tier_config.get("contextual_terms", [])
            if ctx_rules:
                self._contextual_rules[tier_letter] = ctx_rules

        # Compile negative patterns
        negatives = self.config.get("negatives", {})
        hard_rejects = negatives.get("hard_reject_terms", {})
        for category, terms in hard_rejects.items():
            if isinstance(terms, list):
                for term in terms:
                    pat = self._build_word_boundary_pattern(term)
                    self._negative_patterns.append((pat, term))

        # Compile soft negatives
        soft_rejects = negatives.get("soft_reject_terms", {})
        for category, rule_config in soft_rejects.items():
            if isinstance(rule_config, dict):
                terms = rule_config.get("terms", [])
                patterns_raw = rule_config.get("patterns", [])
                overrides = rule_config.get("override_if_also_contains", [])

                compiled_terms = [(self._build_word_boundary_pattern(t), t) for t in terms]
                compiled_patterns = []
                for p in patterns_raw:
                    try:
                        compiled_patterns.append((re.compile(p, re.IGNORECASE), p))
                    except re.error:
                        logger.warning(f"Invalid regex in soft negative: {p}")

                self._soft_negative_patterns.append({
                    "category": category,
                    "description": rule_config.get("description", ""),
                    "term_patterns": compiled_terms,
                    "regex_patterns": compiled_patterns,
                    "override_terms": overrides,
                })

        # Load inclusion rules
        self._inclusion_rules = self.config.get("inclusion_rules", {
            "tier_a_min_matches": 1,
            "tier_b_min_matches": 2,
            "tier_c_requires_dc_context": True,
            "tier_d_separate_category": True,
        })

    def _get_snippet(self, text: str, position: int, length: int = 200) -> str:
        """Extract a context snippet around a match position."""
        start = max(0, position - length // 2)
        end = min(len(text), position + length // 2)
        snippet = text[start:end].strip()
        snippet = re.sub(r'\s+', ' ', snippet)
        return snippet

    def _check_contextual_term(self, term_rule: Dict[str, Any],
                                text: str, tier: str) -> Optional[KeywordMatch]:
        """
        Check a contextual term: the term must appear AND required context
        must be present AND rejected context must be absent.
        """
        term = term_rule.get("term", "")
        require_ctx = term_rule.get("require_context", [])
        reject_ctx = term_rule.get("reject_context", [])

        term_pattern = self._build_word_boundary_pattern(term)
        match = term_pattern.search(text)
        if not match:
            return None

        text_lower = text.lower()

        # Check reject context first
        for reject_term in reject_ctx:
            reject_pat = self._build_word_boundary_pattern(reject_term)
            if reject_pat.search(text):
                logger.debug(f"Contextual term '{term}' rejected by context '{reject_term}'")
                return None

        # Check required context
        if require_ctx:
            has_context = False
            for ctx_term in require_ctx:
                ctx_pat = self._build_word_boundary_pattern(ctx_term)
                if ctx_pat.search(text):
                    has_context = True
                    break
            if not has_context:
                logger.debug(f"Contextual term '{term}' missing required context")
                return None

        group = term_rule.get("group", "contextual")
        snippet = self._get_snippet(text, match.start())
        return KeywordMatch(
            term=term,
            tier=tier,
            group=group,
            matched_text=match.group(),
            snippet=snippet,
            position=match.start(),
            is_contextual=True,
        )

    def _check_dc_context(self, text: str) -> bool:
        """Check if the text has data-centre context for Tier C qualification."""
        tier_c_config = self.config.get("tier_c", {})
        dc_context_terms = tier_c_config.get("dc_context_terms", [
            "data centre", "data center", "server room", "DC",
            "IT infrastructure", "UPS", "precision air", "PAC"
        ])
        for ctx_term in dc_context_terms:
            pat = self._build_word_boundary_pattern(ctx_term)
            if pat.search(text):
                return True
        return False

    def match_text(self, text: str, tender_id: str = "",
                   source_field: str = "combined") -> MatchResult:
        """
        Run the full keyword matching pipeline against the given text.

        Steps:
        1. Find all tier matches (A, B, C, D)
        2. Apply contextual term checks
        3. Check negative keywords
        4. Apply inclusion rules
        5. Determine qualification and category
        """
        result = MatchResult(tender_id=tender_id)

        if not text or not text.strip():
            return result

        # ── Step 1 & 2: Find all tier matches ──────────────────────────
        all_matches: List[KeywordMatch] = []
        tier_b_groups_hit: Set[str] = set()

        for tier_letter, patterns in self._compiled_patterns.items():
            for pat, term, group in patterns:
                for m in pat.finditer(text):
                    snippet = self._get_snippet(text, m.start())
                    km = KeywordMatch(
                        term=term,
                        tier=tier_letter,
                        group=group,
                        matched_text=m.group(),
                        snippet=snippet,
                        position=m.start(),
                        source_field=source_field,
                    )
                    all_matches.append(km)

                    if tier_letter == "B":
                        tier_b_groups_hit.add(group)

        # Check contextual terms
        for tier_letter, ctx_rules in self._contextual_rules.items():
            for rule in ctx_rules:
                ctx_match = self._check_contextual_term(rule, text, tier_letter)
                if ctx_match:
                    ctx_match.source_field = source_field
                    all_matches.append(ctx_match)

        # Deduplicate and filter out subsumed matches
        # Sort by match length descending so longer phrases take priority over substrings (e.g. 'online UPS' over 'UPS')
        sorted_matches = sorted(all_matches, key=lambda m: len(m.matched_text), reverse=True)
        filtered_matches = []
        occupied_spans = []
        for m in sorted_matches:
            m_start = m.position
            m_end = m.position + len(m.matched_text)
            is_subsumed = any(span_start <= m_start and m_end <= span_end for span_start, span_end in occupied_spans)
            if not is_subsumed:
                occupied_spans.append((m_start, m_end))
                filtered_matches.append(m)
        all_matches = sorted(filtered_matches, key=lambda m: m.position)

        tier_b_groups_hit = set(m.group for m in all_matches if m.tier == "B")

        # ── Step 3: Check negative keywords ────────────────────────────
        negative_hits = []

        # Hard negatives
        for neg_pat, neg_term in self._negative_patterns:
            if neg_pat.search(text):
                negative_hits.append({
                    "term": neg_term,
                    "type": "hard_reject",
                })

        # Soft negatives
        for soft_rule in self._soft_negative_patterns:
            triggered = False
            matched_term = ""

            for sp, st in soft_rule["term_patterns"]:
                if sp.search(text):
                    triggered = True
                    matched_term = st
                    break

            if not triggered:
                for rp, rs in soft_rule["regex_patterns"]:
                    if rp.search(text):
                        triggered = True
                        matched_term = rs
                        break

            if triggered:
                # Check overrides
                overridden = False
                for override_term in soft_rule.get("override_terms", []):
                    override_pat = self._build_word_boundary_pattern(override_term)
                    if override_pat.search(text):
                        overridden = True
                        break

                if not overridden:
                    negative_hits.append({
                        "term": matched_term,
                        "type": "soft_reject",
                        "category": soft_rule["category"],
                        "description": soft_rule["description"],
                    })

        result.negative_hits = negative_hits
        result.matches = all_matches

        # ── Step 4: Count tier matches ─────────────────────────────────
        result.tier_a_count = sum(1 for m in all_matches if m.tier == "A")
        result.tier_b_count = sum(1 for m in all_matches if m.tier == "B")
        result.tier_b_distinct_groups = len(tier_b_groups_hit)
        result.tier_c_count = sum(1 for m in all_matches if m.tier == "C")
        result.tier_d_count = sum(1 for m in all_matches if m.tier == "D")

        # Check DC context for Tier C
        if result.tier_c_count > 0:
            result.tier_c_has_dc_context = self._check_dc_context(text)

        # ── Step 5: Check if hard-negatives disqualify ─────────────────
        hard_negatives = [n for n in negative_hits if n["type"] == "hard_reject"]
        has_positive_matches = (result.tier_a_count > 0 or result.tier_b_count > 0
                                or result.tier_c_count > 0 or result.tier_d_count > 0)

        if hard_negatives and not has_positive_matches:
            result.disqualified_by_negative = True
            return result

        # Soft negatives: flag as uncertain if no strong positive match
        soft_negatives = [n for n in negative_hits if n["type"] == "soft_reject"]
        if soft_negatives and not has_positive_matches:
            result.uncertain = True

        # ── Step 6: Apply inclusion rules ──────────────────────────────
        min_a = self._inclusion_rules.get("tier_a_min_matches", 1)
        min_b = self._inclusion_rules.get("tier_b_min_matches", 1)
        min_c = self._inclusion_rules.get("tier_c_min_matches", 1)
        min_d = self._inclusion_rules.get("tier_d_min_matches", 1)
        c_requires_dc = self._inclusion_rules.get("tier_c_requires_dc_context", False)
        d_separate = self._inclusion_rules.get("tier_d_separate_category", False)

        # Rule 1: Tier A (Cyber Security) qualifies for direct match
        if result.tier_a_count >= min_a:
            result.qualified = True
            result.primary_category = "direct"
            result.highest_tier = "A"
            result.inclusion_rule_applied = f"Tier A (Cyber Security): {result.tier_a_count} match(es)"

        # Rule 2: Tier B (IT Infrastructure) qualifies for direct match
        elif result.tier_b_count >= min_b or result.tier_b_distinct_groups >= min_b:
            result.qualified = True
            result.primary_category = "direct"
            result.highest_tier = "B"
            result.inclusion_rule_applied = (
                f"Tier B (IT Infrastructure): {result.tier_b_count} match(es)"
            )

        # Rule 3: Tier C (Cloud) qualifies for direct match
        elif result.tier_c_count >= min_c and (
            result.tier_c_has_dc_context or not c_requires_dc
        ):
            result.qualified = True
            result.primary_category = "direct"
            result.highest_tier = "C"
            result.inclusion_rule_applied = (
                f"Tier C (Cloud): {result.tier_c_count} match(es)"
            )

        # Rule 4: Tier D (Non-IT Infrastructure & Services) qualifies
        elif result.tier_d_count >= min_d:
            result.qualified = True
            result.primary_category = "indirect_review" if d_separate else "direct"
            result.highest_tier = "D"
            result.inclusion_rule_applied = (
                f"Tier D (Non-IT Infra & Services): {result.tier_d_count} match(es)"
            )

        return result

    def match_fields(self, fields: Dict[str, str],
                     tender_id: str = "") -> MatchResult:
        """
        Match against multiple text fields (title, description, scope, etc.)
        and merge results. Each field's matches are tagged with source_field.
        """
        # Combine all fields for overall matching
        combined = " ".join(v for v in fields.values() if v)
        result = self.match_text(combined, tender_id=tender_id, source_field="combined")

        # Also tag individual field matches
        for field_name, field_text in fields.items():
            if not field_text:
                continue
            field_result = self.match_text(field_text, tender_id=tender_id,
                                           source_field=field_name)
            # Update source_field for matches found in this specific field
            for match in field_result.matches:
                # Find the corresponding match in combined results
                for combined_match in result.matches:
                    if (combined_match.term == match.term and
                        combined_match.source_field == "combined"):
                        combined_match.source_field = field_name
                        break

        return result

    def get_config_summary(self) -> Dict[str, Any]:
        """Return a summary of the loaded keyword configuration."""
        summary = {}
        for tier_key in ["tier_a", "tier_b", "tier_c", "tier_d"]:
            tier_config = self.config.get(tier_key, {})
            tier_letter = tier_key[-1].upper()
            groups = tier_config.get("groups", {})
            total_terms = sum(len(terms) for terms in groups.values() if isinstance(terms, list))
            ctx_terms = len(tier_config.get("contextual_terms", []))
            summary[f"tier_{tier_letter}"] = {
                "label": tier_config.get("label", ""),
                "groups": list(groups.keys()),
                "total_terms": total_terms,
                "contextual_terms": ctx_terms,
            }

        negatives = self.config.get("negatives", {})
        hard = negatives.get("hard_reject_terms", {})
        total_hard = sum(len(t) for t in hard.values() if isinstance(t, list))
        soft = negatives.get("soft_reject_terms", {})

        summary["negatives"] = {
            "hard_reject_terms": total_hard,
            "soft_reject_categories": list(soft.keys()),
        }
        summary["inclusion_rules"] = self._inclusion_rules
        return summary
