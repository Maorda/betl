import json
import logging
import re
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ManipulateLLMService:
    def __init__(
        self,
        modelo: Optional[str] = None,
        url_ollama: Optional[str] = None,
        timeout: int = 180
    ):
        self.modelo = modelo or "qwen3:8b"
        self.url_ollama = url_ollama or "http://localhost:11434/api/generate"
        self.timeout = timeout
        # Reutilizar la sesión HTTP para evitar el overhead de handshakes TCP repetidos
        self.session = requests.Session()

    def _extraer_json_puro(self, texto_respuesta: str) -> str:
        """Limpia la respuesta del LLM eliminando bloques de markdown o texto periférico."""
        texto_respuesta = texto_respuesta.strip()
        # Captura únicamente lo que está entre la primera '{' y la última '}'
        match = re.search(r"\{.*\}", texto_respuesta, re.DOTALL)
        if match:
            return match.group(0)
        return texto_respuesta

    def extraer_entidades(
        self, 
        texto_ocr: str, 
        prompt_instruccion: str, 
        estructura_esperada: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envía el texto y las directivas al motor LLM local optimizando latencia
        y garantizando el parseo correcto de objetos JSON.
        """
        if not texto_ocr or not texto_ocr.strip():
            logger.warning("[LLM-Extractor] Se recibió un texto OCR vacío para procesar.")
            return {}

        # Concatenación directa: el prompt_instruccion generado por LLMSchemaBuilder ya incluye las reglas
        prompt_completo = f"{prompt_instruccion}\n\n[DOCUMENTO OCR A ANALIZAR]:\n{texto_ocr}"

        payload = {
            "model": self.modelo,
            "prompt": prompt_completo,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "top_p": 0.1,
                "num_ctx": 4096,      # Reducido de 8192 a 4096 (suficiente para edictos, reduce uso de VRAM)
                "num_predict": 1024   # Detiene la generación tan pronto como el JSON se completa
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
            
            # Sanitizar la respuesta eliminando etiquetas ```json ... ``` si las hubiere
            json_limpio = self._extraer_json_puro(contenido_respuesta)
            datos_extraidos = json.loads(json_limpio)
            
            logger.info("[LLM-Extractor] Extracción semántica completada con éxito.")
            return datos_extraidos

        except requests.exceptions.RequestException as req_err:
            logger.error(f"[LLM-Extractor] Error de conexión con Ollama en {self.url_ollama}: {req_err}")
            return {}
        except json.JSONDecodeError as json_err:
            logger.error(f"[LLM-Extractor] Error decodificando JSON del LLM: {json_err}. Raw: {contenido_respuesta[:150]}")
            return {}
        except Exception as e:
            logger.error(f"[LLM-Extractor] Error inesperado en el servicio LLM: {e}")
            return {}