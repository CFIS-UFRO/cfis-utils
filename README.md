# CFIS Utils

Utility classes and methods used by the CFIS laboratory.

# Requirements

*   Python 3.8 or higher.
    *   Windows: [https://www.python.org/](https://www.python.org/)
    *   Linux and MacOS: Usually pre-installed.
*   Git.
    *   Windows: [https://git-scm.com/download/win](https://git-scm.com/download/win)
    *   Linux: Install it through your package manager, e.g., `sudo apt install git`.
    *   MacOS: Install it through the Xcode command line tools using `xcode-select --install`.

# How to install

You can install the library using pip:
```bash
pip install git+https://github.com/CFIS-UFRO/cfis-utils.git
```

Additionally, you can specify a particular version to install:
```bash
pip install git+https://github.com/CFIS-UFRO/cfis-utils.git@<version>
```
where `<version>` is one of the [available tags](https://github.com/CFIS-UFRO/cfis-utils/tags).

**Latest stable tag**: v2025.07.01.01

# Utility classes

You can find all the classes and methods inside the `src/cfis_utils` folder. The code is written to be self-explanatory, so you should be able to find what you need simply by looking at the code.

After installing the library, you can import the classes like this:
```python
from cfis_utils import <ClassName>
```

# Launchers

You can find launchers inside the `launchers` folder. The objective of these scripts is to provide an easy way to run Python code from the command line, taking into account the dependencies and the environment.

You just need to copy the files to your project, set the required variables, and run them like this:
```bash
python launcher.py
```

# For developers

- The idea is to keep this library compatible with Python 3.8 and above.
- For development it is recommended to use a virtual environment with conda and install all the dependencies in it.
    ```bash
    conda create -n cfis-utils python=3.8
    conda activate cfis-utils
    pip install -r requirements.txt
    ```
- Any time you use a new dependency, please add it to these files too:
    - `requirements.txt`
    - `pyproject.toml`
- The library versions are based on tags, to publish a new version run the script `publish.py`:
    ```bash
    python publish.py
    ```
- To run individual files for testing, you can use the `-m` flag:
    ```bash
    python -m src.cfis_utils.<file without .py>
    ```
- Not only the tags but also the main branch should be stable. If you are planning to make big and possibly breaking changes, please create a new branch and merge it to the main branch when you are done.