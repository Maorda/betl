# dantesito/quipu/entrypoint/main_runner.py
import os
import re
import logging
import asyncio
from dotenv import load_dotenv
from dantesito.quipu.config.settings import QuipuSettings
from dantesito.quipu.workflows.pipeline_orchestrator import PipelineOrchestrator

logger = logging.getLogger("quipu_logger")

async def run_pipeline_entrypoint(remaju_path: str, sunarp_path: str, cej_path: str) -> bool:
    """Entrypoint CLI asíncrono que valida la nomenclatura de los archivos y despierta al orquestador."""
    try:
        # Forzar la lectura física directa del .env en el hilo asíncronico activo para romper la caché de Windows
        load_dotenv(dotenv_path=".env", override=True)

        remaju_name = os.path.basename(remaju_path)
        sunarp_name = os.path.basename(sunarp_path)

        # Expresiones regulares estrictas con captura de grupo para el número de expediente
        remaju_match = re.match(r"^remaju_(?P<expediente>.+)\.pdf$", remaju_name, re.IGNORECASE)
        sunarp_match = re.match(r"^sunarp_(?P<expediente>.+)\.pdf$", sunarp_name, re.IGNORECASE)

        if not remaju_match or not sunarp_match:
            logger.error("❌ Error de nomenclatura: Los archivos deben iniciar con 'remaju_' y 'sunarp_'.")
            return False

        global_id_remaju = remaju_match.group("expediente")
        global_id_sunarp = sunarp_match.group("expediente")

        # REGLA CRÍTICA DE SEGURIDAD: Evitar procesamiento cruzado de expedientes diferentes
        if global_id_remaju != global_id_sunarp:
            logger.error("❌ Error de consistencia: El expediente de REMAJU (%s) no coincide con SUNARP (%s).", global_id_remaju, global_id_sunarp)
            return False

        # Carga inmutable de configuraciones y orquestación lineal
        settings = QuipuSettings()
        orchestrator = PipelineOrchestrator(settings)
        
        # Despacho directo asíncrono
        success = await orchestrator.run_full_cycle(
            global_id=global_id_remaju,
            cej_path=cej_path,
            remaju_path=remaju_path,
            sunarp_path=sunarp_path
        )
        return success

    except Exception as exc:
        logger.error("❌ Error crítico en el runner de entrada: %s", exc)
        return False
