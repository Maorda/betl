# dantesito/chasky/consolidation/consolidator.py
import gc
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from dantesito.chasky.classification.cascade_factory import CascadeFactory
from dantesito.chasky.config.taxonomies import SectionEnum, SourceEnum

logger = logging.getLogger(__name__)


class ChaskyConsolidator:
    """
    Motor principal de consolidación y clasificación de legajos RAG.
    Ensambla el expediente intermedio y despacha la clasificación de 
    fragmentos PDF en lotes (batching) para erradicar los cuellos de botella de red.
    """

    def __init__(self) -> None:
        self._cascade_factory = CascadeFactory()

    def build_master_expediente(
        self,
        global_id: str,
        cej_json_path: str,
        remaju_pdf_path: str,
        sunarp_pdf_path: str,
        output_json_path: str,
    ) -> None:
        """
        Método de entrada principal inmutable.
        Construye el expediente físico intermedio y lo persiste directo en disco
        cumpliendo la política de Cero RAM.
        """
        logger.info(f"Construyendo expediente maestro intermedio para Global ID: {global_id}")

        master_data: Dict[str, Any] = {
            "global_id": global_id,
            "informacion_cej": self._ingest_cej(Path(cej_json_path)),
            "informacion_remaju": self._ingest_pdf_batch(Path(remaju_pdf_path), current_source_context=SourceEnum.REMAJU),
            "informacion_sunarp": self._ingest_pdf_batch(Path(sunarp_pdf_path), current_source_context=SourceEnum.SUNARP),
        }

        # Política de Cero RAM Local: Escribir directo al archivo temporal
        output_path = Path(output_json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Expediente intermedio guardado en disco duro: {output_json_path}")
        
        # Forzar limpieza profunda de memoria
        del master_data
        gc.collect()

    def _ingest_cej(self, json_path: Path) -> Dict[str, Any]:
        """
        Procesa archivos JSON de CEJ mediante flujos (ijson) para consumo de memoria mínimo.
        """
        if not json_path.exists():
            return {}

        logger.info(f"Ingestando datos CEJ desde: {json_path}")
        try:
            import ijson
            
            items = []
            with open(json_path, "rb") as f:
                parser = ijson.items(f, "item")
                for item in parser:
                    items.append(item)

            gc.collect()
            return {"file": json_path.name, "records": items}
        except Exception as err:
            logger.error(f"Error procesando JSON CEJ en {json_path}: {err}", exc_info=True)
            return {}

    def _ingest_pdf_batch(self, pdf_path: Path, current_source_context: Optional[SourceEnum] = None) -> Dict[str, Any]:
        """
        Procesa documentos PDF mediante extracción lineal y clasificación masiva (Batching)
        con la fábrica en cascada, evitando ráfagas HTTP individuales.
        """
        if not pdf_path.exists():
            return {}

        logger.info(f"Ingestando PDF por lotes (Batching) desde: {pdf_path}")
        try:
            lista_completa_chunks: List[str] = self._extract_pdf_chunks(pdf_path)
            if not lista_completa_chunks:
                return {"file": pdf_path.name, "sections": []}

            sections_found: List[Dict[str, Any]] = []

            # REEMPLAZO POR LOTE (BATCHING): Llamada masiva unificada
            resultados_batch = self._cascade_factory.process_chunks_batch(
                lista_completa_chunks,
                current_source=current_source_context,
            )

            # Mapear y rellenar la estructura del JSON intermedio
            for i, chunk in enumerate(lista_completa_chunks):
                detected_source, section = resultados_batch[i]

                if detected_source:
                    current_source_context = detected_source

                sections_found.append(
                    {
                        "chunk": chunk,
                        "source": current_source_context.value if current_source_context else None,
                        "section": section.value if section else None,
                    }
                )

            gc.collect()
            return {"file": pdf_path.name, "sections": sections_found}

        except Exception as err:
            logger.error(f"Error procesando PDF por lotes en {pdf_path}: {err}", exc_info=True)
            return {}

    def _extract_pdf_chunks(self, pdf_path: Path) -> List[str]:
        """
        Extrae fragmentos de texto del PDF utilizando Docling, extrayendo contenido 
        semántico en texto plano para mantener el uso de memoria bajo control (Cero RAM).
        """
        chunks: List[str] = []
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            doc_result = converter.convert(str(pdf_path))
            
            # Exportar a formato Markdown ligero y particionar por bloques de párrafos
            markdown_text = doc_result.document.export_to_markdown()
            
            if markdown_text:
                raw_chunks = markdown_text.split("\n\n")
                for chunk in raw_chunks:
                    clean_chunk = chunk.strip()
                    if clean_chunk:
                        chunks.append(clean_chunk)
            
            # Liberación estricta de objetos pesados de Docling
            del doc_result
            del converter
            gc.collect()
            
        except Exception as err:
            logger.warning(f"No se pudo extraer el texto de {pdf_path} vía Docling: {err}")
        return chunks