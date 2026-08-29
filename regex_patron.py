import re
# Asumiendo la importación de tu estructura de definición de patrones
from core.manipulate.strategy.regex import RegexPatternDefinition
PATRONES_DOCUMENTO = {
    "numero_expediente": RegexPatternDefinition(
        # Captura formatos estándar de expedientes (ej. 01234-2023-0-1801-JR-CI-01 o similares)
        pattern=r"\b\d{4,5}-\d{4}-\d-[0-9]{4}-[A-Z]{2}-[A-Z]{2}-\d{2}\b|\bExp(?:\.|ediente)?[:\s]*([0-9-]+/[0-9]{4})\b",
        flags=re.IGNORECASE
    )
}