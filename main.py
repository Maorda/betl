import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Configuración centralizada de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ETL-Pipeline")

# --- Importaciones desde la raíz del proyecto ---
from llm_patron import PROMPT_PARTIDA_DIRECCION
from regex_patron import PATRONES_DOCUMENTO
from contrato import DtoMapper_expediente

# --- Fase 1: Extracción Física (OCR / PDF / Captcha) ---
from core.extractors.ocr.pdfnative import PDFTextExtractor
from core.extractors.ocr.pdfscan import PDFOCRExtractor
from core.extractors.ocr.pdf_hybrid_extractor import PDFHybridExtractor
from core.extractors.ocr.captcha import CaptchaExtractor
from core.extractors.ocr.orquestator_ocr import OCROrchestrator

# --- Fase 2: Manipulación Semántica (Regex + LLM) ---
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService
from core.manipulate.orquestador_manipulacion import ManipulationOrchestrator

# --- Fase 3: Transformación y Consolidación (Merger) ---
from core.transformation.merger import MergerService


def ejecutar_pipeline_etl(pdf_path: Path, captcha_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Orquesta y ejecuta las tres fases del pipeline ETL de documentos de forma segura.
    """
    logger.info("=== INICIANDO PIPELINE ETL DE DOCUMENTOS ===")
    
    try:
        # =====================================================================
        # FASE 1: EXTRACCIÓN FÍSICA
        # =====================================================================
        logger.info("--> [Fase 1] Inicializando Orquestador de Extracción...")
        
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
            logger.error(f"No se encontró el archivo de prueba: {pdf_path}")
            return None

        pdf_bytes = pdf_path.read_bytes()

        # =====================================================================
        # FASE 2: MANIPULACIÓN SEMÁNTICA (REGEX + LLM EN CASCADA)
        # =====================================================================
        logger.info("--> [Fase 2] Inicializando Servicios de Manipulación...")

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

        logger.info("[Fase 2] Extracción de datos bruta completada.")

        # =====================================================================
        # FASE 3: TRANSFORMACIÓN Y APLICACIÓN DE CONTRATO (MERGER)
        # =====================================================================
        logger.info("--> [Fase 3] Consolidando datos y aplicando DtoMapper_expediente...")

        merger = MergerService(prioridad_regex=True)
        
        resultado_dto = merger.fusionar(
            datos_regex=resultados_fase2.get("datos_regex", {}),
            datos_llm=resultados_fase2.get("datos_llm", {}),
            contrato=DtoMapper_expediente
        )

        logger.info("=== PIPELINE ETL PROCESADO EXITOSAMENTE ===")
        return resultado_dto

    except Exception as e:
        logger.critical(f"Error crítico no controlado durante la ejecución del Pipeline: {e}", exc_info=True)
        return None


def main():
    base_dir = Path(__file__).parent
    pdf_path = base_dir / "pdftest.pdf"
    captcha_path = base_dir / "captchatest.png"

    # Ejecutar pipeline
    resultado_dto = ejecutar_pipeline_etl(pdf_path=pdf_path, captcha_path=captcha_path)

    # Imprimir salida si fue exitosa
    if resultado_dto:
        print("\n--- ESTRUCTURA DTO CAMELCASE FINAL (NESTJS COMPATIBLE) ---")
        print(json.dumps(resultado_dto, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()