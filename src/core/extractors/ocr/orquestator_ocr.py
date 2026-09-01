import logging
import re
from typing import Optional, Any, List, Dict
import pymupdf as fitz
import numpy as np

from core.extractors.ocr.pdfnative import PDFTextExtractor
from core.extractors.ocr.pdfscan import PDFOCRExtractor
from core.extractors.ocr.pdf_hybrid_extractor import PDFHybridExtractor
from core.extractors.ocr.captcha import CaptchaExtractor

logger = logging.getLogger(__name__)


class OCROrchestrator:
    """
    Orquestador exclusivo de la Fase 1: Extracción Física de Texto.
    
    Responsabilidad Única:
    Gestionar los motores de conversión mediante un análisis dinámico de densidad 
    por página para optimizar costo y precisión de la extracción.
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
        # Regex exacta para remover el separador monorregión sin destruir texto real
        self._regex_separador_extractor = re.compile(r"^---\s*Página\s+\d+\s*---\s*\n", re.IGNORECASE)

    @staticmethod
    def _limpiar_texto_ocr(ocr_results: Any, min_score: float = 0.6) -> str:
        """Interpreta y limpia el output crudo de los extractores."""
        if not ocr_results:
            return ""

        if isinstance(ocr_results, str):
            return ocr_results

        clean_lines = []
        if isinstance(ocr_results, list):
            for page in ocr_results:
                if not page:
                    continue
                for block in page:
                    if not block or len(block) < 2:
                        continue
                    _, text_info = block
                    if isinstance(text_info, tuple) and len(text_info) >= 2:
                        text, score = text_info[0], text_info[1]
                        if score >= min_score:
                            clean_lines.append(text.strip())
            return "\n".join(clean_lines)
        
        return str(ocr_results)

    def _evaluar_densidad_pagina(self, pagina: fitz.Page, umbral_tinta: int = 240) -> str:
        """
        Analiza las densidades de una página específica usando vectorización NumPy.
        """
        # 1. Densidad Nativa
        texto_nativo = pagina.get_text()
        caracteres_nativos = len(texto_nativo.strip())

        # 2. Densidad Visual (Vectorizada con NumPy)
        pix = pagina.get_pixmap(colorspace=fitz.csGRAY, alpha=False)
        samples = np.frombuffer(pix.samples, dtype=np.uint8)
        pixeles_tinta = int(np.count_nonzero(samples < umbral_tinta))
        
        total_pixeles = pix.width * pix.height
        porcentaje_tinta = (pixeles_tinta / total_pixeles) * 100 if total_pixeles > 0 else 0.0

        # 3. Lógica de Enrutamiento Basada en Casos
        if caracteres_nativos > 100 and porcentaje_tinta > 0.5:
            # Caso 3: Híbrido (Texto abundante pero con alta carga visual/firmas/sellos)
            if caracteres_nativos / porcentaje_tinta < 30:
                return "hybrid"
            # Caso 1: PDF totalmente digital/nativo
            return "native"
        
        # Caso 2: PDF Escaneado / Imagen (Requiere OCR completo)
        elif caracteres_nativos <= 100 and porcentaje_tinta > 1.5:
            return "scan"
        
        return "native" 

    def extraer_texto_pdf(self, pdf_bytes: bytes, modo: str = "auto") -> str:
        """
        Enruta el PDF al extractor adecuado. 
        En modo 'auto', segmenta y analiza el documento página por página.
        """
        if not pdf_bytes:
            logger.warning("[OCR-Orchestrator] Bytes de PDF vacíos.")
            return ""

        if modo != "auto":
            return self._ejecutar_extractor_completo(modo, pdf_bytes)

        logger.info("[OCR-Orchestrator] Iniciando Extracción Inteligente por Página (Modo 'auto')")
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texto_final_documento = []

        for num_pag in range(len(doc)):
            pagina = doc[num_pag]
            
            estrategia_optima = self._evaluar_densidad_pagina(pagina)
            logger.info(f"[OCR-Orchestrator] Pág {num_pag + 1} clasificada como: '{estrategia_optima.upper()}'")

            # Creación de buffer monopágina aislado
            doc_monopagina = fitz.open()
            doc_monopagina.insert_pdf(doc, from_page=num_pag, to_page=num_pag)
            bytes_monopagina = doc_monopagina.tobytes()
            doc_monopagina.close()

            texto_pagina = self._ejecutar_extractor_completo(estrategia_optima, bytes_monopagina)
            
            if texto_pagina.strip():
                # Eliminación quirúrgica del prefijo "--- Página 1 ---" generado por el sub-extractor monopágina
                contenido_limpio = self._regex_separador_extractor.sub("", texto_pagina).strip()
                
                # Inyección del separador unificado con el índice real global del documento
                texto_final_documento.append(f"--- Página {num_pag + 1} ---\n{contenido_limpio}")

        doc.close()
        return "\n\n".join(texto_final_documento).strip()

    def _ejecutar_extractor_completo(self, modo: str, pdf_bytes: bytes) -> str:
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
        if not self.captcha_service:
            logger.warning("[OCR-Orchestrator] Servicio de captcha no configurado.")
            return ""
        try:
            return self.captcha_service.resolver(ruta_imagen_captcha)
        except Exception as e:
            logger.error(f"[OCR-Orchestrator] Error al resolver el captcha: {e}")
            return ""
