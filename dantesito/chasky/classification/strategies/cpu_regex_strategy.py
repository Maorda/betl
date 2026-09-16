# dantesito/chasky/classification/strategies/cpu_regex_strategy.py

import re
from typing import Dict, List, Optional, Tuple

from dantesito.chasky.classification.strategies.base_strategy import BaseStrategy
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum


class CPURegexStrategy(BaseStrategy):
    """Clasifica chunks mediante expresiones regulares ejecutadas en CPU."""

    _SUNARP_RULES: Dict[SectionEnum, List[re.Pattern[str]]] = {
        SectionEnum.ENCABEZADO: [
            re.compile(
                r"\b(?:ZONA\s+REGISTRAL|OFICINA\s+REGISTRAL)\b"
                r".*\b(?:PARTIDA|FICHA)\b.*\b\d{8}\b",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"\b(?:PARTIDA|FICHA)\b.*\b\d{8}\b"
                r".*\b(?:ZONA\s+REGISTRAL|OFICINA\s+REGISTRAL)\b",
                re.IGNORECASE | re.DOTALL,
            ),
        ],
        SectionEnum.RESOLUCION: [
            re.compile(
                r"\b(?:linderos|medidas\s+perim[eé]tricas)\b"
                r".*\b(?:derecha|izquierda|frente|fondo)\b",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"\b(?:derecha|izquierda|frente|fondo)\b"
                r".*\b(?:linderos|medidas\s+perim[eé]tricas)\b",
                re.IGNORECASE | re.DOTALL,
            ),
        ],
        SectionEnum.PARTES: [
            re.compile(
                r"\b(?:compraventa|asiento\s+c|titular)\b",
                re.IGNORECASE,
            ),
        ],
        SectionEnum.GRAVAMEN: [
            re.compile(
                r"\b(?:hipoteca|embargo|asiento\s+d)\b",
                re.IGNORECASE,
            ),
        ],
    }

    _REMAJU_PARTES_PATTERN: re.Pattern[str] = re.compile(
        r"\b(?:ejecutante|demandado|vs)\b",
        re.IGNORECASE,
    )

    _REMAJU_EXPEDIENTE_PATTERN: re.Pattern[str] = re.compile(
        r"\b\d{5}-\d{4}\b",
        re.IGNORECASE,
    )

    def classify(
        self,
        chunk_text: str,
        current_source: Optional[SourceEnum] = None,
    ) -> Tuple[Optional[SourceEnum], Optional[SectionEnum]]:
        """Clasifica el chunk aplicando primero las reglas SUNARP y luego REMAJU."""
        if not isinstance(chunk_text, str) or not chunk_text:
            return None, None

        for section, patterns in self._SUNARP_RULES.items():
            if section is SectionEnum.ENCABEZADO:
                if any(pattern.search(chunk_text) for pattern in patterns):
                    return SourceEnum.SUNARP, section
                continue

            if any(pattern.search(chunk_text) for pattern in patterns):
                return SourceEnum.SUNARP, section

        if self._REMAJU_PARTES_PATTERN.search(chunk_text):
            return SourceEnum.REMAJU, SectionEnum.PARTES

        if self._REMAJU_EXPEDIENTE_PATTERN.search(chunk_text):
            return SourceEnum.REMAJU, SectionEnum.ENCABEZADO

        return None, None