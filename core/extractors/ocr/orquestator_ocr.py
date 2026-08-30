import logging
from typing import Optional, Any

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

    @staticmethod
    def _limpiar_texto_ocr(ocr_results: Any, min_score: float = 0.6) -> str:
        """
        Interpreta y limpia el output crudo de los extractores.
        Filtra por score mínimo para descartar "basura óptica".
        """
        if not ocr_results:
            return ""

        # Si el extractor ya devolvió un string limpio (ej. PDFTextExtractor), lo retornamos tal cual
        if isinstance(ocr_results, str):
            return ocr_results

        clean_lines = []
        
        # Si el resultado es la lista cruda de PaddleOCR
        if isinstance(ocr_results, list):
            for page in ocr_results:
                if not page:
                    continue
                    
                for block in page:
                    # Validamos que el bloque tenga la estructura [box, (text, score)]
                    if not block or len(block) < 2:
                        continue
                        
                    _, text_info = block
                    
                    if isinstance(text_info, tuple) and len(text_info) >= 2:
                        text, score = text_info[0], text_info[1]
                        if score >= min_score:
                            clean_lines.append(text.strip())
            
            return "\n".join(clean_lines)
        
        # Fallback en caso de que devuelva un formato no reconocido
        return str(ocr_results)

    def extraer_texto_pdf(self, pdf_bytes: bytes, modo: str = "auto") -> str:
        """
        Enruta los bytes del PDF al motor de lectura.
        Si el modo es 'auto', aplica el patrón cascada: Nativo -> OCR -> Híbrido.
        """
        if not pdf_bytes:
            logger.warning("[OCR-Orchestrator] Bytes de PDF vacíos.")
            return ""

        # --- FLUJO CASCADA (AUTO) ---
        if modo == "auto":
            logger.info("[OCR-Orchestrator] Iniciando extracción en cascada (Modo 'auto')")
            
            # 1. Primera línea: Nativo (Rápido, barato, exacto)
            logger.info("[OCR-Orchestrator] Intento 1: PDFTextExtractor (Nativo)")
            texto_nativo = self._ejecutar_extractor("native", pdf_bytes)
            # Si extrajo una cantidad razonable de texto, el PDF es digital. ¡Terminamos rápido!
            if len(texto_nativo) > 50: 
                logger.info("[OCR-Orchestrator] Éxito con extracción Nativa. Omitiendo OCR pesado.")
                return texto_nativo

            # 2. Segunda línea: Escaneado (Más lento, requiere PaddleOCR)
            logger.info("[OCR-Orchestrator] El PDF parece ser una imagen escaneada. Intento 2: PDFOCRExtractor (Scan)")
            texto_scan = self._ejecutar_extractor("scan", pdf_bytes)
            if len(texto_scan) > 50:
                logger.info("[OCR-Orchestrator] Éxito con extracción OCR por Escaneo.")
                return texto_scan

            # 3. Última línea de defensa: Híbrido (Documentos complejos mixtos)
            logger.info("[OCR-Orchestrator] Intento 3: PDFHybridExtractor (Híbrido) como último recurso.")
            texto_hibrido = self._ejecutar_extractor("hybrid", pdf_bytes)
            return texto_hibrido

        # --- FLUJO MANUAL (Por si fuerzas un modo específico) ---
        return self._ejecutar_extractor(modo, pdf_bytes)

    def _ejecutar_extractor(self, modo: str, pdf_bytes: bytes) -> str:
        """Método de ayuda interno para no repetir el bloque try/except."""
        extractor = self.extractores_pdf.get(modo)
        if not extractor:
            logger.error(f"[OCR-Orchestrator] Extractor no configurado para el modo '{modo}'.")
            return ""

        try:
            raw_result = extractor.extraer(pdf_bytes)
            return self._limpiar_texto_ocr(raw_result)
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