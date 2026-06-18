@echo off
echo.
echo  ================================
echo   CreditoFacil - Iniciando app
echo  ================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python no esta instalado.
    echo  Descargalo en: https://python.org/downloads
    echo  Asegurate de marcar "Add Python to PATH"
    pause
    exit /b 1
)

:: Crear entorno virtual si no existe
if not exist "venv\" (
    echo  Instalando dependencias por primera vez...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt --quiet
) else (
    call venv\Scripts\activate
)

echo  Abriendo navegador en http://localhost:5000
echo  (Presiona Ctrl+C en esta ventana para detener el servidor)
echo.

:: Abrir navegador automaticamente
start "" http://localhost:5000

:: Iniciar la app
python app.py
pause
