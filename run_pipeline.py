# run_pipeline.py
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Forzar la inclusión de la raíz en las rutas de Python de forma limpia y agnóstica
BASE_DIR: Path = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from dantesito.chasky.consolidation.consolidator import ChaskyConsolidator

INPUTS_DIR: Path = BASE_DIR / "data" / "inputs"
OUTPUTS_DIR: Path = BASE_DIR / "data" / "outputs"

CEJ_PATH: Path = INPUTS_DIR / "cej_muestra.json"
#REMAJU_PATH: Path = INPUTS_DIR / "remaju_muestra.pdf"
REMAJU_PATH: Path = BASE_DIR / "tests" / "pdftest.pdf"
SUNARP_PATH: Path = INPUTS_DIR / "sunarp_muestra.pdf"
OUTPUT_PATH: Path = OUTPUTS_DIR / "json_maestro_final.json"

GLOBAL_ID: str = "01234-2026-0-1801-JR-CI-01"

# Estructura binaria mínima válida de un PDF de texto simulado para Docling.
# Contiene las palabras registrales clave que gatillan de forma exitosa la Capa 1 (Regex CPU).
MINIMAL_PDF: bytes = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
    b"4 0 obj\n<< /Length 60 >>\nstream\n"
    b"BT /F1 12 Tf 70 700 Td (EXPEDIENTE 01234-2026 HIPOTECA EMBARGO CARGAS LINDEROS ZONA REGISTRAL PARTIDA 12345678) Tj ET\n"
    b"endstream\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
)

def prepare_environment() -> None:
    """Genera carpetas y archivos físicos reales de prueba para alimentar el motor."""
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # Mock de datos JSON estructurados para la fuente CEJ
    cej_data = {
        "expediente": GLOBAL_ID,
        "juzgado": {
            "especialidad": "Civil Comercial", 
            "organo_jurisdiccional": "7mo Juzgado Civil", 
            "distrito_judicial": "Lima"
        },
        "sujetos_procesales": {
            "demandante": "Banco de Crédito del Perú", 
            "demandado": "Constructora Inmobiliaria SAC"
        },
        "historial": [
            {"fecha": "2026-01-15", "hito": "Demanda admitida a trámite."},
            {"fecha": "2026-06-10", "hito": "Se ordena el remate público del inmueble."}
        ]
    }
    
    # Escritura física directa y limpia a disco duro
    CEJ_PATH.write_text(json.dumps(cej_data, ensure_ascii=False, indent=2), encoding="utf-8")
    #REMAJU_PATH.write_bytes(MINIMAL_PDF)
    SUNARP_PATH.write_bytes(MINIMAL_PDF)

def print_success_summary(data: Dict[str, Any]) -> None:
    """Muestra un panel técnico limpio con el resultado consolidado."""
    print()
    print("=" * 72)
    print("✅ SÚPER-PIPELINE COMPLETADO CORRECTAMENTE (NATIVO / NO PATCHES)")
    print("=" * 72)
    print(f"📌 Expediente Global : {data.get('id_expediente_global')}")
    print(f"📅 Consolidación     : {data.get('fecha_consolidacion')}")
    print(f"⚖️  Módulo CEJ        : CONSOLIDADO EN DISCO")
    print(f"🏛️  Módulo REMAJU     : CONSOLIDADO EN DISCO")
    print(f"📑 Módulo SUNARP     : CONSOLIDADO EN DISCO")
    print(f"💾 Archivo Maestro   : {OUTPUT_PATH}")
    print("=" * 72)
    print()

def main() -> None:
    print("=" * 72)
    print("🚀 INICIALIZANDO SÚPER-PIPELINE UNIFICADO DANTESITO-CHASKY")
    print("=" * 72)
    
    try:
        print("📁 Configurando directorios físicos de baja RAM...")
        prepare_environment()
        
        print("📦 Desplegando el chasis del orquestador polimórfico...")
        consolidator = ChaskyConsolidator()
        
        print("⚙️  Ejecutando descosido lineal y extracción (CEJ + REMAJU + SUNARP)...")
        consolidator.build_master_expediente(
            global_id=GLOBAL_ID,
            cej_json_path=str(CEJ_PATH),
            remaju_pdf_path=str(REMAJU_PATH),
            sunarp_pdf_path=str(SUNARP_PATH),
            output_json_path=str(OUTPUT_PATH),
        )

        print("🔍 Verificando integridad del JSON Maestro Final...")
        if not OUTPUT_PATH.exists():
            raise FileNotFoundError(f"Error crítico: El JSON Maestro no se creó en {OUTPUT_PATH}")

        with OUTPUT_PATH.open("r", encoding="utf-8") as output_file:
            master_data: Dict[str, Any] = json.load(output_file)

        print_success_summary(master_data)

    except Exception as exc:
        print(f"\n❌ ERROR CRÍTICO EN PIPELINE: {exc}")
        print()
        print("💡 Sugerencias de diagnóstico:")
        print("   1. Asegúrate de tener cargado el modelo local en segundo plano:")
        print("      ollama run llama3.2:1b")
        print("   2. Si el test de Docling falla por dependencias binarias, verifica")
        print("      que onnxruntime esté correctamente compilado para tu CPU.")
        print("=" * 72)

if __name__ == "__main__":
    main()
