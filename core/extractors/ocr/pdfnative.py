# src/services/pdf_text_extractor.py

import logging

import pymupdf as fitz


logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """
    Extractor de texto nativo desde documentos PDF.

    Utiliza exclusivamente PyMuPDF.

    RESPONSABILIDAD
    ---------------

    Extraer la capa textual que ya existe dentro de un PDF.

    NO realiza:

        - OCR
        - PaddleOCR
        - CAPTCHA
        - Regex
        - LLM
        - minería de información
        - interpretación semántica
        - transformación a DTO
        - reglas de negocio

    Entrada:

        bytes del PDF

    Salida:

        str
    """

    def extraer(
        self,
        pdf_bytes: bytes
    ) -> str:
        """
        Extrae todo el texto nativo del PDF.

        Conserva separación entre páginas para evitar
        que el contenido de páginas diferentes se mezcle.
        """

        if not pdf_bytes:

            logger.warning(
                "[PDF TEXT] "
                "Se recibió un PDF vacío."
            )

            return ""

        paginas = []

        try:

            with fitz.open(
                stream=pdf_bytes,
                filetype="pdf"
            ) as documento:

                total_paginas = len(documento)

                logger.info(
                    "[PDF TEXT] "
                    f"Procesando {total_paginas} páginas."
                )

                for numero_pagina, pagina in enumerate(
                    documento,
                    start=1
                ):

                    try:

                        texto = (
                            pagina
                            .get_text()
                            .strip()
                        )

                    except Exception as exc:

                        logger.warning(
                            "[PDF TEXT] "
                            f"No fue posible extraer "
                            f"la página {numero_pagina}: "
                            f"{exc}"
                        )

                        texto = ""

                    paginas.append(
                        self._formatear_pagina(
                            numero_pagina,
                            texto
                        )
                    )

                    logger.debug(
                        "[PDF TEXT] "
                        f"Página {numero_pagina}: "
                        f"{len(texto)} caracteres."
                    )

                resultado = "\n\n".join(
                    paginas
                ).strip()

                logger.info(
                    "[PDF TEXT] "
                    f"Extracción completada. "
                    f"Caracteres: {len(resultado)}."
                )

                return resultado

        except Exception as exc:

            logger.exception(
                "[PDF TEXT] "
                "Error abriendo/procesando PDF."
            )

            return ""

    # =====================================================================
    # FORMATO
    # =====================================================================

    @staticmethod
    def _formatear_pagina(
        numero_pagina: int,
        texto: str
    ) -> str:
        """
        Agrega un delimitador genérico de página.

        No modifica semánticamente el contenido.
        """

        return (
            f"--- Página {numero_pagina} ---\n"
            f"{texto}"
        )