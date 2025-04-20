@echo off
setlocal enabledelayedexpansion

REM --- Configuration ---
set ENV=conda_env
set PYTHON_VERSION=3.8
set REQUIREMENTS_FILE=requirements.txt
set MAIN=main.py
set CHECK_GIT=1 REM Set to 1 to enable git check, 0 to disable
REM --- End Configuration ---

REM --- Argument Parsing ---
set AUTOCONFIGURE=0
set FORWARD_ARGS=
set "ALL_ARGS=%*"

:arg_loop
REM Check if there are arguments left
if "%~1"=="" goto :end_arg_loop

REM Check for the autoconfigure flag
if /I "%~1"=="--autoconfigure" (
    set AUTOCONFIGURE=1
    echo [Conda launcher] Autoconfigure flag detected.
) else (
    REM Append argument to the list to forward, handling spaces
    set "FORWARD_ARGS=!FORWARD_ARGS! "%~1""
)

REM Shift to the next argument
shift
goto :arg_loop
:end_arg_loop

REM Remove leading space if FORWARD_ARGS is not empty
if defined FORWARD_ARGS set "FORWARD_ARGS=%FORWARD_ARGS:~1%"

REM --- Main Logic ---
echo [Conda launcher] ---------------------------------------

REM Check if autoconfigure was requested
if %AUTOCONFIGURE% == 1 (
    echo [Conda launcher] Starting autoconfiguration process...

    REM Check if conda is installed
    where conda > nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [Conda launcher] Error: Conda command not found. Please ensure Conda is installed and in your PATH.
        exit /b 1
    )
    echo [Conda launcher] Conda found.

    REM Check if git is installed (if CHECK_GIT is 1)
    if %CHECK_GIT% == 1 (
        where git > nul 2>&1
        if %ERRORLEVEL% neq 0 (
            echo [Conda launcher] Error: Git command not found. Please ensure Git is installed and in your PATH.
            exit /b 1
        )
        echo [Conda launcher] Git found.
    )

    REM Check if the environment exists
    echo [Conda launcher] Checking for environment: %ENV%...
    conda env list | findstr /B /C:"%ENV% " > nul
    if %ERRORLEVEL% neq 0 (
        echo [Conda launcher] Environment '%ENV%' not found. Creating environment with Python %PYTHON_VERSION%...
        conda create -n %ENV% python=%PYTHON_VERSION% -y
        if !ERRORLEVEL! neq 0 (
            echo [Conda launcher] Error: Failed to create Conda environment '%ENV%'.
            exit /b 1
        )
        echo [Conda launcher] Environment '%ENV%' created successfully.
    ) else (
        echo [Conda launcher] Environment '%ENV%' found.
    )

    REM Install/update requirements
    echo [Conda launcher] Installing requirements from %REQUIREMENTS_FILE% into %ENV%...
    conda run -n %ENV% python -m pip install -q -r %REQUIREMENTS_FILE%
    if !ERRORLEVEL! neq 0 (
        echo [Conda launcher] Error: Failed to install requirements in '%ENV%'.
        exit /b 1
    )
    echo [Conda launcher] Requirements installed/updated successfully.
    echo [Conda launcher] Autoconfiguration finished.
    echo [Conda launcher] ---------------------------------------
    endlocal
    exit /b 0

) else (
    REM Execute the main script within the environment, passing filtered arguments
    if "%FORWARD_ARGS%"=="" (
        echo [Conda launcher] Executing %MAIN% in %ENV%...
    ) else (
        echo [Conda launcher] Executing %MAIN% %FORWARD_ARGS% in %ENV%...
    )
    echo [Conda launcher] ---------------------------------------
    conda run --no-capture-output -n %ENV% python %MAIN% %FORWARD_ARGS%
    if %ERRORLEVEL% neq 0 (
        echo [Conda launcher] ---------------------------------------
        echo [Conda launcher] Error: Failed to execute %MAIN% in '%ENV%'.
        echo [Conda launcher] ---------------------------------------
        exit /b 1
    )

    echo [Conda launcher] ---------------------------------------
    echo [Conda launcher] Script execution finished successfully.
    echo [Conda launcher] ---------------------------------------
    endlocal
    exit /b 0
)