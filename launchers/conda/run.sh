#!/bin/bash

# --- Configuration ---
ENV="conda_env"
PYTHON_VERSION="3.8"
REQUIREMENTS_FILE="requirements.txt"
MAIN="main.py"
CHECK_GIT=true # Set to true to enable git check, false to disable
# --- End Configuration ---

# --- Argument Parsing ---
AUTOCONFIGURE=false
FORWARD_ARGS=() # Initialize an empty array for arguments to forward

# Iterate through all positional arguments
for arg in "$@"; do
  if [[ "$arg" == "--autoconfigure" ]]; then
    echo "[Conda launcher] Autoconfigure flag detected."
    AUTOCONFIGURE=true
  else
    # Add argument to the forwarding list
    FORWARD_ARGS+=("$arg")
  fi
done

echo "[Conda launcher] ---------------------------------------"

# --- Main Logic ---

# Check if autoconfigure was requested
if [ "$AUTOCONFIGURE" = true ]; then
    echo "[Conda launcher] Starting autoconfiguration process..."

    # Check if conda is installed
    if ! command -v conda &> /dev/null; then
        echo "[Conda launcher] Error: Conda command not found. Please ensure Conda is installed and in your PATH."
        exit 1
    fi
    echo "[Conda launcher] Conda found."

    # Check if git is installed (if CHECK_GIT is true)
    if [ "$CHECK_GIT" = true ]; then
        if ! command -v git &> /dev/null; then
            echo "[Conda launcher] Error: Git command not found. Please ensure Git is installed and in your PATH."
            exit 1
        fi
        echo "[Conda launcher] Git found."
    fi

    # Check if the environment exists
    echo "[Conda launcher] Checking for environment: ${ENV}..."
    # Use 'conda info --envs' which is often more reliable for parsing
    if ! conda info --envs | grep -q "^${ENV}\s"; then
        echo "[Conda launcher] Environment '${ENV}' not found. Creating environment with Python ${PYTHON_VERSION}..."
        conda create -n "${ENV}" python="${PYTHON_VERSION}" -y
        if [ $? -ne 0 ]; then
            echo "[Conda launcher] Error: Failed to create Conda environment '${ENV}'."
            exit 1
        fi
        echo "[Conda launcher] Environment '${ENV}' created successfully."
    else
        echo "[Conda launcher] Environment '${ENV}' found."
    fi

    # Install/update requirements
    echo "[Conda launcher] Installing requirements from ${REQUIREMENTS_FILE} into ${ENV}..."
    conda run --no-capture-output -n "${ENV}" python -m pip install -q -r "${REQUIREMENTS_FILE}"
    if [ $? -ne 0 ]; then
        echo "[Conda launcher] Error: Failed to install requirements in '${ENV}'."
        exit 1
    fi
    echo "[Conda launcher] Requirements installed/updated successfully."
    echo "[Conda launcher] Autoconfiguration finished."
    echo "[Conda launcher] ---------------------------------------"
    exit 0

else
    # Execute the main script within the environment, passing filtered arguments
    if [ ${#FORWARD_ARGS[@]} -eq 0 ]; then
        # No arguments were passed (after filtering)
        echo "[Conda launcher] Executing ${MAIN} in ${ENV}..."
    else
        # Arguments were passed
        echo "[Conda launcher] Executing ${MAIN} ${FORWARD_ARGS[@]} in ${ENV}..."
    fi
    echo "[Conda launcher] ---------------------------------------"
    conda run --no-capture-output -n "${ENV}" python "${MAIN}" "${FORWARD_ARGS[@]}"
    if [ $? -ne 0 ]; then
        echo "[Conda launcher] ---------------------------------------"
        echo "[Conda launcher] Error: Failed to execute ${MAIN} in '${ENV}'."
        echo "[Conda launcher] ---------------------------------------"
        exit 1
    fi

    echo "[Conda launcher] ---------------------------------------"
    echo "[Conda launcher] Script execution finished successfully."
    echo "[Conda launcher] ---------------------------------------"
    exit 0
fi