"""
Tests for the Keyword Matching Engine
Tests the 4-tier domain matching rules (Tier A: Cyber Security, Tier B: IT Infrastructure,
Tier C: Cloud, Tier D: Non-IT Infrastructure & Services), contextual checks,
negative filters, and inclusion logic.
"""

import pytest
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.keywords.matcher import KeywordMatcher, MatchResult


@pytest.fixture
def matcher():
    """Create a KeywordMatcher instance using the project's keywords.yaml."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "keywords.yaml"
    )
    return KeywordMatcher(config_path=config_path)


# ──────────────────────────────────────────────────────────────────────────
# TIER A — Cyber Security Tenders
# ──────────────────────────────────────────────────────────────────────────

class TestTierA:
    """A single meaningful Tier A (Cyber Security) match should qualify the tender."""

    def test_firewall_and_soc_tender(self, matcher):
        """A relevant Tier A cyber security tender should qualify as direct."""
        text = (
            "Supply, installation and configuration of Next-Generation Firewall (NGFW), "
            "Unified Threat Management (UTM), and 24x7 Security Operations Centre (SOC) "
            "with SIEM monitoring for National Informatics Centre"
        )
        result = matcher.match_text(text, tender_id="TEST_CYBER_SOC")
        assert result.qualified is True
        assert result.primary_category == "direct"
        assert result.highest_tier == "A"
        assert result.tier_a_count >= 1

    def test_vapt_and_cert_in_compliance(self, matcher):
        text = "Vulnerability Assessment and Penetration Testing (VAPT) and CERT-In compliance audit for State Data portal"
        result = matcher.match_text(text, tender_id="TEST_VAPT")
        assert result.qualified is True
        assert result.highest_tier == "A"

    def test_edr_and_endpoint_security(self, matcher):
        text = "Deployment of Endpoint Detection and Response (EDR) and anti-ransomware protection across 5000 endpoints"
        result = matcher.match_text(text, tender_id="TEST_EDR")
        assert result.qualified is True
        assert result.highest_tier == "A"

    def test_zero_trust_and_iam(self, matcher):
        text = "Implementation of Zero Trust Network Access and Identity and Access Management (IAM) for e-governance"
        result = matcher.match_text(text, tender_id="TEST_ZTNA")
        assert result.qualified is True
        assert result.highest_tier == "A"

    def test_dlp_and_encryption(self, matcher):
        text = "Data Loss Prevention (DLP) solution and Hardware Security Module (HSM) encryption for RBI payments gateway"
        result = matcher.match_text(text, tender_id="TEST_DLP")
        assert result.qualified is True
        assert result.highest_tier == "A"


# ──────────────────────────────────────────────────────────────────────────
# TIER B — IT Infrastructure (Compute, Storage, Networking, Cabling)
# ──────────────────────────────────────────────────────────────────────────

class TestTierB:
    """Tier B (IT Infrastructure) matches qualify as direct match."""

    def test_servers_and_san_storage(self, matcher):
        """A tender with servers and enterprise storage should qualify under Tier B."""
        text = (
            "Supply, installation and commissioning of 2U Rack Servers, "
            "SAN storage area network, and optical transceiver modules for BSNL"
        )
        result = matcher.match_text(text, tender_id="TEST_SERVERS_SAN")
        assert result.qualified is True
        assert result.primary_category == "direct"
        assert result.highest_tier == "B"
        assert result.tier_b_count >= 1

    def test_core_switches_and_routers(self, matcher):
        text = "Supply and configuration of 48-port Core Switch, managed switch and SD-WAN core router for campus network"
        result = matcher.match_text(text, tender_id="TEST_NETWORKING")
        assert result.qualified is True
        assert result.highest_tier == "B"

    def test_structured_cabling_and_racks(self, matcher):
        text = "Execution of structured cabling with Cat6A OFC cable and 42U server racks for Secretariat complex"
        result = matcher.match_text(text, tender_id="TEST_CABLING")
        assert result.qualified is True
        assert result.highest_tier == "B"

    def test_blade_servers_and_hpc(self, matcher):
        text = "Supply and commissioning of Blade Servers and compute nodes for High Performance Computing cluster"
        result = matcher.match_text(text, tender_id="TEST_BLADE")
        assert result.qualified is True
        assert result.highest_tier == "B"


# ──────────────────────────────────────────────────────────────────────────
# TIER C — Cloud (Platforms, Virtualization, Containers, Migration)
# ──────────────────────────────────────────────────────────────────────────

class TestTierC:
    """Tier C (Cloud) matches qualify as direct match."""

    def test_cloud_hosting_and_migration(self, matcher):
        """A cloud hosting and migration tender should qualify as Tier C."""
        text = (
            "Empanelment of Cloud Service Provider for MeitY empanelled Cloud Hosting, "
            "Cloud Migration, and Disaster Recovery as a Service (DRaaS) for State Government"
        )
        result = matcher.match_text(text, tender_id="TEST_CLOUD_HOSTING")
        assert result.qualified is True
        assert result.highest_tier == "C"
        assert result.tier_c_count >= 1

    def test_vmware_and_nutanix_hci(self, matcher):
        text = "Turnkey deployment of Nutanix hyperconverged infrastructure (HCI) and VMware vSphere virtualization"
        result = matcher.match_text(text, tender_id="TEST_HCI")
        assert result.qualified is True
        assert result.highest_tier == "C"

    def test_kubernetes_containerization(self, matcher):
        text = "Setting up Kubernetes container platform and cloud native microservices architecture for municipal services"
        result = matcher.match_text(text, tender_id="TEST_K8S")
        assert result.qualified is True
        assert result.highest_tier == "C"

    def test_private_cloud_and_iaas(self, matcher):
        text = "Supply, installation and operations of Private Cloud with IaaS and PaaS management portal"
        result = matcher.match_text(text, tender_id="TEST_IAAS")
        assert result.qualified is True
        assert result.highest_tier == "C"


# ──────────────────────────────────────────────────────────────────────────
# TIER D — Non-IT Infrastructure & Services (Power, Cooling, Safety, AMC, FMS)
# ──────────────────────────────────────────────────────────────────────────

class TestTierD:
    """Tier D signals qualify for infrastructure and services."""

    def test_modular_ups_and_cooling(self, matcher):
        """A tender with modular UPS and precision air conditioning."""
        text = (
            "Design, supply, installation and commissioning of 2x300 kVA Modular Online UPS, "
            "Precision Air Conditioning (PAC) units, and FM-200 gas suppression system"
        )
        result = matcher.match_text(text, tender_id="TEST_UPS_PAC")
        assert result.qualified is True
        assert result.highest_tier == "D"
        assert result.tier_d_count >= 1

    def test_camc_and_fms_maintenance(self, matcher):
        text = "Comprehensive Annual Maintenance Contract (CAMC) and 24x7 Facility Management Services (FMS) for power and cooling"
        result = matcher.match_text(text, tender_id="TEST_CAMC")
        assert result.qualified is True
        assert result.highest_tier == "D"

    def test_vesda_and_access_control(self, matcher):
        text = "Installation of VESDA aspirating smoke detection and biometric access control system with IP CCTV surveillance"
        result = matcher.match_text(text, tender_id="TEST_SAFETY")
        assert result.qualified is True
        assert result.highest_tier == "D"


# ──────────────────────────────────────────────────────────────────────────
# NEGATIVE KEYWORDS — Noise Filtering
# ──────────────────────────────────────────────────────────────────────────

class TestNegativeKeywords:
    """Negative keywords should filter out irrelevant tenders."""

    def test_district_collector_noise(self, matcher):
        """A district collector notice containing DC should be rejected."""
        text = (
            "Office of the District Collector, Jaipur. Notice for DC office "
            "renovation and painting work. Deputy Commissioner approval pending."
        )
        result = matcher.match_text(text, tender_id="TEST_DC_NOISE")
        if result.qualified:
            assert len(result.negative_hits) > 0

    def test_ups_courier_rejected(self, matcher):
        text = "Contract for UPS courier delivery services across 5 states"
        result = matcher.match_text(text, tender_id="TEST_UPS_COURIER")
        assert len(result.negative_hits) > 0

    def test_data_entry_noise(self, matcher):
        text = "Hiring of data entry operators for census data collection project"
        result = matcher.match_text(text, tender_id="TEST_DATA_ENTRY")
        assert len(result.negative_hits) > 0

    def test_pac_committee_noise(self, matcher):
        text = "Provincial Armed Constabulary headquarters security arrangements"
        result = matcher.match_text(text, tender_id="TEST_PAC_NOISE")
        assert len(result.negative_hits) > 0


# ──────────────────────────────────────────────────────────────────────────
# EDGE CASES & COMBINED SCENARIOS
# ──────────────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_empty_text(self, matcher):
        result = matcher.match_text("", tender_id="TEST_EMPTY")
        assert result.qualified is False
        assert len(result.matches) == 0

    def test_unrelated_civil_tender(self, matcher):
        text = (
            "Construction of 4-lane highway bridge across Ganga river "
            "with approach roads and toll plaza at NH-33"
        )
        result = matcher.match_text(text, tender_id="TEST_CIVIL")
        assert result.qualified is False

    def test_mixed_tiers_prioritizes_tier_a(self, matcher):
        """When multiple tiers match, highest tier is Tier A (Cyber Security)."""
        text = (
            "Next-Generation Firewall with UTM, 42U Server Racks, "
            "Cloud Migration to AWS, and 3-Year Comprehensive Annual Maintenance (CAMC)"
        )
        result = matcher.match_text(text, tender_id="TEST_MIXED")
        assert result.qualified is True
        assert result.tier_a_count >= 1
        assert result.tier_b_count >= 1
        assert result.tier_c_count >= 1
        assert result.tier_d_count >= 1
        assert result.highest_tier == "A"

    def test_case_insensitive_matching(self, matcher):
        text = "SUPPLY OF NEXT GENERATION FIREWALL AND CORE SWITCH"
        result = matcher.match_text(text, tender_id="TEST_CASE")
        assert result.qualified is True

    def test_config_summary(self, matcher):
        """Config summary should report loaded rules for all 4 domains."""
        summary = matcher.get_config_summary()
        assert "tier_A" in summary
        assert "tier_B" in summary
        assert "tier_C" in summary
        assert "tier_D" in summary
        assert summary["tier_A"]["label"] == "Cyber Security"
        assert summary["tier_B"]["label"] == "IT Infrastructure"
        assert summary["tier_C"]["label"] == "Cloud"
        assert summary["tier_D"]["label"] == "Non-IT Infrastructure & Services"


class TestMatchResult:
    """Test MatchResult serialization."""

    def test_to_dict(self, matcher):
        text = "Next-generation firewall with SIEM and online UPS"
        result = matcher.match_text(text, tender_id="TEST_SERIAL")
        d = result.to_dict()
        assert "tender_id" in d
        assert "qualified" in d
        assert "matches" in d
        assert isinstance(d["matches"], list)


# ──────────────────────────────────────────────────────────────────────────
# NIKOM HISTORICAL TENDERS & REAL-WORLD NOISE FILTERING
# ──────────────────────────────────────────────────────────────────────────

class TestNikomHistoricalTenders:
    """Validates real-world historical tenders executed by Nikom InfraSolutions Pvt. Ltd."""

    def test_turnkey_datacenter_cdac(self, matcher):
        text = "Setting UP of Data Centre on Turnkey basis at CDAC Pune"
        res = matcher.match_text(text, tender_id="NIKOM_01")
        assert res.qualified is True
        assert res.disqualified_by_negative is False

    def test_modular_ups_and_camc_iocl(self, matcher):
        text = (
            "Supply, Installation, Testing & Commissioning of 125 KVA on line double conversion "
            "modular UPS system, expandable up to 200 KVA including 02 year warranty along with "
            "03 year Post Warranty Comprehensive Annual Maintenance Contract (PWCAMC) at IOCL"
        )
        res = matcher.match_text(text, tender_id="NIKOM_02")
        assert res.qualified is True
        assert res.disqualified_by_negative is False

    def test_precision_air_conditioners_ntpc(self, matcher):
        text = "Procurement of 03 Precision Air Conditioners (PACs) for ERP Data Center at NTPC"
        res = matcher.match_text(text, tender_id="NIKOM_03")
        assert res.qualified is True
        assert res.disqualified_by_negative is False

    def test_dr_site_non_it_infra_aai(self, matcher):
        text = "Establishment of Non-IT Infrastructure for Disaster Recovery (DR) Site at Hyderabad AAI"
        res = matcher.match_text(text, tender_id="NIKOM_04")
        assert res.qualified is True
        assert res.disqualified_by_negative is False

    def test_natgrid_firewall(self, matcher):
        text = "NATGRID firewall 2 nos with next generation security"
        res = matcher.match_text(text, tender_id="NIKOM_05")
        assert res.qualified is True
        assert res.highest_tier == "A"

    def test_novec_gas_refilling_grse(self, matcher):
        text = "REFILING OF DATA CENTRE NOVEC GAS AT GRSE, CDO"
        res = matcher.match_text(text, tender_id="NIKOM_06")
        assert res.qualified is True

    def test_dcim_and_power_monitoring_iocl(self, matcher):
        text = "Centralized Power Monitoring System and DCIM software at IOCL complex"
        res = matcher.match_text(text, tender_id="NIKOM_07")
        assert res.qualified is True

    def test_rack_containment_nhpc(self, matcher):
        text = "Supply and Installation of integrated racks infrastructure in Server room with cold aisle containment"
        res = matcher.match_text(text, tender_id="NIKOM_08")
        assert res.qualified is True

    # Negative / Noise Rejection Tests

    def test_reject_medical_gas_hospital(self, matcher):
        text = "CAMC of Medical gas pipe line system along with allied accessories installed at Mata Gujri Hospital"
        res = matcher.match_text(text, tender_id="NOISE_01")
        assert res.qualified is False
        assert res.disqualified_by_negative is True

    def test_reject_passenger_lifts(self, matcher):
        text = "Comprehensive Maintenance Contract of 02 nos. Kone make passenger lifts"
        res = matcher.match_text(text, tender_id="NOISE_02")
        assert res.qualified is False
        assert res.disqualified_by_negative is True

    def test_reject_joinery_carpentry(self, matcher):
        text = "COMPREHENSIVE MAINTENANCE OF JOINERY WORK AND OTHER CONNECTED B R WORK AT INS RAJALI"
        res = matcher.match_text(text, tender_id="NOISE_03")
        assert res.qualified is False
        assert res.disqualified_by_negative is True

    def test_reject_lorry_weighbridge(self, matcher):
        text = "SITC of new 60 MT capacity fully electronic Lorry Weighbridge with cabin incl. 3 years CAMC"
        res = matcher.match_text(text, tender_id="NOISE_04")
        assert res.qualified is False
        assert res.disqualified_by_negative is True

    def test_reject_data_entry_operator(self, matcher):
        text = "Facility Management Services - LumpSum Based - Commercial; DATA ENTRY OPERATOR"
        res = matcher.match_text(text, tender_id="NOISE_05")
        assert res.qualified is False
        assert res.disqualified_by_negative is True

    def test_reject_water_cooler_split_ac(self, matcher):
        text = "Operation and Maintenance of Split Air Conditioners, Water Coolers and Reverse Osmosis (RO)"
        res = matcher.match_text(text, tender_id="NOISE_06")
        assert res.qualified is False
        assert res.disqualified_by_negative is True

    def test_reject_river_pumpset_transformer(self, matcher):
        text = "Upgradation of 100 KVA to 250 KVA transformer for supplying electricity to motor pump sets installed at Shiwane river"
        res = matcher.match_text(text, tender_id="NOISE_07")
        assert res.qualified is False
        assert res.disqualified_by_negative is True

