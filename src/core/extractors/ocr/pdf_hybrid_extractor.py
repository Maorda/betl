import logging
from typing import Any, List, Optional
import pymupdf as fitz
import numpy as np
import cv2
from core.extractors.ocr.detectar_zonas_ocr_en_pdf_hibrido import detectar_zonas_ocr_en_pdf_hibrido

logger = logging.getLogger(__name__)


class PDFHybridExtractor:
    """
    Extractor Híbrido y Agnóstico para documentos PDF.

    RESPONSABILIDAD:
    Convertir páginas de un PDF en texto plano de la manera más eficiente.
    
    ESTRATEGIA REFACTORIZADA (Verdadero Híbrido):
    1. Extrae el texto digital/nativo disponible en la página.
    2. Utiliza 'detectar_zonas_ocr_en_pdf_hibrido' para localizar recuadros con imágenes o firmas densas.
    3. Si existen zonas densas y PaddleOCR está disponible, recorta inteligentemente 
       dichas coordenadas y les aplica OCR, integrando este texto al resultado final.

    NO realiza:
    - Extracción Regex o LLM.
    - Reglas de negocio ni mapeos.
    """

    def __init__(self, dpi: int = 200, language: str = "es", min_native_chars: int = 50):
        self.dpi = dpi
        self.language = language
        self.min_native_chars = min_native_chars  # Mantenido por compatibilidad de firmas
        self.paddle_ocr = None
        self._inicializar_paddle()

    def _inicializar_paddle(self) -> None:
        """Inicializa PaddleOCR de forma diferida (lazy load)."""
        try:
            from paddleocr import PaddleOCR
            # use_angle_cls endereza el texto si la página fue escaneada chueca
            self.paddle_ocr = PaddleOCR(
                use_angle_cls=True, 
                lang=self.language,
                enable_mkldnn=False  # Desactiva la aceleración que causa el crash en Windows
            )
            logger.info(f"[PDF Extractor] PaddleOCR inicializado. Idioma={self.language}")
        except ImportError:
            logger.warning("[PDF Extractor] PaddleOCR no instalado. Solo se leerá texto nativo.")
            self.paddle_ocr = None
        except Exception as exc:
            logger.error(f"[PDF Extractor] Error al cargar PaddleOCR: {exc}")
            self.paddle_ocr = None

    @property
    def disponible_ocr(self) -> bool:
        return self.paddle_ocr is not None

    def extraer(self, pdf_bytes: bytes) -> str:
        """Procesa el PDF completo combinando extracción nativa y OCR focalizado por zonas."""
        if not pdf_bytes:
            logger.warning("[PDF Extractor] Se recibió un PDF vacío (0 bytes).")
            return ""

        paginas_texto: List[str] = []

        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as documento:
                total_paginas = len(documento)
                logger.info(f"[PDF Extractor] Procesando documento híbrido de {total_paginas} páginas.")

                for num_pag, pagina in enumerate(documento, start=1):
                    texto_pagina = self._procesar_pagina(pagina, num_pag)
                    if texto_pagina:
                        paginas_texto.append(f"--- Página {num_pag} ---\n{texto_pagina}")

            resultado = "\n\n".join(paginas_texto).strip()
            logger.info(f"[PDF Extractor] Extracción completada. Caracteres totales: {len(resultado)}.")
            return resultado

        except Exception as exc:
            logger.exception(f"[PDF Extractor] Error crítico procesando documento: {exc}")
            return ""

    def _procesar_pagina(self, pagina: fitz.Page, num_pag: int) -> str:
        """Fusiona texto nativo y OCR quirúrgico basado en análisis de densidad de zonas."""
        bloques_texto_pagina = []

        # 1. Extraer texto nativo existente en la página
        texto_nativo = pagina.get_text().strip()
        if texto_nativo:
            logger.debug(f"[PDF Extractor] Página {num_pag}: Texto nativo recuperado ({len(texto_nativo)} caracteres).")
            bloques_texto_pagina.append(texto_nativo)

        # 2. Buscar zonas densas de imagen (firmas, sellos, textos escaneados)
        try:
            # Reutilizamos los bytes de la página o pasamos el objeto si la función lo soporta.
            # Como la función nativa suele pedir bytes de un documento, pasamos un fragmento de bytes
            doc_temporal = fitz.open()
            doc_temporal.insert_pdf(pagina.parent, from_page=pagina.number, to_page=pagina.number)
            bytes_monopagina = doc_temporal.tobytes()
            doc_temporal.close()

            zonas_escaneadas = detectar_zonas_ocr_en_pdf_hibrido(bytes_monopagina)
        except Exception as exc:
            logger.error(f"[PDF Extractor] Error al detectar zonas en Página {num_pag}: {exc}")
            zonas_escaneadas = []

        # 3. Aplicar OCR quirúrgico únicamente si hay zonas detectadas y OCR habilitado
        if zonas_escaneadas:
            if not self.disponible_ocr:
                logger.warning(f"[PDF Extractor] Se detectaron {len(zonas_escaneadas)} zonas en Pág {num_pag} pero PaddleOCR no está disponible.")
            else:
                logger.info(f"[PDF Extractor] Página {num_pag}: Procesando {len(zonas_escaneadas)} zonas escaneadas/gráficas mediante OCR.")
                for idx, zona in enumerate(zonas_escaneadas, start=1):
                    coordenadas = zona.get("coordenadas")  # Estructura esperada: (x0, y0, x1, y1)
                    if coordenadas:
                        texto_ocr_zona = self._aplicar_ocr_en_zona(pagina, coordenadas, num_pag, idx)
                        if texto_ocr_zona:
                            bloques_texto_pagina.append(texto_ocr_zona)

        return "\n".join(bloques_texto_pagina).strip()

    def _aplicar_ocr_en_zona(self, pagina: fitz.Page, coordenadas: tuple, num_pag: int, idx_zona: int) -> str:
        """Renderiza únicamente la sub-región de la página (clip) y ejecuta el OCR."""
        try:
            # Usamos el parámetro 'clip' para renderizar solo el área densa detectada
            # Multiplicamos por la matriz del DPI para no perder nitidez en el recorte
            zoom = self.dpi / 72  # 72 es el DPI base de PDF
            matriz = fitz.Matrix(zoom, zoom)
            
            pix = pagina.get_pixmap(matrix=matriz, clip=coordenadas)
            img_bytes = pix.tobytes("png")

            # Conversión a formato OpenCV para PaddleOCR
            nparr = np.frombuffer(img_bytes, dtype=np.uint8)
            imagen_cv2 = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if imagen_cv2 is None:
                raise ValueError("cv2.imdecode retornó None al procesar el recorte.")

            # Ejecución del OCR exclusivo en el recuadro recortado
            resultado = self.paddle_ocr.ocr(imagen_cv2)
            texto_zona = self._parsear_salida_paddle(resultado)
            
            if texto_zona.strip():
                logger.debug(f"[PDF Extractor] Zona {idx_zona} de Pág {num_pag} procesada con éxito.")
                return texto_zona.strip()
            
            return ""

        except Exception as exc:
            logger.error(f"[PDF Extractor] Falló el OCR regional en Pág {num_pag}, Zona {idx_zona}: {exc}")
            return ""

    @staticmethod
    def _parsear_salida_paddle(resultado_ocr: Any) -> str:
        """ Extrae limpiamente el texto buscando recursivamente en la salida del OCR. """
        if not resultado_ocr:
            return ""

        lineas_extraidas = []

        def buscar_texto(elemento):
            if isinstance(elemento, dict):
                if 'rec_texts' in elemento and isinstance(elemento['rec_texts'], list):
                    for texto in elemento['rec_texts']:
                        if isinstance(texto, str) and texto.strip():
                            lineas_extraidas.append(texto.strip())
                else:
                    for valor in elemento.values():
                        buscar_texto(valor)
            
            elif isinstance(elemento, list):
                for item in elemento:
                    if item is not None:
                        buscar_texto(item)
            
            elif isinstance(elemento, tuple) and len(elemento) == 2:
                texto = str(elemento[0]).strip()
                if texto and isinstance(elemento[1], (float, int)):
                    lineas_extraidas.append(texto)

        try:
            buscar_texto(resultado_ocr)
        except Exception as exc:
            logger.error(f"[PDF Extractor] Error parseando estructura OCR: {exc}")

        return "\n".join(lineas_extraidas)
