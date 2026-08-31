import re
from typing import Any, Callable, Dict, Optional
from core.helpers.get_or_create_meta import _get_or_create_meta
from core.extractors.extraction_contract import RegexObjective, LLMTarget


# ==========================================
# 3. Decoradores (Construcción del Contrato)
# ==========================================
def regex_strategy(pattern: str, flags: int = re.IGNORECASE, enabled: bool = True):
    """Decorador para inyectar una regla de extracción basada en Regex."""
    def decorator(func: Callable) -> Callable:
        meta = _get_or_create_meta(func)
        meta["regex"] = RegexObjective(enabled=enabled, pattern=pattern, flags=flags)
        return func
    return decorator

def llm_strategy(
    instruction: Optional[str] = None,
    structure: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
):
    """Decorador para inyectar una instrucción o estructura objetivo para un LLM."""
    def decorator(func: Callable) -> Callable:
        meta = _get_or_create_meta(func)
        meta["llm"] = LLMTarget(enabled=enabled, instruction=instruction, structure=structure)
        return func
    return decorator

def campo(data_type: str = "string", description: Optional[str] = None, required: bool = False):
    """Decorador para registrar propiedades base descriptivas del campo."""
    def decorator(func: Callable) -> Callable:
        meta = _get_or_create_meta(func)
        meta.update({
            "data_type": data_type,
            "description": description,
            "required": required,
        })
        return func
    return decorator