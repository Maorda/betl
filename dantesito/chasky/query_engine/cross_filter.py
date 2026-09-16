# dantesito/chasky/query_engine/cross_filter.py
from typing import Any, Dict
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum

class CrossQueryFilter:
    """Generador determinista de filtros cruzados para ChromaDB (0 RAM)."""

    def generate_where_clause(self, query_text: str, doc_id: str) -> Dict[str, Any]:
        """
        Analiza el texto de la consulta en CPU y genera el diccionario exacto
        de metadatos estructurado bajo las restricciones estrictas de la API de ChromaDB.
        """
        if not query_text or not isinstance(query_text, str) or not query_text.strip():
            return {"id_documento": doc_id}

        query_lower = query_text.lower()

        # ⚖️ INTENCIÓN: PARTES (Múltiples fuentes permitidas)
        if any(w in query_lower for w in ["demandante", "ejecutante", "demandado", "sujetos", "partes"]):
            return {
                "$and": [
                    {"id_documento": doc_id},
                    {
                        "$or": [
                            {"$and": [{"fuente": SourceEnum.CEJ.value}, {"tipo_seccion": SectionEnum.PARTES.value}]},
                            {"$and": [{"fuente": SourceEnum.REMAJU.value}, {"tipo_seccion": SectionEnum.PARTES.value}]}
                        ]
                    }
                ]
            }

        # 🏛️ INTENCIÓN: GRAVÁMENES Y CARGAS (Múltiples fuentes permitidas)
        if any(w in query_lower for w in ["hipoteca", "embargo", "cargas", "gravamen", "afectacion"]):
            return {
                "$and": [
                    {"id_documento": doc_id},
                    {
                        "$or": [
                            {"$and": [{"fuente": SourceEnum.SUNARP.value}, {"tipo_seccion": SectionEnum.GRAVAMEN.value}]},
                            {"$and": [{"fuente": SourceEnum.REMAJU.value}, {"tipo_seccion": SectionEnum.GRAVAMEN.value}]}
                        ]
                    }
                ]
            }

        # 📑 INTENCIÓN: LINDEROS Y PROPIEDAD (Fuente fija SUNARP)
        if any(w in query_lower for w in ["linderos", "metraje", "medidas", "área", "area"]):
            return {
                "$and": [
                    {"id_documento": doc_id},
                    {"$and": [{"fuente": SourceEnum.SUNARP.value}, {"tipo_seccion": SectionEnum.RESOLUCION.value}]}
                ]
            }

        # 📋 INTENCIÓN: DATOS JURÍDICOS DE ENCABEZADO (Fuente fija CEJ)
        if any(w in query_lower for w in ["juez", "juzgado", "materia", "expediente"]):
            return {
                "$and": [
                    {"id_documento": doc_id},
                    {"$and": [{"fuente": SourceEnum.CEJ.value}, {"tipo_seccion": SectionEnum.ENCABEZADO.value}]}
                ]
            }

        # Restricción de seguridad por defecto para consultas ambiguas
        return {"id_documento": doc_id}
