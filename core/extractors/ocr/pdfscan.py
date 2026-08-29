# src/services/pdf_ocr_extractor.py

import logging
from typing import Any, List, Optional

import pymupdf as fitz
import numpy as np
import cv2


logger = logging.getLogger(__name__)


class PDFOCRExtractor:
    """
    Extractor OCR especializado para documentos PDF escaneados.

    Utiliza:

        PyMuPDF
            ↓
        Renderizado de página
            ↓
        OpenCV
            ↓
        PaddleOCR
            ↓
        texto

    RESPONSABILIDAD
    ---------------

    Convertir páginas visuales de un PDF en texto.

    NO realiza:

        - extracción Regex
        - extracción LLM
        - interpretación semántica
        - mapeo DTO
        - reglas de negocio
        - CAPTCHA

    Entrada:

        bytes del PDF

    Salida:

        str
    """

    def __init__(
        self,
        dpi: int = 200,
        language: str = "es",
    ):
        """
        dpi:
            Resolución utilizada para renderizar las páginas.

        language:
            Idioma utilizado por PaddleOCR.
        """

        self.dpi = dpi
        self.language = language

        self.paddle_ocr = None

        self._inicializar_paddle()

    # =====================================================================
    # INICIALIZACIÓN
    # =====================================================================

    def _inicializar_paddle(self) -> None:
        """
        Inicializa PaddleOCR.

        La importación es diferida para evitar que la librería
        completa dependa obligatoriamente de PaddleOCR.
        """

        try:

            from paddleocr import PaddleOCR

            self.paddle_ocr = PaddleOCR(
                lang=self.language,
            )

            logger.info(
                "[PDF OCR] "
                "PaddleOCR inicializado correctamente. "
                f"Idioma={self.language}"
            )

        except Exception as exc:

            logger.warning(
                "[PDF OCR] "
                "PaddleOCR no está disponible: "
                f"{exc}"
            )

            self.paddle_ocr = None

    # =====================================================================
    # DISPONIBILIDAD
    # =====================================================================

    @property
    def disponible(self) -> bool:
        """
        Indica si PaddleOCR está disponible.
        """

        return self.paddle_ocr is not None

    # =====================================================================
    # PDF → OCR
    # =====================================================================

    def extraer(
        self,
        pdf_bytes: bytes
    ) -> str:
        """
        Procesa todas las páginas del PDF mediante OCR.
        """

        if not pdf_bytes:

            logger.warning(
                "[PDF OCR] "
                "Se recibió un PDF vacío."
            )

            return ""

        if not self.paddle_ocr:

            logger.warning(
                "[PDF OCR] "
                "PaddleOCR no está disponible."
            )

            return ""

        paginas: List[str] = []

        try:

            with fitz.open(
                stream=pdf_bytes,
                filetype="pdf"
            ) as documento:

                total_paginas = len(documento)

                logger.info(
                    "[PDF OCR] "
                    f"Procesando {total_paginas} páginas."
                )

                for numero_pagina, pagina in enumerate(
                    documento,
                    start=1
                ):

                    texto_pagina = (
                        self._procesar_pagina(
                            pagina,
                            numero_pagina
                        )
                    )

                    paginas.append(
                        self._formatear_pagina(
                            numero_pagina,
                            texto_pagina
                        )
                    )

                resultado = "\n\n".join(
                    paginas
                ).strip()

                logger.info(
                    "[PDF OCR] "
                    f"OCR completado. "
                    f"Caracteres: {len(resultado)}."
                )

                return resultado

        except Exception as exc:

            logger.exception(
                "[PDF OCR] "
                "Error procesando documento."
            )

            return ""

    # =====================================================================
    # PROCESAR PÁGINA
    # =====================================================================

    def _procesar_pagina(
        self,
        pagina: Any,
        numero_pagina: int
    ) -> str:
        """
        Renderiza una página PDF y ejecuta PaddleOCR.
        """

        try:

            pix = pagina.get_pixmap(
                dpi=self.dpi
            )

            img_bytes = pix.tobytes(
                "png"
            )

        except Exception as exc:

            logger.warning(
                "[PDF OCR] "
                f"No fue posible renderizar "
                f"la página {numero_pagina}: "
                f"{exc}"
            )

            return ""

        # -----------------------------------------------------------------
        # PNG → OpenCV
        # -----------------------------------------------------------------

        try:

            nparr = np.frombuffer(
                img_bytes,
                dtype=np.uint8
            )

            imagen = cv2.imdecode(
                nparr,
                cv2.IMREAD_COLOR
            )

        except Exception as exc:

            logger.warning(
                "[PDF OCR] "
                f"Error convirtiendo página "
                f"{numero_pagina} a imagen: "
                f"{exc}"
            )

            return ""

        if imagen is None:

            logger.warning(
                "[PDF OCR] "
                f"No fue posible decodificar "
                f"la imagen de la página "
                f"{numero_pagina}."
            )

            return ""

        # -----------------------------------------------------------------
        # PADDLE OCR
        # -----------------------------------------------------------------

        try:

            resultado = self.paddle_ocr.ocr(
                imagen,
                #cls=True
            )

        except Exception as exc:

            logger.warning(
                "[PDF OCR] "
                f"PaddleOCR falló en página "
                f"{numero_pagina}: "
                f"{exc}"
            )

            return ""

        texto = self._extraer_lineas(
            resultado
        )

        logger.debug(
            "[PDF OCR] "
            f"Página {numero_pagina}: "
            f"{len(texto)} caracteres."
        )

        return texto

    # =====================================================================
    # EXTRAER LÍNEAS
    # =====================================================================

    @staticmethod
    def _extraer_lineas(
        resultado: Any
    ) -> str:
        """
        Convierte la estructura devuelta por PaddleOCR
        en texto plano.

        Esta función no interpreta el contenido.
        """

        if not resultado:

            return ""

        lineas: List[str] = []

        try:

            paginas = resultado

            if not isinstance(
                paginas,
                list
            ):

                return ""

            for pagina in paginas:

                if not pagina:

                    continue

                if not isinstance(
                    pagina,
                    list
                ):

                    continue

                for linea in pagina:

                    texto = (
                        PDFOCRExtractor
                        ._obtener_texto_linea(
                            linea
                        )
                    )

                    if texto:

                        lineas.append(
                            texto
                        )

        except Exception as exc:

            logger.debug(
                "[PDF OCR] "
                f"Error interpretando resultado "
                f"de PaddleOCR: {exc}"
            )

        return "\n".join(
            lineas
        )

    # =====================================================================
    # OBTENER TEXTO DE LÍNEA
    # =====================================================================

    @staticmethod
    def _obtener_texto_linea(
        linea: Any
    ) -> Optional[str]:
        """
        Extrae únicamente el texto de una línea
        devuelta por PaddleOCR.

        Se mantiene defensivo porque la estructura
        puede variar entre versiones del motor.
        """

        try:

            if not isinstance(
                linea,
                (list, tuple)
            ):

                return None

            if len(linea) < 2:

                return None

            contenido = linea[1]

            if isinstance(
                contenido,
                (list, tuple)
            ) and contenido:

                texto = contenido[0]

                if texto is not None:

                    texto = str(
                        texto
                    ).strip()

                    return texto or None

            return None

        except Exception:

            return None

    # =====================================================================
    # FORMATO
    # =====================================================================

    @staticmethod
    def _formatear_pagina(
        numero_pagina: int,
        texto: str
    ) -> str:
        """
        Mantiene separación entre páginas.
        """

        return (
            f"--- Página {numero_pagina} ---\n"
            f"{texto}"
        )