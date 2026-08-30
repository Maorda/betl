import re
from core.manipulate.strategy.regex import RegexPatternDefinition

PATRONES_DOCUMENTO = {
    "numero_expediente": RegexPatternDefinition(
        # Captura formatos estándar y variantes con espacios o barras alternativas por errores de OCR
        pattern=r"\b\d{4,5}[\s\-\/]+\d{4}[\s\-\/]+\d[\s\-\/]+\d{4}[\s\-\/]+[A-Z]{2}[\s\-\/]+[A-Z]{2}[\s\-\/]+\d{2}\b|\bExp(?:\.|ediente)?[:\s]*([0-9-]+/[0-9]{4})\b",
        flags=re.IGNORECASE
    ),
    
    "partida_registral": RegexPatternDefinition(
        # Ampliado para incluir Partida, P.E., Ficha, Tomo y códigos alfanuméricos con espacios o guiones
        pattern=r"(?:Partida|P\.?E\.?|Ficha|Tomo)\s*(?:N[°º]?|\#)?\s*([A-Z0-9\-\s]{5,15})\b",
        flags=re.IGNORECASE
    ),
    
    
}