import sys
import atexit
from typing import Optional
import numpy as np

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QGroupBox, QLabel, QDoubleSpinBox, QPushButton,
    QComboBox, QSplitter, QGridLayout, QSpacerItem, QSizePolicy,
    QSlider, QTabWidget, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer

# Matplotlib imports
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# Import your TridimensionalSpectrum class
from .tridimensional_spectrum import TridimensionalSpectrum


class TridimensionalSpectrumViewer(QMainWindow):
    """
    A 3D spectrum viewer with integrated matplotlib plots and GUI controls.
    
    Features:
    - 3D heatmap visualization with intensity calculated from channel/energy ranges
    - Cross-sectional views (XY, XZ, YZ planes) with interactive sliders
    - Toggle between channel and energy axis for range selection
    - Colormap and transparency controls
    - Interactive matplotlib navigation
    - Automatic QApplication management
    """
    
    _app_instance = None  # Class variable to store app instance
    
    def __init__(self, tridimensional_spectrum: Optional[TridimensionalSpectrum] = None, parent: Optional[QWidget] = None):
        """
        Initialize the TridimensionalSpectrumViewer.
        
        Args:
            tridimensional_spectrum: A TridimensionalSpectrum object to display
            parent: Parent widget (optional)
        """
        # Ensure QApplication exists
        self._ensure_qapplication()
        
        super().__init__(parent)
        
        self.tridimensional_spectrum = tridimensional_spectrum
        self.intensity_data = {}  # Cache for calculated intensities
        self.grid_data = None  # Structured grid data for plotting
        
        # Animation variables
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_threshold_step)
        self.animation_min = 0
        self.animation_max = 1000
        self.animation_current = 0
        self.animation_step = 10
        self.animation_direction = 1  # 1 for forward, -1 for backward
        
        self._setup_ui()
        self._connect_signals()
        
        # Initial setup if data is provided
        if self.tridimensional_spectrum is not None:
            self.update_spectrum_info()
            self.auto_range_all()
            self.calculate_intensities()
            self.update_all_plots()
    
    @classmethod
    def _ensure_qapplication(cls):
        """Ensure a QApplication instance exists."""
        if cls._app_instance is None:
            cls._app_instance = QApplication.instance()
            if cls._app_instance is None:
                cls._app_instance = QApplication(sys.argv)
                
        # Register cleanup function
        atexit.register(cls._cleanup_app)
    
    @classmethod
    def _cleanup_app(cls):
        """Cleanup function for application exit."""
        if cls._app_instance is not None:
            cls._app_instance.quit()
    
    def show_and_exec(self):
        """Show the viewer window and start the Qt event loop."""
        self.show()
        return self._app_instance.exec()
    
    def show_non_blocking(self):
        """Show the viewer window without blocking."""
        self.show()
        return self
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("3D Spectrum Viewer")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create control panel
        control_panel = self._create_control_panel()
        splitter.addWidget(control_panel)
        
        # Create plot panel with tabs
        plot_panel = self._create_plot_panel()
        splitter.addWidget(plot_panel)
        
        # Set splitter proportions (25% controls, 75% plots)
        splitter.setSizes([400, 1200])
    
    def _create_control_panel(self) -> QWidget:
        """Create the control panel with all options."""
        panel = QWidget()
        panel.setMaximumWidth(450)
        panel.setMinimumWidth(350)
        
        layout = QVBoxLayout(panel)
        
        # Range of interest options
        roi_group = QGroupBox("Range of Interest")
        roi_layout = QVBoxLayout(roi_group)
        
        # X-axis type for range selection
        x_axis_layout = QHBoxLayout()
        x_axis_layout.addWidget(QLabel("Range Type:"))
        self.range_type_combo = QComboBox()
        self.range_type_combo.addItems(["Channel", "Energy (eV)"])
        x_axis_layout.addWidget(self.range_type_combo)
        roi_layout.addLayout(x_axis_layout)
        
        # Range selection
        range_layout = QGridLayout()
        
        range_layout.addWidget(QLabel("Min:"), 0, 0)
        self.range_min_spin = QDoubleSpinBox()
        self.range_min_spin.setRange(0, 1e6)
        self.range_min_spin.setDecimals(2)
        self.range_min_spin.setValue(100)
        range_layout.addWidget(self.range_min_spin, 0, 1)
        
        range_layout.addWidget(QLabel("Max:"), 0, 2)
        self.range_max_spin = QDoubleSpinBox()
        self.range_max_spin.setRange(0, 1e6)
        self.range_max_spin.setDecimals(2)
        self.range_max_spin.setValue(200)
        range_layout.addWidget(self.range_max_spin, 0, 3)
        
        roi_layout.addLayout(range_layout)
        
        # Auto-range button for ROI
        self.auto_roi_btn = QPushButton("Auto Range ROI")
        roi_layout.addWidget(self.auto_roi_btn)
        
        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        # Background subtraction
        self.subtract_background_cb = QCheckBox("Subtract Background")
        self.subtract_background_cb.setChecked(True)
        display_layout.addWidget(self.subtract_background_cb)
        
        # Colormap selection
        colormap_layout = QHBoxLayout()
        colormap_layout.addWidget(QLabel("Colormap:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["viridis", "plasma", "inferno", "magma", "hot", "jet", "coolwarm", "RdYlBu"])
        colormap_layout.addWidget(self.colormap_combo)
        display_layout.addLayout(colormap_layout)
        
        # Transparency
        transparency_layout = QHBoxLayout()
        transparency_layout.addWidget(QLabel("Alpha:"))
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.1, 1.0)
        self.alpha_spin.setSingleStep(0.1)
        self.alpha_spin.setDecimals(1)
        self.alpha_spin.setValue(0.7)
        transparency_layout.addWidget(self.alpha_spin)
        display_layout.addLayout(transparency_layout)
        
        # Cross-section controls
        cross_section_group = QGroupBox("Cross-Sections")
        cross_section_layout = QVBoxLayout(cross_section_group)
        
        # Z-slice control
        z_layout = QHBoxLayout()
        z_layout.addWidget(QLabel("Z-slice:"))
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setMinimum(0)
        self.z_slider.setMaximum(10)
        self.z_slider.setValue(5)
        z_layout.addWidget(self.z_slider)
        self.z_value_label = QLabel("5")
        z_layout.addWidget(self.z_value_label)
        cross_section_layout.addLayout(z_layout)
        
        # Y-slice control
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y-slice:"))
        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.setMinimum(0)
        self.y_slider.setMaximum(10)
        self.y_slider.setValue(5)
        y_layout.addWidget(self.y_slider)
        self.y_value_label = QLabel("5")
        y_layout.addWidget(self.y_value_label)
        cross_section_layout.addLayout(y_layout)
        
        # X-slice control
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X-slice:"))
        self.x_slider = QSlider(Qt.Horizontal)
        self.x_slider.setMinimum(0)
        self.x_slider.setMaximum(10)
        self.x_slider.setValue(5)
        x_layout.addWidget(self.x_slider)
        self.x_value_label = QLabel("5")
        x_layout.addWidget(self.x_value_label)
        cross_section_layout.addLayout(x_layout)
        
        # Intensity limits group
        intensity_group = QGroupBox("Intensity Limits")
        intensity_layout = QVBoxLayout(intensity_group)
        
        # Intensity range controls
        intensity_range_layout = QGridLayout()
        
        intensity_range_layout.addWidget(QLabel("Min:"), 0, 0)
        self.intensity_min_spin = QDoubleSpinBox()
        self.intensity_min_spin.setRange(0, 1e9)
        self.intensity_min_spin.setDecimals(0)
        self.intensity_min_spin.setValue(0)
        intensity_range_layout.addWidget(self.intensity_min_spin, 0, 1)
        
        intensity_range_layout.addWidget(QLabel("Max:"), 0, 2)
        self.intensity_max_spin = QDoubleSpinBox()
        self.intensity_max_spin.setRange(0, 1e9)
        self.intensity_max_spin.setDecimals(0)
        self.intensity_max_spin.setValue(1000)
        intensity_range_layout.addWidget(self.intensity_max_spin, 0, 3)
        
        intensity_layout.addLayout(intensity_range_layout)
        
        # Voxel threshold controls
        threshold_layout = QGridLayout()
        
        threshold_layout.addWidget(QLabel("Voxel Threshold:"), 1, 0)
        self.voxel_threshold_spin = QDoubleSpinBox()
        self.voxel_threshold_spin.setRange(0, 1e9)
        self.voxel_threshold_spin.setDecimals(0)
        self.voxel_threshold_spin.setValue(0)
        self.voxel_threshold_spin.setToolTip("Only show voxels with intensity above this threshold")
        threshold_layout.addWidget(self.voxel_threshold_spin, 1, 1, 1, 3)
        
        intensity_layout.addLayout(threshold_layout)
        
        # Animation controls
        animation_layout = QGridLayout()
        
        animation_layout.addWidget(QLabel("Animation Speed (ms):"), 2, 0)
        self.animation_speed_spin = QDoubleSpinBox()
        self.animation_speed_spin.setRange(10, 5000)
        self.animation_speed_spin.setDecimals(0)
        self.animation_speed_spin.setValue(200)
        self.animation_speed_spin.setSuffix(" ms")
        self.animation_speed_spin.setToolTip("Time between animation steps")
        animation_layout.addWidget(self.animation_speed_spin, 2, 1, 1, 3)
        
        intensity_layout.addLayout(animation_layout)
        
        # Buttons layout
        intensity_buttons_layout = QGridLayout()
        
        # Auto-intensity button
        self.auto_intensity_btn = QPushButton("Auto Range")
        intensity_buttons_layout.addWidget(self.auto_intensity_btn, 0, 0)
        
        # Auto-threshold button (sets threshold to 75% between min and max)
        self.auto_threshold_btn = QPushButton("Auto Threshold")
        self.auto_threshold_btn.setToolTip("Set threshold to 75% between min and max intensity")
        intensity_buttons_layout.addWidget(self.auto_threshold_btn, 0, 1)
        
        # Animation buttons
        self.play_threshold_btn = QPushButton("▶ Play")
        self.play_threshold_btn.setToolTip("Animate threshold from min to max intensity")
        intensity_buttons_layout.addWidget(self.play_threshold_btn, 1, 0)
        
        self.stop_threshold_btn = QPushButton("⏹ Stop")
        self.stop_threshold_btn.setToolTip("Stop threshold animation")
        self.stop_threshold_btn.setEnabled(False)
        intensity_buttons_layout.addWidget(self.stop_threshold_btn, 1, 1)
        
        intensity_layout.addLayout(intensity_buttons_layout)
        
        # Control buttons
        buttons_group = QGroupBox("Controls")
        buttons_layout = QVBoxLayout(buttons_group)
        
        self.recalculate_btn = QPushButton("Recalculate Intensities")
        self.reset_btn = QPushButton("Reset View")
        self.export_btn = QPushButton("Export Plots")
        
        buttons_layout.addWidget(self.recalculate_btn)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.export_btn)
        
        # Add all groups to main layout
        layout.addWidget(roi_group)
        layout.addWidget(display_group)
        layout.addWidget(cross_section_group)
        layout.addWidget(intensity_group)
        layout.addWidget(buttons_group)
        
        # Add spacer
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Info panel
        info_group = QGroupBox("Dataset Info")
        info_layout = QVBoxLayout(info_group)
        
        self.info_label = QLabel("No dataset loaded")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("QLabel { font-family: monospace; }")
        info_layout.addWidget(self.info_label)
        
        layout.addWidget(info_group)
        
        return panel
    
    def _create_plot_panel(self) -> QWidget:
        """Create the plot panel with tabs for different views."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 3D View tab
        self.tab_3d = self._create_3d_tab()
        self.tab_widget.addTab(self.tab_3d, "3D View")
        
        # XY Cross-section tab (Z-slice)
        self.tab_xy = self._create_2d_tab("XY")
        self.tab_widget.addTab(self.tab_xy, "XY Cross-section (Z-slice)")
        
        # XZ Cross-section tab (Y-slice)
        self.tab_xz = self._create_2d_tab("XZ")
        self.tab_widget.addTab(self.tab_xz, "XZ Cross-section (Y-slice)")
        
        # YZ Cross-section tab (X-slice)
        self.tab_yz = self._create_2d_tab("YZ")
        self.tab_widget.addTab(self.tab_yz, "YZ Cross-section (X-slice)")
        
        return panel
    
    def _create_3d_tab(self) -> QWidget:
        """Create the 3D visualization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create matplotlib figure and canvas for 3D
        self.figure_3d = Figure(figsize=(10, 8))
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.ax_3d = self.figure_3d.add_subplot(111, projection='3d')
        
        # Create navigation toolbar
        self.toolbar_3d = NavigationToolbar(self.canvas_3d, widget)
        
        # Add to layout
        layout.addWidget(self.toolbar_3d)
        layout.addWidget(self.canvas_3d)
        
        return widget
    
    def _create_2d_tab(self, plane: str) -> QWidget:
        """Create a 2D cross-section tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create matplotlib figure and canvas for 2D
        figure = Figure(figsize=(8, 6))
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)
        
        # Store references
        setattr(self, f'figure_{plane.lower()}', figure)
        setattr(self, f'canvas_{plane.lower()}', canvas)
        setattr(self, f'ax_{plane.lower()}', ax)
        
        # Create navigation toolbar
        toolbar = NavigationToolbar(canvas, widget)
        setattr(self, f'toolbar_{plane.lower()}', toolbar)
        
        # Add to layout
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        
        return widget
    
    def _connect_signals(self):
        """Connect all GUI signals to their handlers."""
        # Range controls
        self.range_type_combo.currentTextChanged.connect(self.on_range_type_changed)
        self.range_min_spin.valueChanged.connect(self.on_range_changed)
        self.range_max_spin.valueChanged.connect(self.on_range_changed)
        self.auto_roi_btn.clicked.connect(self.auto_range_roi)
        
        # Display options
        self.subtract_background_cb.toggled.connect(self.on_display_option_changed)
        self.colormap_combo.currentTextChanged.connect(self.on_display_option_changed)
        self.alpha_spin.valueChanged.connect(self.on_display_option_changed)
        
        # Intensity limits
        self.intensity_min_spin.valueChanged.connect(self.on_display_option_changed)
        self.intensity_max_spin.valueChanged.connect(self.on_display_option_changed)
        self.voxel_threshold_spin.valueChanged.connect(self.on_display_option_changed)
        self.auto_intensity_btn.clicked.connect(self.auto_intensity_range)
        self.auto_threshold_btn.clicked.connect(self.auto_threshold_range)
        
        # Animation controls
        self.play_threshold_btn.clicked.connect(self.start_threshold_animation)
        self.stop_threshold_btn.clicked.connect(self.stop_threshold_animation)
        
        # Sliders
        self.z_slider.valueChanged.connect(self.on_z_slider_changed)
        self.y_slider.valueChanged.connect(self.on_y_slider_changed)
        self.x_slider.valueChanged.connect(self.on_x_slider_changed)
        
        # Buttons
        self.recalculate_btn.clicked.connect(self.recalculate_intensities)
        self.reset_btn.clicked.connect(self.reset_view)
        self.export_btn.clicked.connect(self.export_plots)
    
    def set_tridimensional_spectrum(self, tridimensional_spectrum):
        """Set a new tridimensional spectrum to display."""
        self.tridimensional_spectrum = tridimensional_spectrum
        self.intensity_data.clear()
        self.grid_data = None
        self.update_spectrum_info()
        self.auto_range_all()
        self.calculate_intensities()
        self.update_all_plots()
    
    def update_spectrum_info(self):
        """Update the dataset information display."""
        if self.tridimensional_spectrum is None:
            self.info_label.setText("No dataset loaded")
            return
        
        try:
            num_spectra = self.tridimensional_spectrum.get_num_spectra()
            ranges = self.tridimensional_spectrum.get_spectra_range()
            
            info_text = f"├─ Spectra: {num_spectra}\n"
            info_text += f"├─ X range: [{ranges['x']['min']:.1f}, {ranges['x']['max']:.1f}]\n"
            info_text += f"├─ Y range: [{ranges['y']['min']:.1f}, {ranges['y']['max']:.1f}]\n"
            info_text += f"└─ Z range: [{ranges['z']['min']:.1f}, {ranges['z']['max']:.1f}]\n"
            
            # Update slider ranges
            self.x_slider.setMinimum(int(ranges['x']['min']))
            self.x_slider.setMaximum(int(ranges['x']['max']))
            self.x_slider.setValue(int((ranges['x']['min'] + ranges['x']['max']) / 2))
            
            self.y_slider.setMinimum(int(ranges['y']['min']))
            self.y_slider.setMaximum(int(ranges['y']['max']))
            self.y_slider.setValue(int((ranges['y']['min'] + ranges['y']['max']) / 2))
            
            self.z_slider.setMinimum(int(ranges['z']['min']))
            self.z_slider.setMaximum(int(ranges['z']['max']))
            self.z_slider.setValue(int((ranges['z']['min'] + ranges['z']['max']) / 2))
            
            self.info_label.setText(info_text)
            
        except Exception as e:
            self.info_label.setText(f"Error reading dataset info: {e}")
    
    def auto_range_all(self):
        """Auto-set all ranges based on data."""
        self.auto_range_roi()
        self.auto_intensity_range()
    
    def _calculate_optimal_step(self, min_val, max_val):
        """Calculate optimal step size based on range."""
        range_val = max_val - min_val
        if range_val <= 0:
            return 1
        
        # Simple step calculation based on range
        if range_val <= 10:
            return 1
        elif range_val <= 100:
            return 10
        elif range_val <= 1000:
            return 100
        elif range_val <= 10000:
            return 1000
        else:
            return 10000
    
    def auto_intensity_range(self):
        """Auto-set the intensity range based on current data."""
        if not self.intensity_data:
            return
        
        try:
            intensities = list(self.intensity_data.values())
            if intensities:
                min_intensity = float(np.min(intensities))
                max_intensity = float(np.max(intensities))
                
                # Add some margin (5%)
                intensity_range = max_intensity - min_intensity
                margin = intensity_range * 0.05
                
                final_min = max(0, min_intensity - margin)
                final_max = max_intensity + margin
                
                # Calculate optimal step
                step_size = self._calculate_optimal_step(final_min, final_max)
                
                # Set step size for both spinboxes
                self.intensity_min_spin.setSingleStep(step_size)
                self.intensity_max_spin.setSingleStep(step_size)
                
                # Set values
                self.intensity_min_spin.setValue(final_min)
                self.intensity_max_spin.setValue(final_max)
                
                # Set initial threshold to 3/4 between min and max
                threshold_75 = min_intensity + (max_intensity - min_intensity) * 0.75
                self.voxel_threshold_spin.setValue(threshold_75)
                
                # Set finer step for threshold (1/10 of intensity step, minimum 1)
                threshold_step = max(1, step_size / 10)
                self.voxel_threshold_spin.setSingleStep(threshold_step)
                
        except Exception as e:
            print(f"Error in auto_intensity_range: {e}")
    
    def auto_threshold_range(self):
        """Auto-set the voxel threshold to 75% between min and max intensity."""
        if not self.intensity_data:
            return
        
        try:
            intensities = list(self.intensity_data.values())
            if intensities:
                min_intensity = float(np.min(intensities))
                max_intensity = float(np.max(intensities))
                
                # Set threshold to 75% between min and max intensity
                threshold_75 = min_intensity + (max_intensity - min_intensity) * 0.75
                self.voxel_threshold_spin.setValue(threshold_75)
                
                # Set finer step size for threshold (1/10 of what would be used for intensity)
                intensity_step = self._calculate_optimal_step(min_intensity, max_intensity)
                threshold_step = max(1, intensity_step / 10)
                self.voxel_threshold_spin.setSingleStep(threshold_step)
                
        except Exception as e:
            print(f"Error in auto_threshold_range: {e}")
    
    def start_threshold_animation(self):
        """Start the threshold animation."""
        if not self.intensity_data:
            return
        
        try:
            # Set animation range based on current intensity limits
            self.animation_min = self.intensity_min_spin.value()
            self.animation_max = self.intensity_max_spin.value()
            self.animation_current = self.animation_min
            self.animation_direction = 1
            
            # Calculate step size based on range (finer for animation)
            intensity_step = self._calculate_optimal_step(self.animation_min, self.animation_max)
            self.animation_step = max(1, intensity_step / 10)
            
            # Start timer
            speed = int(self.animation_speed_spin.value())
            self.animation_timer.start(speed)
            
            # Update button states
            self.play_threshold_btn.setEnabled(False)
            self.stop_threshold_btn.setEnabled(True)
            self.play_threshold_btn.setText("▶ Playing...")
            
        except Exception as e:
            print(f"Error starting animation: {e}")
    
    def stop_threshold_animation(self):
        """Stop the threshold animation."""
        self.animation_timer.stop()
        
        # Update button states
        self.play_threshold_btn.setEnabled(True)
        self.stop_threshold_btn.setEnabled(False)
        self.play_threshold_btn.setText("▶ Play")
    
    def animate_threshold_step(self):
        """Perform one step of the threshold animation."""
        try:
            # Update threshold value
            self.voxel_threshold_spin.setValue(self.animation_current)
            
            # Calculate next value
            self.animation_current += self.animation_direction * self.animation_step
            
            # Check bounds and reverse direction if needed
            if self.animation_current >= self.animation_max:
                self.animation_current = self.animation_max
                self.animation_direction = -1
            elif self.animation_current <= self.animation_min:
                self.animation_current = self.animation_min
                self.animation_direction = 1
                
        except Exception as e:
            print(f"Error in animation step: {e}")
            self.stop_threshold_animation()
    
    def auto_range_roi(self):
        """Auto-set the range of interest based on first spectrum."""
        if self.tridimensional_spectrum is None:
            return
        
        try:
            spectra = self.tridimensional_spectrum.get_spectra()
            if not spectra:
                return
            
            # Get first spectrum to determine range
            first_spectrum = next(iter(spectra.values()))
            use_energy = self.range_type_combo.currentText() == "Energy (eV)"
            
            data = first_spectrum.get_data(use_energy_axis=use_energy, without_background=False)
            if data is not None:
                x_axis, _ = data
                self.range_min_spin.setValue(float(np.min(x_axis)))
                self.range_max_spin.setValue(float(np.max(x_axis)))
                
        except Exception as e:
            print(f"Error in auto_range_roi: {e}")
    
    def calculate_intensities(self):
        """Calculate intensities for all spectra based on range of interest."""
        if self.tridimensional_spectrum is None:
            return
        
        try:
            spectra = self.tridimensional_spectrum.get_spectra()
            use_energy = self.range_type_combo.currentText() == "Energy (eV)"
            subtract_bg = self.subtract_background_cb.isChecked()
            range_min = self.range_min_spin.value()
            range_max = self.range_max_spin.value()
            
            self.intensity_data.clear()
            
            for coords, spectrum in spectra.items():
                data = spectrum.get_data(use_energy_axis=use_energy, without_background=subtract_bg)
                if data is not None:
                    x_axis, y_counts = data
                    
                    # Find indices within range of interest
                    mask = (x_axis >= range_min) & (x_axis <= range_max)
                    intensity = np.sum(y_counts[mask])
                    
                    self.intensity_data[coords] = intensity
            
            # Create structured grid data
            self._create_grid_data()
            
        except Exception as e:
            print(f"Error calculating intensities: {e}")
    
    def _create_grid_data(self):
        """Create structured grid data for plotting."""
        if not self.intensity_data:
            return
        
        try:
            coords = list(self.intensity_data.keys())
            intensities = list(self.intensity_data.values())
            
            # Get unique coordinates for each dimension
            x_coords = sorted(set(coord[0] for coord in coords))
            y_coords = sorted(set(coord[1] for coord in coords))
            z_coords = sorted(set(coord[2] for coord in coords))
            
            # Create 3D grid
            X, Y, Z = np.meshgrid(x_coords, y_coords, z_coords, indexing='ij')
            I = np.zeros_like(X, dtype=float)
            
            # Fill intensity grid
            for coord, intensity in self.intensity_data.items():
                x_idx = x_coords.index(coord[0])
                y_idx = y_coords.index(coord[1])
                z_idx = z_coords.index(coord[2])
                I[x_idx, y_idx, z_idx] = intensity
            
            self.grid_data = {
                'X': X, 'Y': Y, 'Z': Z, 'I': I,
                'x_coords': x_coords, 'y_coords': y_coords, 'z_coords': z_coords
            }
            
        except Exception as e:
            print(f"Error creating grid data: {e}")
    
    def update_all_plots(self):
        """Update all plot views."""
        self.update_3d_plot()
        self.update_cross_sections()
    
    def update_3d_plot(self):
        """Update the 3D heatmap plot using voxels."""
        if self.grid_data is None:
            # Clear the entire figure to remove colorbars and other elements
            self.figure_3d.clear()
            self.ax_3d = self.figure_3d.add_subplot(111, projection='3d')
            self.ax_3d.set_title("No data available")
            self.canvas_3d.draw()
            return
        
        try:
            # Clear the entire figure to remove colorbars and other elements
            self.figure_3d.clear()
            self.ax_3d = self.figure_3d.add_subplot(111, projection='3d')
            
            # Get intensity data and coordinates
            coords = list(self.intensity_data.keys())
            intensities = list(self.intensity_data.values())
            
            if not coords:
                self.ax_3d.set_title("No intensity data available")
                self.canvas_3d.draw()
                return
            
            # Extract coordinates
            x_coords = [coord[0] for coord in coords]
            y_coords = [coord[1] for coord in coords]
            z_coords = [coord[2] for coord in coords]
            
            # Create a regular grid for voxels
            x_unique = sorted(set(x_coords))
            y_unique = sorted(set(y_coords))
            z_unique = sorted(set(z_coords))
            
            # Detect 2D data (single Z plane) and duplicate it to create volume
            is_2d_data = len(z_unique) == 1
            if is_2d_data:
                # Calculate a reasonable thickness for the 2D layer
                # Use smaller of x or y range, or default to 0.1
                x_range = max(x_unique) - min(x_unique) if len(x_unique) > 1 else 1
                y_range = max(y_unique) - min(y_unique) if len(y_unique) > 1 else 1
                thickness = min(x_range, y_range) * 0.05  # 5% of smaller spatial dimension
                thickness = max(thickness, 0.1)  # Minimum thickness
                
                # Create second Z plane centered around original Z
                original_z = z_unique[0]
                z_unique = [original_z - thickness/2, original_z + thickness/2]
                
                # Update existing coordinates to the first plane (z - thickness/2)
                coords_2d = coords.copy()
                intensities_2d = intensities.copy()
                
                # Update original coords to be at z - thickness/2
                for i, coord in enumerate(coords):
                    coords[i] = (coord[0], coord[1], original_z - thickness/2)
                
                # Update z_coords list
                z_coords = [original_z - thickness/2] * len(coords)
                
                # Add second plane at z + thickness/2
                for coord, intensity in zip(coords_2d, intensities_2d):
                    new_coord = (coord[0], coord[1], original_z + thickness/2)
                    coords.append(new_coord)
                    intensities.append(intensity)
                
                # Update coordinate lists for second plane
                z_coords.extend([original_z + thickness/2] * len(coords_2d))
            
            # Calculate voxel size (spacing between points)
            dx = (max(x_unique) - min(x_unique)) / (len(x_unique) - 1) if len(x_unique) > 1 else 1
            dy = (max(y_unique) - min(y_unique)) / (len(y_unique) - 1) if len(y_unique) > 1 else 1
            dz = (max(z_unique) - min(z_unique)) / (len(z_unique) - 1) if len(z_unique) > 1 else thickness
            
            # Create 3D grid of boolean values (where to place voxels)
            nx, ny, nz = len(x_unique), len(y_unique), len(z_unique)
            filled = np.zeros((nx, ny, nz), dtype=bool)
            colors = np.empty((nx, ny, nz, 4), dtype=float)  # RGBA colors
            
            # Get intensity limits and threshold
            vmin = self.intensity_min_spin.value()
            vmax = self.intensity_max_spin.value()
            threshold = self.voxel_threshold_spin.value()
            
            # Avoid division by zero
            if vmax == vmin:
                vmax = vmin + 1
            
            # Normalize intensities for colormap
            intensity_array = np.array(intensities)
            intensity_norm = np.clip((intensity_array - vmin) / (vmax - vmin), 0, 1)
            
            # Get colormap
            import matplotlib.cm as cm
            cmap = cm.get_cmap(self.colormap_combo.currentText())
            
            # Initialize colors array with transparent values
            colors[:, :, :, :] = [0, 0, 0, 0]  # Transparent black for empty voxels
            
            # Fill the voxel grid
            voxels_to_show = 0
            for i, (coord, intensity, norm_intensity) in enumerate(zip(coords, intensities, intensity_norm)):
                # Find indices in the regular grid
                try:
                    x_idx = x_unique.index(coord[0])
                    y_idx = y_unique.index(coord[1])
                    z_idx = z_unique.index(coord[2])
                    
                    # Only show voxels with intensity above threshold
                    if intensity > threshold:
                        filled[x_idx, y_idx, z_idx] = True
                        # Get color from colormap
                        color = cmap(norm_intensity)
                        colors[x_idx, y_idx, z_idx] = color
                        voxels_to_show += 1
                except ValueError:
                    # Skip if coordinates are not found (shouldn't happen)
                    continue
            
            # Plot voxels if any exist
            if voxels_to_show > 0 and np.any(filled):
                # Create coordinate grids for proper voxel positioning
                # We need to create coordinate arrays that define the boundaries of each voxel
                # voxels() expects edge coordinates, not center coordinates
                
                # Calculate voxel boundaries (edges, not centers)
                x_edges = np.zeros(len(x_unique) + 1)
                y_edges = np.zeros(len(y_unique) + 1)
                z_edges = np.zeros(len(z_unique) + 1)
                
                # For x edges
                if len(x_unique) > 1:
                    for i in range(len(x_unique)):
                        if i == 0:
                            x_edges[i] = x_unique[i] - dx/2
                        x_edges[i+1] = x_unique[i] + dx/2
                else:
                    x_edges[0] = x_unique[0] - dx/2
                    x_edges[1] = x_unique[0] + dx/2
                
                # For y edges
                if len(y_unique) > 1:
                    for i in range(len(y_unique)):
                        if i == 0:
                            y_edges[i] = y_unique[i] - dy/2
                        y_edges[i+1] = y_unique[i] + dy/2
                else:
                    y_edges[0] = y_unique[0] - dy/2
                    y_edges[1] = y_unique[0] + dy/2
                
                # For z edges
                if len(z_unique) > 1:
                    for i in range(len(z_unique)):
                        if i == 0:
                            z_edges[i] = z_unique[i] - dz/2
                        z_edges[i+1] = z_unique[i] + dz/2
                else:
                    z_edges[0] = z_unique[0] - dz/2
                    z_edges[1] = z_unique[0] + dz/2
                
                # Create meshgrid from edge coordinates
                x_grid, y_grid, z_grid = np.meshgrid(x_edges, y_edges, z_edges, indexing='ij')
                
                # Use voxels with proper coordinate specification
                self.ax_3d.voxels(x_grid, y_grid, z_grid, filled, facecolors=colors, alpha=self.alpha_spin.value())
                
                # Create a colorbar using a dummy mappable
                import matplotlib.colors as mcolors
                norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
                mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
                mappable.set_array([])
                
                cbar = self.figure_3d.colorbar(mappable, ax=self.ax_3d, shrink=0.5, aspect=20)
                cbar.set_label('Intensity')
            else:
                threshold_info = f" (threshold: {threshold:.0f})" if threshold > 0 else ""
                self.ax_3d.text(0.5, 0.5, 0.5, f'No voxels to display{threshold_info}\nTry lowering the voxel threshold', 
                               transform=self.ax_3d.transAxes, ha='center', va='center',
                               fontsize=12, alpha=0.7)
            
            # Set labels and limits
            self.ax_3d.set_xlabel('X')
            self.ax_3d.set_ylabel('Y')
            self.ax_3d.set_zlabel('Z')
            
            # Update title with threshold info
            threshold_info = f" (threshold: {threshold:.0f})" if threshold > 0 else ""
            data_type = "2D Data (extruded)" if is_2d_data else "3D Data"
            self.ax_3d.set_title(f'3D Intensity Heatmap - {voxels_to_show} voxels - {data_type}{threshold_info}')
            
            # Set axis limits to properly frame the voxels
            # Use actual coordinates after any 2D data processing
            if coords:
                actual_x_coords = [coord[0] for coord in coords]
                actual_y_coords = [coord[1] for coord in coords]
                actual_z_coords = [coord[2] for coord in coords]
                
                x_min, x_max = min(actual_x_coords), max(actual_x_coords)
                y_min, y_max = min(actual_y_coords), max(actual_y_coords)
                z_min, z_max = min(actual_z_coords), max(actual_z_coords)
                
                # Add padding based on voxel sizes
                x_min_padded = x_min - dx/2
                x_max_padded = x_max + dx/2
                y_min_padded = y_min - dy/2
                y_max_padded = y_max + dy/2
                z_min_padded = z_min - dz/2
                z_max_padded = z_max + dz/2
                
                # Create square view using min of all mins and max of all maxs
                global_min = min(x_min_padded, y_min_padded, z_min_padded)
                global_max = max(x_max_padded, y_max_padded, z_max_padded)
                
                self.ax_3d.set_xlim(global_min, global_max)
                self.ax_3d.set_ylim(global_min, global_max)
                self.ax_3d.set_zlim(global_min, global_max)
            
            self.figure_3d.tight_layout()
            self.canvas_3d.draw()
            
        except Exception as e:
            self.figure_3d.clear()
            self.ax_3d = self.figure_3d.add_subplot(111, projection='3d')
            self.ax_3d.set_title(f"Error plotting 3D data: {e}")
            self.canvas_3d.draw()
            print(f"Error in update_3d_plot: {e}")
            import traceback
            traceback.print_exc()
    
    def update_cross_sections(self):
        """Update all cross-section plots."""
        self.update_xy_cross_section()
        self.update_xz_cross_section()
        self.update_yz_cross_section()
    
    def update_xy_cross_section(self):
        """Update XY cross-section plot."""
        if self.grid_data is None:
            return
        
        try:
            # Clear the entire figure to remove colorbars
            self.figure_xy.clear()
            self.ax_xy = self.figure_xy.add_subplot(111)
            
            z_idx = self.z_slider.value() - self.z_slider.minimum()
            if z_idx < len(self.grid_data['z_coords']):
                slice_data = self.grid_data['I'][:, :, z_idx]
                
                # Apply intensity limits
                vmin = self.intensity_min_spin.value()
                vmax = self.intensity_max_spin.value()
                
                im = self.ax_xy.imshow(slice_data.T, 
                                     extent=[self.grid_data['x_coords'][0], self.grid_data['x_coords'][-1],
                                            self.grid_data['y_coords'][0], self.grid_data['y_coords'][-1]],
                                     origin='lower',
                                     cmap=self.colormap_combo.currentText(),
                                     vmin=vmin, vmax=vmax)
                
                self.ax_xy.set_xlabel('X')
                self.ax_xy.set_ylabel('Y')
                self.ax_xy.set_title(f'XY Cross-section (Z = {self.grid_data["z_coords"][z_idx]})')
                
                # Add colorbar
                self.figure_xy.colorbar(im, ax=self.ax_xy, label='Intensity')
            
            self.figure_xy.tight_layout()
            self.canvas_xy.draw()
            
        except Exception as e:
            print(f"Error in update_xy_cross_section: {e}")
    
    def update_xz_cross_section(self):
        """Update XZ cross-section plot."""
        if self.grid_data is None:
            return
        
        try:
            # Clear the entire figure to remove colorbars
            self.figure_xz.clear()
            self.ax_xz = self.figure_xz.add_subplot(111)
            
            y_idx = self.y_slider.value() - self.y_slider.minimum()
            if y_idx < len(self.grid_data['y_coords']):
                slice_data = self.grid_data['I'][:, y_idx, :]
                
                # Apply intensity limits
                vmin = self.intensity_min_spin.value()
                vmax = self.intensity_max_spin.value()
                
                im = self.ax_xz.imshow(slice_data.T, 
                                     extent=[self.grid_data['x_coords'][0], self.grid_data['x_coords'][-1],
                                            self.grid_data['z_coords'][0], self.grid_data['z_coords'][-1]],
                                     origin='lower',
                                     cmap=self.colormap_combo.currentText(),
                                     vmin=vmin, vmax=vmax)
                
                self.ax_xz.set_xlabel('X')
                self.ax_xz.set_ylabel('Z')
                self.ax_xz.set_title(f'XZ Cross-section (Y = {self.grid_data["y_coords"][y_idx]})')
                
                # Add colorbar
                self.figure_xz.colorbar(im, ax=self.ax_xz, label='Intensity')
            
            self.figure_xz.tight_layout()
            self.canvas_xz.draw()
            
        except Exception as e:
            print(f"Error in update_xz_cross_section: {e}")
    
    def update_yz_cross_section(self):
        """Update YZ cross-section plot."""
        if self.grid_data is None:
            return
        
        try:
            # Clear the entire figure to remove colorbars
            self.figure_yz.clear()
            self.ax_yz = self.figure_yz.add_subplot(111)
            
            x_idx = self.x_slider.value() - self.x_slider.minimum()
            if x_idx < len(self.grid_data['x_coords']):
                slice_data = self.grid_data['I'][x_idx, :, :]
                
                # Apply intensity limits
                vmin = self.intensity_min_spin.value()
                vmax = self.intensity_max_spin.value()
                
                im = self.ax_yz.imshow(slice_data.T, 
                                     extent=[self.grid_data['y_coords'][0], self.grid_data['y_coords'][-1],
                                            self.grid_data['z_coords'][0], self.grid_data['z_coords'][-1]],
                                     origin='lower',
                                     cmap=self.colormap_combo.currentText(),
                                     vmin=vmin, vmax=vmax)
                
                self.ax_yz.set_xlabel('Y')
                self.ax_yz.set_ylabel('Z')
                self.ax_yz.set_title(f'YZ Cross-section (X = {self.grid_data["x_coords"][x_idx]})')
                
                # Add colorbar
                self.figure_yz.colorbar(im, ax=self.ax_yz, label='Intensity')
            
            self.figure_yz.tight_layout()
            self.canvas_yz.draw()
            
        except Exception as e:
            print(f"Error in update_yz_cross_section: {e}")
    
    # Event handlers
    def on_range_type_changed(self):
        """Handle range type changes."""
        self.auto_range_roi()
    
    def on_range_changed(self):
        """Handle range value changes."""
        # Auto-recalculate when range changes
        self.recalculate_intensities()
    
    def on_display_option_changed(self):
        """Handle display option changes."""
        self.update_all_plots()
    
    def on_z_slider_changed(self, value):
        """Handle Z slider changes."""
        self.z_value_label.setText(str(value))
        self.update_xy_cross_section()
    
    def on_y_slider_changed(self, value):
        """Handle Y slider changes."""
        self.y_value_label.setText(str(value))
        self.update_xz_cross_section()
    
    def on_x_slider_changed(self, value):
        """Handle X slider changes."""
        self.x_value_label.setText(str(value))
        self.update_yz_cross_section()
    
    def recalculate_intensities(self):
        """Recalculate intensities and update all plots."""
        self.calculate_intensities()
        self.update_all_plots()
    
    def reset_view(self):
        """Reset view to default settings."""
        # Stop any running animation
        self.stop_threshold_animation()
        
        self.range_type_combo.setCurrentText("Channel")
        self.subtract_background_cb.setChecked(True)
        self.colormap_combo.setCurrentText("viridis")
        self.alpha_spin.setValue(0.7)
        
        # Reset sliders to center positions
        if self.tridimensional_spectrum is not None:
            try:
                ranges = self.tridimensional_spectrum.get_spectra_range()
                self.z_slider.setValue(int((ranges['z']['min'] + ranges['z']['max']) / 2))
                self.y_slider.setValue(int((ranges['y']['min'] + ranges['y']['max']) / 2))
                self.x_slider.setValue(int((ranges['x']['min'] + ranges['x']['max']) / 2))
            except:
                pass
        
        self.auto_range_all()
        self.recalculate_intensities()
    
    def export_plots(self):
        """Export all current plots to files."""
        # Get base filename from user
        base_filename, _ = QFileDialog.getSaveFileName(
            self, "Export Plots", "3d_spectrum_plots",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)"
        )
        
        if base_filename:
            try:
                import os
                base_path = os.path.splitext(base_filename)[0]
                extension = os.path.splitext(base_filename)[1] or '.png'
                
                # Export 3D plot
                filename_3d = f"{base_path}_3d{extension}"
                self.figure_3d.savefig(filename_3d, dpi=300, bbox_inches='tight')
                
                # Export cross-sections
                filename_xy = f"{base_path}_xy{extension}"
                self.figure_xy.savefig(filename_xy, dpi=300, bbox_inches='tight')
                
                filename_xz = f"{base_path}_xz{extension}"
                self.figure_xz.savefig(filename_xz, dpi=300, bbox_inches='tight')
                
                filename_yz = f"{base_path}_yz{extension}"
                self.figure_yz.savefig(filename_yz, dpi=300, bbox_inches='tight')
                
                base_name = os.path.basename(base_path)
                QMessageBox.information(self, "Export Complete", 
                                      f"Plots exported successfully:\n"
                                      f"• {base_name}_3d{extension}\n"
                                      f"• {base_name}_xy{extension}\n"
                                      f"• {base_name}_xz{extension}\n"
                                      f"• {base_name}_yz{extension}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error exporting plots: {e}")