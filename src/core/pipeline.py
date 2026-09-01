# src/core/pipeline.py
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Importaciones relativas internas del Core
from .extractors.ocr.pdfnative import PDFTextExtractor
from .extractors.ocr.pdfscan import PDFOCRExtractor
from .extractors.ocr.pdf_hybrid_extractor import PDFHybridExtractor
from .extractors.ocr.captcha import CaptchaExtractor
from .extractors.ocr.orquestator_ocr import OCROrchestrator

from .manipulate.strategy.regex import ManipulateRegexService
from .manipulate.strategy.llm import ManipulateLLMService
from .manipulate.orquestador_manipulacion import ManipulationOrchestrator

from .transformation.factory.mapper_factory import DtoTransformerUtils
from .transformation.merger import MergerService

logger = logging.getLogger(__name__)

def ejecutar_pipeline_etl(
    pdf_path: Path, 
    contrato: Any,  # <-- Ahora el usuario pasa su propio contrato como argumento
    captcha_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    
    logger.info("=== INICIANDO PIPELINE ETL DE DOCUMENTOS ===")

    if not pdf_path.exists():
        logger.error(f"No se encontró el archivo de entrada: {pdf_path}")
        return None

    try:
        # FASE 1: EXTRACCIÓN FÍSICA (OCR)
        ocr_orchestrator = OCROrchestrator(
            extractor_native=PDFTextExtractor(),
            extractor_scan=PDFOCRExtractor(),
            extractor_hybrid=PDFHybridExtractor(),
            captcha_service=CaptchaExtractor(),
        )

        if captcha_path and captcha_path.exists():
            codigo_captcha = ocr_orchestrator.resolver_captcha(str(captcha_path))
            logger.info(f"[Fase 1] Captcha resuelto: '{codigo_captcha}'")

        pdf_bytes = pdf_path.read_bytes()

        # FASE 2 Y 3: CONFIGURACIÓN DE MANIPULACIÓN Y CONSOLIDACIÓN ESTRUCTURADA
        regex_service = ManipulateRegexService(patrones_iniciales=contrato)
        llm_service = ManipulateLLMService(modelo="qwen3:8b", timeout=250)
        
        transformer_util = DtoTransformerUtils()
        merger_service = MergerService(prioridad_regex=True, transformer=transformer_util)

        manipulation_orchestrator = ManipulationOrchestrator(
            ocr_orchestrator=ocr_orchestrator,
            regex_service=regex_service,
            llm_service=llm_service,
            merger_service=merger_service,
            chunk_size=8000,
        )

        resultado_dto = manipulation_orchestrator.procesar_documento_pdf(
            pdf_bytes=pdf_bytes,
            contrato=contrato,
            modo_pdf="hybrid",
        )

        logger.info("=== PIPELINE ETL PROCESADO EXITOSAMENTE ===")
        return resultado_dto

    except Exception as e:
        logger.critical(f"Error crítico en Pipeline: {e}", exc_info=True)
        return None
