# dantesito/quipu/workflows/extraction_workflow.py
import json
import logging
from pathlib import Path
from dantesito.chasky.consolidation.consolidator import ChaskyConsolidator
from dantesito.quipu.config.settings import QuipuSettings

logger = logging.getLogger("quipu_logger")


class ExtractionWorkflow:
    def __init__(self, settings: QuipuSettings) -> None:
        self.settings = settings

    def execute(
        self,
        cej_path: str,
        remaju_path: str,
        sunarp_path: str,
    ) -> tuple[str, str, str]:
        return cej_path, remaju_path, sunarp_path
