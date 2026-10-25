"""
Unit tests for field extractor, BOQ parser, and document parsing utilities.
"""

from src.extractors.field_extractor import FieldExtractor
from src.extractors.boq_parser import BoqParser
from src.models.tender import FieldStatus


def test_amount_parsing_crores_lakhs():
    extractor = FieldExtractor()

    # Crores
    amt1 = extractor.parse_amount_in_inr("Estimated cost is Rs. 15.50 Crores inclusive of GST")
    assert amt1 == 155_000_000.0

    amt2 = extractor.parse_amount_in_inr("Tender Value: INR 4.2 Cr")
    assert amt2 == 42_000_000.0

    # Lakhs
    amt3 = extractor.parse_amount_in_inr("EMD amount of Rs. 2.5 Lakhs")
    assert amt3 == 250_000.0

    amt4 = extractor.parse_amount_in_inr("Estimated Tender Fee Rs 50 Lacs")
    assert amt4 == 5_000_000.0

    # Comma format
    amt5 = extractor.parse_amount_in_inr("Total Value: Rs. 1,50,00,000/-")
    assert amt5 == 15_000_000.0


def test_date_parsing():
    extractor = FieldExtractor()

    dt1 = extractor.parse_date_string("Bid submission deadline: 28-11-2026 15:00 Hrs")
    assert dt1 is not None
    assert dt1.day == 28
    assert dt1.month == 11
    assert dt1.year == 2026

    dt2 = extractor.parse_date_string("Opening date: 15-Dec-2026")
    assert dt2 is not None
    assert dt2.day == 15
    assert dt2.month == 12
    assert dt2.year == 2026


def test_emd_and_exemption_extraction():
    extractor = FieldExtractor()

    # Numeric EMD
    field1 = extractor.extract_emd("The bidder must deposit EMD of Rs. 3,50,000 through NEFT/RTGS.")
    assert field1.status == FieldStatus.PRESENT_EXTRACTED
    assert field1.normalized_value == 350000.0

    # Exempted EMD
    field2 = extractor.extract_emd("EMD: Nil / Exempted for MSME registered bidders.")
    assert field2.status == FieldStatus.PRESENT_EXTRACTED
    assert field2.normalized_value == 0.0


def test_certifications_and_oem():
    extractor = FieldExtractor()

    sample_text = (
        "Bidder must possess valid ISO 9001:2015 and ISO 27001 certifications. "
        "Manufacturer Authorization Form (MAF) from OEM is mandatory for UPS and PAC."
    )

    certs = extractor.extract_certifications(sample_text)
    cert_names = [c.normalized_value for c in certs]
    assert "ISO 9001" in cert_names
    assert "ISO 27001" in cert_names

    oem_field = extractor.extract_oem_requirements(sample_text)
    assert oem_field.status == FieldStatus.PRESENT_EXTRACTED
    assert oem_field.normalized_value is True


def test_boq_parser():
    parser = BoqParser()
    sample_text = (
        "Item 1: 2 Nos 120 kVA Online UPS with 30 min VRLA battery backup. "
        "Item 2: 4 Nos 15 TR Precision Air Conditioning (PAC) units for server room. "
        "Item 3: Supply of 10 Nos 42U Server Racks with aisle containment. "
        "Item 4: Clean agent fire suppression system FM-200 with VESDA detector."
    )

    items = parser.parse_equipment_items(sample_text)
    categories = [it["category"] for it in items]

    assert "UPS" in categories
    assert "PAC_HVAC" in categories
    assert "RACKS_CONTAINMENT" in categories
    assert "FIRE_SAFETY" in categories
