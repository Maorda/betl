import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


class CaptchaExtractor:
    """
    Extractor especializado para CAPTCHAs.

    Utiliza ddddocr cuando está disponible.

    RESPONSABILIDAD
    ---------------
    Recibir una imagen CAPTCHA (bytes o ruta) y devolver el texto reconocido.
    """

    def __init__(self):
        """
        Inicializa ddddocr de manera opcional.
        """
        self.engine = None
        self._inicializar()

    # =====================================================================
    # INICIALIZACIÓN
    # =====================================================================

    def _inicializar(self) -> None:
        """
        Inicializa el motor ddddocr.
        """
        try:
            import ddddocr

            self.engine = ddddocr.DdddOcr(show_ad=False)
            logger.info("[CAPTCHA] Motor ddddocr inicializado correctamente.")

        except Exception as exc:
            logger.warning(
                f"[CAPTCHA] ddddocr no está disponible: {exc}"
            )
            self.engine = None

    # =====================================================================
    # DISPONIBILIDAD
    # =====================================================================

    @property
    def disponible(self) -> bool:
        """
        Indica si el motor CAPTCHA está disponible.
        """
        return self.engine is not None

    # =====================================================================
    # PUNTOS DE ENTRADA / EXTRAER
    # =====================================================================

    def resolver(self, image_input: Union[str, Path, bytes]) -> str:
        """
        Método de entrada flexible esperado por el orquestador.
        Acepta rutas de archivo (str/Path) o bytes directamente.
        """
        if not image_input:
            logger.warning("[CAPTCHA] Entrada vacía enviada a resolver().")
            return ""

        # Si recibe una ruta de archivo (str o Path)
        if isinstance(image_input, (str, Path)):
            path = Path(image_input)
            if not path.is_file():
                logger.error(f"[CAPTCHA] Archivo no encontrado: {path}")
                return ""
            try:
                with open(path, "rb") as f:
                    image_bytes = f.read()
                return self.extraer(image_bytes)
            except Exception as exc:
                logger.error(f"[CAPTCHA] Error leyendo archivo de captcha: {exc}")
                return ""

        # Si ya son bytes directamente
        elif isinstance(image_input, bytes):
            return self.extraer(image_input)

        else:
            logger.error(f"[CAPTCHA] Tipo de entrada no soportado: {type(image_input)}")
            return ""

    def extraer(self, image_bytes: bytes) -> str:
        """
        Reconoce el texto de un CAPTCHA a partir de sus bytes.
        """
        if not image_bytes:
            logger.warning("[CAPTCHA] Se recibió una imagen vacía.")
            return ""

        if not self.engine:
            logger.warning("[CAPTCHA] El motor ddddocr no está disponible.")
            return ""

        try:
            resultado = self.engine.classification(image_bytes)

            if resultado is None:
                return ""

            texto = str(resultado).strip().upper()

            logger.debug(
                f"[CAPTCHA] CAPTCHA procesado exitosamente. Longitud={len(texto)}"
            )

            return texto

        except Exception as exc:
            logger.error(f"[CAPTCHA] Error procesando CAPTCHA: {exc}")
            return ""