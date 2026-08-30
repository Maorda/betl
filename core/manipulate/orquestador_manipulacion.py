import json
import logging
from typing import Dict, Any, Optional, List

from core.extractors.ocr.orquestator_ocr import OCROrchestrator
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService

logger = logging.getLogger(__name__)


class ManipulationOrchestrator:
    """
    Orquestador de la Fase 2: Manipulación y Estructuración Semántica de Datos.

    Responsabilidad Única:
    Coordinar el flujo de estructuración en cascada: delegando la obtención de 
    texto plano a la Fase 1, ejecutando Regex como primera línea de defensa determinista,
    pre-procesando los hallazgos, aplicando particionamiento inteligente (Chunking) 
    y delegando al motor LLM de forma optimizada.
    """

    def __init__(
        self,
        ocr_orchestrator: OCROrchestrator,
        regex_service: Optional[ManipulateRegexService] = None,
        llm_service: Optional[ManipulateLLMService] = None,
        merger_service: Optional[Any] = None,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
    ):
        if not ocr_orchestrator:
            raise ValueError("[ManipulationOrchestrator] Requiere una instancia válida de OCROrchestrator.")

        self.ocr_orchestrator = ocr_orchestrator
        self.regex_service = regex_service
        self.llm_service = llm_service
        self.merger_service = merger_service
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

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

    def _dividir_texto(self, texto: str) -> List[str]:
        """
        Divide el texto en fragmentos (chunks) inteligentes respetando saltos de línea 
        y párrafos para evitar cortes abruptos en el contexto del LLM.
        """
        if len(texto) <= self.chunk_size:
            return [texto]

        chunks = []
        inicio = 0
        n = len(texto)

        while inicio < n:
            fin = min(inicio + self.chunk_size, n)
            
            # Intentar recortar en un salto de doble línea (párrafo) si no estamos al final
            if fin < n:
                corte = texto.rfind('\n\n', inicio, fin)
                if corte != -1 and corte > inicio + int(self.chunk_size * 0.5):
                    fin = corte + 2
                else:
                    # Si no hay salto doble, buscar salto simple
                    corte_simple = texto.rfind('\n', inicio, fin)
                    if corte_simple != -1 and corte_simple > inicio + int(self.chunk_size * 0.5):
                        fin = corte_simple + 1

            chunks.append(texto[inicio:fin])
            # Desplazamiento considerando el solapamiento (overlap) para no perder contexto en los bordes
            inicio = fin - self.chunk_overlap if fin < n else n

        return chunks

    def _preprocesar_datos_regex(self, datos_regex: Dict[str, Any]) -> Dict[str, Any]:
        """
        Limpia y aplana los resultados de Regex para evitar inyectar listas crudas 
        o formatos tipo Python repr() al prompt del LLM.
        """
        datos_limpios = {}
        for k, v in datos_regex.items():
            if isinstance(v, list):
                # Filtrar elementos vacíos o nulos y unirlos en una cadena de texto limpia
                elementos = [str(item).strip() for item in v if item]
                if elementos:
                    datos_limpios[k] = ", ".join(elementos)
                else:
                    datos_limpios[k] = None
            elif v is not None and str(v).strip():
                datos_limpios[k] = v
            else:
                datos_limpios[k] = None
        return datos_limpios

    def procesar_texto_plano(
        self,
        texto_ocr: str,
        prompt_instruccion: str,
        patrones_temporales: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta la cascada inteligente: Regex global primero, pre-procesamiento de hallazgos,
        división en Chunks y procesamiento optimizado por el LLM.
        """
        if not texto_ocr or not texto_ocr.strip():
            return {"datos_regex": {}, "datos_llm": {}}

        datos_regex = {}
        
        # --- PASO 1: Extracción Determinista Global con Regex ---
        if self.regex_service:
            logger.info("[ManipulationOrchestrator] Ejecutando motor Regex de primera línea (global)...")
            datos_regex = self.regex_service.extraer_datos(
                texto=texto_ocr,
                patrones_temporales=patrones_temporales,
            )

        # --- PASO 2: Pre-procesar Regex y Preparar contexto para el LLM ---
        prompt_para_llm = prompt_instruccion
        if datos_regex:
            logger.info("[ManipulationOrchestrator] Pre-procesando y limpiando hallazgos de Regex para el contexto del LLM...")
            datos_regex_limpios = self._preprocesar_datos_regex(datos_regex)
            contexto_regex_str = json.dumps(datos_regex_limpios, indent=2, ensure_ascii=False)
            
            prompt_para_llm = (
                f"{prompt_instruccion}\n\n"
                f"--- CONTEXTO PREVIO (DETECTADO AUTOMÁTICAMENTE POR REGEX) ---\n"
                f"{contexto_regex_str}\n\n"
                f"NOTA DE ORIENTACIÓN: Los datos anteriores ya han sido extraídos con alta precisión mediante patrones formales. "
                f"Utilízalos como referencia confirmada, valida su coherencia con el documento y concéntrate en extraer "
                f"los campos faltantes, resolver ambigüedades o procesar el texto libre restante."
            )

        # --- PASO 3: Chunking y Ejecución del LLM por Fragmentos ---
        datos_llm = {}
        if self.llm_service:
            chunks = self._dividir_texto(texto_ocr)
            logger.info(f"[ManipulationOrchestrator] Texto dividido en {len(chunks)} chunk(s) para procesamiento optimizado.")

            resultados_parciales = []
            for idx, chunk in enumerate(chunks, start=1):
                logger.info(f"[ManipulationOrchestrator] Enviando chunk {idx}/{len(chunks)} al motor LLM...")
                
                res_chunk = self.llm_service.extraer_entidades(
                    texto_ocr=chunk,
                    prompt_instruccion=prompt_para_llm,
                )
                if isinstance(res_chunk, dict) and res_chunk:
                    resultados_parciales.append(res_chunk)

            # --- PASO 4: Consolidación de Resultados de Chunks ---
            if self.merger_service and hasattr(self.merger_service, "fusionar_resultados_chunks"):
                datos_llm = self.merger_service.fusionar_resultados_chunks(resultados_parciales)
            else:
                # Fusión predeterminada combinando claves no vacías de los chunks
                datos_llm = resultados_parciales[0] if resultados_parciales else {}
                for res in resultados_parciales[1:]:
                    for k, v in res.items():
                        if v and not datos_llm.get(k):
                            datos_llm[k] = v

        return {
            "datos_regex": datos_regex,
            "datos_llm": datos_llm,
        }