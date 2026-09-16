@echo off
title 🧹 PURGA CORPORATIVA DE ENTORNO QUIPU (KILL MEMORY)
echo =======================================================================
echo 🧹 ELIMINANDO PROCESOS FANTASMA Y RESIDUOS DE MEMORIA EN WINDOWS
echo =======================================================================
echo.

echo ⚙️ 1. Matando instancias ocultas de Uvicorn, Python y Ngrok...
taskkill /f /im uvicorn.exe 2>nul
taskkill /f /im python.exe 2>nul
taskkill /f /im ngrok.exe 2>nul
echo ✅ Procesos en segundo plano purgados de la RAM.
echo.

echo ⚙️ 2. Liberando forzosamente el puerto local 8000 si continuaba retenido...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /f /pid %%a 2>nul
    echo ✅ Puerto 8000 liberado (PID %%a destruido).
)
echo.

echo ⚙️ 3. Limpiando caché física volátil del sistema...
if exist .pytest_cache (
    rmdir /s /q .pytest_cache
    echo ✅ Caché de Pytest eliminada.
)

echo =======================================================================
echo 🏁 MEMORIA LIMPIA Y CACHÉ PURGADA. El entorno está listo para relanzar.
echo =======================================================================
pause
