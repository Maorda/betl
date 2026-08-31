import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Pattern, Union

logger = logging.getLogger(__name__)

RegexPattern = Union[str, Pattern[str]]


@dataclass(frozen=True)
class RegexPatternDefinition:
    pattern: RegexPattern
    flags: int = re.IGNORECASE


class ManipulateRegexService:
    def __init__(
        self,
        patrones_iniciales: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.patterns: Dict[str, Pattern[str]] = {}
        if patrones_iniciales:
            self.cargar_patrones(patrones_iniciales)

    def registrar_patron(
        self,
        nombre: str,
        patron: RegexPattern,
        flags: int = re.IGNORECASE,
    ) -> None:
        nombre = self._normalizar_nombre(nombre)
        patron_compilado = self._compilar_patron(
            patron=patron, flags=flags, nombre=nombre
        )
        self.patterns[nombre] = patron_compilado
        logger.debug(f"[Regex-Extractor] Patrón '{nombre}' registrado exitosamente.")

    def cargar_patrones(self, patrones: Any) -> None:
        """Carga patrones descubriéndolos dinámicamente desde la clase/contrato."""
        diccionario_patrones = self._descubrir_patrones(patrones)
        
        for nombre, definicion in diccionario_patrones.items():
            pattern_str, flags = self._extraer_patron_y_flags(definicion)
            if pattern_str:
                self.registrar_patron(nombre=nombre, patron=pattern_str, flags=flags)

    def extraer_datos(
        self,
        texto: str,
        patrones_temporales: Optional[Any] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not isinstance(texto, str):
            raise TypeError("El texto a evaluar debe ser un string.")

        if not texto.strip():
            logger.warning("[Regex-Extractor] Texto vacío provisto. Abortando extracción.")
            return {}

        patrones = self._preparar_patrones(patrones_temporales)
        if not patrones:
            logger.info("[Regex-Extractor] No existen patrones cargados para ejecutar.")
            return {}

        resultados: Dict[str, List[Dict[str, Any]]] = {}

        for nombre, patron in patrones.items():
            try:
                coincidencias: List[Dict[str, Any]] = []
                for match in patron.finditer(texto):
                    evidencia = self._crear_evidencia(texto=texto, match=match, patron=patron)
                    if evidencia is not None:
                        coincidencias.append(evidencia)
                resultados[nombre] = self._eliminar_duplicados(coincidencias)
            except Exception as exc:
                logger.exception(f"[Regex-Extractor] Error ejecutando patrón '{nombre}': {exc}")
                resultados[nombre] = []

        logger.info(f"[Regex-Extractor] Extracción completada. Patrones procesados: {len(patrones)}")
        return resultados

    def _descubrir_patrones(self, fuente: Any) -> Dict[str, Any]:
        """
        Descubre los patrones leyendo directamente el ExtractionContract inyectado
        por el decorador @contract.
        """
        # 1. Si la fuente es la clase decorada (tiene _extraction_contract)
        if hasattr(fuente, "_extraction_contract"):
            contrato = fuente._extraction_contract
            if hasattr(contrato, "get_regex_fields"):
                # Devuelve un dict { "nombre_campo": ExtractionField, ... }
                return contrato.get_regex_fields()

        # 2. Si por algún motivo pasaron la instancia de ExtractionContract directamente
        if hasattr(fuente, "get_regex_fields"):
            return fuente.get_regex_fields()

        # 3. Fallback: Si es un diccionario legacy (patrones_temporales en el orquestador)
        if isinstance(fuente, dict):
            return fuente

        return {}

    def _preparar_patrones(
        self, patrones_temporales: Optional[Any]
    ) -> Dict[str, Pattern[str]]:
        patrones_activos = dict(self.patterns)
        if not patrones_temporales:
            return patrones_activos

        diccionario_temporales = self._descubrir_patrones(patrones_temporales)
        for nombre, definicion in diccionario_temporales.items():
            nombre_norm = self._normalizar_nombre(nombre)
            pattern_str, flags = self._extraer_patron_y_flags(definicion)
            if pattern_str:
                patrones_activos[nombre_norm] = self._compilar_patron(
                    patron=pattern_str, flags=flags, nombre=nombre_norm
                )
        return patrones_activos

    def _extraer_patron_y_flags(self, definicion: Any) -> tuple[str, int]:
        """
        Extrae el string del patrón y los flags desde el modelo ExtractionField de Pydantic.
        """
        import re
        
        # A. Si la definición es tu modelo Pydantic ExtractionField (viene del _extraction_contract)
        if hasattr(definicion, "regex") and definicion.regex is not None:
            # definicion.regex es una instancia de RegexObjective
            pattern = definicion.regex.pattern or ""
            flags = definicion.regex.flags if definicion.regex.flags else re.IGNORECASE
            return pattern, flags
            
        # B. Si pasaron un objeto que ya tiene 'pattern' directamente (RegexObjective suelto)
        if hasattr(definicion, "pattern"):
            flags = getattr(definicion, "flags", re.IGNORECASE)
            return getattr(definicion, "pattern") or "", flags

        # C. Fallback clásico por si pasan un string temporal
        if isinstance(definicion, (str, re.Pattern)):
            return definicion, re.IGNORECASE
            
        return "", re.IGNORECASE

    @staticmethod
    def _compilar_patron(patron: RegexPattern, flags: int, nombre: str) -> Pattern[str]:
        if isinstance(patron, re.Pattern):
            return patron
        if not isinstance(patron, str):
            raise TypeError(f"El patrón '{nombre}' debe ser string o re.Pattern.")
        if not patron.strip():
            raise ValueError(f"El patrón '{nombre}' no puede estar vacío.")
        try:
            return re.compile(patron, flags)
        except re.error as exc:
            logger.exception(f"[Regex-Extractor] Error compilando patrón '{nombre}'.")
            raise ValueError(f"Regex inválido para '{nombre}': {exc}") from exc

    @staticmethod
    def _crear_evidencia(texto: str, match: re.Match, patron: Pattern[str]) -> Optional[Dict[str, Any]]:
        match_texto = match.group(0)
        if not match_texto:
            return None
        match_limpio = match_texto.strip()
        if not match_limpio:
            return None

        if patron.groupindex:
            datos = {}
            for nombre_grupo, valor in match.groupdict().items():
                if valor is None:
                    continue
                datos[nombre_grupo] = valor.strip() if isinstance(valor, str) else valor
        else:
            datos = {"value": match_limpio}

        return {
            **datos,
            "_source": "regex",
            "_position": match.start(),
            "_end_position": match.end(),
            "_match": match_limpio,
            "_confidence": 1.0,
        }

    @staticmethod
    def _eliminar_duplicados(valores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        resultado: List[Dict[str, Any]] = []
        vistos = set()
        for valor in valores:
            identidad = (
                valor.get("_position"),
                valor.get("_end_position"),
                tuple(sorted((k, str(v)) for k, v in valor.items() if not k.startswith("_")))
            )
            if identidad in vistos:
                continue
            vistos.add(identidad)
            resultado.append(valor)
        return resultado

    @staticmethod
    def _normalizar_nombre(nombre: str) -> str:
        return nombre.strip()