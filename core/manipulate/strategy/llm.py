import json
import logging
import re
from typing import Any, Dict, Optional, Union
import requests

logger = logging.getLogger(__name__)


class ManipulateLLMService:
    def __init__(
        self,
        modelo: Optional[str] = None,
        url_ollama: Optional[str] = None,
        timeout: int = 60
    ):
        self.modelo = modelo or "qwen3:8b"
        self.url_ollama = url_ollama or "http://localhost:11434/api/generate"
        self.timeout = timeout
        self.session = requests.Session()

    def _extraer_json_puro(self, texto_respuesta: str) -> str:
        """Limpia la respuesta del LLM eliminando bloques markdown o texto periférico."""
        texto = texto_respuesta.strip()
        
        # [CORREGIDO] 1. Intentar capturar bloque de código markdown ```json ... ```
        # Usamos re.DOTALL para multilínea y el sufijo ? para que no sea codicioso
        match_codeblock = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL | re.IGNORECASE)
        if match_codeblock:
            return match_codeblock.group(1).strip()
            
        # [CORREGIDO] 2. Buscar primer y último corchete (ideal si el LLM escupe texto antes o después)
        inicio = texto.find("{")
        fin = texto.rfind("}")
        
        if inicio != -1 and fin != -1 and fin > inicio:
            return texto[inicio : fin + 1]
            
        # 3. Fallback: retornar el texto crudo en caso de que ya sea un JSON válido o haya un error
        return texto

    def _construir_prompt_desde_targets(
        self,
        targets: Dict[str, Any],
        instruccion_base: Optional[str] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Transforma targets dinámicos (objetos LLMTarget o dicts) en un prompt estructurado
        y un esquema JSON esperado.
        """
        esquema_esperado = {}
        instrucciones_campos = []

        for field_name, target in targets.items():
            desc = getattr(target, "description", None) or getattr(target, "instruction", None)
            if isinstance(target, dict):
                desc = target.get("description") or target.get("instruction") or "Extraer valor exacto."
                esquema_esperado[field_name] = target.get("type", "string")
            else:
                esquema_esperado[field_name] = getattr(target, "type_hint", "string")

            if desc:
                instrucciones_campos.append(f"- `{field_name}`: {desc}")

        base = instruccion_base or "Extrae la información requerida del documento en el formato JSON solicitado."
        prompt_generado = (
            f"{base}\n\n"
            f"Campos a extraer e instrucciones específicas:\n" + "\n".join(instrucciones_campos) + "\n\n"
            f"Devuelve ÚNICAMENTE un objeto JSON con la siguiente estructura:\n"
            f"{json.dumps(esquema_esperado, indent=2)}"
        )
        return prompt_generado, esquema_esperado

    def extraer_entidades(
        self,
        texto_ocr: str,
        prompt_instruccion: Optional[str] = None,
        estructura_esperada: Optional[Union[Dict[str, Any], Any]] = None,
    ) -> Dict[str, Any]:
        if not texto_ocr or not texto_ocr.strip():
            logger.warning("[LLM-Extractor] Se recibió un texto OCR vacío para procesar.")
            return {}

        prompt_final = prompt_instruccion or ""

        # [CORREGIDO] Descubrir targets desde _extraction_contract (igual que RegexService)
        targets = None
        fuente = estructura_esperada
        
        if hasattr(fuente, "_extraction_contract"):
            contrato = fuente._extraction_contract
            if hasattr(contrato, "get_llm_fields"):
                targets = contrato.get_llm_fields()
            elif hasattr(contrato, "llm_targets"):
                targets = contrato.llm_targets
        elif hasattr(fuente, "llm_targets") and isinstance(fuente.llm_targets, dict):
            targets = fuente.llm_targets
        elif isinstance(fuente, dict) and any(hasattr(v, "description") for v in fuente.values()):
            targets = fuente

        if targets:
            prompt_final, _ = self._construir_prompt_desde_targets(targets, prompt_instruccion)

        if not prompt_final:
            prompt_final = "Extrae todos los campos relevantes en un objeto JSON clave-valor."

        prompt_completo = f"{prompt_final.strip()}\n\n[DOCUMENTO OCR A ANALIZAR]:\n{texto_ocr.strip()}"

        payload = {
            "model": self.modelo,
            "prompt": prompt_completo,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "top_p": 0.1,
                "num_ctx": 4096,
                "num_predict": 1024
            }
        }

        try:
            response = self.session.post(
                self.url_ollama,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            resultado_api = response.json()
            contenido_respuesta = resultado_api.get("response", "{}")

            json_limpio = self._extraer_json_puro(contenido_respuesta)
            datos_extraidos = json.loads(json_limpio)

            logger.info("[LLM-Extractor] Extracción semántica completada con éxito.")
            return datos_extraidos if isinstance(datos_extraidos, dict) else {}

        except requests.exceptions.RequestException as req_err:
            logger.error(f"[LLM-Extractor] Error de conexión con Ollama en {self.url_ollama}: {req_err}")
            return {}
        except json.JSONDecodeError as json_err:
            logger.error(f"[LLM-Extractor] Error decodificando JSON del LLM: {json_err}. Raw: {contenido_respuesta[:150]}")
            return {}
        except Exception as e:
            logger.error(f"[LLM-Extractor] Error inesperado en el servicio LLM: {e}")
            return {}