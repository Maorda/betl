import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Desactiva los logs de Paddle a nivel de sistema (C++)
os.environ["PP_LOG_LEVEL"] = "ERROR"
os.environ["FLAGS_print_extra_info"] = "0"
os.environ["PADDLE_OFFICIAL_MODELS_LOG_LEVEL"] = "ERROR"

# Tu función actual para los loggers de Python
import logging


def _silenciar_loggers_ruidosos() -> None:
    loggers = [
        "ppocr",
        "paddle",
        "paddlex",  # Asegúrate de incluir paddlex aquí también
        "paddle.base",
        "paddle.fluid",
        "paddleocr",
        "PIL",
        "urllib3",
        "pdfminer",
    ]
    for name in loggers:
        l = logging.getLogger(name)
        l.setLevel(logging.ERROR)
        l.propagate = False


_silenciar_loggers_ruidosos()

# Configuración de tu pipeline
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ETL-Pipeline")

# Ahora sí, importa tu contrato o modelos de PaddleX
from contrato import MiContratoRemate

from core.decorators.contract import contract
from core.decorators.strategy import campo, regex_strategy, llm_strategy

# Utilidades
from core.transformation.factory.mapper_factory import DtoTransformerUtils

# Fase 1: Extracción Física
from core.extractors.ocr.pdfnative import PDFTextExtractor
from core.extractors.ocr.pdfscan import PDFOCRExtractor
from core.extractors.ocr.pdf_hybrid_extractor import PDFHybridExtractor
from core.extractors.ocr.captcha import CaptchaExtractor
from core.extractors.ocr.orquestator_ocr import OCROrchestrator

# Fase 2: Manipulación Semántica
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService
from core.manipulate.orquestador_manipulacion import ManipulationOrchestrator

# Fase 3: Consolidación
from core.transformation.merger import MergerService


def ejecutar_pipeline_etl(
    pdf_path: Path, captcha_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    logger.info("=== INICIANDO PIPELINE ETL DE DOCUMENTOS ===")

    if not pdf_path.exists():
        logger.error(f"No se encontró el archivo de entrada: {pdf_path}")
        return None

    try:
        # 1. Instanciar contrato
        contrato = MiContratoRemate()
        
        # === LOG DE DIAGNÓSTICO 1: Inspeccionar si el contrato tiene campos registrados ===
        logger.info(f"[DIAGNÓSTICO] Tipo de contrato: {type(contrato)}")
        
        # Intentar ver cómo almacena los campos el decorador @contract
        campos_regex = getattr(contrato, "get_regex_fields", None)
        campos_llm = getattr(contrato, "get_llm_fields", None)
        
        if callable(campos_regex):
            logger.info(f"[DIAGNÓSTICO] Campos Regex detectados en contrato: {list(campos_regex().keys())}")
        else:
            logger.warning("[DIAGNÓSTICO] El contrato NO tiene método get_regex_fields o no está expuesto.")
            
        if callable(campos_llm):
            logger.info(f"[DIAGNÓSTICO] Campos LLM detectados en contrato: {list(campos_llm().keys())}")
        else:
            logger.warning("[DIAGNÓSTICO] El contrato NO tiene método get_llm_fields o no está expuesto.")
        # ==============================================================================

        # FASE 1: EXTRACCIÓN FÍSICA (Solo resolución de captcha y lectura del PDF)
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

        # FASE 2: MANIPULACIÓN SEMÁNTICA
        # FASE 2: MANIPULACIÓN SEMÁNTICA
        regex_service = ManipulateRegexService(patrones_iniciales=contrato)
        llm_service = ManipulateLLMService(modelo="qwen3:8b", timeout=250)

        manipulation_orchestrator = ManipulationOrchestrator(
            ocr_orchestrator=ocr_orchestrator,
            regex_service=regex_service,
            llm_service=llm_service,
            chunk_size=8000,
        )

        # resultados_fase2 ya es el diccionario plano con los datos extraídos
        resultados_fase2 = manipulation_orchestrator.procesar_documento_pdf(
            pdf_bytes=pdf_bytes,
            contrato=contrato,
            modo_pdf="hybrid",
        )

        logger.info(f"[Fase 2] Datos extraídos crudos: {resultados_fase2}")

        # FASE 3: TRANSFORMACIÓN DIRECTA AL DTO USANDO EL CONTRATO
        # Llamamos directamente a tu método adaptador que ya definiste en MiContratoRemate
        resultado_dto = contrato.adaptar_a_dto(resultados_fase2)

        logger.info("=== PIPELINE ETL PROCESADO EXITOSAMENTE ===")
        return resultado_dto

    except Exception as e:
        logger.critical(f"Error crítico en Pipeline: {e}", exc_info=True)
        return None


def main() -> None:
    base_dir = Path(__file__).parent
    pdf_path = base_dir / "pdftest.pdf"
    captcha_path = base_dir / "captchatest.png"

    resultado_dto = ejecutar_pipeline_etl(
        pdf_path=pdf_path, captcha_path=captcha_path
    )

    if resultado_dto:
        print("\n" + "=" * 60)
        print("ESTRUCTURA DTO CAMELCASE FINAL (NESTJS)")
        print("=" * 60)
        print(json.dumps(resultado_dto, indent=2, ensure_ascii=False))
        print("=" * 60)


if __name__ == "__main__":
    main()