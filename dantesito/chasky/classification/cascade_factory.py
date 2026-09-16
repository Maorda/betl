# dantesito/chasky/classification/cascade_factory.py
import logging
from typing import List, Optional, Tuple

from dantesito.chasky.classification.strategies.base_strategy import BaseStrategy
from dantesito.chasky.classification.strategies.cpu_regex_strategy import CPURegexStrategy
from dantesito.chasky.classification.strategies.context_overlap_strategy import ContextOverlapStrategy
from dantesito.chasky.classification.strategies.gemini_streamer import GeminiStreamer
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum

logger = logging.getLogger(__name__)


class CascadeFactory:
    """
    Fábrica de clasificación en cascada para dantesito-chasky.
    Aplica una arquitectura de enrutamiento por estrategias ordenadas jerárquicamente
    para minimizar latencia y consumo de recursos.
    """

    def __init__(self) -> None:
        """
        Inicializa la secuencia ordenada de estrategias de clasificación:
        1. CPU / Regex (Baja latencia local)
        2. Overlap / Contexto de ventana previa
        3. Gemini AI Studio (Inferencia remota en la nube)
        """
        self._strategies: List[BaseStrategy] = [
            CPURegexStrategy(),
            ContextOverlapStrategy(),
            GeminiStreamer(),
        ]

    def process_chunk(
        self, text: Optional[str], current_source: Optional[SourceEnum] = None
    ) -> Tuple[SourceEnum, SectionEnum]:
        """
        Procesa un fragmento de texto iterando ordenadamente sobre la lista inmutable
        de estrategias hasta que una resuelva de forma exitosa.

        Args:
            text: Fragmento de texto legal a clasificar.
            current_source: Estado previo o fuente actual detectada.

        Returns:
            Tuple[SourceEnum, SectionEnum]: Tupla resultante con la fuente y sección clasificadas.
        """
        effective_source = current_source or SourceEnum.REMAJU

        if not text or not text.strip():
            return effective_source, SectionEnum.RESOLUCION

        for strategy in self._strategies:
            try:
                src_res, sec_res = strategy.classify(text, current_source=effective_source)
                
                if sec_res is not None:
                    final_source = src_res or effective_source
                    return final_source, sec_res
            except Exception as e:
                logger.warning(
                    "Estrategia %s falló durante la clasificación: %s",
                    strategy.__class__.__name__,
                    str(e)
                )

        return effective_source, SectionEnum.RESOLUCION