# AI_ASSISTANT.md

This file provides guidance to AI assistants when working with code in this repository.

## Project Overview

CFIS Utils is a Python utility library for the CFIS laboratory, providing various scientific computing utilities including spectrum analysis, data visualization, hardware communication, and development tools.

## Development Commands

### Environment Setup
```bash
# Create conda environment for development
conda create -n cfis-utils python=3.8
conda activate cfis-utils
pip install -r requirements.txt
```

### Running Individual Modules
```bash
# Test individual modules using Python's -m flag
python -m src.cfis_utils.<module_name>
```

### Publishing New Versions
```bash
# Automated version publishing (updates version, creates tag, pushes to repo)
python publish.py
```

### Using Project Launchers
```bash
# For Linux/MacOS
bash launchers/conda/run.sh --autoconfigure  # Setup environment
bash launchers/conda/run.sh                  # Run main.py

# For Windows
launchers\conda\run.bat --autoconfigure      # Setup environment  
launchers\conda\run.bat                      # Run main.py
```

## Architecture

### Core Utility Modules
The project follows a modular architecture with specialized utility classes in `src/cfis_utils/`:

- **Spectrum Analysis**: `spectrum.py`, `tridimensional_spectrum.py` - Core classes for X-ray fluorescence spectrum data handling
- **Visualization**: `spectrum_viewer.py`, `tridimensional_spectrum_viewer.py` - GUI components for spectrum visualization using PySide6
- **Hardware Communication**: `serial_utils.py`, `usb_utils.py` - Serial and USB device communication
- **System Utilities**: `os_utils.py`, `terminal_utils.py`, `compression_utils.py` - OS-level operations
- **Development Tools**: `git_utils.py`, `publish_utils.py`, `version_utils.py` - Development workflow automation
- **Configuration**: `config_utils.py`, `field_utils.py` - Configuration management and field validation
- **Logging**: `logger_utils.py` - Centralized logging with colorlog support

### Key Design Patterns
- All utility classes are designed as static method containers
- Consistent logging integration across modules using LoggerUtils
- JSON-based spectrum data format with compression support
- Linear energy calibration model for spectrum data (energy = slope_a * channel + intercept_b)

### Dependencies
Core dependencies include numpy, matplotlib, PySide6, pyserial, pyusb, colorlog, and tomlkit. The project maintains Python 3.8+ compatibility.

### Version Management
- Uses date-based versioning: `vyyyy.mm.dd.xx` format
- Automated publishing through `publish.py` script
- Version synchronization between `pyproject.toml` and `README.md`
- Git tag creation and repository pushing automation

