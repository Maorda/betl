# dantesito/quipu/consolidator/master_builder.py

import json
from datetime import datetime, timezone
from pathlib import Path

from dantesito.quipu.config.schemas import CreateExpedienteDto
from dantesito.quipu.config.settings import QuipuSettings


class MasterBuilder:
    def __init__(self, settings: QuipuSettings) -> None:
        self.settings = settings

    def assemble_and_save(
        self,
        global_id: str,
        data_cej: dict,
        data_remaju: dict,
        data_sunarp: dict,
    ) -> Path:
        payload = {
            "id_expediente_global": global_id,
            "informacion_cej": data_cej,
            "informacion_remaju": data_remaju,
            "informacion_sunarp": data_sunarp,
            "drive_legajo_url": None,
        }

        dto = CreateExpedienteDto(**payload)

        master_payload = dto.model_dump()
        master_payload["fecha_consolidacion"] = (
            datetime.now(timezone.utc).isoformat()
        )

        self.settings.output_json_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_file_path = (
            self.settings.output_json_dir / f"exp_{global_id}.json"
        )

        with output_file_path.open("w", encoding="utf-8") as json_file:
            json.dump(
                master_payload,
                json_file,
                ensure_ascii=False,
                indent=2,
            )

        return output_file_path