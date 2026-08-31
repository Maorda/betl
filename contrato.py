from typing import Any, Dict, Optional, Set
from core.transformation.factory.mapper_factory import DtoTransformerUtils


class DtoMapper_expediente:
    """Contrato DTO adaptado a Opción 1 con búsqueda resiliente de Opción 2."""

    CAMPOS_PERMITIDOS_EXPEDIENTE: Set[str] = {"numero"}
    CAMPOS_PERMITIDOS_PREDIO: Set[str] = {"partidaRegistral", "direccion"}

    MAPEOS_DEFAULT: Dict[str, Any] = {
        "mapeo_expediente": {
            "numero": "numero_expediente"
        },
        "mapeo_predio": {
            "partidaRegistral": "partida_electronica",
            "direccion": "direccion"
        }
    }

    def __init__(self, transformer: DtoTransformerUtils) -> None:
        self.transformer = transformer

    def adaptar_a_dto(self, datos: Dict[str, Any], mapeos: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not datos or not isinstance(datos, dict):
            datos = {}

        mapeos = mapeos if mapeos is not None else self.MAPEOS_DEFAULT

        # Resiliencia de búsqueda (funciona con diccionarios planos o anidados)
        expediente_raw = datos.get("expediente", datos)
        predio_raw = datos.get("predio", datos)

        return {
            "expediente": self.transformer.mapear_seccion(
                expediente_raw,
                mapeos.get("mapeo_expediente"),
                self.CAMPOS_PERMITIDOS_EXPEDIENTE
            ),
            "predio": self.transformer.mapear_seccion(
                predio_raw,
                mapeos.get("mapeo_predio"),
                self.CAMPOS_PERMITIDOS_PREDIO
            )
        }

    def filtrar_y_mapear(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        return self.adaptar_a_dto(datos)