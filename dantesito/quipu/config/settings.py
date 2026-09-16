# dantesito/quipu/config/settings.py
import logging
import os
from pathlib import Path


def setup_physical_logging(data_dir_str: str = "./data") -> None:
    """Autogenera la carpeta de persistencia y configura el escritor de logs físicos en disco duro."""
    log_folder = Path(data_dir_str)
    log_folder.mkdir(parents=True, exist_ok=True)
    log_file_path = log_folder / "quipu.log"

    # Configurar el formateador industrial y enlazar el FileHandler y el StreamHandler simultáneamente
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file_path, encoding="utf-8"),
            logging.StreamHandler(),  # Mantiene la impresión visual en la pantalla negra
        ],
        force=True,  # Rompe cualquier caché previa de logging de librerías de terceros
    )


class QuipuSettings:
    """Clase inmutable de configuraciones corporativas mediante propiedades de solo lectura."""

    def __init__(self, data_dir: str | None = None) -> None:
        try:
            self._nestjs_api_url = os.environ["NESTJS_API_URL"].strip()
        except KeyError as exc:
            raise ValueError("La variable de entorno NESTJS_API_URL es obligatoria.") from exc

        try:
            self._google_drive_folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"].strip()
        except KeyError as exc:
            raise ValueError("La variable de entorno GOOGLE_DRIVE_FOLDER_ID es obligatoria.") from exc

        try:
            self._gemini_api_key = os.environ["GEMINI_API_KEY"].strip()
        except KeyError as exc:
            raise ValueError("La variable de entorno GEMINI_API_KEY es obligatoria.") from exc

        self._data_dir = data_dir or os.getenv("DATA_DIR", "./data").strip()

        # Inicialización del chasis de auditoría de logs físicos en disco duro
        setup_physical_logging(self._data_dir)

    # Propiedades públicas de solo lectura (Simulación estricta de frozen=True)
    @property
    def NESTJS_API_URL(self) -> str:
        return self._nestjs_api_url
    
    @property
    def GOOGLE_DRIVE_FOLDER_ID(self) -> str:
        return self._google_drive_folder_id
    
    @property
    def GEMINI_API_KEY(self) -> str:
        return self._gemini_api_key
    
    @property
    def DATA_DIR(self) -> str:
        return self._data_dir

    # 📂 PROPIEDADES INMUTABLES DE RUTAS DEL SISTEMA DE ARCHIVOS (MANTENER INTACTAS)
    @property
    def raw_pdf_dir(self) -> Path:
        path = Path(self.DATA_DIR) / "01_raw" / "pdfs_mixtos"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    @property
    def raw_cej_dir(self) -> Path:
        path = Path(self.DATA_DIR) / "01_raw" / "cej_nativos"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    @property
    def staged_dir(self) -> Path:
        path = Path(self.DATA_DIR) / "02_staged"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    @property
    def vector_db_dir(self) -> Path:
        path = Path(self.DATA_DIR) / "03_vector_db"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    @property
    def output_json_dir(self) -> Path:
        path = Path(self.DATA_DIR) / "04_output" / "json_maestro"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()
