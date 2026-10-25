"""
Tender Intelligence Pipeline Orchestrator
Coordinates multi-source discovery, detail retrieval, document parsing,
structured field extraction, Nikom capability matching, and report generation.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.tender import (
    TenderRecord, RetrievalLevel, RetrievalResult, FieldStatus, ReadinessClassification
)
from src.utils.http_client import HttpClient
from src.adapters.cppp_epublish import CpppEpublishAdapter
from src.adapters.cppp_latest import CpppLatestTendersAdapter
from src.adapters.search_discovery import SearchDiscoveryAdapter
from src.extractors.field_extractor import FieldExtractor
from src.extractors.document_parser import DocumentParser
from src.extractors.boq_parser import BoqParser
from src.matcher.feasibility_engine import FeasibilityEngine
from src.matcher.nikom_profile import NIKOM_PROFILE
from src.storage.store import TenderStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class TenderPipeline:
    """End-to-end tender intelligence retrieval and feasibility analysis pipeline."""

    def __init__(
        self,
        base_dir: str = "data",
        reports_dir: str = "reports",
        rate_limit_seconds: float = 1.5,
        use_cache: bool = True
    ):
        self.base_dir = base_dir
        self.reports_dir = reports_dir
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        self.http_client = HttpClient(
            cache_dir=os.path.join(base_dir, "cache"),
            rate_limit_seconds=rate_limit_seconds
        )

        # Adapters
        self.epublish_adapter = CpppEpublishAdapter(self.http_client)
        self.cppp_latest_adapter = CpppLatestTendersAdapter(self.http_client)
        self.search_adapter = SearchDiscoveryAdapter(self.http_client)

        # Extractors
        self.field_extractor = FieldExtractor()
        self.doc_parser = DocumentParser()
        self.boq_parser = BoqParser()

        # Matcher & Storage
        self.feasibility_engine = FeasibilityEngine(NIKOM_PROFILE)
        self.storage = TenderStorage(base_dir=base_dir)

        # Pipeline state & metrics
        self.discovered_tenders: List[TenderRecord] = []
        self.evaluations: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}

    def run_pipeline(
        self,
        max_discover: int = 50,
        enable_search_discovery: bool = True,
        enrich_details: bool = True,
        download_docs: bool = True,
        include_benchmarks: bool = True
    ) -> Dict[str, Any]:
        """
        Executes the entire autonomous discovery and evaluation workflow.
        Returns complete execution summary and feasibility metrics.
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("STARTING NIKOM TENDER INTELLIGENCE FEASIBILITY PIPELINE")
        logger.info("=" * 60)

        # -------------------------------------------------------------
        # Phase 1: Multi-source Discovery
        # -------------------------------------------------------------
        logger.info("\n--- Phase 1: Multi-Source Discovery ---")
        tenders = []

        # 1. CPPP ePublish
        try:
            logger.info("Discovering from CPPP ePublish portal...")
            ep_tenders = self.epublish_adapter.discover_tenders(max_tenders=max_discover // 2)
            tenders.extend(ep_tenders)
            logger.info(f"Retrieved {len(ep_tenders)} tenders from CPPP ePublish")
        except Exception as e:
            logger.error(f"CPPP ePublish discovery error: {e}")

        # 2. CPPP Latest Active
        try:
            logger.info("Discovering from CPPP Latest Active Tenders...")
            cl_tenders = self.cppp_latest_adapter.discover_tenders(max_tenders=max_discover // 2)
            tenders.extend(cl_tenders)
            logger.info(f"Retrieved {len(cl_tenders)} tenders from CPPP Latest")
        except Exception as e:
            logger.error(f"CPPP Latest discovery error: {e}")

        # 3. Search Engine Discovery
        if enable_search_discovery:
            try:
                logger.info("Running search engine discovery queries...")
                sd_tenders = self.search_adapter.discover_tenders(max_tenders=20, max_queries=6)
                tenders.extend(sd_tenders)
                logger.info(f"Retrieved {len(sd_tenders)} tenders from Search Discovery")
            except Exception as e:
                logger.error(f"Search discovery error: {e}")

        # 4. Domain Benchmark Suite (Ground truth verification)
        if include_benchmarks:
            try:
                from data.seed_benchmarks import get_benchmark_tenders
                benchmarks = get_benchmark_tenders()
                tenders.extend(benchmarks)
                logger.info(f"Loaded {len(benchmarks)} domain benchmark and control tenders")
            except Exception as be:
                logger.warning(f"Could not load benchmarks: {be}")

        # Deduplicate tenders across sources
        self.discovered_tenders = self._deduplicate_tenders(tenders)
        logger.info(f"Total Unique Tenders Discovered: {len(self.discovered_tenders)}")

        # -------------------------------------------------------------
        # Phase 2 & 3: Detail Enrichment, Document Parsing & Extraction
        # -------------------------------------------------------------
        logger.info("\n--- Phase 2 & 3: Enrichment, Extraction & Normalization ---")
        for idx, tender in enumerate(self.discovered_tenders, 1):
            logger.info(f"[{idx}/{len(self.discovered_tenders)}] Processing Tender ID: {tender.tender_id} - {tender.title[:60] if tender.title else 'No Title'}...")

            # Detail fetch
            if enrich_details and tender.detail_url:
                self._enrich_tender_details(tender)

            # Extraction from title, scope, documents
            self._extract_structured_fields(tender)

        # -------------------------------------------------------------
        # Phase 4: Feasibility Matching & Verdict Determination
        # -------------------------------------------------------------
        logger.info("\n--- Phase 4: Nikom Feasibility Matching & Scoring ---")
        self.evaluations = []
        for tender in self.discovered_tenders:
            eval_res = self.feasibility_engine.evaluate_tender(tender)
            self.evaluations.append(eval_res)

        # -------------------------------------------------------------
        # Phase 5: Storage
        # -------------------------------------------------------------
        logger.info("\n--- Phase 5: Persistence to JSON and CSV ---")
        for t in self.discovered_tenders:
            self.storage.save_tender(t)
        self.storage.save_all_tenders(self.discovered_tenders)
        self.storage.save_csv(self.discovered_tenders)

        # -------------------------------------------------------------
        # Phase 6: Aggregate Metrics & Feasibility Assessment
        # -------------------------------------------------------------
        duration_sec = (datetime.now() - start_time).total_seconds()
        self.metrics = self._calculate_metrics(duration_sec)

        # Save evaluation summary
        eval_summary_file = os.path.join(self.reports_dir, "feasibility_evaluations.json")
        with open(eval_summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metrics": self.metrics,
                "evaluations": self.evaluations
            }, f, indent=2, default=str)

        logger.info(f"Pipeline completed in {duration_sec:.1f}s.")
        logger.info(f"GO Decisions: {self.metrics.get('verdicts', {}).get('GO', 0)}")
        logger.info(f"CAUTION Decisions: {self.metrics.get('verdicts', {}).get('CAUTION', 0)}")
        logger.info(f"NO-GO Decisions: {self.metrics.get('verdicts', {}).get('NO-GO', 0)}")

        return {
            "metrics": self.metrics,
            "tenders_count": len(self.discovered_tenders),
            "evaluations_count": len(self.evaluations)
        }

    def _enrich_tender_details(self, tender: TenderRecord):
        """Fetch detail page and attach/download any discovered documents."""
        try:
            if tender.source_portal == "CPPP_ePublish":
                if not tender.issuing_organization:
                    self.epublish_adapter.get_tender_details(tender)
            elif tender.source_portal == "CPPP_Latest":
                self.cppp_latest_adapter.get_tender_details(tender)
            elif tender.detail_url:
                resp = self.http_client.get(tender.detail_url)
                if resp['success']:
                    tender.retrieval_results.append(RetrievalResult(
                        level=RetrievalLevel.DETAIL_RETRIEVAL,
                        success=True,
                        source_url=tender.detail_url,
                        response_code=resp.get('status_code', 200)
                    ))

            # Download and extract text from attached documents if present
            docs_dir = os.path.join(self.base_dir, "raw", "documents")
            os.makedirs(docs_dir, exist_ok=True)

            for doc in tender.documents[:3]:  # Limit to first 3 docs per tender
                if doc.url and not doc.downloaded:
                    clean_filename = re.sub(r'[^\w\.-]', '_', doc.filename or "doc.pdf")
                    save_path = os.path.join(docs_dir, f"{tender.tender_id}_{clean_filename}")
                    dl_res = self.http_client.download_file(doc.url, save_path)
                    if dl_res['success']:
                        doc.downloaded = True
                        doc.download_path = save_path
                        doc.file_size = dl_res.get('size')

                        # Extract text if PDF
                        if save_path.lower().endswith('.pdf'):
                            pdf_res = self.doc_parser.extract_text_from_pdf(save_path)
                            if pdf_res['success']:
                                doc.text_extracted = True
                                doc.extracted_text = pdf_res['full_text']
                                logger.info(f"Extracted {pdf_res['total_chars']} chars from PDF for {tender.tender_id}")
                    else:
                        doc.access_error = dl_res.get('error')

        except Exception as e:
            logger.warning(f"Failed to enrich details for {tender.tender_id}: {e}")

    def _extract_structured_fields(self, tender: TenderRecord):
        """Apply regex and rule extractors to title, description, and attached texts."""
        combined_text = " ".join(filter(None, [
            tender.title,
            tender.scope_of_work.raw_text if tender.scope_of_work else None,
            tender.department,
            tender.issuing_organization
        ]))

        # EMD
        if not tender.emd_amount or tender.emd_amount.status != FieldStatus.PRESENT_EXTRACTED:
            extracted_emd = self.field_extractor.extract_emd(combined_text)
            if extracted_emd.status == FieldStatus.PRESENT_EXTRACTED:
                tender.emd_amount = extracted_emd

        # Tender Fee
        if not tender.tender_fee or tender.tender_fee.status != FieldStatus.PRESENT_EXTRACTED:
            extracted_fee = self.field_extractor.extract_tender_fee(combined_text)
            if extracted_fee.status == FieldStatus.PRESENT_EXTRACTED:
                tender.tender_fee = extracted_fee

        # Estimated Value
        if not tender.estimated_value or tender.estimated_value.status != FieldStatus.PRESENT_EXTRACTED:
            extracted_val = self.field_extractor.extract_estimated_value(combined_text)
            if extracted_val.status == FieldStatus.PRESENT_EXTRACTED:
                tender.estimated_value = extracted_val

        # Submission Deadline
        if not tender.submission_deadline or tender.submission_deadline.status != FieldStatus.PRESENT_EXTRACTED:
            extracted_deadline = self.field_extractor.extract_submission_deadline(combined_text)
            if extracted_deadline.status == FieldStatus.PRESENT_EXTRACTED:
                tender.submission_deadline = extracted_deadline

        # Turnover
        if not tender.minimum_turnover or tender.minimum_turnover.status != FieldStatus.PRESENT_EXTRACTED:
            extracted_to = self.field_extractor.extract_turnover_requirement(combined_text)
            if extracted_to.status == FieldStatus.PRESENT_EXTRACTED:
                tender.minimum_turnover = extracted_to

        # Experience
        if not tender.experience_requirement or tender.experience_requirement.status != FieldStatus.PRESENT_EXTRACTED:
            extracted_exp = self.field_extractor.extract_experience_requirement(combined_text)
            if extracted_exp.status == FieldStatus.PRESENT_EXTRACTED:
                tender.experience_requirement = extracted_exp

        # Certifications
        certs = self.field_extractor.extract_certifications(combined_text)
        if certs:
            tender.certifications_required = certs

        # OEM Requirements
        oem_req = self.field_extractor.extract_oem_requirements(combined_text)
        tender.oem_requirements = oem_req

        # BOQ Items
        boq_items = self.boq_parser.parse_equipment_items(combined_text)
        if boq_items:
            for item in boq_items:
                tender.technical_specifications.append(
                    self.field_extractor.extract_estimated_value("")  # placeholder to maintain schema
                )

    def _deduplicate_tenders(self, tenders: List[TenderRecord]) -> List[TenderRecord]:
        """Deduplicate tender list based on ID and title."""
        seen_ids = set()
        seen_titles = set()
        deduped = []
        for t in tenders:
            if not t.title:
                continue

            title_key = re.sub(r'[^a-zA-Z0-9]', '', t.title.lower())[:35]
            id_key = t.tender_id.strip() if t.tender_id else None

            if id_key and id_key in seen_ids:
                continue
            if title_key and title_key in seen_titles:
                continue

            if id_key:
                seen_ids.add(id_key)
            if title_key:
                seen_titles.add(title_key)

            deduped.append(t)
        return deduped

    def _calculate_metrics(self, duration_sec: float) -> Dict[str, Any]:
        """Compute aggregate feasibility metrics."""
        total = len(self.discovered_tenders)
        if total == 0:
            return {"total_tenders": 0, "duration_seconds": duration_sec}

        # Level counts
        level_counts = {}
        for t in self.discovered_tenders:
            lvl = t.get_retrieval_level()
            level_counts[lvl] = level_counts.get(lvl, 0) + 1

        # Verdict counts
        verdict_counts = {"GO": 0, "GO (PROVISIONAL)": 0, "CAUTION": 0, "NO-GO": 0}
        for ev in self.evaluations:
            v = ev.get("verdict", "NO-GO")
            verdict_counts[v] = verdict_counts.get(v, 0) + 1

        # Readiness counts
        readiness_counts = {}
        for t in self.discovered_tenders:
            r = t.readiness.value
            readiness_counts[r] = readiness_counts.get(r, 0) + 1

        # Field extraction success rates
        fields_to_check = [
            "title", "submission_deadline", "estimated_value",
            "emd_amount", "tender_fee", "minimum_turnover"
        ]
        field_extraction_counts = {}
        for f in fields_to_check:
            extracted_count = 0
            for t in self.discovered_tenders:
                val = getattr(t, f, None)
                if val:
                    if hasattr(val, "status"):
                        if val.status == FieldStatus.PRESENT_EXTRACTED:
                            extracted_count += 1
                    else:
                        extracted_count += 1
            field_extraction_counts[f] = {
                "count": extracted_count,
                "percentage": round((extracted_count / total) * 100, 1)
            }

        # Document download statistics
        total_docs = sum(len(t.documents) for t in self.discovered_tenders)
        downloaded_docs = sum(sum(1 for d in t.documents if d.downloaded) for t in self.discovered_tenders)
        extracted_text_docs = sum(sum(1 for d in t.documents if d.text_extracted) for t in self.discovered_tenders)

        # Average composite score
        scores = [ev.get("composite_score", 0.0) for ev in self.evaluations]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        return {
            "total_tenders_processed": total,
            "pipeline_duration_seconds": round(duration_sec, 2),
            "retrieval_level_breakdown": level_counts,
            "readiness_breakdown": readiness_counts,
            "verdicts": verdict_counts,
            "average_feasibility_score": avg_score,
            "field_extraction_rates": field_extraction_counts,
            "document_stats": {
                "total_documents_linked": total_docs,
                "downloaded_documents": downloaded_docs,
                "text_extracted_documents": extracted_text_docs,
                "download_success_rate_pct": round((downloaded_docs / total_docs * 100), 1) if total_docs > 0 else 0.0
            }
        }
