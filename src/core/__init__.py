# src/core/__init__.py
import logging

# Evita el mensaje "No handlers could be found for logger..." en sistemas cliente
logging.getLogger("core").addHandler(logging.NullHandler())
# 1. Importaciones de la Fase 1 (Extracción e interfaces OCR)
from .extractors.ocr.pdfnative import PDFTextExtractor
from .extractors.ocr.pdfscan import PDFOCRExtractor
from .extractors.ocr.pdf_hybrid_extractor import PDFHybridExtractor
from .extractors.ocr.captcha import CaptchaExtractor
from .extractors.ocr.orquestator_ocr import OCROrchestrator

# 2. Importaciones de la Fase 2 (Manipulación y Estrategias)
from .manipulate.strategy.regex import ManipulateRegexService
from .manipulate.strategy.llm import ManipulateLLMService
from .manipulate.orquestador_manipulacion import ManipulationOrchestrator

# 3. Importaciones de la Fase 3 (Transformación y Consolidación)
from .transformation.factory.mapper_factory import DtoTransformerUtils
from .transformation.merger import MergerService

# Agregamos la importación de la función directa
from .pipeline import ejecutar_pipeline_etl

# 4. Definición de la interfaz pública de tu librería
__all__ = [
    # Fase 1
    "PDFTextExtractor",
    "PDFOCRExtractor",
    "PDFHybridExtractor",
    "CaptchaExtractor",
    "OCROrchestrator",
    
    # Fase 2
    "ManipulateRegexService",
    "ManipulateLLMService",
    "ManipulationOrchestrator",
    
    # Fase 3
    "DtoTransformerUtils",
    "MergerService",
    # Nueva función de acceso rápido
    "ejecutar_pipeline_etl", 
]
