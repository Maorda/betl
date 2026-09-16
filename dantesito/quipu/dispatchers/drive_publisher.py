# dantesito/quipu/dispatchers/drive_publisher.py
import logging
import os
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from dantesito.quipu.config.settings import QuipuSettings

logger = logging.getLogger("quipu_logger")


class GoogleDrivePublisher:
    """
    Despachador oficial para la carga de legajos en formato PDF hacia Google Drive
    utilizando cuentas de servicio y transferencias resumibles para minimizar el uso de RAM.
    """

    def __init__(self, settings: QuipuSettings) -> None:
        self.settings = settings

        # 1. Recuperar los datos de la cuenta de servicio desde el entorno de Windows
        client_email = os.environ.get("GOOGLE_CLIENT_EMAIL", "").strip()
        private_key = os.environ.get("GOOGLE_PRIVATE_KEY", "").strip()
        project_id = os.environ.get("GOOGLE_PROJECT_ID", "").strip()
        token_uri = os.environ.get("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token").strip()

        # Tratamiento de escape para la clave privada de Google (reemplazar saltos de línea crudos)
        if "\\n" in private_key:
            private_key = private_key.replace("\\n", "\n")

        if not client_email or not private_key:
            raise ValueError(
                "🚨 ERROR CRÍTICO: GOOGLE_CLIENT_EMAIL o GOOGLE_PRIVATE_KEY no configurados en el .env"
            )

        # 2. Construir el diccionario de información de la cuenta de servicio en tiempo de ejecución
        info = {
            "type": "service_account",
            "project_id": project_id,
            "private_key": private_key,
            "client_email": client_email,
            "token_uri": token_uri,
        }

        # 3. Inicializar credenciales oficiales de Google Cloud
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        # 4. Construir el servicio inyectándole explícitamente las credenciales autenticadas
        self.service = build("drive", "v3", credentials=credentials)

    def upload_legajo(self, local_pdf_path: str) -> Optional[str]:
        try:
            if not os.path.exists(local_pdf_path):
                logger.error("El archivo local no existe en la ruta: %s", local_pdf_path)
                return None

            file_name = os.path.basename(local_pdf_path)

            file_metadata = {
                "name": file_name,
                "parents": [self.settings.GOOGLE_DRIVE_FOLDER_ID],
            }

            media = MediaFileUpload(
                local_pdf_path,
                mimetype="application/pdf",
                resumable=True,
            )

            file_response = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                )
                .execute()
            )

            file_id = file_response.get("id")
            if not file_id:
                logger.error("No se pudo recuperar el ID del archivo creado en Google Drive.")
                return None

            logger.info("Legajo subido con éxito a Google Drive. File ID: %s", file_id)
            return f"https://drive.google.com/file/d/{file_id}/view"

        except Exception:
            logger.exception(
                "Error durante la subida del legajo PDF a Google Drive: %s",
                local_pdf_path,
            )
            return None
