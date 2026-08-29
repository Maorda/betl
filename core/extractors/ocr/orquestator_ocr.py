import logging
from typing import Optional

from core.extractors.ocr.pdfnative import PDFTextExtractor
from core.extractors.ocr.pdfscan import PDFOCRExtractor
from core.extractors.ocr.pdf_hybrid_extractor import PDFHybridExtractor
from core.extractors.ocr.captcha import CaptchaExtractor

logger = logging.getLogger(__name__)


class OCROrchestrator:
    """
    Orquestador exclusivo de la Fase 1: Extracción Física de Texto.
    
    Responsabilidad Única:
    Gestionar los motores de conversión de documentos/imágenes a cadenas de texto plano (string).
    """

    def __init__(
        self,
        extractor_native: Optional[PDFTextExtractor] = None,
        extractor_scan: Optional[PDFOCRExtractor] = None,
        extractor_hybrid: Optional[PDFHybridExtractor] = None,
        captcha_service: Optional[CaptchaExtractor] = None,
    ):
        self.extractores_pdf = {
            "native": extractor_native,
            "scan": extractor_scan,
            "hybrid": extractor_hybrid,
        }
        self.captcha_service = captcha_service

    def extraer_texto_pdf(self, pdf_bytes: bytes, modo: str = "hybrid") -> str:
        """Enruta los bytes del PDF al motor de lectura adecuado."""
        if not pdf_bytes:
            logger.warning("[OCR-Orchestrator] Bytes de PDF vacíos.")
            return ""

        extractor = self.extractores_pdf.get(modo)
        if not extractor:
            logger.error(f"[OCR-Orchestrator] Extractor no configurado para el modo '{modo}'.")
            return ""

        try:
            logger.info(f"[OCR-Orchestrator] Ejecutando lectura PDF en modo '{modo}'...")
            return extractor.extraer(pdf_bytes)
        except Exception as e:
            logger.exception(f"[OCR-Orchestrator] Error extrayendo texto en modo '{modo}': {e}")
            return ""

    def resolver_captcha(self, ruta_imagen_captcha: str) -> str:
        """Delega la resolución del captcha al servicio especializado."""
        if not self.captcha_service:
            logger.warning("[OCR-Orchestrator] Servicio de captcha no configurado.")
            return ""

        try:
            logger.info(f"[OCR-Orchestrator] Solicitando resolución de captcha: {ruta_imagen_captcha}")
            return self.captcha_service.resolver(ruta_imagen_captcha)
        except Exception as e:
            logger.error(f"[OCR-Orchestrator] Error al resolver el captcha: {e}")
            return ""