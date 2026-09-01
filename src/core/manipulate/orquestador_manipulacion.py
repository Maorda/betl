import os
import sys
import warnings
import json
import logging
import re
from typing import Dict, Any, Optional, List

# Configuración de entornos de logging para evitar ruido en consola
os.environ["GLOG_minloglevel"] = "3"
os.environ["PPOCR_LOGGING"] = "0"
os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
warnings.filterwarnings("ignore")

logging.getLogger("ppocr").setLevel(logging.ERROR)
logging.getLogger("paddle").setLevel(logging.ERROR)

from core.extractors.ocr.orquestator_ocr import OCROrchestrator
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService
from core.transformation.merger import MergerService

logger = logging.getLogger(__name__)


class ManipulationOrchestrator:
    """
    Orquestador central de la Fase 2: Procesamiento y Extracción de Datos.
    
    Responsabilidad Única:
    Gestionar el flujo de datos desde el texto crudo hasta la estructura final, 
    coordinando las estrategias de Extracción (Regex/LLM) y Fusión.
    """

    def __init__(
        self,
        ocr_orchestrator: OCROrchestrator,
        regex_service: Optional[ManipulateRegexService] = None,
        llm_service: Optional[ManipulateLLMService] = None,
        merger_service: Optional[MergerService] = None,
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
        # Regex para identificar los saltos de página generados por el nuevo OCROrchestrator
        self._regex_pagina = re.compile(r"--- Página \d+ ---")

    def procesar_documento_pdf(
        self,
        pdf_bytes: bytes,
        contrato: Optional[Any] = None,
        prompt_instruccion: str = "Extrae la información estructurada del documento según el contrato.",
        modo_pdf: str = "auto",  # CAMBIO CLAVE: Cambiado de 'hybrid' a 'auto' para activar la densidad dinámica
        patrones_temporales: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enruta los bytes del PDF al orquestador OCR inteligente y procesa el texto plano resultante.
        """
        texto_ocr = self.ocr_orchestrator.extraer_texto_pdf(
            pdf_bytes=pdf_bytes,
            modo=modo_pdf
        )

        if not texto_ocr or not texto_ocr.strip():
            logger.warning("[ManipulationOrchestrator] El procesamiento OCR devolvió un texto vacío.")
            return {"datos_regex": {}, "datos_llm": {}, "error": "No se pudo extraer texto del documento PDF."}

        return self.procesar_texto_plano(
            texto_ocr=texto_ocr,
            prompt_instruccion=prompt_instruccion,
            estructura_esperada=contrato,
            patrones_temporales=patrones_temporales,
        )

    def procesar_texto_plano(
        self,
        texto_ocr: str,
        prompt_instruccion: str,
        estructura_esperada: Optional[Any] = None,
        patrones_temporales: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Aplica estrategias secuenciales y combinadas de Regex y LLM sobre el contenido textual extraído.
        """
        datos_regex_limpios = {}
        resultados_llm_parciales = []

        # 1. Ejecución Estratégica de Regex
        if self.regex_service:
            try:
                patrones = patrones_temporales or estructura_esperada
                datos_regex_crudos = self.regex_service.extraer_datos(texto_ocr, patrones)
                datos_regex_limpios = self._preprocesar_datos_regex(datos_regex_crudos)
                logger.info(f"[Regex] Extracción exitosa. Campos detectados: {list(datos_regex_limpios.keys())}")
            except Exception as e:
                logger.error(f"[Regex] Error ejecutando extracción: {e}", exc_info=True)

        # 2. Segmentación Avanzada respetando fronteras de Páginas del OCROrchestrator
        chunks = self._dividir_texto(texto_ocr)
        logger.info(f"[LLM] Texto segmentado en {len(chunks)} chunks para procesamiento.")
        
        # 3. Procesamiento en paralelo/secuencial de Chunks mediante LLM
        for idx, chunk in enumerate(chunks, start=1):
            if self.llm_service:
                prompt_para_llm = prompt_instruccion
                if datos_regex_limpios:
                    # Inyección del contexto determinista estructurado para guiar y restringir al LLM
                    prompt_para_llm += f"\n\nContexto previo verificado extraído por Regex: {json.dumps(datos_regex_limpios, ensure_ascii=False)}"

                logger.debug(f"[LLM] Procesando chunk {idx}/{len(chunks)} ({len(chunk)} caracteres).")
                res_chunk = self.llm_service.extraer_entidades(
                    texto_ocr=chunk,
                    prompt_instruccion=prompt_para_llm,
                    estructura_esperada=estructura_esperada
                )
                if res_chunk:
                    resultados_llm_parciales.append(res_chunk)

        # Consolidación interna de respuestas parciales de diccionarios de LLM
        datos_llm_consolidados = {}
        for res in resultados_llm_parciales:
            if isinstance(res, dict):
                datos_llm_consolidados.update({k: v for k, v in res.items() if v is not None})

        # 4. Fusión Semántica Estricta usando el MergerService
        if self.merger_service:
            logger.info("[Merger] Iniciando fase de fusión y validación contra contrato contractual.")
            resultado_final = self.merger_service.fusionar(
                datos_regex=datos_regex_limpios,
                datos_llm=datos_llm_consolidados,
                contrato=estructura_esperada
            )
        else:
            logger.warning("[Merger] MergerService no configurado. Realizando unión directa (Fallback).")
            resultado_final = {**datos_llm_consolidados, **datos_regex_limpios}

        return resultado_final

    def _dividir_texto(self, texto: str) -> List[str]:
        """
        Refactorización Óptima: Divide el texto respetando los marcadores de página unificados 
        generados por el OCROrchestrator para mantener coherencia contextual completa.
        """
        if len(texto) <= self.chunk_size:
            return [texto]

        # Divide el documento usando el marcador exacto de cambio de página
        partes_paginas = self._regex_pagina.split(texto)
        marcadores = self._regex_pagina.findall(texto)

        chunks = []
        chunk_actual = []
        longitud_actual = 0

        # Reconstruye bloques de páginas que quepan juntas dentro de la ventana de contexto del chunk_size
        for i, parte in enumerate(partes_paginas):
            marcador_asociado = marcadores[i-1] if i > 0 else ""
            bloque_pagina = f"{marcador_asociado}\n{parte}" if marcador_asociado else parte
            longitud_bloque = len(bloque_pagina)

            if longitud_actual + longitud_bloque <= self.chunk_size or not chunk_actual:
                chunk_actual.append(bloque_pagina)
                longitud_actual += longitud_bloque
            else:
                chunks.append("".join(chunk_actual))
                # Manejo del overlap básico reinsertando la última sección si aplica
                chunk_actual = [bloque_pagina]
                longitud_actual = longitud_bloque

        if chunk_actual:
            chunks.append("".join(chunk_actual))

        return chunks

    def _preprocesar_datos_regex(self, datos_regex: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae el valor o texto del match de los diccionarios de evidencia."""
        datos_limpios = {}
        for k, v in datos_regex.items():
            if isinstance(v, list):
                elementos = []
                for item in v:
                    if isinstance(item, dict):
                        val = item.get("value") or item.get("_match")
                        if val:
                            elementos.append(str(val).strip())
                    elif item:
                        elementos.append(str(item).strip())
                
                if elementos:
                    datos_limpios[k] = ", ".join(elementos) if len(elementos) > 1 else elementos[0]
                else:
                    datos_limpios[k] = None
            elif isinstance(v, dict):
                datos_limpios[k] = v.get("value") or v.get("_match")
            elif v is not None and str(v).strip():
                datos_limpios[k] = v
            else:
                datos_limpios[k] = None
        return datos_limpios
