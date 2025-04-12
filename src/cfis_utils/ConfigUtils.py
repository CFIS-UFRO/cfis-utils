# Standard imports
from typing import List, Dict, Any
# Third-party imports
import toml

class ConfigUtils:
    """
    Utility class for handling TOML configuration files.
    """

    @staticmethod
    def generate_template_config_file(config_template: List[Dict[str, Any]], output_path: str) -> None:
        """
        Generates a TOML configuration file from a template.

        Each item in the template list should be a dictionary with keys:
        'parameter': Name of the parameter (str).
        'default_value': The default value for the parameter.
        'description': A description for the parameter (str).

        Args:
            config_template: A list of dictionaries defining the configuration parameters.
            output_path: The path where the TOML file will be saved.

        Raises:
            IOError: If there's an error writing the file.
            KeyError: If a dictionary in the template is missing a required key.
        """
        if not output_path.lower().endswith('.toml'):
            raise ValueError("The output file must have a .toml extension.")
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in config_template:
                parameter_name = item['parameter']
                value = item['default_value']
                description = item['description']

                # Write description as a comment
                if description:
                    f.write(f"# {description}\n")

                # Write key-value pair, formatting value correctly for TOML
                if isinstance(value, str):
                    # TOML strings need to be enclosed in quotes
                    # Escape backslashes and quotes within the string
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'{parameter_name} = "{escaped_value}"\n\n')
                elif isinstance(value, bool):
                    # TOML booleans are lowercase
                    f.write(f'{parameter_name} = {str(value).lower()}\n\n')
                else:
                    # Handles integers, floats
                    f.write(f'{parameter_name} = {value}\n\n')

    @staticmethod
    def load_config_file(config_path: str) -> Dict[str, Any]:
        """
        Loads configuration parameters from a TOML file.

        Args:
            config_path: The path to the TOML configuration file.

        Returns:
            A dictionary containing the key-value pairs from the TOML file.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            toml.TomlDecodeError: If the file content is not valid TOML.
            IOError: If there's an error reading the file.
        """
        if not config_path.lower().endswith('.toml'):
            raise ValueError("The configuration file must have a .toml extension.")
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = toml.load(f)
        return config_data

if __name__ == "__main__":
    # Example usage
    config_template = [
        {
            'parameter': 'example_string',
            'default_value': 'Hello, World!',
            'description': 'An example string parameter.'
        },
        {
            'parameter': 'example_integer',
            'default_value': 42,
            'description': 'An example integer parameter.'
        },
        {
            'parameter': 'example_boolean',
            'default_value': True,
            'description': 'An example boolean parameter.'
        },
        {
            'parameter': 'example_list',
            'default_value': [1, 2, 3],
            'description': 'An example list parameter.'
        }
    ]
    ConfigUtils.generate_template_config_file(config_template, "example_config.toml")
    loaded_config = ConfigUtils.load_config_file("example_config.toml")
    print(loaded_config)