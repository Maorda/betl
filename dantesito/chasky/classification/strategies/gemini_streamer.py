# dantesito/chasky/classification/strategies/gemini_streamer.py
import logging
import os
from typing import Optional, Tuple

from google import genai
from google.genai import types

from dantesito.chasky.classification.strategies.base_strategy import BaseStrategy
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum

# 🤫 SILENCIADOR DE ADVERTENCIAS DE LA SDK DE GOOGLE
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("google.genai._api_client").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class GeminiStreamer(BaseStrategy):
    """
    Estrategia de inferencia remota en la nube utilizando el nuevo SDK unificado google-genai.
    Hereda de BaseStrategy y realiza la clasificación semántica de fragmentos
    de texto legal mediante el modelo gemini-3.5-flash-lite sin impacto en la memoria RAM local.
    """

    SYSTEM_INSTRUCTION = (
        "Actúa como un clasificador determinista de documentos legales en Perú. "
        "Analiza el siguiente fragmento de texto y clasifícalo estrictamente en UNA de estas categorías:\n"
        "- 'encabezado'\n"
        "- 'partes'\n"
        "- 'resolucion'\n"
        "- 'gravamen'\n"
        "- 'desconocido'\n\n"
        "Reglas de salida:\n"
        "Responde ÚNICA y EXCLUSIVAMENTE con la palabra de la categoría seleccionada en minúsculas. "
        "No incluyas explicaciones, saludos, formato Markdown, negritas ni signos de puntuación."
    )

    SECTION_MAP = {
        "encabezado": SectionEnum.ENCABEZADO,
        "resolucion": SectionEnum.RESOLUCION,
        "partes": SectionEnum.PARTES,
        "gravamen": SectionEnum.GRAVAMEN,
    }

    def __init__(self) -> None:
        """
        Inicializa el cliente oficial unificado de Google GenAI y configura el nombre del modelo.
        Aplica un motor de rescate de dos niveles leyendo estrictamente el entorno y el archivo .env físico.
        """
        api_key = ""

        # Nivel de Rescate 1: Entorno del sistema operativo
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_key:
            api_key = env_key

        # Nivel de Rescate 2: Escaneo físico del archivo .env
        if not api_key:
            env_path = ".env"
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line.startswith("GEMINI_API_KEY"):
                            try:
                                parsed_tokens = clean_line.split("=", 1)
                                if len(parsed_tokens) == 2:
                                    parsed_key = parsed_tokens[1].strip().strip('"').strip("'")
                                    if parsed_key:
                                        api_key = parsed_key
                                        break
                            except Exception:
                                pass

        # Validación estricta de la credencial para proteger la ejecución en Windows
        if not api_key or not (api_key.startswith("AIzaSy") or api_key.startswith("AQ.")):
            raise ValueError(
                "🚨 ERROR CRÍTICO DE CONFIGURACIÓN: La variable 'GEMINI_API_KEY' "
                "no está definida en el entorno ni en el archivo .env raíz."
            )

        self.client = genai.Client(api_key=api_key)
        # Sincronizado estrictamente al modelo verificado por los tests del proyecto
        self.model_name = "gemini-3.5-flash-lite"

    def classify(
        self, chunk_text: str, current_source: Optional[SourceEnum] = None
    ) -> Tuple[Optional[SourceEnum], Optional[SectionEnum]]:
        """
        Envía el fragmento de texto a la API de Gemini 3.5 Flash Lite y traduce la respuesta
        a la tupla de taxonomía esperada.
        """
        if not chunk_text or not chunk_text.strip():
            return None, None

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=chunk_text,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=0.1,
                ),
            )

            if not response or not hasattr(response, "text") or not response.text:
                logger.warning("Respuesta vacía o no válida recibida de la API de Gemini.")
                return None, None

            label = response.text.strip().lower()

            if label == "desconocido":
                return None, None

            section_enum = self.SECTION_MAP.get(label)
            if section_enum is None:
                logger.warning(
                    "Etiqueta desconocida o fuera de taxonomía devuelta por Gemini: '%s'", label
                )
                return None, None

            return None, section_enum

        except Exception as e:
            logger.error(
                "Error durante la inferencia remota con el cliente Google GenAI: %s",
                str(e),
                exc_info=True,
            )
            return None, None
