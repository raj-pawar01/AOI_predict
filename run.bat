@echo off
echo ======================================================================
echo          Air Quality Prediction Comparative Analysis System
echo ======================================================================
echo.

:: Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in system PATH.
    echo Please install Python 3.9+ and try again.
    pause
    exit /b 1
)

:: Check and create virtual environment
if not exist ".venv" (
    echo Creating Python virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Install requirements if needed
echo Installing project dependencies (this may take a minute)...
.venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

:: Create data directories
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
if not exist "models" mkdir models

:: Check and generate dataset
if not exist "data\raw\city_hour.csv" (
    echo Generating air quality synthetic datasets...
    .venv\Scripts\python -c "from ml.data_generator import generate_full_dataset; generate_full_dataset('data/raw/city_hour.csv')"
    if %errorlevel% neq 0 (
        echo ERROR: Data generation failed.
        pause
        exit /b 1
    )
)

echo.
echo Setup check passed. Starting Flask web server...
echo Access the application at: http://127.0.0.1:5000/
echo.
.venv\Scripts\python app.py

pause
