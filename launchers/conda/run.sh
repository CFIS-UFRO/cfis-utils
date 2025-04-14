#!/bin/bash

# --- Configuration ---
ENV="conda_env"
PYTHON_VERSION="3.8"
REQUIREMENTS_FILE="requirements.txt"
MAIN="main.py"
# --- End Configuration ---

# --- Argument Parsing ---
INSTALL_REQ=false
FORWARD_ARGS=() # Initialize an empty array for arguments to forward

# Iterate through all positional arguments
for arg in "$@"; do
  if [[ "$arg" == "--install_requirements" ]]; then
    echo "[Conda launcher] Install requirements flag detected."
    INSTALL_REQ=true
  else
    # Add argument to the forwarding list
    FORWARD_ARGS+=("$arg")
  fi
done


echo "[Conda launcher] ---------------------------------------"

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "[Conda launcher] Error: Conda command not found. Please ensure Conda is installed and in your PATH."
    exit 1
fi
echo "[Conda launcher] Conda found."

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
    # Force install requirements if environment is newly created
    INSTALL_REQ=true
    echo "[Conda launcher] Forcing requirements installation for new environment."
else
    echo "[Conda launcher] Environment '${ENV}' already exists."
fi

# Install requirements if requested or if env was just created
if [ "$INSTALL_REQ" = true ]; then
    echo "[Conda launcher] Installing requirements from ${REQUIREMENTS_FILE} into ${ENV}..."
    conda run -n "${ENV}" python -m pip install -q -r "${REQUIREMENTS_FILE}"
    if [ $? -ne 0 ]; then
        echo "[Conda launcher] Error: Failed to install requirements in '${ENV}'."
        exit 1
    fi
    echo "[Conda launcher] Requirements installed successfully."
else
    echo "[Conda launcher] Skipping requirements installation."
fi


# Execute the main script within the environment, passing filtered arguments
# Use "${FORWARD_ARGS[@]}" to handle arguments with spaces correctly
if [ ${#FORWARD_ARGS[@]} -eq 0 ]; then
    # No arguments were passed (after filtering)
    echo "[Conda launcher] Executing ${MAIN} in ${ENV}..."
else
    # Arguments were passed
    echo "[Conda launcher] Executing ${MAIN} ${FORWARD_ARGS[@]} in ${ENV}..."
fi
echo "[Conda launcher] ---------------------------------------"
conda run -n "${ENV}" python "${MAIN}" "${FORWARD_ARGS[@]}"
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