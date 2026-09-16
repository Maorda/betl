@echo off
chcp 65001 >nul
title Servidor de Ingesta Quipu + pyngrok Unificado

echo =======================================================================
echo 🚀 INICIALIZANDO INFRAESTRUCTURA REMOTA (FASTAPI + PYNGROK + GEMINI)
echo =======================================================================
echo.

:: 1. Activación limpia del entorno virtual de Python
echo ⚙️ 1. Activando entorno virtual de Python (venv)...
set PYTHONPATH=.
call .\venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 🚨 ERROR: No se pudo activar el entorno virtual en .\venv\
    pause
    exit /b 1
)
echo ✅ Entorno virtual activo de forma correcta.
echo.

:: 2. Validación de existencia del entorno físico corporativo
if not exist ".env" (
    echo 🚨 ERROR CRÍTICO: No se encuentra el archivo .env en la raíz del proyecto.
    pause
    exit /b 1
)

:: 3. Arranque del microservicio FastAPI (Inyección modular del .env sin bloqueos)
echo ⚙️ 2. Lanzando Microservicio FastAPI (api_server.py) en puerto 8000...
:: Se usa cmd /k para mantener la persistencia visual y capturar logs en caliente
start "Quipu FastAPI Backend" cmd /k python -m uvicorn dantesito.quipu.entrypoint.api_server:app --host 127.0.0.1 --port 8000 --env-file .env --log-level info
echo ✅ Servidor FastAPI corriendo de forma aislada en una nueva ventana de memoria.
echo.

:: 4. Pausa de cortesía de 3 segundos para la estabilización del socket de red
echo ⚙️ 3. Esperando apertura del puerto local...
timeout /t 3 /nobreak >nul
echo.

:: 5. Apertura programática y segura del túnel de red usando la ruta física real
echo ⚙️ 4. Abriendo túnel público seguro de última generación vía pyngrok...
if exist "dantesito\quipu\entrypoint\tunnel_launcher.py" (
    python dantesito/quipu/entrypoint/tunnel_launcher.py
) else (
    echo 🚨 ERROR CRÍTICO: No se encontró tunnel_launcher.py en la ruta contractual.
    pause
    exit /b 1
)

echo.
echo =======================================================================
echo 🏁 INFRAESTRUCTURA INICIADA - SISTEMA EN OPERACIÓN REMOTA
echo =======================================================================
