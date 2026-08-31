import os
import sys
import warnings
import json
import logging
from typing import Dict, Any, Optional, List

os.environ["GLOG_minloglevel"] = "3"
os.environ["PPOCR_LOGGING"] = "0"
os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
warnings.filterwarnings("ignore")

import logging
logging.getLogger("ppocr").setLevel(logging.ERROR)
logging.getLogger("paddle").setLevel(logging.ERROR)

from core.extractors.ocr.orquestator_ocr import OCROrchestrator
from core.manipulate.strategy.regex import ManipulateRegexService
from core.manipulate.strategy.llm import ManipulateLLMService
from core.transformation.merger import MergerService

logger = logging.getLogger(__name__)


class ManipulationOrchestrator:

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

    def procesar_documento_pdf(
        self,
        pdf_bytes: bytes,
        contrato: Optional[Any] = None,
        prompt_instruccion: str = "Extrae la información estructurada del documento según el contrato.",
        modo_pdf: str = "hybrid",
        patrones_temporales: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        texto_ocr = self.ocr_orchestrator.extraer_texto_pdf(
            pdf_bytes=pdf_bytes,
            modo=modo_pdf
        )

        if not texto_ocr or not texto_ocr.strip():
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
        datos_regex_limpios = {}
        resultados_llm_parciales = []

        # 1. Aplicar Regex (Corrección de método extraer_datos)
        if self.regex_service:
            try:
                # Pasar el contrato si no hay patrones temporales explícitos
                patrones = patrones_temporales or estructura_esperada
                datos_regex_crudos = self.regex_service.extraer_datos(texto_ocr, patrones)
                datos_regex_limpios = self._preprocesar_datos_regex(datos_regex_crudos)
            except Exception as e:
                logger.error(f"[Regex] Error ejecutando extracción: {e}", exc_info=True)

        # 2. Dividir texto en chunks para el LLM
        chunks = self._dividir_texto(texto_ocr)
        
        # 3. Procesar chunks con el LLM
        for chunk in chunks:
            if self.llm_service:
                prompt_para_llm = prompt_instruccion
                if datos_regex_limpios:
                    prompt_para_llm += f"\n\nContexto previo extraído por Regex: {json.dumps(datos_regex_limpios, ensure_ascii=False)}"

                res_chunk = self.llm_service.extraer_entidades(
                    texto_ocr=chunk,
                    prompt_instruccion=prompt_para_llm,
                    estructura_esperada=estructura_esperada
                )
                if res_chunk:
                    resultados_llm_parciales.append(res_chunk)

        # Consolidador interno para chunks de LLM
        datos_llm_consolidados = {}
        for res in resultados_llm_parciales:
            if isinstance(res, dict):
                datos_llm_consolidados.update({k: v for k, v in res.items() if v is not None})

        # 4. Fusionar resultados usando MergerService (Corrección de llamada)
        if self.merger_service:
            resultado_final = self.merger_service.fusionar(
                datos_regex=datos_regex_limpios,
                datos_llm=datos_llm_consolidados,
                contrato=estructura_esperada
            )
        else:
            resultado_final = {**datos_llm_consolidados, **datos_regex_limpios}

        return resultado_final

    def _dividir_texto(self, texto: str) -> List[str]:
        if len(texto) <= self.chunk_size:
            return [texto]

        chunks = []
        inicio = 0
        n = len(texto)

        while inicio < n:
            fin = min(inicio + self.chunk_size, n)
            
            if fin < n:
                corte = texto.rfind('\n\n', inicio, fin)
                if corte != -1 and corte > inicio + int(self.chunk_size * 0.5):
                    fin = corte + 2
                else:
                    corte_simple = texto.rfind('\n', inicio, fin)
                    if corte_simple != -1 and corte_simple > inicio + int(self.chunk_size * 0.5):
                        fin = corte_simple + 1

            chunks.append(texto[inicio:fin])
            inicio = fin - self.chunk_overlap if fin < n else n

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