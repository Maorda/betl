import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RegexObjective(BaseModel):
    """Objetivo runtime de extracción mediante Regex. Solo describe QUÉ ejecutar."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    pattern: Optional[str] = None
    flags: int = 0


class LLMTarget(BaseModel):
    """Objetivo runtime de extracción mediante LLM. Solo describe instrucción y estructura."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    instruction: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None


class ExtractionField(BaseModel):
    """Representa un campo objetivo de información a extraer."""
    model_config = ConfigDict(extra="forbid")

    name: str
    data_type: str = "string"
    description: Optional[str] = None
    required: bool = False
    regex: Optional[RegexObjective] = None
    llm: Optional[LLMTarget] = None


class ExtractionContract(BaseModel):
    """Contrato runtime que consolida los campos y estrategias de extracción."""
    model_config = ConfigDict(extra="forbid")

    mapper_type: Optional[str] = None
    version: str = "1.0"
    fields: Dict[str, ExtractionField] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_field(self, field: ExtractionField) -> None:
        """Agrega un campo al contrato normalizando su nombre."""
        if not isinstance(field, ExtractionField):
            raise TypeError("field debe ser una instancia de ExtractionField.")

        nombre = field.name.strip()
        if not nombre:
            raise ValueError("El nombre del campo no puede estar vacío.")

        if nombre in self.fields:
            raise ValueError(f"El campo '{nombre}' ya existe en el ExtractionContract.")

        if nombre != field.name:
            field = field.model_copy(update={"name": nombre})

        self.fields[nombre] = field

    def get_field(self, nombre: str) -> Optional[ExtractionField]:
        return self.fields.get(nombre)

    def has_field(self, nombre: str) -> bool:
        return nombre in self.fields

    def count_fields(self) -> int:
        return len(self.fields)

    def get_regex_fields(self) -> Dict[str, ExtractionField]:
        """Campos con estrategia Regex habilitada."""
        return {
            nombre: field
            for nombre, field in self.fields.items()
            if field.regex and field.regex.enabled
        }

    def get_llm_fields(self) -> Dict[str, ExtractionField]:
        """Campos con estrategia LLM habilitada."""
        return {
            nombre: field
            for nombre, field in self.fields.items()
            if field.llm and field.llm.enabled
        }

    def validar(self) -> List[str]:
        """Valida la consistencia interna y la validez sintáctica de las reglas."""
        errores: List[str] = []

        if not self.fields:
            return ["El ExtractionContract no contiene campos."]

        for nombre, field in self.fields.items():
            nombre_limpio = nombre.strip()
            
            if not nombre_limpio:
                errores.append("Existe un campo con nombre vacío en las llaves del contrato.")

            if not field.name or not field.name.strip():
                errores.append(f"El campo '{nombre}' tiene un atributo 'name' vacío.")
            elif field.name.strip() != nombre_limpio:
                errores.append(f"El nombre interno '{field.name}' no coincide con su clave '{nombre}'.")

            if not field.data_type or not field.data_type.strip():
                errores.append(f"El campo '{nombre}' no tiene especificado 'data_type'.")

            # Validaciones para Regex
            if field.regex and field.regex.enabled:
                if not field.regex.pattern or not field.regex.pattern.strip():
                    errores.append(f"El campo '{nombre}' tiene Regex habilitado pero 'pattern' está vacío.")
                else:
                    # Intento de compilación real para asegurar sintaxis
                    try:
                        re.compile(field.regex.pattern, field.regex.flags)
                    except (re.error, ValueError, TypeError) as exc:
                        errores.append(f"El campo '{nombre}' posee una Regex inválida ({field.regex.pattern}): {exc}")

            # Validaciones para LLM
            if field.llm and field.llm.enabled:
                if not field.llm.instruction and not field.llm.structure:
                    errores.append(
                        f"El campo '{nombre}' tiene LLM habilitado pero carece de 'instruction' o 'structure'."
                    )

        return errores