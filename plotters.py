import os
import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import LogNorm, Normalize
from config_manager import UNIT_MAP

def process_raw_data_for_plotting(raw_cdata, raw_xydata, raw_time, config):
    """
    Processes raw cdata, xydata, and time using the given plot configuration
    to produce plottable data and parameters.
    """
    plot_title = config["plot_title"].format(time=raw_time / config.get("tscale_val", UNIT_MAP["time_unit"]))
    cdata_plotting = raw_cdata / config.get("cscale_val", 1.0)

    resolution_factor = config.get("resolution_factor", 1)
    if resolution_factor > 1:
        cdata_plotting = cdata_plotting[::resolution_factor, ::resolution_factor]

    xy_data_plotting = raw_xydata / config.get("xscale_val", UNIT_MAP["len_unit"])

    plot_params = {
        "title": plot_title,
        "cmap": config["cmap"],
        "vmin": config["vmin"],
        "vmax": config["vmax"],
        "clabel": config["clabel"],
        "xlabel": config["xlabel"],
        "ylabel": config["ylabel"],
        "xlim": config["xlim"],
        "ylim": config["ylim"],
    }
    
    return cdata_plotting, xy_data_plotting, plot_params

def plot_2d_image(cdata, xydata, plot_config, save_path=None, return_fig=False):
    """
    Generates and saves a 2D image plot using Matplotlib.
    This function can either save the figure to a file or return the figure object.
    
    Args:
        cdata (np.ndarray): The 2D data array to plot.
        xydata (list or np.ndarray): The extent of the plot, e.g., [[xmin, ymin], [xmax, ymax]].
        plot_config (dict): A dictionary containing all plotting parameters.
        save_path (str, optional): The full path to save the output image. Defaults to None.
        return_fig (bool): If True, returns the figure object instead of saving. Defaults to False.
    """
    fig = plt.figure(figsize=plot_config.get("figsize", (7, 5)))
    ax = fig.add_subplot(111)
    
    # Rotate data to match original output
    cdata = np.rot90(cdata, 1)

    # Image settings
    im_kwargs = {
        "extent": [xydata[0, 0], xydata[0, 1], xydata[1, 0], xydata[1, 1]],
        "cmap": plot_config.get("cmap", "viridis"),
        "vmin": plot_config.get("vmin"),
        "vmax": plot_config.get("vmax"),
        "aspect": "auto",
    }
    
    vmin = im_kwargs.pop("vmin")
    vmax = im_kwargs.pop("vmax")
    
    if plot_config.get("cscale_is_log"):
        # LogNorm needs positive values, handle potential errors
        try:
            norm = LogNorm(vmin=vmin, vmax=vmax)
        except:
            norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)
        
    im = ax.imshow(cdata, norm=norm, **im_kwargs)

    # Apply xlim and ylim if provided
    if plot_config.get("xlim") not in (None, "", "None"):
        ax.set_xlim(json.loads(plot_config.get("xlim")))
    if plot_config.get("ylim") not in (None, "", "None"):
        ax.set_ylim(json.loads(plot_config.get("ylim")))
        
    if plot_config.get("xscale_is_log"): ax.set_xscale("log")
    if plot_config.get("yscale_is_log"): ax.set_yscale("log")

    # Colorbar settings
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label(plot_config.get("clabel", ""), size=14)
    
    # Labels and Title
    ax.set_xlabel(plot_config.get("xlabel", ""), size=14)
    ax.set_ylabel(plot_config.get("ylabel", ""), size=14)
    ax.set_title(plot_config.get("title", ""), size=20)
    
    # Ticks
    ax.tick_params(axis='both', which='major', labelsize=12)
    
    # Save the figure
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        print(f"Saved plot to {save_path}")
    
    if return_fig:
        return fig
    
    plt.close(fig)

def plot_time_space_colormap(data_tx, time_array, spatial_extent, plot_config, save_path=None, return_fig=False):
    """
    Plots a 2D colormap where X-axis is space and Y-axis is time.
    """
    fig = plt.figure(figsize=plot_config.get("figsize", (8, 6)))
    ax = fig.add_subplot(111)
    
    t_min = time_array[0] / plot_config.get("yscale_val", UNIT_MAP["time_unit"])
    t_max = time_array[-1] / plot_config.get("yscale_val", UNIT_MAP["time_unit"])
    
    s_min = spatial_extent[0] / plot_config.get("xscale_val", UNIT_MAP["len_unit"])
    s_max = spatial_extent[1] / plot_config.get("xscale_val", UNIT_MAP["len_unit"])
    
    # Transpose data so that time is Y-axis and space is X-axis
    im_kwargs = {
        "extent": [s_min, s_max, t_min, t_max],
        "cmap": plot_config.get("cmap", "RdBu_r"),
        "vmin": plot_config.get("vmin"),
        "vmax": plot_config.get("vmax"),
        "aspect": "auto",
        "origin": "lower"
    }
    
    vmin = im_kwargs.pop("vmin")
    vmax = im_kwargs.pop("vmax")
    
    data_scaled = data_tx / plot_config.get("cscale_val", 1.0)
    
    if plot_config.get("cscale_is_log"):
        try:
            norm = LogNorm(vmin=vmin, vmax=vmax)
        except:
            norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)
    
    im = ax.imshow(data_scaled, norm=norm, **im_kwargs)
    
    if plot_config.get("xlim") not in (None, "", "None"):
        ax.set_xlim(json.loads(plot_config.get("xlim")))
    if plot_config.get("ylim") not in (None, "", "None"):
        ax.set_ylim(json.loads(plot_config.get("ylim")))

    if plot_config.get("xscale_is_log"): ax.set_xscale("log")
    if plot_config.get("yscale_is_log"): ax.set_yscale("log")

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label(plot_config.get("clabel", ""), size=14)
    
    ax.set_xlabel(plot_config.get("xlabel", "Space [$\\mu m$]"), size=14)
    ax.set_ylabel(plot_config.get("ylabel", "Time [$T_L$]"), size=14)
    ax.set_title(plot_config.get("plot_title", "Time-Space Map"), size=18)
    ax.tick_params(axis='both', which='major', labelsize=12)
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        print(f"Saved plot to {save_path}")
    
    if return_fig:
        return fig
    plt.close(fig)


def plot_fluid_element_phase_space(time_array, ux, uy, uz, save_path=None, return_fig=False):
    """
    Plots the fluid element momentum over time. 
    1. Momentum vs Time (px, pz)
    2. Phase Space Orbit (pz vs px) - "Figure 8"
    3. FFT of pz to find 2omega (SHG) component.
    """
    import scipy.fftpack
    from config_manager import freq_L

    t_TL = time_array / plot_config.get("yscale_val", UNIT_MAP["time_unit"])
    figs = []

    # Figure 1: Momentum over time
    fig1 = plt.figure(figsize=(6, 5))
    ax1 = fig1.add_subplot(111)
    ax1.plot(t_TL, ux, label="$p_x / (m_e c)$", color='blue')
    ax1.plot(t_TL, uz, label="$p_z / (m_e c)$", color='red')
    ax1.set_xlabel("Time [$T_L$]", size=14)
    ax1.set_ylabel("Momentum", size=14)
    ax1.set_title("Fluid Element Momentum", size=16)
    ax1.legend()
    ax1.grid(True)
    fig1.tight_layout()
    figs.append(fig1)
    
    # Figure 2: Phase Orbit
    fig2 = plt.figure(figsize=(6, 5))
    ax2 = fig2.add_subplot(111)
    ax2.plot(ux, uz, color='purple', linewidth=1)
    ax2.set_xlabel("$p_x / (m_e c)$", size=14)
    ax2.set_ylabel("$p_z / (m_e c)$", size=14)
    ax2.set_title("Phase Orbit ($p_x$ vs $p_z$)", size=16)
    ax2.grid(True)
    fig2.tight_layout()
    figs.append(fig2)
    
    # Figure 3: FFT of pz
    fig3 = plt.figure(figsize=(6, 5))
    ax3 = fig3.add_subplot(111)
    if len(t_TL) > 1:
        dt = time_array[1] - time_array[0]
        yf = scipy.fftpack.fft(uz)
        xf = scipy.fftpack.fftfreq(len(uz), dt)
        
        pos_mask = xf > 0
        freqs_omegaL = xf[pos_mask] / freq_L # Normalize to laser frequency
        amp = 2.0/len(uz) * np.abs(yf[pos_mask])
        
        ax3.plot(freqs_omegaL, amp, color='darkgreen')
        ax3.set_xlim(0, 5) # Show up to 5 omega_L
        ax3.set_xlabel("Frequency [$\\omega / \\omega_L$]", size=14)
        ax3.set_ylabel("Amplitude", size=14)
        ax3.set_title("FFT of $p_z$ (Longitudinal)", size=16)
        
        ax3.axvline(2.0, color='red', linestyle='--', alpha=0.5, label="$2\\omega_L$ (SHG)")
        ax3.legend()
        ax3.grid(True)
    fig3.tight_layout()
    figs.append(fig3)
        
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        base, ext = os.path.splitext(save_path)
        fig1.savefig(f"{base}_momentum{ext}")
        fig2.savefig(f"{base}_orbit{ext}")
        fig3.savefig(f"{base}_fft{ext}")
        print(f"Saved fluid element plots to {os.path.dirname(save_path)}")
    
    if return_fig:
        return figs
    for f in figs:
        plt.close(f)

def plot_reduced_file(file_path, plot_config=None, save_path=None, return_fig=False):
    import numpy as np
    import matplotlib.pyplot as plt
    import os
    
    if plot_config is None:
        plot_config = {}
        
    with open(file_path, 'r') as f:
        header_line = f.readline().strip()
        
    col_names = []
    if header_line.startswith('#'):
        parts = header_line[1:].split()
        for p in parts:
            if ']' in p:
                p = p.split(']', 1)[1]
            col_names.append(p)
    
    data = np.loadtxt(file_path)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if data.ndim == 1:
        data = data.reshape(1, -1)
        
    cscale = plot_config.get("cscale_val", 1.0)
    xscale = plot_config.get("xscale_val", 1.0)
    yscale = plot_config.get("yscale_val", 1.0)
        
    if data.shape[1] > 10:
        t = data[:, 1] / yscale
        spectra = data[:, 2:] / cscale
        
        cmap = plot_config.get('cmap', 'viridis')
        
        def parse_float(val):
            try:
                return float(val) if val not in (None, "", "None", "null") else None
            except (ValueError, TypeError):
                return None
                
        vmin = parse_float(plot_config.get('vmin'))
        vmax = parse_float(plot_config.get('vmax'))
        
        extent_x_max = spectra.shape[1] / xscale
        extent = [0, extent_x_max, t[0], t[-1]] if len(t) > 1 else [0, extent_x_max, 0, 1]
        
        if plot_config.get("cscale_is_log"):
            try:
                norm = LogNorm(vmin=vmin, vmax=vmax)
            except:
                norm = Normalize(vmin=vmin, vmax=vmax)
        else:
            norm = Normalize(vmin=vmin, vmax=vmax)
            
        im = ax.imshow(spectra, aspect='auto', origin='lower', cmap=cmap, norm=norm,
                       extent=extent)
        fig.colorbar(im, ax=ax, label=plot_config.get('clabel', 'Intensity'))
        
        ax.set_xlabel(plot_config.get('xlabel', "Bin Index"))
        ax.set_ylabel(plot_config.get('ylabel', "Time (s)"))
        
    else:
        t = data[:, 1] / xscale
        for i in range(2, data.shape[1]):
            label = col_names[i] if i < len(col_names) else f"Col {i}"
            ax.plot(t, data[:, i] / yscale, label=label)
            
        ax.set_xlabel(plot_config.get('xlabel', "Time (s)"))
        ax.set_ylabel(plot_config.get('ylabel', "Value"))
        ax.legend()
        ax.grid(True)
        
    import json
    def parse_list(val):
        if isinstance(val, list): return val
        if val in (None, "", "None", "null"): return None
        try: return json.loads(val)
        except: return None
        
    xlim = parse_list(plot_config.get('xlim'))
    ylim = parse_list(plot_config.get('ylim'))
    
    if data.shape[1] <= 10 and not ylim:
        def parse_float(val):
            try: return float(val) if val not in (None, "", "None", "null") else None
            except (ValueError, TypeError): return None
        vmin = parse_float(plot_config.get('vmin'))
        vmax = parse_float(plot_config.get('vmax'))
        if vmin is not None or vmax is not None:
            ylim = [vmin, vmax]
            
    if xlim: ax.set_xlim(xlim)
    if ylim: ax.set_ylim(ylim)
    
    if plot_config.get("xscale_is_log"): ax.set_xscale("log")
    if plot_config.get("yscale_is_log"): ax.set_yscale("log")
        
    title = plot_config.get('plot_title', os.path.basename(file_path))
    if "{" in title: # In case there's an unformatted template like {time}
        title = os.path.basename(file_path)
    ax.set_title(title)
    
    fig.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight')
        print(f"Saved reduced file plot to {save_path}")
        
    if return_fig:
        return fig
    plt.close(fig)
