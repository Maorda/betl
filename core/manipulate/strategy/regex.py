# `src/services/ExtractorRegexService.py`
import logging
import re
from dataclasses import dataclass
from typing import (Any, Dict, List, Optional, Pattern, Union,)
logger = logging.getLogger(__name__)
RegexPattern = Union[str, Pattern[str]]
@dataclass(frozen=True)
class RegexPatternDefinition:
    pattern: RegexPattern
    flags: int = re.IGNORECASE
class ManipulateRegexService:
    def __init__(
        self,
        patrones_iniciales: Optional[Dict[str, RegexPatternDefinition]] = None,
    ) -> None:
        self.patterns: Dict[str, Pattern[str]] = {}
        if patrones_iniciales:
            self.cargar_patrones(patrones_iniciales)
    def registrar_patron(self, nombre: str, patron: RegexPattern, flags: int = re.IGNORECASE,) -> None:
        nombre = self._normalizar_nombre(nombre)
        patron_compilado = self._compilar_patron(patron=patron,flags=flags,nombre=nombre,)
        self.patterns[nombre] = patron_compilado
        logger.debug("[Regex-Extractor] " f"Patrón '{nombre}' registrado.")
    def cargar_patrones(self, patrones: Dict[str, Union[RegexPattern,RegexPatternDefinition,],]) -> None:
        for nombre, definicion in patrones.items():
            if isinstance(definicion,RegexPatternDefinition,):
                self.registrar_patron(nombre=nombre,patron=definicion.pattern,flags=definicion.flags,)
                continue
            self.registrar_patron(nombre=nombre,patron=definicion,)
    def extraer_datos(
        self,
        texto: str,
        patrones_temporales: Optional[Dict[str, Union[RegexPattern, RegexPatternDefinition]]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not isinstance(texto,str,): raise TypeError("texto debe ser un string.")
        if not texto.strip():
            logger.warning("[Regex-Extractor] " "Texto vacío.")
            return {}
        patrones = self._preparar_patrones(patrones_temporales)
        if not patrones:
            logger.info("[Regex-Extractor] " "No existen patrones para ejecutar.")
            return {}
        resultados: Dict[str,List[Dict[str, Any]],] = {}
        for nombre, patron in patrones.items():
            try:
                coincidencias: List[Dict[str, Any],] = []
                for match in patron.finditer(texto):
                    evidencia = self._crear_evidencia(texto=texto,match=match,patron=patron,)
                    if evidencia is not None:
                        coincidencias.append(evidencia)
                resultados[nombre] = self._eliminar_duplicados(coincidencias)
            except Exception as exc:
                logger.exception("[Regex-Extractor] " f"Error ejecutando patrón '{nombre}'.")
                # El motor continúa con los demás patrones.
                resultados[nombre] = []
        logger.info("[Regex-Extractor] " "Extracción completada. " f"Patrones={len(patrones)}")
        return resultados
    def _preparar_patrones(self,patrones_temporales: Optional[Dict[str,Union[RegexPattern,RegexPatternDefinition]]]) -> Dict[str,Pattern[str]]:
        patrones = dict(self.patterns)
        if not patrones_temporales: return patrones
        for nombre, definicion in patrones_temporales.items():
            nombre_normalizado = self._normalizar_nombre(nombre)
            if isinstance(definicion,RegexPatternDefinition,):
                patrones[nombre_normalizado] = self._compilar_patron(patron=definicion.pattern, flags=definicion.flags, nombre=nombre_normalizado)
                continue
            patrones[nombre_normalizado] = self._compilar_patron(patron=definicion, flags=re.IGNORECASE,nombre=nombre_normalizado)
        return patrones
    @staticmethod
    def _compilar_patron(patron: RegexPattern, flags: int, nombre: str,) -> Pattern[str]:
        if isinstance(patron,re.Pattern,): return patron
        if not isinstance(patron,str,):
            raise TypeError(f"El patrón '{nombre}' debe ser un string o un re.Pattern.")
        if not patron.strip():
            raise ValueError(f"El patrón '{nombre}' no puede estar vacío.")
        try:
            return re.compile(patron,flags,)
        except re.error as exc:
            logger.exception("[Regex-Extractor] " f"Error compilando patrón '{nombre}'.")
            raise ValueError(f"Regex inválido para '{nombre}': {exc}") from exc

    @staticmethod
    def _crear_evidencia(texto: str,match: re.Match,patron: Pattern[str]) -> Optional[Dict[str, Any]]:
        match_texto = match.group(0)
        if not match_texto: return None
        match_limpio = match_texto.strip()
        if not match_limpio: return None
        if patron.groupindex:
            datos = {}
            for (nombre_grupo, valor,) in match.groupdict().items():
                if valor is None: continue
                if isinstance(valor,str,):
                    valor = valor.strip()
                datos[nombre_grupo] = valor
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
        resultado: List[Dict[str, Any],] = []
        vistos = set()
        for valor in valores:
            identidad = (valor.get("_position",),valor.get("_end_position"),tuple(sorted((clave,str(dato)) for clave, dato in valor.items() if clave not in {"_position","_end_position"})))
            if identidad in vistos: continue
            vistos.add(identidad)
            resultado.append(valor)
        return resultado
    @staticmethod
    def _normalizar_nombre(nombre: str,) -> str:
        if not isinstance(nombre,str,):
            raise TypeError("El nombre del patrón debe ser un string.")
        nombre = nombre.strip()
        if not nombre: raise ValueError("El nombre del patrón no puede estar vacío.")
        return nombre