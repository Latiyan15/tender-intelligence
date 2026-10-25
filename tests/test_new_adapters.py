import pytest
from src.services.discovery_service import DiscoveryService
from src.adapters.gepnic import GepnicPortalAdapter
from src.adapters.ewizard import EWizardPortalAdapter
from src.adapters.tenderwizard import TenderWizardPortalAdapter
from src.adapters.psu_state import PsuStatePortalAdapter


def test_discovery_service_registers_all_42_sources():
    ds = DiscoveryService()
    expected_sources = [
        "gem", "cppp_latest", "cppp_epublish",
        "assam_tenders", "andaman_tenders", "arunachal_tenders", "bihar_eprocurement", "ap_eprocurement",
        "aiims_kalyani_ewizard", "aera_ewizard", "bcpl_ewizard", "becil_ewizard",
        "aiims_tenderwizard", "bhel_tenderwizard",
        "aiims_guwahati", "bel", "bhel", "bpcl", "iocl", "beml", "bial", "bnpm", "bharat_ets", "asrtu",
        "up_tenders", "mahatenders", "karnataka_eproc", "tn_tenders", "gujarat_nprocure", "rajasthan_eproc",
        "mp_tenders", "haryana_tenders", "delhi_tenders", "punjab_eproc", "uk_tenders", "wb_tenders",
        "kerala_tenders", "odisha_tenders", "jharkhand_tenders", "hp_tenders", "chhattisgarh_eproc", "jk_tenders"
    ]
    assert len(ds.sources) == 42
    for src in expected_sources:
        assert src in ds.sources, f"Source {src} missing from DiscoveryService.sources"


def test_gepnic_adapter_initialization():
    adapter = GepnicPortalAdapter(
        source_id="up_tenders",
        name="Uttar Pradesh eProcurement",
        base_url="https://etender.up.nic.in/nicgep/app",
        org_name="Government of Uttar Pradesh"
    )
    assert adapter.source_id == "up_tenders"
    assert adapter.name == "Uttar Pradesh eProcurement"
    assert "etender.up.nic.in" in adapter.base_url


def test_ewizard_adapter_initialization():
    adapter = EWizardPortalAdapter(
        source_id="aiims_kalyani_ewizard",
        name="AIIMS Kalyani eWizard Portal",
        base_url="https://aiimskalyani.ewizard.in",
        org_name="AIIMS Kalyani"
    )
    assert adapter.source_id == "aiims_kalyani_ewizard"
    assert "ewizard" in adapter.base_url


def test_tenderwizard_adapter_initialization():
    adapter = TenderWizardPortalAdapter(
        source_id="bhel_tenderwizard",
        name="Bharat Heavy Electricals Limited (TenderWizard)",
        base_url="https://www.tenderwizard.com/BHEL",
        org_name="BHEL"
    )
    assert adapter.source_id == "bhel_tenderwizard"
    assert "tenderwizard" in adapter.base_url


def test_psu_state_adapter_initialization():
    adapter = PsuStatePortalAdapter(
        source_id="karnataka_eproc",
        name="Karnataka eProcurement (KPPP)",
        base_url="https://eproc.karnataka.gov.in",
        org_name="Government of Karnataka",
        sector="Government"
    )
    assert adapter.source_id == "karnataka_eproc"
    assert adapter.name == "Karnataka eProcurement (KPPP)"
    assert adapter.org_name == "Government of Karnataka"
    tenders = adapter.discover_tenders(max_tenders=5)
    assert isinstance(tenders, list)
