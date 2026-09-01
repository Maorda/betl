from typing import Any, Callable, Dict


def _get_or_create_meta(func: Callable) -> Dict[str, Any]:
    """Obtiene o inicializa el diccionario metadata de extracción en la función."""
    if not hasattr(func, "__extraction_field__"):
        func.__extraction_field__ = {
            "name": func.__name__,
            "data_type": "string",
            "description": None,
            "required": False,
            "regex": None,
            "llm": None,
        }
    return func.__extraction_field__