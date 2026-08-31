import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Silenciar el spam de PaddleOCR
logging.getLogger("ppocr").setLevel(logging.ERROR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ETL-Pipeline")


from llm_patron import PROMPT_PARTIDA_DIRECCION
from regex_patron import PATRONES_DOCUMENTO

# Contratos y Utilidades
from core.transformation.factory.mapper_factory import DtoTransformerUtils
from contrato import DtoMapper_expediente

# Fase 1: Extracción
from core.extractors.ocr.pdfnative import PDFTextExtractor
from core.extractors.ocr.pdfscan import PDFOCRExtractor
from core.extractors.ocr.pdf_hybrid_extractor import PDFHybridExtractor
from core.extractors.ocr.captcha import CaptchaExtractor
from core.extractors.ocr.orquestator_ocr import OCROrchestrator

# Fase 2: Manipulación
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService
from core.manipulate.orquestador_manipulacion import ManipulationOrchestrator

# Fase 3: Consolidación
from core.transformation.merger import MergerService


def ejecutar_pipeline_etl(pdf_path: Path, captcha_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    logger.info("=== INICIANDO PIPELINE ETL DE DOCUMENTOS ===")
    
    try:
        # FASE 1: EXTRACCIÓN FÍSICA
        ocr_orchestrator = OCROrchestrator(
            extractor_native=PDFTextExtractor(),
            extractor_scan=PDFOCRExtractor(),
            extractor_hybrid=PDFHybridExtractor(),
            captcha_service=CaptchaExtractor()
        )

        if captcha_path and captcha_path.exists():
            codigo_captcha = ocr_orchestrator.resolver_captcha(str(captcha_path))
            logger.info(f"[Fase 1] Captcha resuelto: '{codigo_captcha}'")

        if not pdf_path.exists():
            logger.error(f"No se encontró el archivo: {pdf_path}")
            return None

        pdf_bytes = pdf_path.read_bytes()

        # FASE 2: MANIPULACIÓN SEMÁNTICA
        regex_service = ManipulateRegexService(patrones_iniciales=PATRONES_DOCUMENTO)
        llm_service = ManipulateLLMService(modelo="qwen3:8b", timeout=250)

        manipulation_orchestrator = ManipulationOrchestrator(
            ocr_orchestrator=ocr_orchestrator,
            regex_service=regex_service,
            llm_service=llm_service
        )

        resultados_fase2 = manipulation_orchestrator.procesar_documento_pdf(
            pdf_bytes=pdf_bytes,
            prompt_instruccion=PROMPT_PARTIDA_DIRECCION,
            modo_pdf="hybrid"
        )

        # FASE 3: TRANSFORMACIÓN Y CONTRATO DTO
        transformer_utils = DtoTransformerUtils()
        mapper_expediente = DtoMapper_expediente(transformer=transformer_utils)
        logger.info(f"Salida cruda LLM: {resultados_fase2.get('datos_llm')}")
        merger = MergerService(prioridad_regex=True, transformer=transformer_utils)
        
        resultado_dto = merger.fusionar(
            datos_regex=resultados_fase2.get("datos_regex", {}),
            datos_llm=resultados_fase2.get("datos_llm", {}),
            contrato=mapper_expediente
        )

        logger.info("=== PIPELINE ETL PROCESADO EXITOSAMENTE ===")
        return resultado_dto

    except Exception as e:
        logger.critical(f"Error crítico durante el Pipeline: {e}", exc_info=True)
        return None


def main():
    base_dir = Path(__file__).parent
    pdf_path = base_dir / "pdftest.pdf"
    captcha_path = base_dir / "captchatest.png"

    resultado_dto = ejecutar_pipeline_etl(pdf_path=pdf_path, captcha_path=captcha_path)

    if resultado_dto:
        print("\n--- ESTRUCTURA DTO CAMELCASE FINAL (NESTJS COMPATIBLE) ---")
        print(json.dumps(resultado_dto, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()