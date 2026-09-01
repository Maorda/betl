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


class ETLDocumentPipeline:
    """
    Fábrica y motor de ejecución persistente para el pipeline ETL de documentos.
    Mantiene los modelos y servicios en memoria para optimizar el rendimiento multianálisis.
    """

    def __init__(
        self, 
        modelo_llm: str = "qwen3:8b", 
        timeout_llm: int = 250, 
        chunk_size: int = 8000,
        ocr_lang: str = "es"
    ):
        logger.info("[Pipeline] Inicializando componentes pesados e infraestructura ETL...")
        
        # 1. Componentes Fijos de la Fase 1 (OCR y Densidad)
        # Se instancian una sola vez para evitar recargas costosas de PaddleOCR en memoria
        self.ocr_orchestrator = OCROrchestrator(
            extractor_native=PDFTextExtractor(),
            extractor_scan=PDFOCRExtractor(language=ocr_lang),
            extractor_hybrid=PDFHybridExtractor(language=ocr_lang),
            captcha_service=CaptchaExtractor(),
        )

        # 2. Servicios Base de la Fase 2 y 3
        self.llm_service = ManipulateLLMService(modelo=modelo_llm, timeout=timeout_llm)
        self.transformer_util = DtoTransformerUtils()
        self.merger_service = MergerService(prioridad_regex=True, transformer=self.transformer_util)
        
        # Parámetros de segmentación de texto
        self.chunk_size = chunk_size

    def ejecutar(
        self,
        pdf_path: Path,
        contrato: Any,
        captcha_path: Optional[Path] = None,
        modo_pdf: str = "auto"  # ACTIVADO: 'auto' permite activar la densidad por página vectorizada
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta el flujo completo de extracción física, análisis y consolidación contractual.
        """
        logger.info(f"=== INICIANDO PROCESAMIENTO ETL: {pdf_path.name} ===")

        if not pdf_path.exists():
            logger.error(f"[Pipeline] No se encontró el archivo de entrada: {pdf_path}")
            return None

        try:
            # --- FASE 1: RESOLUCIÓN DE SEGURIDAD Y CAPTCHA ---
            if captcha_path and captcha_path.exists():
                codigo_captcha = self.ocr_orchestrator.resolver_captcha(str(captcha_path))
                logger.info(f"[Fase 1] Captcha resuelto de forma independiente: '{codigo_captcha}'")

            # Lectura física del archivo binario
            pdf_bytes = pdf_path.read_bytes()

            # --- FASE 2: INSTANCIACIÓN DINÁMICA DE ESTRATEGIAS ---
            # El servicio de Regex es el único que muta fuertemente según el contrato del documento
            regex_service = ManipulateRegexService(patrones_iniciales=contrato)

            # Construcción instantánea del orquestador de manipulación (reutilizando instancias core)
            manipulation_orchestrator = ManipulationOrchestrator(
                ocr_orchestrator=self.ocr_orchestrator,
                regex_service=regex_service,
                llm_service=self.llm_service,
                merger_service=self.merger_service,
                chunk_size=self.chunk_size,
            )

            # --- FASE 3: EXTRACCIÓN MÚLTIPLE Y FUSIÓN ESTRUCTURADA ---
            resultado_dto = manipulation_orchestrator.procesar_documento_pdf(
                pdf_bytes=pdf_bytes,
                contrato=contrato,
                modo_pdf=modo_pdf,
            )

            logger.info(f"=== PIPELINE ETL PROCESADO EXITOSAMENTE: {pdf_path.name} ===")
            return resultado_dto

        except Exception as e:
            logger.critical(f"[Pipeline] Error crítico en la ejecución del flujo: {e}", exc_info=True)
            return None


# --- FUNCIÓN DE ENTRADA COMPATIBLE (Mantiene compatibilidad hacia atrás si la necesitas) ---
_pipeline_global_cache: Optional[ETLDocumentPipeline] = None

def ejecutar_pipeline_etl(
    pdf_path: Path, 
    contrato: Any,  
    captcha_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Función envolvente que asegura compatibilidad hacia atrás manteniendo la caché del pipeline.
    """
    global _pipeline_global_cache
    if _pipeline_global_cache is None:
        _pipeline_global_cache = ETLDocumentPipeline()
        
    return _pipeline_global_cache.ejecutar(
        pdf_path=pdf_path,
        contrato=contrato,
        captcha_path=captcha_path,
        modo_pdf="auto"  # Forzamos la automatización inteligente por densidad
    )
