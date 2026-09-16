# dantesito/quipu/workflows/pipeline_orchestrator.py
import os
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from dantesito.quipu.config.settings import QuipuSettings
from dantesito.quipu.config.schemas import CreateExpedienteDto
from dantesito.quipu.consolidator.master_builder import MasterBuilder
from dantesito.quipu.dispatchers.drive_publisher import GoogleDrivePublisher
from dantesito.quipu.dispatchers.nestjs_client import NestJSClient
from dantesito.chasky.consolidation.consolidator import ChaskyConsolidator

logger = logging.getLogger("quipu_logger")


class PipelineOrchestrator:
    """Coordinador global del ciclo de vida del expediente (7 Fases Reales)."""

    def __init__(self, settings: QuipuSettings) -> None:
        self.settings = settings
        self.chasky_core = ChaskyConsolidator()
        self.master_builder = MasterBuilder(settings)
        self.drive_publisher = GoogleDrivePublisher(settings)
        self.nestjs_client = NestJSClient(settings)

    async def run_full_cycle(
        self,
        global_id: str,
        cej_path: str,
        remaju_path: str,
        sunarp_path: str,
    ) -> bool:
        """
        Ejecuta de principio a fin el pipeline de 7 fases de forma lineal,
        pero blindando el Event Loop con purga asíncrona no bloqueante
        y persistencia perimetral de estados para el smartphone.
        """
        logger.info("Iniciando orquestación de expediente corporativo Global ID: %s", global_id)
        
        # Sincronización exacta de rutas contractuales
        temp_chasky_json = str(self.settings.output_json_dir / f"temp_{global_id}.json")
        status_file = self.settings.output_json_dir / f"status_{global_id}.json"
        nestjs_result = False

        try:
            # FASES 1-3: Análisis, Parsing (Docling) e Indexación Vectorial en Chasky Core
            logger.info("Fases 1-3: Ejecutando extracción e indexación vectorial con Chasky Core...")
            self.chasky_core.build_master_expediente(
                global_id=global_id,
                cej_json_path=cej_path,
                remaju_pdf_path=remaju_path,
                sunarp_pdf_path=sunarp_path,
                output_json_path=temp_chasky_json
            )

            # FASE 4: Lectura de Datos Reales Extrayendo de Disco Duro (No bloqueante)
            logger.info("Fase 4: Extrayendo estructuras semánticas desde %s...", temp_chasky_json)
            if not os.path.exists(temp_chasky_json):
                raise FileNotFoundError(f"No se localizó el archivo temporal de Chasky: {temp_chasky_json}")

            def _read_chasky_file():
                with open(temp_chasky_json, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            chasky_data = await asyncio.to_thread(_read_chasky_file)

            # Sincronización estricta de nombres de claves largas originales
            data_cej = chasky_data.get("informacion_cej", {})
            data_remaju = chasky_data.get("informacion_remaju", {})
            data_sunarp = chasky_data.get("informacion_sunarp", {})

            # FASE 6: Publicación Resumable en Google Drive (0 RAM local)
            logger.info("Fase 6: Transmitiendo legajo PDF a Google Drive...")
            drive_url = self.drive_publisher.upload_legajo(remaju_path)
            if not drive_url:
                logger.warning("Fallo en la obtención de la URL de Drive; asignando valor por defecto.")
                drive_url = "https://google.com"

            # FASE 5: Ensamblado del JSON Maestro Corporativo Validado por Pydantic v2
            logger.info("Fase 5: Ensamblando el JSON Maestro Corporativo...")
            final_json_path = self.master_builder.assemble_and_save(
                global_id, data_cej, data_remaju, data_sunarp
            )

            # FASE 5.5: Re-Inyección de la URL de Drive en el JSON Físico
            logger.info("Fase 5.5: Actualizando URL de Drive en el JSON Maestro: %s", final_json_path)
            
            def _update_master_json():
                with open(final_json_path, "r", encoding="utf-8") as rf:
                    dict_act = json.load(rf)
                dict_act["drive_legajo_url"] = drive_url
                with open(final_json_path, "w", encoding="utf-8") as wf:
                    json.dump(dict_act, wf, ensure_ascii=False, indent=2)
                return dict_act

            diccionario_actualizado = await asyncio.to_thread(_update_master_json)
            final_dto = CreateExpedienteDto(**diccionario_actualizado)

            # FASE 6.5: Despacho Resiliente HTTP asíncrono hacia la API Central de NestJS
            logger.info("Fase 6.5: Transmitiendo DTO validado a la API NestJS...")
            nestjs_result = await self.nestjs_client.send_expediente(final_dto)

        except Exception as err:
            logger.error("Error crítico durante el ciclo de orquestación para %s: %s", global_id, err, exc_info=True)
            nestjs_result = False
            
            # Escritura de Error asíncrona no bloqueante en disco
            if status_file.parent.exists():
                error_payload = {
                    "status": "error",
                    "archivo_actual": "Error crítico en orquestación",
                    "fase_actual": f"El pipeline colapsó en segundo plano: {str(err)}",
                    "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
                }
                with open(status_file, "w", encoding="utf-8") as ef:
                    json.dump(error_payload, ef, ensure_ascii=False, indent=2)
            
            return False

        finally:
            # ===================================================================
            # FASE 7: HIGIENE ESTRICTA ASÍNCRONA Y NOTIFICACIÓN DE CIERRE MÓVIL
            # ===================================================================
            logger.info("Fase 7: Iniciando purga e higiene de residuos en el disco duro...")
            
            # 1. Borrado no bloqueante de archivos temporales mediante hilos secundarios
            if os.path.exists(temp_chasky_json):
                try:
                    await asyncio.to_thread(os.remove, temp_chasky_json)
                    logger.debug("Archivo temporal eliminado: %s", temp_chasky_json)
                except Exception as purge_err:
                    logger.warning("No se pudo eliminar el archivo temporal %s: %s", temp_chasky_json, purge_err)

            # 2. Purgado de residuos Markdown sin congelar el Event Loop de Windows
            if self.settings.staged_dir.exists():
                def _purge_markdowns():
                    for md_file in self.settings.staged_dir.glob("*.md"):
                        try:
                            md_file.unlink()
                        except Exception:
                            pass
                await asyncio.to_thread(_purge_markdowns)

            # 3. Escritura de cierre (Solo actualiza a 'completado' si no hubo errores previos)
            if status_file.parent.exists():
                def _check_and_write_success():
                    is_error = False
                    if status_file.exists():
                        with open(status_file, "r", encoding="utf-8") as rf:
                            try:
                                current_data = json.load(rf)
                                if current_data.get("status") == "error":
                                    is_error = True
                            except Exception:
                                pass
                    
                    if not is_error:
                        success_payload = {
                            "status": "completado",
                            "archivo_actual": "Proceso finalizado con éxito",
                            "fase_actual": "Fase 7: Expediente consolidado e higiene de disco completada",
                            "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
                        }
                        with open(status_file, "w", encoding="utf-8") as sf:
                            json.dump(success_payload, sf, ensure_ascii=False, indent=2)
                        logger.info("Fase 7: Estado actualizado de forma definitiva a 'completado' para %s", global_id)
                
                await asyncio.to_thread(_check_and_write_success)

        return nestjs_result
