# dantesito/quipu/entrypoint/api_server.py
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Header, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from dantesito.quipu.entrypoint.main_runner import run_pipeline_entrypoint

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Quipu Remote Control Server",
    description="Servidor de control remoto e interfaz interactiva Mobile-First para ejecución de orquestación Quipu con monitoreo en tiempo real.",
    version="1.3.0",
)


class PipelineTriggerRequest(BaseModel):
    numero_expediente: str


def _get_auth_token() -> str:
    """Obtiene el token de autorización configurado en las variables de entorno."""
    return os.environ.get("QUIPU_API_AUTH_TOKEN", "Messenger2")


def _get_data_dir() -> Path:
    """Obtiene el directorio de almacenamiento estándar basado en la variable de entorno DATA_DIR."""
    return Path(os.environ.get("DATA_DIR", "./data"))


def _build_file_paths(global_id: str) -> dict:
    """Construye y retorna el diccionario de rutas físicas del expediente respetando DATA_DIR."""
    clean_id = global_id.replace("/", "_").replace("\\", "_").strip()
    data_dir = _get_data_dir()
    return {
        "remaju_path": str(data_dir / "01_raw" / f"remaju_{clean_id}.pdf"),
        "sunarp_path": str(data_dir / "01_raw" / f"sunarp_{clean_id}.pdf"),
        "cej_path": str(data_dir / "01_raw" / f"cej_{clean_id}.json"),
        "output_json_path": str(data_dir / "04_output" / f"master_{clean_id}.json"),
    }


def _get_status_file_path(global_id: str) -> Path:
    """Calcula la ruta física del archivo JSON de estado utilizando el directorio estándar DATA_DIR."""
    clean_id = global_id.replace("/", "_").replace("\\", "_").strip()
    return _get_data_dir() / "04_output" / f"status_{clean_id}.json"


def _render_ui(message: str = "", status_type: str = "neutral", expediente_val: str = "", is_running: bool = False) -> str:
    """Genera la plantilla HTML responsiva Mobile-First con cliente de sondeo en tiempo real (Polling)."""
    alert_box = ""
    if message:
        colors = {
            "error": ("#3b1111", "#f87171", "#fca5a5"),
            "success": ("#0f2d18", "#4ade80", "#86efac"),
            "warning": ("#451a03", "#f59e0b", "#fde68a"),
        }
        bg_color, border_color, text_color = colors.get(status_type, ("#1e293b", "#475569", "#f8fafc"))
        alert_box = f"""
        <div id="alert-box" style="background-color: {bg_color}; border: 1px solid {border_color}; color: {text_color}; padding: 16px; border-radius: 8px; margin-bottom: 20px; font-size: 0.95rem; line-height: 1.45;">
            {message}
        </div>
        """

    form_display = "none" if is_running else "block"
    monitor_display = "block" if is_running else "none"
    exp_escaped = expediente_val.replace("'", "\\'")

    polling_script = ""
    if is_running:
        polling_script = f"""
        <script>
            const expedienteId = "{exp_escaped}";
            const tokenSeguridad = "{os.environ.get("QUIPU_API_AUTH_TOKEN", "Messenger2")}";
            
            function actualizarProgreso() {{
                fetch('/api/v1/status/' + encodeURIComponent(expedienteId), {{
                    method: 'GET',
                    headers: {{
                        'X-Auth-Token': tokenSeguridad
                    }}
                }})
                .then(response => {{
                    if (!response.ok) throw new Error('No autorizado o error de red');
                    return response.json();
                }})
                .then(data => {{
                    const statusText = document.getElementById('status-text');
                    const fileText = document.getElementById('file-text');
                    const phaseText = document.getElementById('phase-text');
                    
                    if (data && data.status) {{
                        statusText.innerText = data.status.toUpperCase();
                        fileText.innerText = data.archivo_actual || 'Ninguno';
                        phaseText.innerText = data.fase_actual || 'Esperando asignación...';
                        
                        if (data.status === 'completado' || data.status === 'error') {{
                            clearInterval(window.pollInterval);
                            document.getElementById('loading-indicator').style.display = 'none';
                            document.getElementById('final-actions').style.display = 'block';
                        }}
                    }}
                }})
                .catch(err => {{
                    console.error('Error consultando estado perimetral:', err);
                }});
            }}

            window.pollInterval = setInterval(actualizarProgreso, 6000);
            actualizarProgreso();
        </script>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quipu Remote Control</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 16px;
        }}
        .card {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 24px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .header h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #38bdf8;
            margin-bottom: 6px;
        }}
        .header p {{
            font-size: 0.875rem;
            color: #94a3b8;
        }}
        .form-group {{
            margin-bottom: 18px;
        }}
        label {{
            display: block;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 6px;
            color: #cbd5e1;
        }}
        input[type="text"],
        input[type="password"] {{
            width: 100%;
            padding: 14px;
            background-color: #0f172a;
            border: 1px solid #475569;
            border-radius: 8px;
            color: #ffffff;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        input[type="text"]:focus,
        input[type="password"]:focus {{
            border-color: #38bdf8;
        }}
        button {{
            width: 100%;
            padding: 16px;
            background-color: #10b981;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
            margin-top: 8px;
        }}
        button:hover {{
            background-color: #059669;
        }}
        button:active {{
            background-color: #047857;
            transform: scale(0.98);
        }}
        .monitor-box {{
            background-color: #0f172a;
            border: 1px solid #475569;
            border-radius: 10px;
            padding: 16px;
            margin-top: 16px;
        }}
        .monitor-item {{
            margin-bottom: 10px;
            font-size: 0.9rem;
        }}
        .monitor-label {{
            color: #94a3b8;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .monitor-value {{
            color: #38bdf8;
            font-weight: 600;
            word-break: break-all;
        }}
        .spinner {{
            text-align: center;
            margin: 16px 0;
            color: #f59e0b;
            font-weight: 600;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>⚡ Quipu Control</h1>
            <p>Orquestación & Análisis Semántico</p>
        </div>
        {alert_box}
        
        <!-- Formulario de Ingreso -->
        <div id="form-container" style="display: {form_display};">
            <form action="/" method="POST">
                <div class="form-group">
                    <label for="numero_expediente">N° Expediente</label>
                    <input type="text" id="numero_expediente" name="numero_expediente" value="{expediente_val}" placeholder="Ej: 0200-jp-2051-IE" required autocomplete="off">
                </div>
                <div class="form-group">
                    <label for="token_seguridad">Contraseña</label>
                    <input type="password" id="token_seguridad" name="token_seguridad" placeholder="Ingrese su Contraseña" required>
                </div>
                <button type="submit">🚀 Iniciar Análisis Semántico</button>
            </form>
        </div>

        <!-- Panel de Monitoreo Dinámico en Tiempo Real -->
        <div id="monitor-container" style="display: {monitor_display};">
            <div style="font-size: 0.95rem; line-height: 1.45; color: #cbd5e1; margin-bottom: 12px; text-align: center;">
                El expediente <b>{expediente_val}</b> se está procesando activamente en la PC de la oficina.
            </div>
            <div class="monitor-box">
                <div class="monitor-item">
                    <div class="monitor-label">Estado del Pipeline</div>
                    <div id="status-text" class="monitor-value">INICIANDO...</div>
                </div>
                <div class="monitor-item">
                    <div class="monitor-label">Fase Actual</div>
                    <div id="phase-text" class="monitor-value">Preparando entorno de ejecución</div>
                </div>
                <div class="monitor-item">
                    <div class="monitor-label">Archivo Analizado</div>
                    <div id="file-text" class="monitor-value">Iniciando escaneo...</div>
                </div>
            </div>
            
            <div id="loading-indicator" class="spinner">
                ⏳ Monitoreando en vivo (actualizando cada 6s)...
            </div>
            
            <div id="final-actions" style="display: none; margin-top: 16px;">
                <button onclick="window.location.href='/'">🔄 Procesar Nuevo Expediente</button>
            </div>
        </div>
    </div>
    {polling_script}
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def get_web_interface() -> HTMLResponse:
    """Ruta GET para servir la interfaz web interactiva Mobile-First."""
    return HTMLResponse(content=_render_ui())


@app.post("/", response_class=HTMLResponse)
async def handle_web_form(
    background_tasks: BackgroundTasks,
    numero_expediente: str = Form(...),
    token_seguridad: str = Form(...),
) -> HTMLResponse:
    """Ruta POST asíncrona desconectada que inicializa el estado en disco y despacha el pipeline."""
    expected_token = _get_auth_token()
    if token_seguridad != expected_token:
        return HTMLResponse(
            content=_render_ui(
                message="🔒 Acceso Denegado (401): La Contraseña es incorrecta.",
                status_type="error",
                expediente_val=numero_expediente,
            ),
            status_code=401,
        )

    clean_expediente = numero_expediente.strip()

    # 1. Obtener las rutas físicas estándar usando _build_file_paths
    paths = _build_file_paths(clean_expediente)

    # 2. Crear el archivo de estado inicial en disco (Cero RAM) antes de disparar la tarea
    status_file = _get_status_file_path(clean_expediente)
    status_file.parent.mkdir(parents=True, exist_ok=True)
    initial_status = {
        "status": "procesando",
        "archivo_actual": "Iniciando descarga y preparación",
        "fase_actual": "Fase 1: Encolado y Descarga de Legajos",
        "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
    }
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(initial_status, f, ensure_ascii=False, indent=2)

    # 3. Despachar tarea de fondo con la firma de producción estándar
    background_tasks.add_task(
        run_pipeline_entrypoint,
        remaju_path=paths["remaju_path"],
        sunarp_path=paths["sunarp_path"],
        cej_path=paths["cej_path"],
    )

    # 4. Retornar la UI renderizada en modo de monitoreo activo
    return HTMLResponse(
        content=_render_ui(
            message=f"🚀 <b>¡Pipeline Gatillado Exitosamente!</b> Conectado al motor local.",
            status_type="success",
            expediente_val=clean_expediente,
            is_running=True
        )
    )


@app.get("/api/v1/status/{numero_expediente}")
async def get_pipeline_status(
    numero_expediente: str,
    x_auth_token: str = Header(None, alias="X-Auth-Token"),
) -> JSONResponse:
    """
    Endpoint perimetral de consulta rápida (Polling). Lee directamente el estado desde 
    el archivo JSON en disco duro validando el token de seguridad corporativo.
    """
    expected_token = _get_auth_token()
    if not x_auth_token or x_auth_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorización 'X-Auth-Token' Inválido o Ausente.",
        )

    status_file = _get_status_file_path(numero_expediente)
    
    if not status_file.exists():
        return JSONResponse(
            content={
                "status": "inactivo",
                "archivo_actual": "No encontrado o en cola",
                "fase_actual": "Sin actividad reciente registrada",
                "ultima_actualizacion": None,
            }
        )

    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as err:
        logger.error(f"Error leyendo archivo de estado físico para {numero_expediente}: {err}")
        return JSONResponse(
            content={
                "status": "error",
                "archivo_actual": "Error de lectura en disco",
                "fase_actual": str(err),
            },
            status_code=500
        )


@app.post("/api/v1/trigger-pipeline")
async def trigger_pipeline_api(
    background_tasks: BackgroundTasks,
    payload: PipelineTriggerRequest,
    x_auth_token: str = Header(None, alias="X-Auth-Token"),
) -> JSONResponse:
    """Endpoint REST JSON asíncrono para disparo programático del pipeline con inicialización de estado."""
    expected_token = _get_auth_token()
    if not x_auth_token or x_auth_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorización 'X-Auth-Token' Inválido o Ausente.",
        )

    clean_expediente = payload.numero_expediente.strip()
    paths = _build_file_paths(clean_expediente)

    # Inicializar estado en disco
    status_file = _get_status_file_path(clean_expediente)
    status_file.parent.mkdir(parents=True, exist_ok=True)
    initial_status = {
        "status": "procesando",
        "archivo_actual": "Iniciando vía API programática",
        "fase_actual": "Fase 1: Inicialización remota",
        "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
    }
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(initial_status, f, ensure_ascii=False, indent=2)

    background_tasks.add_task(
        run_pipeline_entrypoint,
        remaju_path=paths["remaju_path"],
        sunarp_path=paths["sunarp_path"],
        cej_path=paths["cej_path"],
    )
    
    return JSONResponse(
        content={
            "success": True, 
            "message": f"Pipeline gatillado exitosamente en segundo plano. Monitoreando expediente {clean_expediente}."
        }
    )