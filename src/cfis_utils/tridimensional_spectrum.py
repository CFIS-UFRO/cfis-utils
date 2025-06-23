# Standard imports
import logging
from typing import Optional, Tuple, Dict, Union
from pathlib import Path
import json
# Local imports
from . import LoggerUtils
from . import Spectrum
from . import CompressionUtils
# Third-party imports
import numpy as np

class TridimensionalSpectrum:
    """
    Class to store and manipulate multiple fluorescence spectra with spatial coordinates.
    """
    
    FORMAT_VERSION = "1.0" # Version for the JSON format
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes an empty TridimensionalSpectrum object.

        Args:
            logger: Optional logger instance. If None, a new one named "TridimensionalSpectrum"
                    will be created using LoggerUtils.
        """
        self.logger = logger if logger else LoggerUtils.get_logger("TridimensionalSpectrum")
        self._spectra: Dict[Tuple[float, float, float], Spectrum] = dict() # Store spectra
    
    def clear(self) -> None:
        """
        Clears all spectra from the collection.
        """
        self.logger.debug("[TRIDIMENSIONAL SPECTRUM] Clearing all spectra from the collection.")
        self._spectra.clear()

    def load_from_folder(self, folder_path: Union[str, Path]) -> None:
        """
        Loads multiple fluorescence spectra from a folder.

        Args:
            folder_path: Path to the folder containing the spectrum files.
        """
        self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Loading spectra from folder {folder_path}")
        # Validate
        folder_path = Path(folder_path)
        if not folder_path.is_dir():
            raise ValueError(f"The specified path {folder_path} is not a directory.")
        if not folder_path.exists():
            raise FileNotFoundError(f"The specified path {folder_path} does not exist.")
        # Clear existing spectra
        self.clear()
        # Iterate over the files
        for i, file_path in enumerate(folder_path.iterdir()):
            self.logger.debug(f"[TRIDIMENSIONAL SPECTRUM] Loading spectrum {i+1}/{len(list(folder_path.iterdir()))}")
            self.add_new_spectrum_from_file(file_path)
        # Final message
        self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Successfully loaded {len(self._spectra)} spectra from folder {folder_path}")

    def add_new_spectrum_from_file(self, file_path: Union[str, Path]) -> None:
        """
        Adds a new spectrum to the collection from a JSON file.

        Args:
            file_path: Path to the JSON file containing the spectrum data.
        """
        self.logger.debug(f"[TRIDIMENSIONAL SPECTRUM] Adding new spectrum from file {file_path}")
        # Validate
        file_path = Path(file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"The specified path {file_path} does not exist.")
        if file_path.suffix != ".json":
            raise ValueError(f"The specified path {file_path} is not a JSON file.")
        # Init spectrum object
        spectrum = Spectrum(logger=self.logger)
        # Load spectrum from file
        spectrum.load_from_json(file_path)
        # Get metadata
        metadata = spectrum.get_metadata()
        # Coordinates can be present in two formats:
        # 1. As separate "x", "y", "z" fields in metadata
        # 2. As a "position" field containing x, y, z coordinates
        if "position" in metadata:
            # Case 2: coordinates are in "position" field
            position = metadata["position"]
            if not isinstance(position, dict):
                raise ValueError(f"Metadata 'position' field must be a dict in {file_path}")
            if "x" not in position or "y" not in position or "z" not in position:
                raise ValueError(f"Metadata 'position' field is missing 'x', 'y', or 'z' coordinates in {file_path}")
            coords = tuple(map(float, [position["x"], position["y"], position["z"]]))
        elif "x" in metadata and "y" in metadata and "z" in metadata:
            # Case 1: coordinates are separate fields
            coords = tuple(map(float, [metadata["x"], metadata["y"], metadata["z"]]))
        else:
            raise ValueError(f"Metadata is missing coordinates. Expected either 'x', 'y', 'z' fields or 'position' field with x, y, z in {file_path}")
        self.add_new_spectrum(spectrum, coords)

    def add_new_spectrum(self, spectrum: Spectrum, coords: Tuple[float, float, float]) -> None:
        """
        Adds a new spectrum to the collection.

        Args:
            spectrum: Spectrum object to add.
            coords: Tuple of coordinates (x, y, z) for the spectrum.
        """
        self.logger.debug(f"[TRIDIMENSIONAL SPECTRUM] Adding new spectrum at coordinates {coords}")
        self._spectra[coords] = spectrum

    def get_spectrum(self, coords: Tuple[float, float, float]) -> Optional[Spectrum]:
        """
        Gets a spectrum from the collection.

        Args:
            coords: Tuple of coordinates (x, y, z) for the spectrum.

        Returns:
            The spectrum at the specified coordinates, or None if not found.
        """
        return self._spectra.get(coords)
        
    def get_spectra(self) -> Dict[Tuple[float, float, float], Spectrum]:
        """
        Returns a copy of the dictionary of spectra.

        Returns:
            A copy of the dictionary of spectra.
        """
        return self._spectra.copy()
        
    def get_num_spectra(self) -> int:
        """
        Returns the number of spectra in the collection.

        Returns:
            The number of spectra in the collection.
        """
        return len(self._spectra)

    def get_spectra_range(self) -> Tuple[float, float, float]:
        """
        Returns the minimum and maximum x, y, and z coordinates of the spectra.

        Returns:
            A tuple (min_x, max_x, min_y, max_y, min_z, max_z).
        """
        coords = np.array(list(self._spectra.keys()))
        ranges = coords.min(axis=0), coords.max(axis=0)
        return {
            "x": {
                "min": ranges[0][0],
                "max": ranges[1][0]
            },
            "y": {
                "min": ranges[0][1],
                "max": ranges[1][1]
            },
            "z": {
                "min": ranges[0][2],
                "max": ranges[1][2]
            }
        }
        
    def save_as_json(self, filename: Union[str, Path], compressed: bool = False, compresslevel: int = 9) -> None:
        """
        Saves the collection of spectra to a JSON file.

        Args:
            filename: The base path for the file (e.g., 'my_spectra.json').
                      Extension will be forced to .json.
            compressed: If True, saves compressed via CompressionUtils after
                        saving the uncompressed version first. Defaults to False.
            compresslevel: Compression level (0-9) used if compressed is True.
                           Defaults to 9.
        """
        # Validate
        filename = Path(filename).with_suffix(".json")
        operation_desc = "compressed JSON" if compressed else "JSON"
        self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Saving spectra to {operation_desc} file (base: {filename})")
        # Create the data dictionary
        spectra_data = {
            "format_version": self.FORMAT_VERSION,
            "spectra": {str(k): v.get_as_json() for k, v in self._spectra.items()}
            }
        # Save uncompressed first
        try:
            with filename.open('w', encoding='utf-8') as f:
                json.dump(spectra_data, f, indent=4)
            self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Uncompressed JSON saved to {filename}")
            # Compress if requested
            if compressed:
                self.logger.debug(f"[TRIDIMENSIONAL SPECTRUM] Compressing {filename}...")
                try:
                    CompressionUtils.compress_file_gz(
                        input_filepath=filename,  # .gz extension handled by CompressionUtils
                        compresslevel=compresslevel,
                        remove_original=True # Remove the original uncompressed file
                    )
                    self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Successfully compressed")
                except Exception as e_comp:
                    self.logger.error(f"[TRIDIMENSIONAL SPECTRUM] Compression failed for {filename}: {e_comp}")
                    raise IOError(f"Compression failed for {filename}: {e_comp}") from e_comp
        except IOError as e:
            self.logger.error(f"[TRIDIMENSIONAL SPECTRUM] Failed to write/compress {operation_desc} file {filename}: {e}")
            raise IOError(f"Failed to write/compress {operation_desc} file {filename}: {e}") from e
        except Exception as e:
            self.logger.exception(f"[TRIDIMENSIONAL SPECTRUM] An unexpected error occurred saving {filename}")
            raise Exception(f"An unexpected error occurred saving {filename}") from e
        
    def load_from_json(self, filename: Union[str, Path], compressed: bool = False) -> None:
        """
        Loads the collection of spectra from a JSON file.

        Args:
            filename: The path to the JSON file containing the spectra data.
            compressed: If True, loads compressed via CompressionUtils. Defaults to False.
        """
        filename = Path(filename).with_suffix(".json")
        operation_desc = "compressed JSON" if compressed else "JSON"
        self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Loading spectra from {operation_desc} file (base: {filename})")

        # Reset current state before loading
        self.clear()

        try:
            # Step 1: Decompress if requested
            if compressed:
                self.logger.debug(f"[TRIDIMENSIONAL SPECTRUM] Decompressing file from {filename}...")
                try:
                    CompressionUtils.decompress_file_gz(
                        input_filepath=filename, # .gz extension handled by CompressionUtils
                    )
                    self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Successfully decompressed to: {filename}")
                except (FileNotFoundError, IOError) as e_decomp:
                    self.logger.error(f"[TRIDIMENSIONAL SPECTRUM] Decompression failed for file derived from {filename}: {e_decomp}")
                    if isinstance(e_decomp, FileNotFoundError):
                        raise FileNotFoundError(f"Decompression failed for file derived from {filename}: {e_decomp}") from e_decomp
                    raise IOError(f"Decompression failed for file derived from {filename}: {e_decomp}") from e_decomp
            # Step 2: Load the JSON file
            with filename.open('r', encoding='utf-8') as f:
                spectra_data = json.load(f)
            self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Successfully loaded {len(spectra_data['spectra'])} spectra from {filename}")
            # Step 3: Load each spectrum
            for coords, spectrum_data in spectra_data['spectra'].items():
                coords = tuple(map(float, coords.replace("(", "").replace(")", "").split(",")))
                spectrum = Spectrum(logger=self.logger)
                spectrum.load_from_json_string(json.dumps(spectrum_data))
                self.add_new_spectrum(spectrum, coords)
            self.logger.info(f"[TRIDIMENSIONAL SPECTRUM] Successfully loaded {len(self._spectra)} spectra from {filename}")
            # Step 4: Remove the decompressed file if it was decompressed
            if compressed:
                try:
                    filename.unlink()  # Remove the decompressed file
                    self.logger.debug(f"[TRIDIMENSIONAL SPECTRUM] Removed decompressed file: {filename}")
                except Exception as e_unlink:
                    self.logger.error(f"[TRIDIMENSIONAL SPECTRUM] Failed to remove decompressed file {filename}: {e_unlink}")
                    raise IOError(f"[TRIDIMENSIONAL SPECTRUM] Failed to remove decompressed file {filename}: {e_unlink}") from e_unlink
        except (FileNotFoundError, IOError) as e:
            self.logger.error(f"[TRIDIMENSIONAL SPECTRUM] Failed to load {operation_desc} file {filename}: {e}")
            raise IOError(f"Failed to load {operation_desc} file {filename}: {e}") from e
        except Exception as e:
            self.logger.exception(f"[TRIDIMENSIONAL SPECTRUM] An unexpected error occurred loading {filename}")
            raise Exception(f"An unexpected error occurred loading {filename}") from e

    def show(self):
        """
        Shows the tridimensional spectrum using the TridimensionalSpectrumViewer class.
        """
        from .tridimensional_spectrum_viewer import TridimensionalSpectrumViewer
        viewer = TridimensionalSpectrumViewer(self)
        viewer.show_and_exec()
        

if __name__ == "__main__":
    # Test
    tridimensional_spectrum = TridimensionalSpectrum()
    tridimensional_spectrum.load_from_folder("./test_spectra_2d")
    tridimensional_spectrum.show()