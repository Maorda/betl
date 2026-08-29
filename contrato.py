"""
contrato.py

Mapeador y limpiador reducido exclusivamente para las entidades capturadas por
Regex (numero_expediente) y LLM (partida_electronica, direccion).
"""

from typing import Any, Dict, Optional, Set


class DtoMapper_expediente:
    """Contrato DTO reducido para Expediente y Predio/Dirección."""

    # ------------------------------------------------------------------
    # WHITELIST DE CAMPOS PERMITIDOS (NESTJS CAMELCASE)
    # ------------------------------------------------------------------
    CAMPOS_PERMITIDOS_EXPEDIENTE: Set[str] = {"numero"}
    CAMPOS_PERMITIDOS_PREDIO: Set[str] = {"partidaRegistral", "direccion"}

    # ------------------------------------------------------------------
    # MAPEOS (DTO camelCase <- Origen Regex / LLM snake_case)
    # ------------------------------------------------------------------
    MAPEO_EXPEDIENTE_DEFAULT = {
        "numero": "numero_expediente"
    }

    MAPEO_PREDIO_DEFAULT = {
        "partidaRegistral": "partida_electronica",
        "direccion": "direccion"
    }

    MAPEOS_DEFAULT = {
        "mapeo_expediente": MAPEO_EXPEDIENTE_DEFAULT,
        "mapeo_predio": MAPEO_PREDIO_DEFAULT
    }

    # ------------------------------------------------------------------
    # MÉTODOS DE LIMPIEZA Y TRANSFORMACIÓN
    # ------------------------------------------------------------------
    @staticmethod
    def limpiar(val: Any) -> Any:
        """Limpia la entrada preservando primitivos y eliminando basura de marcas de agua."""
        if val is None:
            return None
        if isinstance(val, (int, float, bool)):
            return val

        txt = str(val).strip()
        if not txt or "Firma Web" in txt or "Descarga componente" in txt:
            return None
        return txt

    @staticmethod
    def _mapear_seccion(
        datos_seccion: Optional[Dict[str, Any]], 
        mapa_seccion: Optional[Dict[str, str]], 
        campos_permitidos: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """Mapea un diccionario omitiendo claves cuyo valor final sea None."""
        resultado = {}
        if not datos_seccion or not isinstance(datos_seccion, dict):
            return resultado

        if mapa_seccion:
            for dto_key, etiqueta_raw in mapa_seccion.items():
                val = datos_seccion.get(etiqueta_raw, datos_seccion.get(dto_key, None))
                val_limpio = DtoMapper_expediente.limpiar(val)
                if val_limpio is not None:
                    resultado[dto_key] = val_limpio
        else:
            for key, val in datos_seccion.items():
                val_limpio = DtoMapper_expediente.limpiar(val)
                if val_limpio is not None:
                    resultado[key] = val_limpio

        if campos_permitidos:
            resultado = {k: v for k, v in resultado.items() if k in campos_permitidos}

        return resultado

    def filtrar_y_mapear(self, datos_extraidos: dict) -> dict:
        """Punto de entrada cuando se usa una instancia del contrato."""
        return self.adaptar_a_dto(datos_extraidos)

    # ------------------------------------------------------------------
    # PUNTO DE ENTRADA PRINCIPAL
    # ------------------------------------------------------------------
    @classmethod
    def adaptar_a_dto(cls, datos: Dict[str, Any], mapeos: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Adapta los datos fusionados (Regex + LLM) a la estructura reducida en camelCase.
        Soporta diccionarios planos o con subestructuras.
        """
        if not datos or not isinstance(datos, dict):
            datos = {}

        mapeos = mapeos if mapeos is not None else cls.MAPEOS_DEFAULT

        # Permite resolver claves tanto si están en la raíz como si vienen en sub-diccionarios
        expediente_raw = datos.get("expediente", datos)
        predio_raw = datos.get("predio", datos)

        return {
            "expediente": cls._mapear_seccion(
                expediente_raw, 
                mapeos.get("mapeo_expediente"), 
                cls.CAMPOS_PERMITIDOS_EXPEDIENTE
            ),
            "predio": cls._mapear_seccion(
                predio_raw, 
                mapeos.get("mapeo_predio"), 
                cls.CAMPOS_PERMITIDOS_PREDIO
            )
        }