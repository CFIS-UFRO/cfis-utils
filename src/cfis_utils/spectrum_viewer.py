import sys
import atexit
from typing import Optional, Tuple, Dict, Any
import numpy as np
from pathlib import Path

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QGroupBox, QLabel, QDoubleSpinBox, QPushButton,
    QComboBox, QSplitter, QFrame, QGridLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Matplotlib imports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# Import your Spectrum class (adjust the import path as needed)
# from your_module import Spectrum


class SpectrumViewer(QMainWindow):
    """
    A robust spectrum viewer with integrated matplotlib plot and GUI controls.
    
    Features:
    - Toggle raw counts, background, and subtracted spectra
    - Choose between channel and energy axis
    - Set custom axis ranges
    - Linear/logarithmic scale options
    - Interactive matplotlib navigation
    - Automatic QApplication management
    """
    
    _app_instance = None  # Class variable to store app instance
    
    def __init__(self, spectrum=None, parent=None):
        """
        Initialize the SpectrumViewer.
        
        Args:
            spectrum: A Spectrum object to display
            parent: Parent widget (optional)
        """
        # Ensure QApplication exists
        self._ensure_qapplication()
        
        super().__init__(parent)
        
        self.spectrum = spectrum
        self.current_lines = {}  # Store plot lines for updating
        
        self._setup_ui()
        self._connect_signals()
        
        # Initial plot if spectrum is provided
        if self.spectrum is not None:
            self.update_spectrum_info()
            self.auto_range_all()
            self.update_plot()
    
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
        """
        Show the viewer window and start the Qt event loop.
        This method blocks until the window is closed.
        """
        self.show()
        return self._app_instance.exec()
    
    def show_non_blocking(self):
        """
        Show the viewer window without blocking.
        Useful when you want to continue executing other code.
        """
        self.show()
        return self
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Spectrum Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
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
        
        # Create plot panel
        plot_panel = self._create_plot_panel()
        splitter.addWidget(plot_panel)
        
        # Set splitter proportions (30% controls, 70% plot)
        splitter.setSizes([300, 900])
        
    def _create_control_panel(self) -> QWidget:
        """Create the control panel with all options."""
        panel = QWidget()
        panel.setMaximumWidth(350)
        panel.setMinimumWidth(250)
        
        layout = QVBoxLayout(panel)
        
        # Spectrum display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        self.show_raw_cb = QCheckBox("Show Raw Counts")
        self.show_raw_cb.setChecked(True)
        
        self.show_background_cb = QCheckBox("Show Background")
        self.show_background_cb.setChecked(False)
        
        self.show_subtracted_cb = QCheckBox("Show Subtracted")
        self.show_subtracted_cb.setChecked(False)
        
        display_layout.addWidget(self.show_raw_cb)
        display_layout.addWidget(self.show_background_cb)
        display_layout.addWidget(self.show_subtracted_cb)
        
        # Axis options
        axis_group = QGroupBox("Axis Options")
        axis_layout = QVBoxLayout(axis_group)
        
        # X-axis type
        x_axis_layout = QHBoxLayout()
        x_axis_layout.addWidget(QLabel("X-Axis:"))
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["Channel", "Energy (eV)"])
        x_axis_layout.addWidget(self.x_axis_combo)
        axis_layout.addLayout(x_axis_layout)
        
        # Y-axis scale
        y_scale_layout = QHBoxLayout()
        y_scale_layout.addWidget(QLabel("Y-Scale:"))
        self.y_scale_combo = QComboBox()
        self.y_scale_combo.addItems(["Linear", "Logarithmic"])
        y_scale_layout.addWidget(self.y_scale_combo)
        axis_layout.addLayout(y_scale_layout)
        
        # Axis ranges
        ranges_group = QGroupBox("Axis Ranges")
        ranges_layout = QGridLayout(ranges_group)
        
        # X-axis range
        ranges_layout.addWidget(QLabel("X Min:"), 0, 0)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1e6, 1e6)
        self.x_min_spin.setDecimals(2)
        self.x_min_spin.setValue(0)
        ranges_layout.addWidget(self.x_min_spin, 0, 1)
        
        ranges_layout.addWidget(QLabel("X Max:"), 0, 2)
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1e6, 1e6)
        self.x_max_spin.setDecimals(2)
        self.x_max_spin.setValue(2048)
        ranges_layout.addWidget(self.x_max_spin, 0, 3)
        
        # Y-axis range
        ranges_layout.addWidget(QLabel("Y Min:"), 1, 0)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1e6, 1e6)
        self.y_min_spin.setDecimals(2)
        self.y_min_spin.setValue(0)
        ranges_layout.addWidget(self.y_min_spin, 1, 1)
        
        ranges_layout.addWidget(QLabel("Y Max:"), 1, 2)
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1e6, 1e6)
        self.y_max_spin.setDecimals(2)
        self.y_max_spin.setValue(1000)
        ranges_layout.addWidget(self.y_max_spin, 1, 3)
        
        # Auto-range buttons
        self.auto_x_btn = QPushButton("Auto X")
        self.auto_y_btn = QPushButton("Auto Y")
        self.auto_all_btn = QPushButton("Auto All")
        
        auto_layout = QHBoxLayout()
        auto_layout.addWidget(self.auto_x_btn)
        auto_layout.addWidget(self.auto_y_btn)
        auto_layout.addWidget(self.auto_all_btn)
        
        # Control buttons
        buttons_group = QGroupBox("Controls")
        buttons_layout = QVBoxLayout(buttons_group)
        
        self.reset_btn = QPushButton("Reset View")
        self.export_btn = QPushButton("Export Plot")
        
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.export_btn)
        
        # Add all groups to main layout
        layout.addWidget(display_group)
        layout.addWidget(axis_group)
        layout.addWidget(ranges_group)
        layout.addLayout(auto_layout)
        layout.addWidget(buttons_group)
        
        # Add spacer to push everything to top
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Info panel
        info_group = QGroupBox("Spectrum Info")
        info_layout = QVBoxLayout(info_group)
        
        self.info_label = QLabel("No spectrum loaded")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("QLabel { font-family: monospace; }")
        info_layout.addWidget(self.info_label)
        
        layout.addWidget(info_group)
        
        return panel
    
    def _create_plot_panel(self) -> QWidget:
        """Create the matplotlib plot panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Create navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, panel)
        
        # Add to layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        return panel
    
    def _connect_signals(self):
        """Connect all GUI signals to their handlers."""
        # Checkboxes
        self.show_raw_cb.toggled.connect(self.on_display_option_changed)
        self.show_background_cb.toggled.connect(self.on_display_option_changed)
        self.show_subtracted_cb.toggled.connect(self.on_display_option_changed)
        
        # Combo boxes
        self.x_axis_combo.currentTextChanged.connect(self.on_axis_option_changed)
        self.y_scale_combo.currentTextChanged.connect(self.on_axis_option_changed)
        
        # Spin boxes
        self.x_min_spin.valueChanged.connect(self.update_plot)
        self.x_max_spin.valueChanged.connect(self.update_plot)
        self.y_min_spin.valueChanged.connect(self.update_plot)
        self.y_max_spin.valueChanged.connect(self.update_plot)
        
        # Buttons
        self.reset_btn.clicked.connect(self.reset_view)
        self.export_btn.clicked.connect(self.export_plot)
        self.auto_x_btn.clicked.connect(self.auto_range_x_and_update)
        self.auto_y_btn.clicked.connect(self.auto_range_y_and_update)
        self.auto_all_btn.clicked.connect(self.auto_range_all_and_update)
    
    def set_spectrum(self, spectrum):
        """
        Set a new spectrum to display.
        
        Args:
            spectrum: A Spectrum object
        """
        self.spectrum = spectrum
        self.update_spectrum_info()
        self.auto_range_all()
        self.update_plot()
    
    def update_spectrum_info(self):
        """Update the spectrum information display."""
        if self.spectrum is None:
            self.info_label.setText("No spectrum loaded")
            return
        
        try:
            num_channels = self.spectrum.get_num_channels()
            cal_a, cal_b = self.spectrum.get_calibration()
            metadata = self.spectrum.get_metadata()

            info_text = f"├─ Channels : {num_channels}\n"
            info_text += f"├─ Calibration:\n"
            info_text += f"│  ├─ A: {cal_a:.4f}\n"
            info_text += f"│  └─ B: {cal_b:.4f}\n"

            if metadata:
                info_text += "└─ Metadata:\n"
                metadata_items = list(metadata.items())[:3]
                for i, (key, value) in enumerate(metadata_items):
                    if i == len(metadata_items) - 1 and len(metadata) <= 3:
                        # Last item and no more metadata
                        info_text += f"   └─ {key}: {value}\n"
                    else:
                        # Not last item or there are more items
                        info_text += f"   ├─ {key}: {value}\n"
                
                if len(metadata) > 3:
                    info_text += f"   └─ ... ({len(metadata)-3} more)\n"

            self.info_label.setText(info_text)
            
        except Exception as e:
            self.info_label.setText(f"Error reading spectrum info: {e}")
    
    def on_display_option_changed(self):
        """Handle display option changes."""
        self.update_plot()
    
    def on_axis_option_changed(self):
        """Handle axis option changes."""
        if self.x_axis_combo.currentText() == "Energy (eV)":
            self.auto_range_x()
        self.update_plot()
    
    def auto_range_x(self):
        """Auto-scale X axis based on current spectrum."""
        if self.spectrum is None:
            return
        
        try:
            use_energy = self.x_axis_combo.currentText() == "Energy (eV)"
            data = self.spectrum.get_data(use_energy_axis=use_energy, without_background=False)
            
            if data is not None:
                x_axis, _ = data
                self.x_min_spin.setValue(float(np.min(x_axis)))
                self.x_max_spin.setValue(float(np.max(x_axis)))
        except Exception as e:
            print(f"Error in auto_range_x: {e}")
    
    def auto_range_y(self):
        """Auto-scale Y axis based on current data."""
        if self.spectrum is None:
            return
        
        try:
            # Get all possible y data
            all_y_data = []
            
            if self.show_raw_cb.isChecked():
                raw_data = self.spectrum.get_data(use_energy_axis=False, without_background=False)
                if raw_data is not None:
                    all_y_data.append(raw_data[1])
            
            if self.show_background_cb.isChecked() and hasattr(self.spectrum, '_background_counts'):
                if self.spectrum._background_counts is not None:
                    all_y_data.append(self.spectrum._background_counts)
            
            if self.show_subtracted_cb.isChecked():
                subtracted = self.spectrum.get_counts_without_background()
                if subtracted is not None:
                    all_y_data.append(subtracted)
            
            if all_y_data:
                combined_y = np.concatenate(all_y_data)
                if self.y_scale_combo.currentText() == "Logarithmic":
                    positive_values = combined_y[combined_y > 0]
                    if len(positive_values) > 0:
                        self.y_min_spin.setValue(float(np.min(positive_values)) * 0.5)
                        self.y_max_spin.setValue(float(np.max(combined_y)) * 2)
                else:
                    margin = (np.max(combined_y) - np.min(combined_y)) * 0.1
                    self.y_min_spin.setValue(float(np.min(combined_y) - margin))
                    self.y_max_spin.setValue(float(np.max(combined_y) + margin))
        except Exception as e:
            print(f"Error in auto_range_y: {e}")
    
    def auto_range_all(self):
        """Auto-scale both axes."""
        self.auto_range_x()
        self.auto_range_y()

    def auto_range_x_and_update(self):
        """Auto-scale X axis and update plot."""
        self.auto_range_x()
        self.update_plot()

    def auto_range_y_and_update(self):
        """Auto-scale Y axis and update plot."""
        self.auto_range_y()
        self.update_plot()

    def auto_range_all_and_update(self):
        """Auto-scale both axes and update plot."""
        self.auto_range_all()
        self.update_plot()

    def reset_view(self):
        """Reset view to default settings."""
        self.show_raw_cb.setChecked(True)
        self.show_background_cb.setChecked(False)
        self.show_subtracted_cb.setChecked(False)
        self.x_axis_combo.setCurrentText("Channel")
        self.y_scale_combo.setCurrentText("Linear")
        self.auto_range_all()
        self.update_plot()
    
    def update_plot(self):
        """Update the matplotlib plot based on current settings."""
        if self.spectrum is None:
            self.ax.clear()
            self.ax.set_title("No spectrum loaded")
            self.canvas.draw()
            return
        
        try:
            # Clear previous plot
            self.ax.clear()
            self.current_lines.clear()
            
            # Get plot settings
            use_energy = self.x_axis_combo.currentText() == "Energy (eV)"
            use_log = self.y_scale_combo.currentText() == "Logarithmic"
            
            # Plot raw counts
            if self.show_raw_cb.isChecked():
                data = self.spectrum.get_data(use_energy_axis=use_energy, without_background=False)
                if data is not None:
                    x_axis, y_counts = data
                    line, = self.ax.plot(x_axis, y_counts, label="Raw Counts", color='blue', linewidth=1.5)
                    self.current_lines['raw'] = line
            
            # Plot background
            if self.show_background_cb.isChecked() and hasattr(self.spectrum, '_background_counts'):
                if self.spectrum._background_counts is not None:
                    x_axis_data = self.spectrum.get_data(use_energy_axis=use_energy, without_background=False)
                    if x_axis_data is not None:
                        x_axis, _ = x_axis_data
                        bg_counts = self.spectrum._background_counts
                        if len(x_axis) == len(bg_counts):
                            line, = self.ax.plot(x_axis, bg_counts, label="Background", 
                                               color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
                            self.current_lines['background'] = line
            
            # Plot subtracted
            if self.show_subtracted_cb.isChecked():
                subtracted = self.spectrum.get_counts_without_background()
                if subtracted is not None:
                    x_axis_data = self.spectrum.get_data(use_energy_axis=use_energy, without_background=False)
                    if x_axis_data is not None:
                        x_axis, _ = x_axis_data
                        if len(x_axis) == len(subtracted):
                            line, = self.ax.plot(x_axis, subtracted, label="Subtracted", 
                                               color='green', linewidth=1.5)
                            self.current_lines['subtracted'] = line
            
            # Set labels and title
            xlabel = "Energy (eV)" if use_energy else "Channel"
            self.ax.set_xlabel(xlabel)
            self.ax.set_ylabel("Counts")
            
            num_channels = self.spectrum.get_num_channels()
            self.ax.set_title(f"Spectrum ({num_channels} channels)")
            
            # Set scale
            if use_log:
                self.ax.set_yscale('log')
            else:
                self.ax.set_yscale('linear')
            
            # Set ranges
            self.ax.set_xlim(self.x_min_spin.value(), self.x_max_spin.value())
            self.ax.set_ylim(self.y_min_spin.value(), self.y_max_spin.value())
            
            # Add grid and legend
            self.ax.grid(True, alpha=0.3)
            if len(self.current_lines) > 1:
                self.ax.legend()
            
            # Tight layout and draw
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            self.ax.clear()
            self.ax.set_title(f"Error plotting spectrum: {e}")
            self.canvas.draw()
            print(f"Error in update_plot: {e}")
    
    def export_plot(self):
        """Export the current plot to a file."""
        from PySide6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Plot", "spectrum_plot.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)"
        )
        
        if filename:
            try:
                self.figure.savefig(filename, dpi=300, bbox_inches='tight')
                print(f"Plot exported to: {filename}")
            except Exception as e:
                print(f"Error exporting plot: {e}")
