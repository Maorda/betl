# dantesito/chasky/classification/strategies/llm_router_strategy.py

from typing import Any, Dict, Optional, Tuple

import requests

from dantesito.chasky.classification.strategies.base_strategy import BaseStrategy
from dantesito.chasky.config.settings import Settings
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum


class LLMRouterStrategy(BaseStrategy):
    """Estrategia de clasificación de respaldo mediante Ollama."""

    _DEFAULT_ENDPOINT: str = "http://localhost:11434/api/generate"
    _SYSTEM_PROMPT: str = (
        "Clasifica este fragmento en una sola palabra: "
        "PARTES, GRAVAMEN, RESOLUCION, ENCABEZADO o DESCONOCIDO"
    )

    def __init__(self, endpoint: str = _DEFAULT_ENDPOINT) -> None:
        self._endpoint: str = endpoint

    def classify(
        self,
        chunk_text: str,
        current_source: Optional[SourceEnum] = None,
    ) -> Tuple[Optional[SourceEnum], Optional[SectionEnum]]:
        """Clasifica el fragmento mediante el modelo local de Ollama."""
        if not isinstance(chunk_text, str) or not chunk_text:
            return None, None

        payload: Dict[str, Any] = {
            "model": Settings.LLM_MODEL_NAME,
            "prompt": f"{self._SYSTEM_PROMPT}\n\n{chunk_text}",
            "stream": False,
            "keep_alive": Settings.OLLAMA_KEEP_ALIVE,
            "options": {
                "num_predict": 10,
            },
        }

        try:
            response: requests.Response = requests.post(
                self._endpoint,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            response_data: Dict[str, Any] = response.json()
        except (requests.RequestException, ValueError, TypeError):
            return None, None

        result: str = str(response_data.get("response", "")).strip().upper()

        if "DESCONOCIDO" in result:
            return None, None
        if "PARTES" in result:
            return None, SectionEnum.PARTES
        if "GRAVAMEN" in result:
            return None, SectionEnum.GRAVAMEN
        if "RESOLUCION" in result:
            return None, SectionEnum.RESOLUCION
        if "ENCABEZADO" in result:
            return None, SectionEnum.ENCABEZADO

        return None, None