# main.py
import logging
import sys
from pathlib import Path
from core.utils.cargar_clase_contrato_judicial import cargar_clase_contrato_judicial
import logging
logger = logging.getLogger(__name__)



RAIZ_PROYECTO = Path(__file__).parent
sys.path.append(str(RAIZ_PROYECTO))
sys.path.append(str(RAIZ_PROYECTO / "src"))

# Importamos tu pipeline optimizado por densidad NumPy
from core.pipeline import ETLDocumentPipeline

# Configuración limpia de logs en consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)






def main():
    # Parámetros e infraestructura de rutas fijas solicitadas
    ruta_pdf = Path(r"d:\betl\testpdf.pdf")
    ruta_contrato = Path(r"d:\betl\contrato.py")
    
    logger.info("=== INICIANDO ENTORNO DE PRUEBAS DE INFRAESTRUCTURA ETL ===")
    
    try:
        # 1. Extraer la Clase del Contrato (sin instanciar con paréntesis)
        contrato_clase = cargar_clase_contrato_judicial(ruta_contrato)
        
        # 2. Inicializar el Pipeline Persistente (Carga pesada de memoria en caché una única vez)
        pipeline = ETLDocumentPipeline(
            modelo_llm="qwen3:8b", 
            timeout_llm=250, 
            chunk_size=8000,
            ocr_lang="es"
        )
        
        # 3. Lanzar procesamiento automático (OCR Regional + Densidad Vectorizada por NumPy)
        logger.info(f"[Pipeline] Enviando documento {ruta_pdf.name} al motor analítico...")
        resultado_final = pipeline.ejecutar(
            pdf_path=ruta_pdf,
            contrato=contrato_clase,  # Pasamos la clase directamente al orquestador
            captcha_path=None,
            modo_pdf="auto"           # Automatización por análisis de píxeles activa
        )
        
        # 4. Impresión estructurada del DTO procesado
        if resultado_final:
            logger.info("¡Pipeline ETL procesado y consolidado con éxito!")
            print("\n================ DTO ESTRUCTURADO FINAL (FUSIÓN) ================")
            import json
            print(json.dumps(resultado_final, indent=4, ensure_ascii=False))
            print("=================================================================\n")
        else:
            logger.error("[Pipeline] El flujo terminó pero el MergerService o el OCR devolvieron vacío.")
            
    except Exception as e:
        logger.error(f"Error crítico abortivo en el punto de entrada principal: {e}", exc_info=True)


if __name__ == "__main__":
    main()
