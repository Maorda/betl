import logging


logger = logging.getLogger(__name__)


class CaptchaExtractor:
    """
    Extractor especializado para CAPTCHAs.

    Utiliza ddddocr cuando está disponible.

    RESPONSABILIDAD
    ---------------

    Recibir una imagen CAPTCHA y devolver el texto
    reconocido.

    NO realiza:

        - OCR de documentos
        - lectura de PDF
        - PaddleOCR
        - Regex
        - LLM
        - minería de información
        - reglas de negocio
        - DTO mapping

    Entrada:

        bytes de imagen

    Salida:

        str
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

        La dependencia es opcional para que el framework
        pueda utilizarse aunque no necesite resolver CAPTCHAs.
        """

        try:

            import ddddocr

            self.engine = (
                ddddocr.DdddOcr(
                    show_ad=False
                )
            )

            logger.info(
                "[CAPTCHA] "
                "Motor ddddocr inicializado correctamente."
            )

        except Exception as exc:

            logger.warning(
                "[CAPTCHA] "
                "ddddocr no está disponible: "
                f"{exc}"
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
    # EXTRAER
    # =====================================================================

    def extraer(
        self,
        image_bytes: bytes
    ) -> str:
        """
        Reconoce el texto de un CAPTCHA.
        """

        if not image_bytes:

            logger.warning(
                "[CAPTCHA] "
                "Se recibió una imagen vacía."
            )

            return ""

        if not self.engine:

            logger.warning(
                "[CAPTCHA] "
                "El motor ddddocr no está disponible."
            )

            return ""

        try:

            resultado = (
                self.engine.classification(
                    image_bytes
                )
            )

            if resultado is None:

                return ""

            texto = (
                str(resultado)
                .strip()
                .upper()
            )

            logger.debug(
                "[CAPTCHA] "
                f"CAPTCHA procesado. "
                f"Longitud={len(texto)}"
            )

            return texto

        except Exception as exc:

            logger.error(
                "[CAPTCHA] "
                f"Error procesando CAPTCHA: "
                f"{exc}"
            )

            return ""