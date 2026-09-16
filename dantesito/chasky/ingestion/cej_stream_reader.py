# dantesito/chasky/ingestion/cej_stream_reader.py
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple, Union
import ijson

from dantesito.chasky.config.taxonomies import SectionEnum


class CEJStreamReader:
    """Lector iterativo de expedientes CEJ en streaming con memoria RAM O(1)."""

    def stream_and_flatten(
        self, json_path: Union[str, Path]
    ) -> Iterator[Tuple[SectionEnum, str]]:
        """Abre un archivo JSON de CEJ y emite tuplas (SectionEnum, texto_aplanado)

        sin cargar todo el documento en memoria RAM.

        :param json_path: Ruta del archivo JSON a procesar.
        :return: Generador de tuplas (seccion, texto_formateado).
        :raises FileNotFoundError: Si el archivo especificado no existe.
        :raises ValueError: Si el archivo JSON está corrupto o es inválido.
        """
        path = Path(json_path)
        if not path.is_file():
            raise FileNotFoundError(f"El archivo especificado no existe: {path}")

        try:
            with open(path, "rb") as file:
                # Iterar sobre las claves del objeto raíz
                parser = ijson.kvitems(file, "")
                for key, value in parser:
                    if key in ("expediente", "encabezado", "datos_generales"):
                        yield from self._process_encabezado(value)
                    elif key in ("partes", "sujetos_procesales", "partes_procesales"):
                        yield from self._process_partes(value)
                    elif key in ("resoluciones", "actuaciones", "historial", "proveidos"):
                        yield from self._process_resoluciones(value)
        except ijson.JSONError as exc:
            raise ValueError(f"El archivo JSON está corrupto o es inválido: {path}") from exc

    def _process_encabezado(
        self, data: Dict[str, Any]
    ) -> Iterator[Tuple[SectionEnum, str]]:
        """Procesa y aplana los datos del juzgado/proceso."""
        if not isinstance(data, dict):
            return

        lines: List[str] = []
        for key, val in data.items():
            if val is not None:
                label = key.replace("_", " ").upper()
                lines.append(f"{label}: {val}")

        if lines:
            text_block = "\n".join(lines)
            yield (SectionEnum.ENCABEZADO, text_block)

    def _process_partes(
        self, data: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> Iterator[Tuple[SectionEnum, str]]:
        """Procesa y aplana los sujetos procesales."""
        items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            items = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            items = [data]

        for item in items:
            rol = item.get("rol") or item.get("tipo_parte") or item.get("condicion") or "PARTE"
            nombre = item.get("nombre") or item.get("razon_social") or item.get("nombres") or ""
            doc_tipo = item.get("tipo_documento") or item.get("doc_tipo")
            doc_num = item.get("numero_documento") or item.get("doc_num")

            doc_info = f" | {doc_tipo}: {doc_num}" if doc_tipo and doc_num else ""
            formatted_text = f"ROL: {rol} | NOMBRE: {nombre}{doc_info}".strip()
            
            yield (SectionEnum.PARTES, formatted_text)

    def _process_resoluciones(
        self, data: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> Iterator[Tuple[SectionEnum, str]]:
        """Procesa cronológicamente el historial de actuaciones/proveídos."""
        items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            items = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            items = [data]

        for item in items:
            fecha = item.get("fecha") or item.get("fecha_resolucion") or item.get("fecha_ingreso") or "S/F"
            tipo = item.get("tipo") or item.get("tipo_proveido") or item.get("resolucion") or "RESOLUCION"
            sumilla = item.get("sumilla") or item.get("descripcion") or item.get("proveido") or ""

            formatted_text = f"FECHA: {fecha} | TIPO: {tipo} | SUMILLA: {sumilla}".strip()
            yield (SectionEnum.RESOLUCION, formatted_text)