import logging
from typing import Any, Dict, Optional, Type, Union
from core.transformation.factory.mapper_factory import DtoTransformerUtils

logger = logging.getLogger("MergerService")


class MergerService:
    def __init__(self, prioridad_regex: bool = True, transformer: Optional[DtoTransformerUtils] = None):
        self.prioridad_regex = prioridad_regex
        self.transformer = transformer or DtoTransformerUtils()

    def fusionar(
        self,
        datos_regex: Optional[Dict[str, Any]] = None,
        datos_llm: Optional[Dict[str, Any]] = None,
        contrato: Optional[Union[Type[Any], Any]] = None
    ) -> Dict[str, Any]:
        datos_regex = datos_regex or {}
        datos_llm = datos_llm or {}

        logger.info("Iniciando fusión de datos Regex y LLM...")

        datos_regex_normalizados = {
            k: self._normalizar_valor_regex(v) for k, v in datos_regex.items()
        }

        datos_consolidados = self._merge_deep(datos_llm, datos_regex_normalizados)

        if contrato:
            logger.info("Aplicando contrato de mapeo / DTO...")
            return self._aplicar_contrato(datos_consolidados, contrato)

        logger.info("Fusión finalizada sin contrato DTO.")
        return datos_consolidados

    def _aplicar_contrato(self, datos: Dict[str, Any], contrato: Union[Type[Any], Any]) -> Dict[str, Any]:
        try:
            if isinstance(contrato, type):
                try:
                    instancia = contrato(transformer=self.transformer)
                except TypeError:
                    instancia = contrato()
            else:
                instancia = contrato

            if hasattr(instancia, "adaptar_a_dto") and callable(getattr(instancia, "adaptar_a_dto")):
                return instancia.adaptar_a_dto(datos)

            if hasattr(instancia, "filtrar_y_mapear") and callable(getattr(instancia, "filtrar_y_mapear")):
                return instancia.filtrar_y_mapear(datos)

            if callable(instancia):
                return instancia(datos)

            logger.warning("El contrato provisto no posee método de adaptación compatible. Retornando consolidados.")
            return datos

        except Exception as e:
            logger.error(f"Error al aplicar el contrato DTO: {e}", exc_info=True)
            return datos

    def _merge_deep(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        resultado = base.copy() if isinstance(base, dict) else {}
        if not isinstance(override, dict):
            return resultado

        for clave, valor_override in override.items():
            if clave not in resultado:
                resultado[clave] = valor_override
                continue

            valor_base = resultado[clave]

            if isinstance(valor_base, dict) and isinstance(valor_override, dict):
                resultado[clave] = self._merge_deep(valor_base, valor_override)
            elif isinstance(valor_base, list) and isinstance(valor_override, list):
                resultado[clave] = valor_override if valor_override else valor_base
            else:
                if self.prioridad_regex:
                    if self._tiene_valor(valor_override):
                        resultado[clave] = valor_override
                else:
                    if not self._tiene_valor(valor_base) and self._tiene_valor(valor_override):
                        resultado[clave] = valor_override

        return resultado

    @staticmethod
    def _tiene_valor(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, str) and not val.strip():
            return False
        return True

    @staticmethod
    def _normalizar_valor_regex(val: Any) -> Any:
        # Caso 1: Diccionario con metadatos o valor interno
        if isinstance(val, dict):
            if "value" in val:
                return MergerService._normalizar_valor_regex(val["value"])
            if "_match" in val:
                return MergerService._normalizar_valor_regex(val["_match"])
            return {k: MergerService._normalizar_valor_regex(v) for k, v in val.items() if not k.startswith("_")}

        # Caso 2: Lista de evidencias/coincidencias
        elif isinstance(val, list):
            elementos_normalizados = [
                MergerService._normalizar_valor_regex(item)
                for item in val if item is not None
            ]
            elementos_str = [
                str(item).strip()
                for item in elementos_normalizados if str(item).strip()
            ]
            return ", ".join(elementos_str) if elementos_str else None

        # Caso 3: Primitivos (str, int, float, etc.)
        return val