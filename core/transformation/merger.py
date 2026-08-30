import logging
from typing import Any, Dict, Optional, Type, Union

logger = logging.getLogger("MergerService")


class MergerService:
    """
    Servicio de la Fase 3 del ETL.
    Consolida extracciones heterogéneas (Regex + LLM) y aplica contratos/DTOs
    para garantizar la estructura y tipos requeridos por la API destino.
    """

    def __init__(self, prioridad_regex: bool = True):
        """
        :param prioridad_regex: Si es True, los valores extraídos por Regex 
                                tienen mayor prioridad que los de LLM por su alta precisión.
        """
        self.prioridad_regex = prioridad_prioritaria = prioridad_regex

    def fusionar(
        self,
        datos_regex: Optional[Dict[str, Any]] = None,
        datos_llm: Optional[Dict[str, Any]] = None,
        contrato: Optional[Union[Type[Any], Any]] = None
    ) -> Dict[str, Any]:
        """
        Punto de entrada principal para la consolidación de datos.

        :param datos_regex: Diccionario con datos extraídos por patrones Regex.
        :param datos_llm: Diccionario con datos extraídos por LLM/JSON.
        :param contrato: Clase o instancia del DTO Mapper (ej. DtoMapper_expediente).
        :return: Diccionario transformado listo para consumir.
        """
        datos_regex = datos_regex or {}
        datos_llm = datos_llm or {}

        logger.info("Iniciando fusión de datos Regex y LLM...")

        # Normalizar datos de regex para extraer el valor real si vienen envueltos en metadatos
        datos_regex_normalizados = {
            k: self._normalizar_valor_regex(v) for k, v in datos_regex.items()
        }

        # 1. Consolidación bruta de estructuras
        datos_consolidados = self._merge_deep(datos_llm, datos_regex_normalizados)

        # 2. Aplicación de Contrato / DTO Mapper si está presente
        if contrato:
            logger.info("Aplicando contrato de mapeo DTO...")
            return self._aplicar_contrato(datos_consolidados, contrato)

        logger.info("Fusión finalizada sin contrato DTO.")
        return datos_consolidados

    def _merge_deep(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realiza una fusión recursiva de dos diccionarios.
        Resuelve conflictos priorizando valores no nulos según la estrategia configurada.
        """
        resultado = base.copy() if isinstance(base, dict) else {}

        if not isinstance(override, dict):
            return resultado

        for clave, valor_override in override.items():
            if clave not in resultado:
                resultado[clave] = valor_override
                continue

            valor_base = resultado[clave]

            # Caso 1: Ambos son sub-diccionarios -> Fusión recursiva
            if isinstance(valor_base, dict) and isinstance(valor_override, dict):
                resultado[clave] = self._merge_deep(valor_base, valor_override)

            # Caso 2: Ambos son listas -> Concatenación / Preservar si hay datos
            elif isinstance(valor_base, list) and isinstance(valor_override, list):
                resultado[clave] = valor_override if valor_override else valor_base

            # Caso 3: Tipo escalar o conflicto
            else:
                if self.prioridad_regex:
                    # Sobrescribe solo si el valor override no es nulo/vacío
                    if self._tiene_valor(valor_override):
                        resultado[clave] = valor_override
                else:
                    if not self._tiene_valor(valor_base) and self._tiene_valor(valor_override):
                        resultado[clave] = valor_override

        return resultado

    def _aplicar_contrato(self, datos: Dict[str, Any], contrato: Union[Type[Any], Any]) -> Dict[str, Any]:
        """
        Soporta mapeadores pasados como Clase o Instancia, detectando
        métodos estándar como 'adaptar_a_dto' o 'filtrar_y_mapear'.
        """
        try:
            # Caso 1: Contrato con método estático / classmethod 'adaptar_a_dto'
            if hasattr(contrato, "adaptar_a_dto") and callable(getattr(contrato, "adaptar_a_dto")):
                return contrato.adaptar_a_dto(datos)

            # Caso 2: Instancia con método 'filtrar_y_mapear'
            if hasattr(contrato, "filtrar_y_mapear") and callable(getattr(contrato, "filtrar_y_mapear")):
                instancia = contrato() if isinstance(contrato, type) else contrato
                return instancia.filtrar_y_mapear(datos)

            # Caso 3: Callable genérico
            if callable(contrato):
                return contrato(datos)

            logger.warning("El contrato provisto no tiene un método compatible. Se retornan datos consolidados.")
            return datos

        except Exception as e:
            logger.error(f"Error al aplicar el contrato DTO: {e}", exc_info=True)
            return datos

    @staticmethod
    def _tiene_valor(val: Any) -> bool:
        """Verifica si un valor es válido (no None ni String vacío)."""
        if val is None:
            return False
        if isinstance(val, str) and not val.strip():
            return False
        return True
    @staticmethod
    @staticmethod
    def _normalizar_valor_regex(val: Any) -> Any:
        """
        Si el valor es un diccionario con 'value', extrae el valor interno.
        Si es una lista, la aplana y la convierte en un string limpio para evitar corchetes.
        """
        if isinstance(val, dict):
            if "value" in val:
                return MergerService._normalizar_valor_regex(val["value"])
            return {k: MergerService._normalizar_valor_regex(v) for k, v in val.items()}
        
        elif isinstance(val, list):
            # Filtrar elementos nulos/vacíos y unirlos en una cadena de texto limpia
            elementos = [str(item).strip() for item in val if item is not None and str(item).strip()]
            if not elementos:
                return None
            # Si prefieres solo el primer elemento usa: return elementos[0]
            # Si prefieres unirlos todos en texto plano usa: 
            return ", ".join(elementos)
            
        return val