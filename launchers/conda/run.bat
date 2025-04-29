@echo off
setlocal enabledelayedexpansion

REM --- Configuration ---
set ENV=conda_env
set PYTHON_VERSION=3.8
set REQUIREMENTS_FILE=requirements.txt
set MAIN=main.py
REM Set to 1 to enable git check, 0 to disable
set CHECK_GIT=1
REM --- End Configuration ---

REM --- Check for double-click execution ---
echo "!cmdcmdline!" | findstr /E /C:"\"%~nx0\"\"" > nul
if %errorlevel% == 0 (
    echo This script must be run from a terminal.
    echo Press any key to exit.
    pause
    exit /b 1
)

REM --- Argument Parsing ---
set AUTOCONFIGURE=0
set FORWARD_ARGS=

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

REM --- Find Conda and activate base environment ---
set "CONDA_ACTIVATION_SCRIPT="
echo [Conda launcher] Searching for Conda activation script (conda.bat)...

REM Define potential paths for conda.bat in condabin
set "SEARCH_PATHS="
set "SEARCH_PATHS=!SEARCH_PATHS! "%USERPROFILE%\anaconda3\condabin\conda.bat""
set "SEARCH_PATHS=!SEARCH_PATHS! "%USERPROFILE%\miniconda3\condabin\conda.bat""
set "SEARCH_PATHS=!SEARCH_PATHS! "%ProgramData%\Anaconda3\condabin\conda.bat""
set "SEARCH_PATHS=!SEARCH_PATHS! "%ProgramData%\Miniconda3\condabin\conda.bat""

REM Check each path
for %%P in (!SEARCH_PATHS!) do (
    if exist %%~P (
        set "CONDA_ACTIVATION_SCRIPT=%%~P"
        echo [Conda launcher] Found Conda activation script at: !CONDA_ACTIVATION_SCRIPT!
        goto :conda_script_found
    )
)

:conda_script_found
if not defined CONDA_ACTIVATION_SCRIPT
(
    echo [Conda launcher] Error: Conda activation script (conda.bat or activate.bat) not found in typical locations.
    echo [Conda launcher] Please ensure Conda is installed correctly.
    exit /b 1
)

REM Activate the base environment
echo [Conda launcher] Activating Conda base environment using: %CONDA_ACTIVATION_SCRIPT%...
call "%CONDA_ACTIVATION_SCRIPT%" activate base
if %ERRORLEVEL% neq 0 (
    echo [Conda launcher] Error: Failed to activate Conda base environment using !CONDA_ACTIVATION_SCRIPT!.
    echo [Conda launcher] Check if the activation script is correct and the base environment exists.
    exit /b 1
)
echo [Conda launcher] Conda base environment activated.
REM --- End Conda Find and Activate ---


REM --- Main Logic ---
echo [Conda launcher] ---------------------------------------

REM Check if autoconfigure was requested
if %AUTOCONFIGURE% == 1 (
    echo [Conda launcher] Starting autoconfiguration process...

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
    conda run -n %ENV% python -m pip install -r %REQUIREMENTS_FILE%
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