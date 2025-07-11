# Standard imports
import json
import time
import logging
from typing import Optional, Tuple, Union, Dict, Any, List
from pathlib import Path
# Local imports
from . import LoggerUtils
from . import CompressionUtils
# Third-party imports
import numpy as np
from collections import OrderedDict

class Spectrum:
    """
    Class to store and manipulate an X-ray fluorescence spectrum.
    """
    FORMAT_VERSION = "1.0" # Version for the custom JSON format

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes an empty Spectrum object.

        Args:
            logger: Optional logger instance. If None, a new one named "Spectrum"
                    will be created using LoggerUtils.
        """
        self.logger = logger if logger else LoggerUtils.get_logger("Spectrum")
        self._raw_counts: Optional[np.ndarray] = None
        self._background_counts: Optional[np.ndarray] = None
        # Linear calibration: energy = slope_a * channel + intercept_b
        self._cal_a: float = 1.0 # eV per channel (slope)
        self._cal_b: float = 0.0 # eV at channel 0 (intercept)
        self._metadata: Dict[str, Any] = OrderedDict() # Store metadata

    def set_raw_counts(self, counts: Union[List[int], np.ndarray]) -> None:
        """
        Sets the raw spectrum counts.

        Args:
            counts: A list or NumPy array of counts per channel.
        """
        if isinstance(counts, list):
            self._raw_counts = np.array(counts, dtype=np.int32)
        elif isinstance(counts, np.ndarray):
            # Ensure dtype is appropriate, copy to avoid external modification
            self._raw_counts = counts.astype(np.int32, copy=True)
        else:
            raise TypeError("counts must be a list or NumPy array.")

        if np.any(self._raw_counts < 0):
             self.logger.warning("[SPECTRUM] Raw counts contain negative values.")
             self._raw_counts = np.maximum(0, self._raw_counts)

        # Reset background if the number of channels changes implicitly
        if self._background_counts is None or len(self._raw_counts) != len(self._background_counts):
            if self._background_counts is not None: # Log only if overwriting non-None
                self.logger.warning("[SPECTRUM] Number of channels changed or background mismatch. Resetting background to zeros.")
            self._reset_background()
        self.logger.debug(f"[SPECTRUM] Raw counts set with {len(self._raw_counts)} channels.")

    def set_calibration(self, slope_a: float, intercept_b: float) -> None:
        """
        Sets the linear energy calibration constants (Energy = A * channel + B).

        Args:
            slope_a: The slope (A) in eV/channel.
            intercept_b: The intercept (B) in eV for channel 0.
        """
        if not isinstance(slope_a, (int, float)) or not isinstance(intercept_b, (int, float)):
            raise TypeError("Calibration constants A and B must be numeric.")
        self._cal_a = float(slope_a)
        self._cal_b = float(intercept_b)
        self.logger.debug(f"[SPECTRUM] Calibration set: A={self._cal_a}, B={self._cal_b}")

    def get_calibration(self) -> Tuple[float, float]:
        """Returns the calibration constants (A, B)."""
        return self._cal_a, self._cal_b

    def get_num_channels(self) -> int:
        """Returns the number of channels in the spectrum."""
        return len(self._raw_counts) if self._raw_counts is not None else 0

    def _calculate_energy_axis(self) -> Optional[np.ndarray]:
        """Internal helper to calculate the energy axis based on calibration."""
        num_channels = self.get_num_channels()
        if num_channels > 0:
            channels = np.arange(num_channels)
            energy = self._cal_a * channels + self._cal_b  # Energy = A * channel + B
            return energy
        return None

    def _reset_background(self) -> None:
        """Internal helper to set the background to zeros matching raw counts shape."""
        if self._raw_counts is not None:
            # Create a zeros array with the same shape and type as raw_counts
            self._background_counts = np.zeros_like(self._raw_counts, dtype=np.int32)
            self.logger.debug("[SPECTRUM] Background reset to array of zeros.")
        else:
            # If no raw counts, background should also be None
            self._background_counts = None
            # Log a warning because this function shouldn't ideally be called without raw counts
            self.logger.warning("[SPECTRUM] _reset_background called but no raw counts exist.")

    def get_data(self, use_energy_axis: bool = False, without_background: bool = False) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Returns the spectrum data (optionally background-subtracted) vs channels or energy.

        Args:
            use_energy_axis: If True, returns energy (eV) vs counts on the x-axis.
                             If False, returns channel vs counts. Defaults to False.
            without_background: If True, returns background-subtracted counts on the y-axis.
                                If False, returns raw counts. Defaults to False.

        Returns:
            A tuple (x_axis, y_counts) or None if no data is set or an error occurs.
            x_axis is either channel numbers or energy in eV.
            y_counts is either raw counts or background-subtracted counts (clipped at zero).
        """
        # Determine which counts to use (y-axis)
        y_counts: Optional[np.ndarray] = None
        if without_background:
            y_counts = self.get_counts_without_background()
            if y_counts is None:
                # This typically means raw_counts was None, which get_counts_without_background handles
                self.logger.warning("[SPECTRUM] Cannot get background-subtracted data (raw counts likely missing).")
                return None
        else:
            y_counts = self._raw_counts
            if y_counts is None:
                self.logger.warning("[SPECTRUM] No raw counts data available.")
                return None

        # Determine which axis to use (x-axis) based on the length of the selected y_counts
        num_channels = len(y_counts)
        x_axis: Optional[np.ndarray] = None
        if use_energy_axis:
            # Calculate energy axis based on the number of channels in y_counts
            channels_for_cal = np.arange(num_channels)
            x_axis = self._cal_a * channels_for_cal + self._cal_b
            if x_axis is None: # Should not happen if num_channels > 0
                 self.logger.error("[SPECTRUM] Failed to calculate energy axis.")
                 return None
        else:
            # Return channel axis corresponding to y_counts
            x_axis = np.arange(num_channels)

        return x_axis, y_counts

    def add_metadata(self, metadata_dict: Dict[str, Any]) -> None:
        """
        Adds or updates metadata associated with the spectrum.

        Args:
            metadata_dict: A dictionary containing metadata key-value pairs.
        """
        if not isinstance(metadata_dict, dict):
            raise TypeError("metadata_dict must be a dictionary.")
        self._metadata.update(metadata_dict)
        self.logger.debug(f"[SPECTRUM] Metadata updated: {metadata_dict}")

    def get_metadata(self) -> Dict[str, Any]:
        """Returns the current metadata dictionary."""
        return self._metadata.copy() # Return a copy

    def set_background(self, background_spectrum: 'Spectrum') -> None:
        """
        Sets another Spectrum object as the background for this spectrum.

        Args:
            background_spectrum: A Spectrum object containing the background data.

        Raises:
            TypeError: If background_spectrum is not a Spectrum instance.
            ValueError: If the number of channels does not match the main spectrum.
        """
        if not isinstance(background_spectrum, Spectrum):
            raise TypeError("background_spectrum must be an instance of Spectrum.")
        if self._raw_counts is None:
             raise ValueError("Cannot set background before setting raw counts for the main spectrum.")

        bg_counts = background_spectrum._raw_counts # Access internal directly
        if bg_counts is None:
             raise ValueError("The provided background spectrum object does not contain raw counts.")

        if self.get_num_channels() != len(bg_counts):
            raise ValueError(f"Channel count mismatch: Main spectrum has {self.get_num_channels()} channels, background has {len(bg_counts)} channels.")

        self._background_counts = bg_counts.astype(np.int32, copy=True) # Store a copy
        self.logger.debug(f"[SPECTRUM] Background spectrum set with {len(self._background_counts)} channels.")

    def reset_background(self) -> None:
        """Resets the background spectrum to an array of zeros."""
        self._reset_background() # Call the helper

    def get_counts_without_background(self) -> Optional[np.ndarray]:
        """
        Returns the raw counts minus the background counts.
        Counts are clipped at zero (no negative counts).
        Returns:
            A NumPy array of background-subtracted counts, or None if no raw data.
        """
        if self._raw_counts is None:
            return None

        # Assume _background_counts is always an array (zeros or real) if _raw_counts exists
        if self._background_counts is None: # Should only happen if _reset_background failed when raw_counts was set
            self.logger.error("[SPECTRUM] Background is None despite raw counts existing. Resetting background.")
            self._reset_background()
            if self._background_counts is None: # If reset still failed
                return self._raw_counts.copy() # Fallback

        if len(self._raw_counts) != len(self._background_counts):
            self.logger.error("[SPECTRUM] Channel mismatch between raw and background counts during subtraction. Resetting background and returning raw counts.")
            self._reset_background() # Attempt to fix for future calls
            return self._raw_counts.copy()

        # Subtract (background might be zeros or actual data) and clip at zero
        subtracted_counts = np.maximum(0, self._raw_counts - self._background_counts)
        return subtracted_counts

    def save_as_mca(self, filename: Union[str, Path]) -> None:
        """
        Saves the spectrum counts to a MCA text file.

        This version ONLY writes the data block (counts per channel)
        preceded by "<<DATA>>" and followed by "<<END>>". No other metadata
        or headers are included.

        Args:
            filename: The path to the file to save (e.g., 'my_spectrum.mca').
        """
        if self._raw_counts is None:
            raise ValueError("[SPECTRUM] Cannot save MCA file: No raw counts data available.")
        
        filepath = Path(filename).with_suffix(".mca")
        self.logger.info(f"[SPECTRUM] Saving spectrum counts to MCA file: {filepath}")

        try:
            with filepath.open('w', encoding='utf-8') as f:
                # Write only the DATA block
                f.write("<<DATA>>\n")
                for count in self._raw_counts:
                    f.write(f"{count}\n")
                f.write("<<END>>\n")
            self.logger.info(f"[SPECTRUM] Spectrum counts successfully saved to {filepath}")
        except IOError as e:
             self.logger.error(f"[SPECTRUM] Failed to write MCA file {filepath}: {e}")
             raise IOError(f"Failed to write MCA file {filepath}: {e}") # Re-raise standard IOError

    def load_from_mca(self, filename: Union[str, Path]) -> None:
        """
        Loads spectrum counts from a MCA text file, replacing current data.

        This simplified version ONLY reads integer values found between lines
        starting with "<<DATA>>" and "<<END>>". All other lines and metadata
        are ignored. Existing calibration and metadata in the
        object are NOT reset by this method.

        Args:
            filename: The path to the MCA file to load.
        """
        filepath = Path(filename).with_suffix(".mca")
        self.logger.info(f"[SPECTRUM] Loading spectrum counts from MCA file: {filepath}")
        if not filepath.is_file():
            raise FileNotFoundError(f"[SPECTRUM] MCA file not found: {filepath}")

        raw_counts_list = []
        in_data_section = False

        try:
            with filepath.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue

                    if line.startswith("<<DATA>>"):
                        in_data_section = True
                        continue # Don't try to parse the tag itself as data
                    # Any other tag stops the data section
                    elif line.startswith("<<"):
                        in_data_section = False
                        # If we hit <<END>>, we can stop reading early
                        if line.startswith("<<END>>"):
                            break
                        continue

                    if in_data_section:
                        try:
                             raw_counts_list.append(int(line))
                        except ValueError:
                             self.logger.warning(f"Could not parse data line as integer: '{line}'")
                             continue

            if raw_counts_list:
                self.set_raw_counts(raw_counts_list)
            else:
                self.logger.warning("[SPECTRUM] No valid data points found...")
                self._raw_counts = np.array([], dtype=np.int32)
                self._reset_background() # Ensure background is also None/empty

            self.logger.info(f"[SPECTRUM] Spectrum counts successfully loaded from {filepath} ({self.get_num_channels()} channels).")

        except IOError as e:
             self.logger.error(f"[SPECTRUM] Failed to read MCA file {filepath}: {e}")
             raise IOError(f"Failed to read MCA file {filepath}: {e}")
        except Exception as e:
            self.logger.exception(f"[SPECTRUM] An unexpected error occurred loading MCA file {filepath}")
            raise # Re-raise the original exception

    def clear(self) -> None:
        """
        Clears all data from the spectrum.
        """
        self._raw_counts = None
        self._background_counts = None
        self._cal_a = 1.0
        self._cal_b = 0.0
        self._metadata = OrderedDict()

    def get_as_json(self) -> dict:
        """
        Returns the spectrum data as a JSON-serializable dictionary.
        """
        return {
            "format_version": self.FORMAT_VERSION,
            "num_channels": self.get_num_channels(),
            "calibration_a": self._cal_a,
            "calibration_b": self._cal_b,
            "metadata": self._metadata,
            "raw_counts": self._raw_counts.tolist(),
            "background_counts": self._background_counts.tolist() if self._background_counts is not None else None,
        }

    def load_from_json_string(self, json_string: str) -> None:
        """
        Loads spectrum data from a JSON string.
        """
        # Clear existing data
        self.clear()
        # Load
        data = json.loads(json_string)
        file_version = data.get("format_version")
        if file_version != self.FORMAT_VERSION:
            self.logger.warning(f"[SPECTRUM] Loading JSON file with version {file_version}, expected {self.FORMAT_VERSION}. Attempting to load anyway.")

        self.set_calibration(data.get('calibration_a', 1.0), data.get('calibration_b', 0.0))
        self.add_metadata(data.get('metadata', {}))

        raw_counts = data.get('raw_counts')
        if raw_counts is not None and isinstance(raw_counts, list):
            self.set_raw_counts(np.array(raw_counts, dtype=np.int32))
        else:
            raise ValueError("[SPECTRUM] JSON file 'raw_counts' is not a list or is missing.")

        bg_counts = data.get('background_counts')
        if bg_counts is not None and isinstance(bg_counts, list):
            background_spectrum = Spectrum()
            background_spectrum.set_raw_counts(np.array(bg_counts, dtype=np.int32))
            try:
                self.set_background(background_spectrum)
            except ValueError as e:
                self.logger.warning(f"[SPECTRUM] Failed to set background from JSON: {e}. Resetting background to zeros.")
                self._reset_background()
        elif self._background_counts is not None:
            self.logger.debug("[SPECTRUM] JSON file has no background_counts, resetting background to zeros.")
            self._reset_background()

        if "num_channels" in data and data["num_channels"] != self.get_num_channels():
                self.logger.warning(f"[SPECTRUM] Number of channels in JSON ({data['num_channels']}) does not match length of loaded raw_counts ({self.get_num_channels()}).")


    def save_as_json(self,
                     filename: Union[str, Path],
                     compressed: bool = False,
                     compresslevel: int = 9) -> None:
        """
        Saves the spectrum data to JSON. If compressed=True, it saves the
        uncompressed JSON first, then compresses it using CompressionUtils,
        and finally removes the uncompressed file.

        Args:
            filename: The base path for the file (e.g., 'my_spectrum.json').
                      Extension will be forced to .json.
            compressed: If True, saves compressed via CompressionUtils after
                        saving the uncompressed version first. Defaults to False.
            compresslevel: Compression level (0-9) used if compressed is True.
                           Defaults to 9.
        """
        if self._raw_counts is None:
             raise ValueError("[SPECTRUM] Cannot save JSON file: No raw counts data available.")

        filepath = Path(filename).with_suffix(".json")
        operation_desc = "compressed JSON" if compressed else "JSON"
        self.logger.info(f"[SPECTRUM] Saving spectrum to {operation_desc} file (base: {filepath})")

        data_to_save = self.get_as_json()

        try:
            # Step 1: Always save uncompressed first
            with filepath.open('w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
            self.logger.info(f"[SPECTRUM] Uncompressed JSON saved to {filepath}")

            # Step 2: Compress if requested
            if compressed:
                self.logger.debug(f"[SPECTRUM] Compressing {filepath}...")
                try:
                    CompressionUtils.compress_file_gz(
                        input_filepath=filepath,  # .gz extension handled by CompressionUtils
                        compresslevel=compresslevel,
                        remove_original=True # Remove the original uncompressed file
                    )
                    self.logger.info(f"[SPECTRUM] Successfully compressed")
                except Exception as e_comp:
                    self.logger.error(f"[SPECTRUM] Compression failed for {filepath}: {e_comp}")
                    raise IOError(f"Compression failed for {filepath}: {e_comp}") from e_comp

        except IOError as e:
             self.logger.error(f"[SPECTRUM] Failed to write/compress {operation_desc} file {filepath}: {e}")
             raise IOError(f"Failed to write/compress {operation_desc} file {filepath}: {e}") from e
        except TypeError as e:
            self.logger.error(f"[SPECTRUM] Failed to serialize data to JSON: {e}. Check metadata types.")
            raise TypeError(f"Failed to serialize data to JSON: {e}") from e
        except Exception as e:
            self.logger.exception(f"[SPECTRUM] An unexpected error occurred saving {filepath}")
            raise

    def load_from_json(self, filename: Union[str, Path], compressed: bool = False) -> None:
        """
        Loads spectrum data from JSON. If compressed=True, it decompresses
        the file using CompressionUtils first, loads the data, and then removes
        the decompressed file.

        Args:
            filename: The path to the JSON file (e.g., 'my_spectrum.json') or the
                      base path if compressed is True.
            compressed: If True, attempts decompression via CompressionUtils first.
                        Defaults to False.
        """
        filepath = Path(filename).with_suffix(".json")
        operation_desc = "compressed JSON" if compressed else "JSON"
        self.logger.info(f"[SPECTRUM] Loading spectrum from {operation_desc} file")

        try:
            # Step 1: Decompress if requested
            if compressed:
                self.logger.debug(f"[SPECTRUM] Decompressing file from {filepath}...")
                try:
                    CompressionUtils.decompress_file_gz(
                        input_filepath=filepath, # .gz extension handled by CompressionUtils
                    )
                    self.logger.info(f"[SPECTRUM] Successfully decompressed to: {filepath}")
                except (FileNotFoundError, IOError) as e_decomp:
                    self.logger.error(f"[SPECTRUM] Decompression failed for file derived from {filepath}: {e_decomp}")
                    if isinstance(e_decomp, FileNotFoundError):
                         raise FileNotFoundError(f"[SPECTRUM] Compressed file not found for base {filepath}: {e_decomp}") from e_decomp
                    else:
                         raise IOError(f"[SPECTRUM] Decompression failed for base {filepath}: {e_decomp}") from e_decomp
                except Exception as e_decomp_other:
                    self.logger.error(f"[SPECTRUM] Unexpected decompression error for {filepath}: {e_decomp_other}")
                    raise IOError(f"[SPECTRUM] Unexpected decompression error for {filepath}: {e_decomp_other}") from e_decomp_other

            # Step 2: Check if the target uncompressed file exists now
            if not filepath.is_file():
                raise FileNotFoundError(f"[SPECTRUM] Target JSON file not found: {filepath}")

            # Step 3: Load and parse the uncompressed JSON
            with filepath.open('r', encoding='utf-8') as f:
                self.load_from_json_string(f.read())
            
            # Step 4: Remove the uncompressed file if it was decompressed
            if compressed:
                try:
                    filepath.unlink()  # Remove the uncompressed file
                    self.logger.debug(f"[SPECTRUM] Removed uncompressed file: {filepath}")
                except Exception as e_unlink:
                    self.logger.error(f"[SPECTRUM] Failed to remove uncompressed file {filepath}: {e_unlink}")
                    raise IOError(f"[SPECTRUM] Failed to remove uncompressed file {filepath}: {e_unlink}") from e_unlink

            self.logger.info(f"[SPECTRUM] Spectrum successfully loaded from {filepath} ({self.get_num_channels()} channels).")

        except (FileNotFoundError, IOError) as e:
             self.logger.error(f"[SPECTRUM] Failed to read/access {operation_desc} file {filepath}: {e}")
             raise
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
             self.logger.exception(f"[SPECTRUM] Failed to parse JSON file {filepath}")
             raise ValueError(f"[SPECTRUM] Failed to parse JSON file {filepath}: {e}") from e
        except Exception as e:
             self.logger.exception(f"[SPECTRUM] An unexpected error occurred loading {filepath}")
             raise

    def show(self):
        """
        Opens a SpectrumViewer window to display the spectrum.
        """
        from . import SpectrumViewer

        if self._raw_counts is None:
            self.logger.error("[SPECTRUM] Cannot view: No raw counts data available.")
            return

        viewer = SpectrumViewer(spectrum=self)
        viewer.show_and_exec()

    def test_generate_3d_spectrum_folder(
        self,
        output_folder: Union[str, Path],
        grid_points: Tuple[int, int, int],
        channels_of_interest: List[int],
        physical_size: Optional[Tuple[float, float, float]] = None,
        total_num_channels: int = 2048,
        max_intensity_signal: int = 1000,
        base_noise_max_count: int = 10,
        sphere_center_coords: Optional[Tuple[float, float, float]] = None,
        sphere_radius: Optional[float] = None,
        default_calibration_a: float = 0.01, # Example: 0.01 keV/channel
        default_calibration_b: float = 0.0,  # Example: 0 keV offset
        save_compressed: bool = False,
        num_detectors: int = 4
    ) -> None:
        """
        Generates a folder of 3D spectrum data, with a spherical region of
        higher intensity in specified channels.

        Coordinates are given by "position" field containing "x", "y", "z" in the metadata of each spectrum.

        The intensity for 'channels_of_interest' will be highest at the sphere's center
        and fall off linearly to the sphere's edge. Outside the sphere, these channels
        will only contain base noise. Other channels will always contain base noise.

        Args:
            output_folder: Path to the folder where spectrum files will be saved.
                        It will be created if it doesn't exist.
            grid_points: A tuple (nx, ny, nz) for the number of sampling points in each axis.
            channels_of_interest: List of channel indices that will have the spherical signal.
            physical_size: Optional tuple (Lx, Ly, Lz) for the physical dimensions of the space.
                         If None, defaults to grid_points values (1 unit per point).
            total_num_channels: Total number of channels in each spectrum.
            max_intensity_signal: Maximum count value for the added signal at the sphere's center
                                for the channels_of_interest.
            base_noise_max_count: Maximum count for the uniform random noise U[0, base_noise_max_count]
                                present in all channels.
            sphere_center_coords: Optional (cx, cy, cz) for the sphere's center in physical coordinates.
                                If None, defaults to the geometric center of the physical space.
            sphere_radius: Optional radius of the sphere in physical units. If None, defaults to 40% of the
                        smallest physical dimension.
            default_calibration_a: Default 'A' calibration parameter (e.g., energy_per_channel).
            default_calibration_b: Default 'B' calibration parameter (e.g., energy_at_channel_0).
            save_compressed: Whether to save spectrum files as compressed JSON.
                            This depends on `CompressionUtils` being available to the `Spectrum` class.
            num_detectors: Number of detectors to simulate at each grid point. Each detector will have
                         slight variations in noise levels, signal intensities, and calibration parameters.
        """

        output_folder_path = Path(output_folder)
        try:
            output_folder_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Could not create output folder {output_folder_path}: {e}")
            return

        self.logger.info(f"Generating spectra in: {output_folder_path.resolve()}")

        nx, ny, nz = grid_points
        if not (nx > 0 and ny > 0 and nz > 0):
            self.logger.error("Grid points must be positive integers.")
            return

        # Set physical dimensions (default: 1 unit per grid point)
        if physical_size is None:
            Lx, Ly, Lz = float(nx), float(ny), float(nz)
        else:
            Lx, Ly, Lz = physical_size
            if not (Lx > 0 and Ly > 0 and Lz > 0):
                self.logger.error("Physical dimensions must be positive.")
                return

        # Calculate physical coordinates for each grid point
        # Grid points go from 0 to n-1, physical coordinates from 0 to L
        dx = Lx / (nx - 1) if nx > 1 else 0
        dy = Ly / (ny - 1) if ny > 1 else 0
        dz = Lz / (nz - 1) if nz > 1 else 0

        # Determine sphere properties in physical coordinates
        if sphere_center_coords is None:
            actual_cx, actual_cy, actual_cz = Lx / 2.0, Ly / 2.0, Lz / 2.0
        else:
            actual_cx, actual_cy, actual_cz = sphere_center_coords
        
        actual_R = sphere_radius if sphere_radius is not None else (min(Lx, Ly, Lz) * 0.4)
        
        if actual_R <= 0:
            self.logger.info("Sphere radius is non-positive. No spherical signal will be generated.")
            # Continue to generate noise-only spectra if R <= 0

        self.logger.info(f"Grid points: {grid_points}")
        self.logger.info(f"Physical size: ({Lx:.2f}, {Ly:.2f}, {Lz:.2f})")
        self.logger.info(f"Spatial resolution: dx={dx:.3f}, dy={dy:.3f}, dz={dz:.3f}")
        self.logger.info(f"Sphere properties: center=({actual_cx:.2f}, {actual_cy:.2f}, {actual_cz:.2f}), radius={actual_R:.2f}")
        self.logger.info(f"Spectrum details: total_channels={total_num_channels}, max_signal={max_intensity_signal}, base_noise_max={base_noise_max_count}")

        # Validate channels of interest
        valid_channels_of_interest = []
        for ch_idx in channels_of_interest:
            if 0 <= ch_idx < total_num_channels:
                valid_channels_of_interest.append(ch_idx)
            else:
                self.logger.warning(f"Channel index {ch_idx} is out of bounds (0-{total_num_channels-1}) and will be ignored.")
        
        if not valid_channels_of_interest and actual_R > 0:
            self.logger.warning("No valid channels_of_interest provided for the signal, but sphere radius is positive.")
        self.logger.info(f"Signal will be applied to channels: {valid_channels_of_interest}")

        # Generate spectra for each point in the 3D grid
        generated_count = 0
        
        # Generate detector-specific variations dynamically
        detector_variations = {}
        for i in range(num_detectors):
            if i == 0:
                # Reference detector (no variations)
                detector_variations[i] = {"noise_factor": 1.0, "signal_factor": 1.0, "calibration_offset": 0.0}
            else:
                # Generate slight variations for other detectors
                noise_factor = 1.0 + (i - 1) * 0.05 * (1 if i % 2 == 1 else -1)  # ±5% per detector
                signal_factor = 1.0 + (i - 1) * 0.03 * (1 if i % 2 == 0 else -1)  # ±3% per detector  
                calibration_offset = (i - 1) * 0.0005 * (1 if i % 2 == 1 else -1)  # Small calibration variations
                
                detector_variations[i] = {
                    "noise_factor": noise_factor,
                    "signal_factor": signal_factor,
                    "calibration_offset": calibration_offset
                }
        
        for x_idx in range(nx):
            for y_idx in range(ny):
                for z_idx in range(nz):
                    # Calculate physical coordinates for this grid point
                    x_phys = x_idx * dx
                    y_phys = y_idx * dy
                    z_phys = z_idx * dz

                    # Calculate distance to sphere center using physical coordinates
                    distance = np.sqrt((x_phys - actual_cx)**2 + 
                                    (y_phys - actual_cy)**2 + 
                                    (z_phys - actual_cz)**2)

                    in_sphere = (actual_R > 0 and distance <= actual_R)
                    
                    # Generate spectra for each detector at this position
                    for detector_id in range(num_detectors):
                        spec = Spectrum(logger=self.logger)
                        
                        # Get detector-specific variations
                        variations = detector_variations[detector_id]
                        
                        # Apply detector-specific noise variation
                        detector_noise_max = int(base_noise_max_count * variations["noise_factor"])
                        base_counts = np.random.randint(0, detector_noise_max + 1, 
                                                        size=total_num_channels, dtype=np.int32)
                        current_counts = base_counts.copy()

                        # Add signal to channels of interest if inside the sphere
                        if in_sphere:
                            # Linear falloff: intensity_factor = 1.0 at center (d=0), 0.0 at edge (d=R)
                            intensity_factor = 1.0 - (distance / actual_R)
                            
                            for ch_idx in valid_channels_of_interest:
                                # Apply detector-specific signal variation
                                detector_signal = int(max_intensity_signal * intensity_factor * variations["signal_factor"])
                                current_counts[ch_idx] += detector_signal
                        
                        spec.set_raw_counts(current_counts)
                        
                        # Apply detector-specific calibration variation
                        detector_cal_a = default_calibration_a + variations["calibration_offset"]
                        spec.set_calibration(slope_a=detector_cal_a, intercept_b=default_calibration_b)
                        
                        metadata: Dict[str, Any] = {
                            "position": {
                                "x": float(f"{x_phys:.3f}"),
                                "y": float(f"{y_phys:.3f}"),
                                "z": float(f"{z_phys:.3f}")
                            },
                            "grid_indices": {
                                "x_idx": x_idx,
                                "y_idx": y_idx,
                                "z_idx": z_idx
                            },
                            "is_in_sphere": bool(in_sphere),
                            "distance_to_center": float(f"{distance:.3f}"),
                            "sphere_details": {"center": (actual_cx, actual_cy, actual_cz), "radius": actual_R},
                            "physical_size": (Lx, Ly, Lz),
                            "spatial_resolution": (dx, dy, dz),
                            "device_id": detector_id
                        }
                        spec.add_metadata(metadata)

                        # Define filename with detector ID and save
                        filename = output_folder_path / f"spectrum_{x_idx:03d}_{y_idx:03d}_{z_idx:03d}_det{detector_id}.json"
                        try:
                            # The Spectrum class's save_as_json handles compression details
                            spec.save_as_json(filename, compressed=save_compressed)
                            generated_count += 1
                        except Exception as e:
                            self.logger.error(f"Failed to save spectrum {filename}: {e}")
                
            self.logger.info(f"Progress: Generated spectra for x_slice = {x_idx + 1}/{nx}")

        self.logger.info(f"Finished generating {generated_count} spectra in {output_folder_path.resolve()}.")
        
if __name__ == "__main__":
    # Example usage
    spectrum = Spectrum()
    
    # Generate 2D test dataset: 10x10 points in a 2x2 physical space (with z=1 for pseudo-2D)
    spectrum.test_generate_3d_spectrum_folder(
        output_folder="test_spectra_2d",
        grid_points=(10, 10, 1),  # 10 points per dimension, 1 point in z
        physical_size=(2.0, 2.0, 0.1),  # 2x2 physical dimensions, thin z
        channels_of_interest=[0, 1, 2],
        total_num_channels=1024,
        max_intensity_signal=1000,
        base_noise_max_count=10,
        sphere_center_coords=(1.0, 1.0, 0.05),  # Center of the 2x2 space
        sphere_radius=0.8,  # Radius in physical units
        default_calibration_a=0.01,
        default_calibration_b=0.0,
        save_compressed=False,
        num_detectors=4  # Number of detectors at each point
    )
    # spectrum.test_generate_3d_spectrum_folder(
    #     output_folder="test_spectra",
    #     dimensions=(10, 10, 10),
    #     channels_of_interest=[0, 1, 2],
    #     total_num_channels=1024,
    #     max_intensity_signal=1000,
    #     base_noise_max_count=10,
    #     sphere_center_coords=(5, 5, 5),
    #     sphere_radius=5,
    #     default_calibration_a=0.01,
    #     default_calibration_b=0.0,
    #     save_compressed=False
    # )