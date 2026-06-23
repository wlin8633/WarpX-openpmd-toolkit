# WarpX Data Analysis GUI - User Manual

Welcome to the WarpX Data Analysis Tool! This application provides a comprehensive GUI to visualize and analyze simulation data output from WarpX (OpenPMD and Reduced Files).

## 1. Getting Started
1. **Folder Path**: Select or type the root directory of your WarpX simulation output.
2. **Header Name**: Select the specific diagnostic you want to analyze (e.g., `diags/diag1` for 2D OpenPMD, or `diags/reducedfiles` for text-based outputs).
3. **Plot Data**: Choose the specific field or file to plot (e.g., `Ex`, `rho`, `FieldEnergy.txt`).
4. **Analysis Mode**:
   - `Single File`: View one specific timestep file (use the text box to enter the index, e.g., 20).
   - `Batch`: Process and view multiple files across a time range. Use the `Start` and `End` fields.
   - `1D Line Probe`: Draw a time-evolution line probe along a given coordinate (Z or Y axis).
   - `Fluid Element`: Analyze phase space data for fluid elements.
   - `Reduced File`: Analyze textual output files like Energy Spectra or Field Energy logs.

## 2. Interactive Plot Window
Once you click **Run Analysis**, an interactive plot window will appear.
- **Slider**: In Batch mode, use the slider to smoothly scrub through simulation timesteps.
- **Config**: Click the Config button to open the plot settings.
- **Save**: Click Save to export the currently viewed plot to a `.png` file.

## 3. Plot Configurations (Config Window)
The Config Window allows you to heavily customize your graphs without editing the code.
- **cmap**: Set the matplotlib colormap (e.g., `viridis`, `RdBu_r`, `magma`).
- **vmin / vmax**: Adjust the minimum and maximum values for the color scale. (Leave empty or type `None` for auto-scaling).
- **xlim / ylim**: Set coordinate boundaries. Input must be a valid list, e.g., `[0, 100]`.
- **xscale, yscale, cscale**: Used to convert simulation units to physical units. 
  - You can use predefined constants: `len_unit`, `time_unit`, `Efield_unit`, `Bfield_unit`, `jfield_unit`, `rho_unit`, etc.
  - You can evaluate math: `sc.c`, `np.pi`, `1e-6`.
  - **Log Scale**: Prepend `log:` to force a logarithmic scale. 
    - Example: `log: len_unit` sets the axis to log scale while dividing by `len_unit`.
    - Example: `log: 1.0` sets the axis to log scale without any division.

## 4. Saving Plots
Check the **Save Plot** box on the main UI to automatically export images.
- **Mimic analysis_app saving**: If checked, files will be intelligently sorted into folders like `plotting/2d_Ex/` or `plotting/reducedfiles/` automatically.
- Alternatively, you can specify a custom save directory.
- **Load and save all plots in batch**: Check this box in Batch mode to automatically render and save every frame from `Start` to `End` into the designated folder.

## 5. Performance Note
When running **Batch** analysis over a massive amount of frames (e.g., thousands of timesteps), ensure you check `Load and save all plots...`. The application will efficiently process them one by one, save them, and free the RAM immediately to prevent Out-Of-Memory (OOM) crashes.
