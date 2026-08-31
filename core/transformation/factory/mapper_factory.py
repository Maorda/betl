from typing import Any, Dict, List, Optional, Set


class DtoTransformerUtils:
    """Servicio utilitario reusable para limpieza y mapeo de secciones DTO."""

    @staticmethod
    def limpiar(val: Any) -> Any:
        """Limpia primitivos y filtra basura común de marcas de agua."""
        if val is None:
            return None
        if isinstance(val, (int, float, bool)):
            return val

        txt = str(val).strip()
        if not txt or "Firma Web" in txt or "Descarga componente" in txt:
            return None
        return txt

    def mapear_seccion(
        self,
        datos_seccion: Optional[Dict[str, Any]],
        mapa_seccion: Optional[Dict[str, str]],
        campos_permitidos: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """Mapea claves raw a camelCase y aplica whitelisting."""
        resultado = {}
        if not datos_seccion or not isinstance(datos_seccion, dict):
            return resultado

        if mapa_seccion:
            for dto_key, etiqueta_raw in mapa_seccion.items():
                val = datos_seccion.get(etiqueta_raw, datos_seccion.get(dto_key, None))
                val_limpio = self.limpiar(val)
                if val_limpio is not None:
                    resultado[dto_key] = val_limpio
        else:
            for key, val in datos_seccion.items():
                val_limpio = self.limpiar(val)
                if val_limpio is not None:
                    resultado[key] = val_limpio

        if campos_permitidos:
            resultado = {k: v for k, v in resultado.items() if k in campos_permitidos}

        return resultado

    def mapear_lista_segura(
        self,
        lista_raw: Optional[List[Any]],
        mapa_item: Optional[Dict[str, str]],
        campos_permitidos: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """Mapea arreglos de elementos de forma segura."""
        resultado = []
        if isinstance(lista_raw, list):
            for item in lista_raw:
                item_mapeado = self.mapear_seccion(item, mapa_item, campos_permitidos)
                if item_mapeado:
                    resultado.append(item_mapeado)
        return resultado