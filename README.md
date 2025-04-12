# CFIS Utils
Utility classes and methods used by our lab.

# How to install

You can install the library using pip:
```bash
pip install git+https://github.com/CFIS-UFRO/cfis-utils.git@<version>
```
where `<version>` is one of the [available tags](https://github.com/CFIS-UFRO/cfis-utils/tags) in the repository.

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