import logging
from typing import Dict, Any, Optional

from core.extractors.ocr.orquestator_ocr import OCROrchestrator
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService

logger = logging.getLogger(__name__)


class ManipulationOrchestrator:
    """
    Orquestador de la Fase 2: Manipulación y Estructuración Semántica de Datos.

    Responsabilidad Única:
    Coordinar el flujo de estructuración de información delegando la obtención de 
    texto plano a la Fase 1 (OCROrchestrator) y enrutando los datos a los motores 
    de análisis (Regex, LLM) y consolidación (Merger).
    """

    def __init__(
        self,
        ocr_orchestrator: OCROrchestrator,
        regex_service: Optional[ManipulateRegexService] = None,
        llm_service: Optional[ManipulateLLMService] = None,
        merger_service: Optional[Any] = None,
    ):
        if not ocr_orchestrator:
            raise ValueError("[ManipulationOrchestrator] Requiere una instancia válida de OCROrchestrator.")

        self.ocr_orchestrator = ocr_orchestrator
        self.regex_service = regex_service
        self.llm_service = llm_service
        self.merger_service = merger_service

    def procesar_documento_pdf(
        self,
        pdf_bytes: bytes,
        prompt_instruccion: str,
        contrato: Optional[Any] = None,
        modo_pdf: str = "hybrid",
        patrones_temporales: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Flujo completo a partir de un archivo PDF en bytes.
        """
        # 1. Delegar obtención de texto a la Fase 1 (OCROrchestrator)
        texto_ocr = self.ocr_orchestrator.extraer_texto_pdf(pdf_bytes, modo=modo_pdf)

        if not texto_ocr or not texto_ocr.strip():
            logger.warning("[ManipulationOrchestrator] No se obtuvo texto del PDF. Proceso cancelado.")
            return {}

        # 2. Ejecutar la manipulación de datos sobre el texto obtenido
        return self.procesar_texto_plano(
            texto_ocr=texto_ocr,
            prompt_instruccion=prompt_instruccion,
            patrones_temporales=patrones_temporales,
        )

    def procesar_texto_plano(
        self,
        texto_ocr: str,
        prompt_instruccion: str,
        patrones_temporales: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ejecuta los manipuladores y devuelve los resultados crudos."""
        if not texto_ocr or not texto_ocr.strip():
            return {"datos_regex": {}, "datos_llm": {}}

        datos_regex = {}
        datos_llm = {}

        if self.regex_service:
            datos_regex = self.regex_service.extraer_datos(
                texto=texto_ocr,
                patrones_temporales=patrones_temporales,
            )

        if self.llm_service:
            datos_llm = self.llm_service.extraer_entidades(
                texto_ocr=texto_ocr,
                prompt_instruccion=prompt_instruccion,
            )

        return {
            "datos_regex": datos_regex,
            "datos_llm": datos_llm,
        }