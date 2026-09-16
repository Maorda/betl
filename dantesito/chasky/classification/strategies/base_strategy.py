# dantesito/chasky/classification/strategies/base_strategy.py

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum


class BaseStrategy(ABC):
    """Contrato base para las estrategias de clasificación de chunks."""

    @abstractmethod
    def classify(
        self,
        chunk_text: str,
        current_source: Optional[SourceEnum] = None,
    ) -> Tuple[Optional[SourceEnum], Optional[SectionEnum]]:
        """Clasifica un chunk y retorna su fuente y sección."""
        raise NotImplementedError