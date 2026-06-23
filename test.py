# %%
from data_loaders import load_time_series_field, load_fluid_element_series
from plotters import plot_time_space_colormap, plot_fluid_element_phase_space

folder = "./example_data"

# 1. 測試電子流體軌跡 (Fluid Element) 與 FFT
t, ux, uy, uz = load_fluid_element_series(folder, "fluid_el_center", "electron")
if t is not None:
    plot_fluid_element_phase_space(t, ux, uy, uz, save_path="./fluid_orbit.png")

# 2. 測試一維電場隨時間演化 (Line Probe)
data_tx, t_arr, s_arr, extent = load_time_series_field(folder, "line_probe_field", "E", coord="x")
if data_tx is not None:
    # 建立一個簡單的設定檔
    cfg = {"plot_title": "Ex Time-Space", "cmap": "RdBu_r", "vmin": -1, "vmax": 1, "unit_conversion": 1.0} 
    plot_time_space_colormap(data_tx, t_arr, extent, cfg, save_path="./line_probe_Ex.png")

# %%
