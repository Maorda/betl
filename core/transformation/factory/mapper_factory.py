from typing import Any, Dict, List, Optional, Set
import re

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

        # =========================================================================
        # NUEVA REGLA: Extractor de rescate para Expedientes Judiciales Peruanos
        # =========================================================================
        # Si detecta el patrón oficial de 25 dígitos dentro de un texto sucio, lo aísla.
        patron_expediente = r"([0-9]{5}-[0-9]{4}-[0-9]+-[0-9]{4}-[A-Z]{2}-[A-Z]{2}-[0-9]{2})"
        match_exp = re.search(patron_expediente, txt, re.IGNORECASE)
        if match_exp:
            return match_exp.group(1).upper() # Devuelve estrictamente el código en mayúsculas

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

    # ==========================================
    # NUEVO MÉTODO: Integración con tus Contratos
    # ==========================================
    def transformar_por_contrato(self, contrato: Any, datos_extraidos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lee la configuración 'mapeo_dto' del contrato y transforma los datos extraídos
        aplicando de forma automática las reglas de limpieza corporativas.
        """
        meta = getattr(contrato, "_metadata", {})
        mapeo = meta.get("mapeo_dto", {})
        
        # Si el contrato no define un mapeo estructural, limpiamos el diccionario plano completo
        if not mapeo:
            return self.mapear_seccion(datos_extraidos, mapa_seccion=None)

        resultado: Dict[str, Any] = {}
        
        for seccion, campos in mapeo.items():
            if isinstance(campos, dict):
                # Caso: Sub-objetos anidados (Ej: 'expediente' o 'predio')
                # Invertimos el mapa temporalmente porque mapear_seccion busca { dto_key: raw_key }
                mapa_invertido = {dto_key: raw_key for dto_key, raw_key in campos.items()}
                
                seccion_mapeada = self.mapear_seccion(datos_extraidos, mapa_invertido)
                if seccion_mapeada:  # Solo añadir la sección si contiene datos válidos
                    resultado[seccion] = seccion_mapeada
            else:
                # Caso: Propiedades en la raíz del DTO
                val_crudo = datos_extraidos.get(campos)
                val_limpio = self.limpiar(val_crudo)
                if val_limpio is not None:
                    resultado[seccion] = val_limpio

        return resultado