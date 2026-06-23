# %%
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import scipy.constants as sc
from matplotlib.colors import LogNorm
import matplotlib.patches as patches
from data_loaders import find_diag_file

def analyze_fft(folder_path, file_num, roi_z_bounds, moving_roi=True, fixed_x_center=0.0, roi_x_width=40.0, save_dir='fft_frames'):
    """
    Performs 2D Spatial FFT analysis on a specific WarpX simulation snapshot.
    
    Parameters:
    - folder_path: Path to the simulation diagnostic folder (parent of fdiag)
    - file_num: Integer file number to load (1-based index)
    - roi_z_bounds: Tuple of (z_min, z_max) in micrometers
    - moving_roi: Boolean. If True, centers the X-ROI dynamically on the laser peak. If False, uses fixed_x_center.
    - fixed_x_center: Center of the X-ROI in micrometers if moving_roi is False.
    - roi_x_width: Width of the X-ROI in micrometers.
    - save_dir: Directory to save the resulting plot.
    """
    os.makedirs(save_dir, exist_ok=True)
    
    LAMBDA_0 = 800e-9 
    K_0 = 2 * np.pi / LAMBDA_0
    
    dataList = ['Ex', 'Ez', 'By']
    print(f"\n--- Processing File Number {file_num} ---")
    
    dataset, readout_names, readout_data, xydata, time = find_diag_file(
        folderPath=folder_path, 
        fileName='fdiag', 
        fileNumber=file_num, 
        dataList=dataList
    )

    if not readout_data:
        print(f"Failed to read data for file {file_num}. Skipping.")
        return

    Ex = readout_data['openpmd_Ex']
    Ez = readout_data['openpmd_Ez']
    By = readout_data['openpmd_By']
    time_ps = time * 1e12 # type: ignore

    nx, nz = Ex.shape
    xmin, xmax = xydata[0] # type: ignore
    zmin, zmax = xydata[1] # type: ignore

    x_grid = np.linspace(xmin, xmax, nx) * 1e6 # um
    z_grid = np.linspace(zmin, zmax, nz) * 1e6 # um
    dx_m = (xmax - xmin) / nx
    dz_m = (zmax - zmin) / nz

    # --- Spatial Cropping ---
    if moving_roi:
        Ez_env_x = np.max(np.abs(Ez), axis=1)
        laser_x_idx = np.argmax(Ez_env_x)
        center_x_um = x_grid[laser_x_idx]
        print(f"Dynamically detected laser peak at x = {center_x_um:.2f} um")
    else:
        center_x_um = fixed_x_center
        print(f"Using fixed ROI centered at x = {center_x_um:.2f} um")

    x_min_crop = center_x_um - roi_x_width/2
    x_max_crop = center_x_um + roi_x_width/2
    z_min_crop, z_max_crop = roi_z_bounds

    x_mask = (x_grid >= x_min_crop) & (x_grid <= x_max_crop)
    z_mask = (z_grid >= z_min_crop) & (z_grid <= z_max_crop)

    x_crop = x_grid[x_mask]
    z_crop = z_grid[z_mask]
    Ex_c = Ex[np.ix_(x_mask, z_mask)]
    Ez_c = Ez[np.ix_(x_mask, z_mask)]
    By_c = By[np.ix_(x_mask, z_mask)]

    nx_c, nz_c = Ex_c.shape
    if nx_c == 0 or nz_c == 0:
        print(f"Warning: Cropped region is empty for file {file_num}. Check bounds.")
        return

    # Apply 2D Hann Window
    window_x = np.hanning(nx_c)
    window_z = np.hanning(nz_c)
    window_2d = window_x[:, np.newaxis] * window_z[np.newaxis, :]

    Ex_w = Ex_c * window_2d
    Ez_w = Ez_c * window_2d

    # --- 2D Spatial FFT ---
    Ex_fft = np.fft.fftshift(np.fft.fft2(Ex_w))
    Ez_fft = np.fft.fftshift(np.fft.fft2(Ez_w))

    I_Ex = np.abs(Ex_fft)**2
    I_Ez = np.abs(Ez_fft)**2

    kx = np.fft.fftshift(np.fft.fftfreq(nx_c, d=dx_m)) * 2 * np.pi
    kz = np.fft.fftshift(np.fft.fftfreq(nz_c, d=dz_m)) * 2 * np.pi

    kx_norm = kx / K_0
    kz_norm = kz / K_0
    KX, KZ = np.meshgrid(kx_norm, kz_norm) 

    # --- Plotting ---
    fig, axs = plt.subplots(2, 2, figsize=(14, 12))
    I_Ez_plot = I_Ez.T
    I_Ex_plot = I_Ex.T

    # Plot 1: Ez FFT
    ax = axs[0, 0]
    im = ax.pcolormesh(KX, KZ, I_Ez_plot, norm=LogNorm(vmin=I_Ez_plot.max()*1e-6, vmax=I_Ez_plot.max()), cmap='magma', shading='auto')
    ax.set_title(r'$|E_z(k_x, k_z)|^2$ (Fundamental Laser & Wakefield)')
    ax.set_xlabel(r'$k_x / k_0$ (Propagation)')
    ax.set_ylabel(r'$k_z / k_0$ (Transverse)')
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    fig.colorbar(im, ax=ax)
    ax.add_patch(plt.Circle((0, 0), 1, color='white', fill=False, linestyle='--', alpha=0.5, label='Fundamental (800nm)'))
    ax.add_patch(plt.Circle((0, 0), 2, color='cyan', fill=False, linestyle='--', alpha=0.8, label='Second Harmonic (400nm)'))
    ax.legend(loc='upper right')

    # Plot 2: Ex FFT
    ax = axs[0, 1]
    im2 = ax.pcolormesh(KX, KZ, I_Ex_plot, norm=LogNorm(vmin=I_Ex_plot.max()*1e-6, vmax=I_Ex_plot.max()), cmap='magma', shading='auto')
    ax.set_title(r'$|E_x(k_x, k_z)|^2$ (Transverse Emission / SHG)')
    ax.set_xlabel(r'$k_x / k_0$ (Propagation)')
    ax.set_ylabel(r'$k_z / k_0$ (Transverse)')
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    fig.colorbar(im2, ax=ax)
    ax.add_patch(plt.Circle((0, 0), 1, color='white', fill=False, linestyle='--', alpha=0.5))
    ax.add_patch(plt.Circle((0, 0), 2, color='cyan', fill=False, linestyle='--', alpha=0.8))

    # Plot 3: Zoom Ex
    ax = axs[1, 0]
    im3 = ax.pcolormesh(KX, KZ, I_Ex_plot, norm=LogNorm(vmin=I_Ex_plot.max()*1e-6, vmax=I_Ex_plot.max()), cmap='viridis', shading='auto')
    ax.set_title(r'Zoom: 90-deg 400nm ($|E_x|^2$)')
    ax.set_xlabel(r'$k_x / k_0$')
    ax.set_ylabel(r'$k_z / k_0$')
    ax.set_xlim(-0.5, 0.5)
    ax.set_ylim(1.5, 2.5)
    fig.colorbar(im3, ax=ax)

    # Plot 4: Full By with ROI Box
    ax = axs[1, 1]
    By_full_plot = By.T
    X_full_mesh, Z_full_mesh = np.meshgrid(x_grid, z_grid)
    im4 = ax.pcolormesh(X_full_mesh, Z_full_mesh, By_full_plot, cmap='RdBu', shading='auto')
    ax.set_title(r'Full $B_y$ with FFT ROI (Red Box)')
    ax.set_xlabel(r'$x (\mu m)$')
    ax.set_ylabel(r'$z (\mu m)$')
    fig.colorbar(im4, ax=ax, label='Tesla')

    rect = patches.Rectangle(
        (x_min_crop, z_min_crop),         
        roi_x_width,                      
        z_max_crop - z_min_crop,            
        linewidth=2, edgecolor='red', facecolor='none', linestyle='--'
    )
    ax.add_patch(rect)

    plt.suptitle(f'Localized 2D Spatial FFT at {time_ps:.2f} ps (File {file_num})', fontsize=16)
    plt.tight_layout()
    
    save_path = os.path.join(save_dir, f'FFT_Analysis_{file_num:04d}.png')
    plt.savefig(save_path, dpi=300)
    print(f"Plot saved to {save_path}")
    # Calculate integration of 90-deg 400nm signal
    mask_k = (KX >= -0.1) & (KX <= 0.1) & (KZ >= 1.94) & (KZ <= 2.06)
    integrated_intensity = float(np.sum(I_Ex_plot[mask_k]))

    plt.close(fig) # close to prevent memory leak in loop
    
    return time_ps, integrated_intensity


def _pool_worker(kwargs):
    try:
        return analyze_fft(**kwargs)
    except Exception as e:
        print(f"Error in worker processing file {kwargs.get('file_num')}: {e}")
        return None

# ==========================================
# Main Execution Loop
# ==========================================
if __name__ == '__main__':
    import argparse
    import multiprocessing
    
    parser = argparse.ArgumentParser(description="2D Spatial FFT Analysis Tool for WarpX")
    parser.add_argument("--folder", type=str, required=True, help="Path to the simulation output directory")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=int, help="A single file number to process.")
    group.add_argument("--batch", type=int, nargs=2, metavar=('START', 'END'),
                       help="A range of file numbers to process (e.g., --batch 25 150).")
    
    parser.add_argument("-np", type=int, default=1, help="Number of parallel processes. Default is 1.")
    
    # FFT specific arguments
    parser.add_argument("--roi_z_bounds", type=float, nargs=2, default=[-10.0, 10.0], help="Z bounds for ROI (min max) in um")
    parser.add_argument("--moving_roi", action="store_true", help="Center X-ROI dynamically on laser peak. Overrides fixed_x_center.")
    parser.add_argument("--fixed_x_center", type=float, default=0.0, help="Fixed X-center for ROI in um")
    parser.add_argument("--roi_x_width", type=float, default=150.0, help="Width of X-ROI in um")
    parser.add_argument("--save_dir", type=str, default="", help="Custom directory to save plots. Defaults to plotting/fft_frames inside folder.")
    
    args = parser.parse_args()
    
    FOLDER_PATH = os.path.expanduser(args.folder)
    SAVE_DIR = args.save_dir if args.save_dir else os.path.join(FOLDER_PATH, 'plotting', 'fft_frames')
    
    if args.file:
        files_to_analyze = [args.file]
    else:
        files_to_analyze = range(args.batch[0], args.batch[1] + 1)
        
    results_time = []
    results_intensity = []
    
    tasks = []
    for f_num in files_to_analyze:
        kwargs = {
            'folder_path': FOLDER_PATH,
            'file_num': f_num,
            'roi_z_bounds': tuple(args.roi_z_bounds),
            'moving_roi': args.moving_roi,
            'fixed_x_center': args.fixed_x_center,
            'roi_x_width': args.roi_x_width,
            'save_dir': SAVE_DIR
        }
        tasks.append(kwargs)
        
    print(f"Starting processing with {args.np} workers for {len(tasks)} tasks.")
    
    with multiprocessing.Pool(processes=args.np, maxtasksperchild=1) as pool:
        results = pool.map(_pool_worker, tasks)
        
    for res in results:
        if res is not None:
            time_ps, intensity = res
            results_time.append(time_ps)
            results_intensity.append(intensity)
            
    # --- Plotting the Integration Result ---
    if len(results_time) > 0:
        import scipy.integrate
        
        # Ensure data is sorted by time
        sorted_indices = np.argsort(results_time)
        t_arr = np.array(results_time)[sorted_indices]
        inst_intensity = np.array(results_intensity)[sorted_indices]
        
        # Cumulative integration over time: \int I(t) dt
        cum_intensity = scipy.integrate.cumulative_trapezoid(inst_intensity, t_arr, initial=0)
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Left Y-Axis: Instantaneous Intensity
        color1 = 'crimson'
        ax1.plot(t_arr, inst_intensity, 'o-', color=color1, linewidth=2, markersize=6, label='Instantaneous')
        ax1.set_xlabel('Time (ps)', fontsize=14)
        ax1.set_ylabel('Instantaneous Spatial Integral of $|E_x|^2$', color=color1, fontsize=14)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.set_yscale('log')
        ax1.grid(True, which="both", ls="--", alpha=0.6)
        
        # Right Y-Axis: Cumulative Time-Integrated Intensity
        ax2 = ax1.twinx()
        color2 = 'teal'
        ax2.plot(t_arr, cum_intensity, 's--', color=color2, linewidth=2, markersize=6, label='Cumulative (CCD)')
        ax2.set_ylabel(r'Cumulative Time-Integrated Signal ($\int I dt$)', color=color2, fontsize=14)
        ax2.tick_params(axis='y', labelcolor=color2)
        # Using linear scale for cumulative since it starts at 0
        
        plt.title('90-deg 400nm SHG Intensity: Instantaneous vs Time-Integrated (CCD)', fontsize=16)
        fig.tight_layout()
        
        save_int_path = os.path.join(os.path.dirname(SAVE_DIR), 'FFT_Integration.png')
        plt.savefig(save_int_path, dpi=300)
        print(f"Integration Plot saved to {save_int_path}")
        
        # Save the numerical data to an .npz file
        save_npz_path = os.path.join(os.path.dirname(SAVE_DIR), 'FFT_Integration_Data.npz')
        np.savez(save_npz_path, time_ps=t_arr, inst_intensity=inst_intensity, cum_intensity=cum_intensity)
        print(f"Numerical data saved to {save_npz_path}")

# %%
