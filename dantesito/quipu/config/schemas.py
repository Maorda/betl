from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CreateExpedienteDto(BaseModel):
    id_expediente_global: str = Field(
        ...,
        min_length=1,
        description="Código Único de Expediente Judicial",
    )
    informacion_cej: Dict[str, Any] = Field(
        ...,
        description="Estructura JSON mapeada de la fuente CEJ",
    )
    informacion_remaju: Dict[str, Any] = Field(
        ...,
        description="Estructura JSON extraída de la fuente REMAJU",
    )
    informacion_sunarp: Dict[str, Any] = Field(
        ...,
        description="Estructura JSON indexada de la fuente SUNARP",
    )
    drive_legajo_url: Optional[str] = Field(
        default=None,
        description="Enlace persistente del legajo cargado en Google Drive",
    )

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }