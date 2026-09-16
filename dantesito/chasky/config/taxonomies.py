# dantesito/chasky/config/taxonomies.py
from enum import Enum


class SourceEnum(str, Enum):
    """
    Fuentes origen de información legal permitidas de forma estricta.
    Evita la proliferación de strings libres en pipelines de ingesta.
    """
    REMAJU = "remaju"
    SUNARP = "sunarp"
    CEJ = "cej"


class SectionEnum(str, Enum):
    """
    Secciones estructurales para la segmentación y clasificación semántica de documentos.
    """
    ENCABEZADO = "encabezado"
    RESOLUCION = "resolucion"
    PARTES = "partes"
    GRAVAMEN = "gravamen"