import inspect
from typing import Optional, Dict, Any, Type
from core.extractors.extraction_contract import ExtractionContract, ExtractionField

# ==========================================
# 2. Decorador de Clase (Ensamblador)
# ==========================================
def contract(
    mapper_type: Optional[str] = None,
    version: str = "1.0",
    metadata: Optional[Dict[str, Any]] = None,
):
    """Decorador de clase que inyecta la configuración del ExtractionContract en la clase misma."""
    def decorator(cls: Type) -> Type:
        # Inyectamos los metadatos directamente en la clase para que 
        # el método adaptar_a_dto pueda leer self._metadata
        cls._metadata = metadata or {}
        cls._metadata["mapper_type"] = mapper_type
        cls._metadata["version"] = version
        
        contract_inst = ExtractionContract(
            mapper_type=mapper_type, 
            version=version, 
            metadata=cls._metadata
        )
        cls_fields = {}

        for attr_name, attr in inspect.getmembers(cls):
            if hasattr(attr, "__extraction_field__"):
                f_data = attr.__extraction_field__
                cls_fields[f_data["name"]] = f_data
                contract_inst.add_field(
                    ExtractionField(
                        name=f_data["name"],
                        data_type=f_data["data_type"],
                        description=f_data["description"],
                        required=f_data["required"],
                        regex=f_data["regex"],
                        llm=f_data["llm"],
                    )
                )

        cls._metadata["__fields_raw__"] = cls_fields
        cls._extraction_contract = contract_inst # Guardamos la instancia del contrato internamente
        
        errores = contract_inst.validar()
        if errores:
            raise ValueError(f"Contrato declarativo '{cls.__name__}' inválido: {'; '.join(errores)}")

        # Retornamos la CLASE original, ahora enriquecida. 
        # Así, cuando MergerService haga `instancia = contrato()`, será una instancia de MiContratoRemate.
        return cls

    return decorator