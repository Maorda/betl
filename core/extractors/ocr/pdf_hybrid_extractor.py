import logging
from typing import Any, List, Optional
import pymupdf as fitz
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class PDFHybridExtractor:
    """
    Extractor Híbrido y Agnóstico para documentos PDF.

    RESPONSABILIDAD:
    Convertir páginas de un PDF en texto plano de la manera más eficiente.
    
    ESTRATEGIA:
    1. Intenta extraer texto digital/nativo de la página (Rápido y 100% exacto).
    2. Si no encuentra texto (ej. página escaneada), aplica OCR con PaddleOCR.

    NO realiza:
    - Extracción Regex o LLM.
    - Reglas de negocio ni mapeos.
    """

    def __init__(self, dpi: int = 200, language: str = "es", min_native_chars: int = 50):
        self.dpi = dpi
        self.language = language
        self.min_native_chars = min_native_chars # Umbral para decidir si necesita OCR
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
        """Procesa el PDF completo combinando extracción nativa y OCR según se necesite."""
        if not pdf_bytes:
            logger.warning("[PDF Extractor] Se recibió un PDF vacío (0 bytes).")
            return ""

        paginas_texto: List[str] = []

        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as documento:
                total_paginas = len(documento)
                logger.info(f"[PDF Extractor] Procesando documento de {total_paginas} páginas.")

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
        """Decide inteligentemente si usa lectura nativa u OCR para la página actual."""
        
        # 1. Intento de lectura nativa (Digital)
        texto_nativo = pagina.get_text().strip()
        
        if len(texto_nativo) >= self.min_native_chars:
            logger.debug(f"[PDF Extractor] Página {num_pag}: Texto nativo detectado.")
            return texto_nativo

        # 2. Si no hay suficiente texto, asumimos que es una imagen escaneada
        logger.debug(f"[PDF Extractor] Página {num_pag}: Escaneada. Aplicando OCR...")
        if not self.disponible_ocr:
            logger.warning(f"[PDF Extractor] Página {num_pag} requiere OCR pero PaddleOCR no está disponible.")
            return texto_nativo # Retorna lo poco que haya encontrado

        return self._aplicar_ocr(pagina, num_pag)

    def _aplicar_ocr(self, pagina: fitz.Page, num_pag: int) -> str:
        """Renderiza la página a imagen y ejecuta el modelo OCR."""
        try:
            # Renderizado de la página a imagen (PixMap)
            pix = pagina.get_pixmap(dpi=self.dpi)
            img_bytes = pix.tobytes("png")

            # Conversión a formato OpenCV para PaddleOCR
            nparr = np.frombuffer(img_bytes, dtype=np.uint8)
            imagen_cv2 = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if imagen_cv2 is None:
                raise ValueError("cv2.imdecode retornó None")

            # Ejecución del OCR
            resultado = self.paddle_ocr.ocr(imagen_cv2)
            
            return self._parsear_salida_paddle(resultado)

        except Exception as exc:
            logger.error(f"[PDF Extractor] Falló el OCR en la página {num_pag}: {exc}")
            return ""

    @staticmethod
    def _parsear_salida_paddle(resultado_ocr: Any) -> str:
        """
        Extrae limpiamente el texto buscando recursivamente en la salida del OCR.
        Soporta la estructura clásica (tuplas) y la estructura moderna de PaddleX (diccionarios con 'rec_texts').
        """
        if not resultado_ocr:
            return ""

        lineas_extraidas = []

        def buscar_texto(elemento):
            # 1. Soporte para la nueva estructura (Diccionarios que contienen 'rec_texts')
            if isinstance(elemento, dict):
                if 'rec_texts' in elemento and isinstance(elemento['rec_texts'], list):
                    for texto in elemento['rec_texts']:
                        if isinstance(texto, str) and texto.strip():
                            lineas_extraidas.append(texto.strip())
                else:
                    # Explorar los valores del diccionario por si hay listas anidadas
                    for valor in elemento.values():
                        buscar_texto(valor)
            
            # 2. Soporte para listas (iteramos por cada elemento)
            elif isinstance(elemento, list):
                for item in elemento:
                    if item is not None:
                        buscar_texto(item)
            
            # 3. Soporte para la estructura clásica (Tuplas de (texto, confianza))
            elif isinstance(elemento, tuple) and len(elemento) == 2:
                texto = str(elemento[0]).strip()
                # Verificamos que el segundo elemento sea un número (la confianza)
                if texto and isinstance(elemento[1], (float, int)):
                    lineas_extraidas.append(texto)

        try:
            buscar_texto(resultado_ocr)
        except Exception as exc:
            logger.error(f"[PDF Extractor] Error parseando estructura OCR: {exc}")

        return "\n".join(lineas_extraidas)