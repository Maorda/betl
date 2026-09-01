import re
from typing import Any, Dict
from core.decorators.contract import contract
from core.decorators.strategy import campo, regex_strategy, llm_strategy


@contract(
    mapper_type="remate_judicial",
    version="2.0.0",
    metadata={
        "description": "Contrato de extracción para edictos de remate judicial",
        "mapeo_dto": {
            "expediente": {"numero": "numero_expediente"},
            "predio": {
                "partidaRegistral": "partida_electronica",
                "direccion": "direccion",
            },
        },
    },
)
class MiContratoRemate:
    """Contrato estructurado para la extracción de datos en edictos de remate judicial."""

    @regex_strategy(
        # Patrón estricto para el formato oficial de 25 caracteres del Poder Judicial de Perú
        pattern=r"\b([0-9]{5}-[0-9]{4}-[0-9]+-[0-9]{4}-[A-Z]{2}-[A-Z]{2}-[0-9]{2})\b",
        flags=re.IGNORECASE,
        enabled=True,
    )
    @llm_strategy(
        instruction=(
            "Extrae ÚNICAMENTE el número de expediente judicial estándar en su formato completo "
            "de 25 caracteres (Ejemplo: 00103-2014-0-1408-JR-CI-01). No incluyas etiquetas como "
            "'EXPEDIENTE:', saltos de línea, ni otros números de trámites como '11/2025'."
        ),
        enabled=True,
    )
    def numero_expediente(self) -> None:
        pass

    @campo(
        data_type="string",
        description="Número de registro del inmueble en Registros Públicos (Partida Electrónica, Ficha, Tomo).",
        required=False,
    )
    @regex_strategy(
        pattern=r"(?:Partida|P\.?E\.?|Ficha|Tomo)\s*(?:N[°º]?|\#)?\s*([0-9A-Z\-]{5,15})\b",
        flags=re.IGNORECASE,
        enabled=True,
    )
    @llm_strategy(
        instruction=(
            "Busca el número de partida electrónica, ficha o tomo registral en SUNARP "
            "(Ej: P21012001 o números de 8 dígitos)."
        ),
        enabled=True,
    )
    def partida_electronica(self) -> None:
        pass

    @campo(
        data_type="string",
        description="Ubicación física completa de la propiedad.",
        required=False,
    )
    @llm_strategy(
        instruction=(
            "Extrae la dirección exacta o ubicación del inmueble mencionada en el documento "
            "(calle, distrito, provincia, departamento)."
        ),
        enabled=True,
    )
    def direccion(self) -> None:
        pass