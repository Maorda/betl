import json
import logging
from pathlib import Path

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

# --- Fase 2: Manipulación Semántica (Regex / LLM) ---
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService
from core.manipulate.orquestador_manipulacion import ManipulationOrchestrator

# --- Fase 3: Transformación y Consolidación (Merger) ---
from core.transformation.merger import MergerService


def main():
    base_dir = Path(__file__).parent
    pdf_path = base_dir / "pdftest.pdf"
    captcha_path = base_dir / "captchatest.png"

    logger.info("=== INICIANDO PIPELINE ETL DE DOCUMENTOS ===")
    
    # =========================================================================
    # FASE 1: EXTRACCIÓN FÍSICA
    # =========================================================================
    logger.info("--> [Fase 1] Inicializando Orquestador de Extracción...")
    
    ocr_orchestrator = OCROrchestrator(
        extractor_native=PDFTextExtractor(),
        extractor_scan=PDFOCRExtractor(),
        extractor_hybrid=PDFHybridExtractor(),
        captcha_service=CaptchaExtractor()
    )

    # 1.1. Resolver captcha si el archivo de prueba existe
    if captcha_path.exists():
        codigo_captcha = ocr_orchestrator.resolver_captcha(str(captcha_path))
        logger.info(f"[Fase 1] Captcha resuelto: '{codigo_captcha}'")

    # 1.2. Verificar y cargar el archivo PDF
    if not pdf_path.exists():
        logger.error(f"No se encontró el archivo de prueba: {pdf_path}")
        return

    pdf_bytes = pdf_path.read_bytes()

    # =========================================================================
    # FASE 2: MANIPULACIÓN SEMÁNTICA (REGEX + LLM)
    # =========================================================================
    logger.info("--> [Fase 2] Inicializando Servicios de Manipulación...")

    regex_service = ManipulateRegexService(patrones_iniciales=PATRONES_DOCUMENTO)
    llm_service = ManipulateLLMService(modelo="qwen3:8b", timeout=60)

    manipulation_orchestrator = ManipulationOrchestrator(
        ocr_orchestrator=ocr_orchestrator,
        regex_service=regex_service,
        llm_service=llm_service
    )

    # Ejecución de extracción bruta (obtiene tanto datos_regex como datos_llm)
    resultados_fase2 = manipulation_orchestrator.procesar_documento_pdf(
        pdf_bytes=pdf_bytes,
        prompt_instruccion=PROMPT_PARTIDA_DIRECCION,
        modo_pdf="hybrid"
    )

    logger.info("[Fase 2] Extracción de datos bruta completada.")

    # =========================================================================
    # FASE 3: TRANSFORMACIÓN Y APLICACIÓN DE CONTRATO (MERGER)
    # =========================================================================
    logger.info("--> [Fase 3] Consolidando datos y aplicando DtoMapper_expediente...")

    merger = MergerService(prioridad_regex=True)
    
    # Se pasa la clase DtoMapper_expediente (importada de contrato.py)
    resultado_dto = merger.fusionar(
        datos_regex=resultados_fase2.get("datos_regex", {}),
        datos_llm=resultados_fase2.get("datos_llm", {}),
        contrato=DtoMapper_expediente
    )

    # =========================================================================
    # ENTREGA DE RESULTADOS
    # =========================================================================
    logger.info("=== PIPELINE ETL PROCESADO EXITOSAMENTE ===")
    print("\n--- ESTRUCTURA DTO CAMELCASE FINAL (NESTJS COMPATIBLE) ---")
    print(json.dumps(resultado_dto, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()