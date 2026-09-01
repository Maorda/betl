import re
from typing import Any, Dict, List, Optional, Type, Callable
from pydantic import BaseModel, Field, ConfigDict
from core.manipulate.strategy.regex import RegexPatternDefinition

class RegexObjective(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    pattern: Optional[str] = None
    flags: int = 0


class LLMTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    instruction: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None

class ExtractionField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    data_type: str = "string"
    description: Optional[str] = None
    required: bool = False
    regex: Optional[RegexObjective] = None
    llm: Optional[LLMTarget] = None

class MergeContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mapper_type: Optional[str] = None
    version: str = "1.0"
    fields: Dict[str, ExtractionField] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_field(self, field: ExtractionField) -> None:
        nombre = field.name.strip()
        if not nombre:
            raise ValueError("Nombre de campo vacío.")
        if nombre in self.fields:
            raise ValueError(f"El campo '{nombre}' ya existe en el contrato.")
        if nombre != field.name:
            field = field.model_copy(update={"name": nombre})
        self.fields[nombre] = field

    def get_regex_fields(self) -> Dict[str, ExtractionField]:
        return {k: v for k, v in self.fields.items() if v.regex and v.regex.enabled}

    def get_llm_fields(self) -> Dict[str, ExtractionField]:
        return {k: v for k, v in self.fields.items() if v.llm and v.llm.enabled}

    def validar(self) -> List[str]:
        errores: List[str] = []
        if not self.fields:
            return ["El ExtractionContract no contiene campos."]
        for nombre, field in self.fields.items():
            if field.regex and field.regex.enabled:
                if not field.regex.pattern or not field.regex.pattern.strip():
                    errores.append(f"Campo '{nombre}' tiene Regex activo pero patrón vacío.")
                else:
                    try:
                        re.compile(field.regex.pattern, field.regex.flags)
                    except Exception as e:
                        errores.append(f"Regex inválida en campo '{nombre}': {e}")
            if field.llm and field.llm.enabled:
                if not field.llm.instruction and not field.llm.structure:
                    errores.append(f"Campo '{nombre}' tiene LLM activo pero carece de instrucciones.")
        return errores

    def _procesar_subcoleccion_regex(self, texto: str, target_cls: Any) -> List[Dict[str, Any]]:
        patrones_sub: Dict[str, RegexPatternDefinition] = {}
        sub_campos_schema: Dict[str, Any] = {}

        for attr_name in dir(target_cls):
            attr = getattr(target_cls, attr_name)
            if hasattr(attr, "__extraction_field__"):
                f_data = attr.__extraction_field__
                sub_campos_schema[f_data["name"]] = f_data
                if f_data.get("regex"):
                    patrones_sub[f_data["name"]] = RegexPatternDefinition(
                        pattern=f_data["regex"].pattern,
                        flags=f_data["regex"].flags
                    )

        if not patrones_sub:
            return []

        evidencias_sub = self.regex_service.extraer_datos(texto=texto, patrones_temporales=patrones_sub)
        objetos_reconstruidos: List[Dict[str, Any]] = []
        max_elementos = max([len(l) for l in evidencias_sub.values()]) if evidencias_sub else 0

        for i in range(max_elementos):
            obj_instancia = {k: None for k in sub_campos_schema.keys()}

            for campo_sub, lista_evidencias in evidencias_sub.items():
                if i < len(lista_evidencias):
                    evidencia = lista_evidencias[i]
                    claves = [k for k in evidencia.keys() if not k.startswith("_")]
                    valor_crudo = evidencia[claves[0]] if claves else evidencia.get("value")

                    meta_campo = sub_campos_schema.get(campo_sub, {})
                    data_type = meta_campo.get("data_type", "string")

                    if data_type == "float" and not claves:
                        match_num = re.search(r"[0-9.,]+", str(valor_crudo))
                        if match_num:
                            valor_crudo = match_num.group(0)

                    obj_instancia[campo_sub] = self._cast_value_direct(valor_crudo, data_type, campo_sub)
                    obj_instancia[f"_{campo_sub}_meta"] = {
                        "_position": evidencia.get("_position"),
                        "_match": evidencia.get("_match")
                    }

            if any(v is not None for k, v in obj_instancia.items() if not k.startswith("_")):
                objetos_reconstruidos.append(obj_instancia)

        return objetos_reconstruidos