import importlib.util
from typing import Any
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def cargar_clase_contrato_judicial(ruta_contrato: Path) -> Any:
    """
    Carga dinámicamente el archivo contrato.py desde el disco D: 
    y extrae la clase decorada lista para ser procesada por el Core.
    """
    if not ruta_contrato.exists():
        raise FileNotFoundError(f"No se encontró el archivo de contrato en: {ruta_contrato}")
    
    # Proceso oficial de importación dinámica en tiempo de ejecución
    spec = importlib.util.spec_from_file_location("contrato_modulo", str(ruta_contrato))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    
    # 1. Intento de carga directa por el nombre explícito definido
    if hasattr(modulo, "MiContratoRemate"):
        clase_contrato = getattr(modulo, "MiContratoRemate")
        logger.info("[Contrato] Clase 'MiContratoRemate' localizada e importada con éxito.")
        return clase_contrato
        
    # 2. Fallback de barrido reflexivo en caso de que cambies el nombre de la clase
    for atributo_nombre in dir(modulo):
        atributo = getattr(modulo, atributo_nombre)
        # Buscamos clases que tengan el atributo inyectado por tu decorador @contract
        if isinstance(atributo, type) and hasattr(atributo, "_extraction_contract"):
            logger.info(f"[Contrato] Detectada clase con contrato declarativo válido: '{atributo_nombre}'")
            return atributo
                
    raise AttributeError("No se localizó ninguna clase decorada con @contract en contrato.py")