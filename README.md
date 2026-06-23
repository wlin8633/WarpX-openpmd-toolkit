# WarpX openPMD Toolkit

A comprehensive, Python-based graphical user interface (GUI) and toolkit for analyzing and visualizing simulation outputs from [WarpX](https://github.com/ECP-WarpX/WarpX) (both openPMD standard and Reduced Diagnostics). 

This toolkit streamlines the post-processing workflow for laser-plasma interaction simulations, offering interactive visualization, batch processing, and physical unit conversions.

## ✨ Features

- **Interactive GUI**: User-friendly interface to load, explore, and plot simulation data without writing custom scripts every time.
- **Multi-Mode Analysis**:
  - **Single Snapshot**: Visualize 2D/3D fields or particle data at a specific timestep.
  - **Batch Processing**: Automatically render and save plots across a time series, with built-in memory management to prevent OOM (Out-Of-Memory) errors.
  - **1D Line Probing**: Track the time-evolution of fields along specific coordinates.
  - **Fluid Elements & Reduced Diagnostics**: Built-in support for phase-space plotting, particle energy spectra, and field energy logs.
  - **2D FFT**: Capabilities for spatial and temporal frequency analysis (`2D-FFT.py`).
- **Dynamic Configuration**: Adjust colormaps, limits (`vmin`/`vmax`), and unit scaling (including logarithmic scales and math evaluations like `1e-6` or `np.pi`) on the fly.
- **Automated Exporting**: Intelligently sort and save generated plots into structured directories (e.g., `plotting/2d_Ex/`).

## 🚀 Getting Started

### Prerequisites
Make sure you have the required core libraries installed (typically standard in plasma physics environments):
```bash
pip install numpy matplotlib scipy openpmd-api
```

### Running the Application
Launch the main interactive analysis GUI:
```bash
python interactive_analysis.py
```
For command-line or headless batch processing:
```bash
python analysis_cli.py
```

## 📖 Documentation

For detailed step-by-step instructions on how to use the GUI, configure plot settings, and scale physical units, please refer to the **[User Manual](UserManual.md)**.
