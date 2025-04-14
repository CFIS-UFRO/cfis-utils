# Standard imports
import os
from typing import List, Dict, Any
# Third-party imports
import tomlkit
from tomlkit.exceptions import ParseError

class ConfigUtils:
    """
    Utility class for handling TOML configuration files.
    """

    @staticmethod
    def generate_template_config_file(config_template: List[Dict[str, Any]], output_path: str) -> None:
        """
        Generates or updates a TOML configuration file from a template using tomlkit.

        If the output_path does not exist, it creates a new TOML file based
        on the provided template, including descriptions.
        If the output_path exists, it loads the existing configuration using tomlkit,
        preserves its formatting/comments, and appends only the parameters from the
        template that are not already present in the file, including their descriptions.

        Each item in the template list should be a dictionary with keys:
        'parameter': Name of the parameter (str).
        'default_value': The default value for the parameter.
        'description': A description (comment) for the parameter (str).

        Args:
            config_template: A list of dictionaries defining the configuration parameters.
            output_path: The path where the TOML file will be saved or updated.

        Raises:
            ValueError: If the output file path does not end with '.toml'.
            IOError: If there's an error writing or reading the file.
            KeyError: If a dictionary in the template is missing a required key.
            tomlkit.exceptions.ParseError: If the existing file content is not valid TOML.
        """
        if not output_path.lower().endswith('.toml'):
            raise ValueError("The output file must have a .toml extension.")

        doc: tomlkit.TOMLDocument

        if os.path.exists(output_path):
            # --- File exists: Load, check for missing keys, update, and save ---
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    doc = tomlkit.load(f)
            except ParseError as e:
                print(f"Error parsing existing TOML file {output_path}: {e}")
                raise
            except IOError as e:
                print(f"Error reading existing config file {output_path}: {e}")
                raise

            existing_params = set(doc.keys())
            items_to_add = [
                item for item in config_template
                if item['parameter'] not in existing_params
            ]

            if items_to_add:
                # Add a separator comment before adding new items
                doc.add(tomlkit.nl()) # Add a newline
                doc.add(tomlkit.comment("--- Parameters added by ConfigUtils ---"))
                doc.add(tomlkit.nl()) # Add a newline

                for item in items_to_add:
                    parameter_name = item['parameter']
                    value = item['default_value']
                    description = item['description']

                    # Add the comment associated with the parameter
                    if description:
                        doc.add(tomlkit.comment(description))

                    # Add the key-value pair using tomlkit.item to preserve type
                    # Use tomlkit.item() which intelligently handles Python types
                    doc[parameter_name] = tomlkit.item(value)

                    # Add a newline after the item for spacing
                    doc.add(tomlkit.nl())

                # Save the modified document back to the file (overwrite with new content)
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(tomlkit.dumps(doc))
                except IOError as e:
                    print(f"Error writing updated config file {output_path}: {e}")
                    raise
        else:
            # --- File does not exist: Create a new document from the template ---
            doc = tomlkit.document()
            try:
                for item in config_template:
                    parameter_name = item['parameter']
                    value = item['default_value']
                    description = item['description']

                    # Add the comment before the key-value pair
                    if description:
                        doc.add(tomlkit.comment(description))

                    # Add the key-value pair
                    doc[parameter_name] = tomlkit.item(value)

                    # Add a newline for spacing between parameters
                    doc.add(tomlkit.nl())

                # Write the new document to the file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(tomlkit.dumps(doc))

            except IOError as e:
                print(f"Error writing new config file {output_path}: {e}")
                raise
            except KeyError as e:
                 print(f"Missing key in config_template item: {e}")
                 raise

    @staticmethod
    def load_config_file(config_path: str) -> tomlkit.TOMLDocument:
        """
        Loads configuration parameters from a TOML file using tomlkit.

        Args:
            config_path: The path to the TOML configuration file.

        Returns:
            A tomlkit.TOMLDocument object containing the data and formatting
            from the TOML file. Behaves like a dictionary.

        Raises:
            ValueError: If the config file path does not end with '.toml'.
            FileNotFoundError: If the config file doesn't exist.
            tomlkit.exceptions.ParseError: If the file content is not valid TOML.
            IOError: If there's an error reading the file.
        """
        if not config_path.lower().endswith('.toml'):
            raise ValueError("The configuration file must have a .toml extension.")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                # Use tomlkit.load to get a document preserving structure
                config_data = tomlkit.load(f)
            return config_data
        except FileNotFoundError:
            print(f"Error: Configuration file not found at {config_path}")
            raise
        except ParseError:
            print(f"Error: Could not parse TOML file at {config_path}. Check syntax.")
            raise
        except IOError as e:
            print(f"Error reading configuration file {config_path}: {e}")
            raise

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