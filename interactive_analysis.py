import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from config_manager import PLOT_CONFIGS, load_plot_configs
from data_loaders import _load_raw_data
from plotters import process_raw_data_for_plotting, plot_2d_image

def _process_one_file_worker(folder, header, file_num, yt_field, config, mimic_save, save_plot_enabled, save_plot_path):
    import os
    import gc
    import matplotlib.pyplot as plt
    from data_loaders import _load_raw_data
    from plotters import process_raw_data_for_plotting, plot_2d_image
    
    raw_data_tuple_with_dataset = _load_raw_data(folder, header, file_num, yt_field)
    if raw_data_tuple_with_dataset:
        raw_cdata, raw_xydata, raw_time, _ = raw_data_tuple_with_dataset
        
        cdata_plotting, xy_data_plotting, plot_params = process_raw_data_for_plotting(
            raw_cdata, raw_xydata, raw_time, config
        )
        
        save_path = None
        if save_plot_enabled:
            plot_config_name = config["name"]
            if mimic_save:
                save_dir = os.path.join(folder, "plotting", f"2d_{plot_config_name}")
                filename = f"{plot_config_name}_{file_num:04d}.png"
                save_path = os.path.join(save_dir, filename)
                os.makedirs(save_dir, exist_ok=True)
            else:
                save_dir = save_plot_path
                if save_dir:
                    filename = f"{plot_config_name}_{file_num:04d}.png"
                    save_path = os.path.join(save_dir, filename)
                    os.makedirs(save_dir, exist_ok=True)
        
        if save_path:
            plot_2d_image(cdata_plotting, xy_data_plotting, plot_params, save_path=save_path, return_fig=False)
            
        del raw_cdata, raw_xydata, raw_time, cdata_plotting, xy_data_plotting, plot_params, raw_data_tuple_with_dataset
        plt.close('all')
        gc.collect()

class PlotWindow(tk.Toplevel):
    def __init__(self, master, fig=None, analysis_params=None, analysis_gui_instance=None):
        super().__init__(master)
        self.title("Plot Viewer")
        
        scale_factor = 1.0
        if analysis_gui_instance:
            scale_factor = analysis_gui_instance.get_scale_factor()
        self.geometry(f"{int(800 * scale_factor)}x{int(800 * scale_factor)}")

        # Create a container frame for the plot and its toolbar
        self.fig_frame_container = ttk.Frame(self)
        self.fig_frame_container.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.preloaded_data = None
        self.analysis_gui_instance = analysis_gui_instance
        self.mimic_analysis_app_save = False # Default value
        self.raw_data_preloaded = False # New flag to indicate if raw data is preloaded

        if analysis_params:
            if "preloaded_data" in analysis_params:
                self.preloaded_data = analysis_params["preloaded_data"]
                temp_analysis_params = analysis_params.copy()
                del temp_analysis_params["preloaded_data"]
                self.analysis_params = temp_analysis_params
            else:
                self.analysis_params = analysis_params
            
            self.mimic_analysis_app_save = analysis_params.get("mimic_analysis_app_save", False)
            self.raw_data_preloaded = analysis_params.get("raw_data_preloaded", False) # Use new flag
        else:
            self.analysis_params = {"start": 0, "end": 0, "config": {}} # Default empty params
            self.raw_data_preloaded = False # Default to False if no analysis_params
        
        self.start = self.analysis_params.get("start", 0)
        self.end = self.analysis_params.get("end", 0)

        # Initialize preloaded_data structure if not already passed (e.g., for single file mode)
        if self.preloaded_data is None and self.start <= self.end:
            self.preloaded_data = [None] * (self.end - self.start + 1)

        if fig:
            self._display_figure(fig)
        
        # Only create slider controls if in batch mode (start != end)
        if self.start != self.end:
            controls_frame = ttk.Frame(self)
            controls_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

            self.current_file = tk.IntVar(value=self.start)
            
            # Add Previous Button
            prev_button = ttk.Button(controls_frame, text="<", command=self._decrement_file, width=3)
            prev_button.pack(side=tk.LEFT, padx=2)

            ttk.Label(controls_frame, text="File:").pack(side=tk.LEFT)
            self.slider = ttk.Scale(controls_frame, from_=self.start, to=self.end, orient=tk.HORIZONTAL, variable=self.current_file, command=self._on_slider_move)
            self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            self.file_entry = ttk.Entry(controls_frame, textvariable=self.current_file, width=5)
            self.file_entry.pack(side=tk.LEFT)
            self.file_entry.bind("<Return>", self._on_entry_change)

            # Add Next Button
            next_button = ttk.Button(controls_frame, text=">", command=self._increment_file, width=3)
            next_button.pack(side=tk.LEFT, padx=2)
            
            self.update_plot(self.start) # Initial plot for batch mode
        else:
            # For single file mode, current_file is conceptually just 'start' or 'end'
            self.current_file = tk.IntVar(value=self.start) # Still create current_file for consistent access
            if not self.analysis_params.get("static_plot", False):
                self.update_plot(self.start) # Initial plot for single file mode

    def _on_slider_move(self, val):
        self.current_file.set(int(float(val)))
        self.update_plot(int(float(val)))

    def _on_entry_change(self, event):
        try:
            val = int(self.file_entry.get())
            if self.start <= val <= self.end:
                self.current_file.set(val)
                self.update_plot(val)
        except ValueError:
            pass # Or show an error

    def _increment_file(self):
        current = self.current_file.get()
        if current < self.end:
            self.current_file.set(current + 1)
            self.update_plot(current + 1)

    def _decrement_file(self):
        current = self.current_file.get()
        if current > self.start:
            self.current_file.set(current - 1)
            self.update_plot(current - 1)

    def update_plot(self, file_num):
        # Always reload global configs to ensure the latest version is used
        load_plot_configs()
        save_path = None
        cdata_plotting, xy_data_plotting, plot_params = None, None, None

        # Get the name of the plot configuration from the original analysis parameters
        plot_config_name = self.analysis_params["config"]["name"]
        
        # Get the LATEST configuration from the reloaded global PLOT_CONFIGS
        latest_config = PLOT_CONFIGS.get(plot_config_name)
        if not latest_config:
            messagebox.showerror("Error", f"Plot configuration '{plot_config_name}' not found after reload.")
            return

        raw_cdata, raw_xydata, raw_time = None, None, None
        cdata_plotting, xy_data_plotting, plot_params = None, None, None

        if self.raw_data_preloaded: # Changed from plots_pre_saved
            idx = file_num - self.start
            if 0 <= idx < len(self.preloaded_data) and self.preloaded_data[idx] is not None:
                # Raw data is preloaded. Process it now with the latest config.
                raw_cdata, raw_xydata, raw_time = self.preloaded_data[idx]
            else:
                messagebox.showinfo("No Preloaded Raw Data", f"Preloaded raw data for file {file_num} is missing. Cannot display.")
                return
        else:
            # Not in preloaded mode, or not raw data preloaded, load raw data.
            raw_data_tuple = _load_raw_data(self.analysis_params["folder"], self.analysis_params["header"], file_num, latest_config["yt_field"])
            if raw_data_tuple:
                raw_cdata, raw_xydata, raw_time, _ = raw_data_tuple
            else:
                messagebox.showinfo("No Data", f"Could not load raw data for file {file_num}.")
                return
        
        # Now process the raw data with the latest config
        if raw_cdata is not None:
            cdata_plotting, xy_data_plotting, plot_params = process_raw_data_for_plotting(
                raw_cdata, raw_xydata, raw_time, latest_config
            )
        
        save_path = None
        if self.analysis_gui_instance and self.analysis_gui_instance.save_plot_enabled.get():
            if self.mimic_analysis_app_save:
                # Mimic analysis_app saving behavior
                folderPath = self.analysis_params["folder"]
                save_dir = os.path.join(folderPath, "plotting", f"2d_{plot_config_name}")
                filename = f"{plot_config_name}_{file_num:04d}.png"
                save_path = os.path.join(save_dir, filename)
                os.makedirs(save_dir, exist_ok=True)
            else:
                # Original saving behavior with user-specified path
                save_dir = self.analysis_gui_instance.save_plot_path.get()
                if save_dir:
                    filename = f"{plot_config_name}_{file_num:04d}.png"
                    save_path = os.path.join(save_dir, filename)
                    os.makedirs(save_dir, exist_ok=True)
                else:
                    messagebox.showwarning("Save Plot", "Save path not specified in settings.")
        
        if cdata_plotting is not None:
            fig = plot_2d_image(cdata_plotting, xy_data_plotting, plot_params, return_fig=True, save_path=save_path)
            if not self.analysis_gui_instance.skip_display_plot.get():
                self._display_figure(fig)
            else:
                plt.close(fig)

    def _display_figure(self, fig):
        # Clear existing widgets from the figure container
        for widget in self.fig_frame_container.winfo_children():
            widget.destroy()
        
        canvas = FigureCanvasTkAgg(fig, self.fig_frame_container) # Use fig_frame_container as parent
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        toolbar = NavigationToolbar2Tk(canvas, self.fig_frame_container) # Use fig_frame_container as parent
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        plt.close(fig)

class AnalysisGUI:
    def __init__(self, master):
        self.master = master
        master.title("Interactive Analysis Tool")
        master.geometry("700x500") # Set an initial window size
        main_frame = ttk.Frame(master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # --- WIDGETS ---
        ttk.Label(main_frame, text="Folder Path:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.folder_path = tk.StringVar()
        folder_entry = ttk.Entry(main_frame, textvariable=self.folder_path, width=50)
        folder_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E))
        browse_button = ttk.Button(main_frame, text="Browse...", command=self.browse_folder)
        browse_button.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(main_frame, text="Header Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.header_name = tk.StringVar()
        self.header_menu = ttk.Combobox(main_frame, textvariable=self.header_name)
        self.header_menu.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E))
        get_headers_btn = ttk.Button(main_frame, text="Get Headers", command=self.get_headers)
        get_headers_btn.grid(row=1, column=3, sticky=tk.W, padx=5)

        ttk.Label(main_frame, text="Analysis Mode:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.analysis_mode = tk.StringVar(value="2D Snapshot")
        mode_choices = ["2D Snapshot", "1D Line Probe", "Fluid Element", "Reduced File"]
        self.mode_menu = ttk.Combobox(main_frame, textvariable=self.analysis_mode, state="readonly", values=mode_choices)
        self.mode_menu.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E))
        self.mode_menu.bind("<<ComboboxSelected>>", self.on_mode_change)

        self.process_mode = tk.StringVar(value="batch")
        ttk.Label(main_frame, text="Processing Mode:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(main_frame, text="Batch", variable=self.process_mode, value="batch", command=self.toggle_entries).grid(row=3, column=1, sticky=tk.W)
        ttk.Radiobutton(main_frame, text="Single File", variable=self.process_mode, value="single", command=self.toggle_entries).grid(row=3, column=2, sticky=tk.W)

        ttk.Label(main_frame, text="Start #:").grid(row=4, column=0, sticky=tk.W)
        self.batch_start = tk.StringVar()
        self.batch_start_entry = ttk.Entry(main_frame, textvariable=self.batch_start, width=10)
        self.batch_start_entry.grid(row=4, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="End #:").grid(row=4, column=2, sticky=tk.W)
        self.batch_end = tk.StringVar()
        self.batch_end_entry = ttk.Entry(main_frame, textvariable=self.batch_end, width=10)
        self.batch_end_entry.grid(row=4, column=3, sticky=tk.W, padx=5)

        ttk.Label(main_frame, text="Single File #:").grid(row=5, column=0, sticky=tk.W)
        self.single_file = tk.StringVar()
        self.single_file_entry = ttk.Entry(main_frame, textvariable=self.single_file, width=10)
        self.single_file_entry.grid(row=5, column=1, sticky=tk.W)

        ttk.Label(main_frame, text="Plot Data:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.plot_data = tk.StringVar(value="all")
        self.plot_data_menu = ttk.Combobox(main_frame, textvariable=self.plot_data, state="readonly", values=["all"])
        self.plot_data_menu.grid(row=6, column=1, columnspan=2, sticky=(tk.W, tk.E))
        get_fields_button = ttk.Button(main_frame, text="Get Fields", command=self.get_fields)
        get_fields_button.grid(row=6, column=3, sticky=tk.W, padx=5)

        ttk.Label(main_frame, text="Plot Type:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.plot_type = tk.StringVar()
        plot_choices = self.load_plot_choices()
        self.plot_type_menu = ttk.Combobox(main_frame, textvariable=self.plot_type, state="readonly", values=plot_choices)
        self.plot_type_menu.grid(row=7, column=1, columnspan=2, sticky=(tk.W, tk.E))

        main_frame.grid_rowconfigure(8, minsize=20)
        
        ttk.Button(main_frame, text="Run Analysis", command=self.run_analysis).grid(row=9, column=0, columnspan=4, pady=10)
        
        # Frame for settings and config buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=10, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        center_frame = ttk.Frame(buttons_frame)
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        ttk.Button(center_frame, text="Settings", command=self.open_settings_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(center_frame, text="Plot Config", command=self.open_config_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(center_frame, text="Help", command=self.open_help_window).pack(side=tk.LEFT, padx=5)
        
        # UI Scale
        scale_frame = ttk.Frame(buttons_frame)
        scale_frame.pack(side=tk.RIGHT, padx=5)
        self.ui_scale = tk.StringVar(value="100%")
        self.ui_scale_entry = ttk.Entry(scale_frame, textvariable=self.ui_scale, width=6)
        self.ui_scale_entry.pack(side=tk.RIGHT, padx=5)
        self.ui_scale_entry.bind("<Return>", self.on_scale_change)
        self.ui_scale_entry.bind("<FocusOut>", self.on_scale_change)
        ttk.Label(buttons_frame, text="Scale %:").pack(side=tk.RIGHT)

        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)

        self.plot_window = None # To hold the reference to the plot window.
        self.config_file = 'gui_config.json'
        self.load_and_save_all_batch = tk.BooleanVar(value=False) # Renamed setting
        self.save_plot_enabled = tk.BooleanVar(value=False)
        self.save_plot_path = tk.StringVar(value="")
        self.mimic_analysis_app_save = tk.BooleanVar(value=False) # New setting for saving behavior
        self.skip_display_plot = tk.BooleanVar(value=False) # Skip showing to avoid memory leak
        self.load_config()
        self.toggle_entries()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.save_config()
        self.master.destroy()
        
    def open_help_window(self):
        help_win = tk.Toplevel(self.master)
        help_win.title("User Manual")
        scale_factor = self.get_scale_factor()
        help_win.geometry(f"{int(700 * scale_factor)}x{int(500 * scale_factor)}")
        
        text_widget = tk.Text(help_win, wrap="word", padx=10, pady=10, font=("Helvetica", 10))
        scrollbar = ttk.Scrollbar(help_win, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        text_widget.pack(side="left", fill="both", expand=True)
        
        try:
            with open(os.path.join(os.path.dirname(__file__), "UserManual.md"), "r") as f:
                content = f.read()
        except FileNotFoundError:
            content = "UserManual.md not found. Please ensure the file exists."
            
        text_widget.insert("1.0", content)
        text_widget.configure(state="disabled") # Make read-only

    def on_mode_change(self, event=None):
        mode = self.analysis_mode.get()
        if mode == "2D Snapshot":
            self.plot_type_menu.config(state="readonly")
            self.process_mode.set("batch")
            self.toggle_entries()
        elif mode == "1D Line Probe":
            self.plot_type_menu.config(state="disabled")
            self.process_mode.set("single")
            self.toggle_entries()
        elif mode == "Fluid Element":
            self.plot_type_menu.config(state="disabled")
            self.process_mode.set("single")
            self.toggle_entries()
            self.plot_data_menu['values'] = ["electron", "hydrogen"]
            if self.plot_data.get() not in ["electron", "hydrogen"]:
                self.plot_data.set("electron")

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.folder_path.set(config.get("folder_path", ""))
            self.header_name.set(config.get("header_name", "plt"))
            
            # Use getattr/hasattr logic to not break existing gui_config
            if hasattr(self, 'analysis_mode'):
                self.analysis_mode.set(config.get("analysis_mode", "2D Snapshot"))
                self.on_mode_change()
                
            self.process_mode.set(config.get("process_mode", "batch"))
            self.batch_start.set(config.get("batch_start", ""))
            self.batch_end.set(config.get("batch_end", ""))
            self.single_file.set(config.get("single_file", ""))
            
            # Reload PLOT_CONFIGS here to ensure plot_choices are up-to-date
            load_plot_configs()
            plot_choices = self.load_plot_choices()
            
            self.plot_type_menu['values'] = plot_choices # Update combobox values
            # Set plot_type only if it exists in the reloaded choices, otherwise default
            saved_plot_type = config.get("plot_type", "")
            if saved_plot_type in plot_choices:
                self.plot_type.set(saved_plot_type)
            elif plot_choices:
                self.plot_type.set(plot_choices[0]) # Default to first available
            else:
                self.plot_type.set("") # No choices available

            self.load_and_save_all_batch.set(config.get("load_and_save_all_batch", False)) # Load renamed setting
            self.save_plot_enabled.set(config.get("save_plot_enabled", False))
            self.save_plot_path.set(config.get("save_plot_path", ""))
            self.mimic_analysis_app_save.set(config.get("mimic_analysis_app_save", False)) # Load new setting
            self.skip_display_plot.set(config.get("skip_display_plot", False))
            
            # Load and apply UI scale
            self.ui_scale.set(config.get("ui_scale", "100%"))
            self.apply_ui_scale()
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_config(self):
        config = {
            "folder_path": self.folder_path.get(), "header_name": self.header_name.get(),
            "analysis_mode": self.analysis_mode.get() if hasattr(self, 'analysis_mode') else "2D Snapshot",
            "process_mode": self.process_mode.get(), "batch_start": self.batch_start.get(),
            "batch_end": self.batch_end.get(), "single_file": self.single_file.get(),
            "plot_type": self.plot_type.get(),
            "load_and_save_all_batch": self.load_and_save_all_batch.get(), # Save renamed setting
            "save_plot_enabled": self.save_plot_enabled.get(),
            "save_plot_path": self.save_plot_path.get(),
            "mimic_analysis_app_save": self.mimic_analysis_app_save.get(), # Save new setting
            "skip_display_plot": self.skip_display_plot.get(),
            "ui_scale": self.ui_scale.get(),
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def on_scale_change(self, event=None):
        self.apply_ui_scale()
        self.save_config()

    def get_scale_factor(self):
        try:
            return float(self.ui_scale.get().replace('%', '')) / 100.0
        except ValueError:
            return 1.0

    def apply_ui_scale(self):
        scale_factor = self.get_scale_factor()
        
        from tkinter import font
        for font_name in ["TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"]:
            try:
                f = font.nametofont(font_name)
                if not hasattr(self, '_original_font_sizes'):
                    self._original_font_sizes = {}
                if font_name not in self._original_font_sizes:
                    self._original_font_sizes[font_name] = f.cget("size")
                
                base_size = self._original_font_sizes[font_name]
                new_size = int(base_size * scale_factor)
                if base_size < 0:
                    new_size = -int(abs(base_size) * scale_factor)
                f.configure(size=new_size)
            except Exception:
                pass
                
        base_w, base_h = 700, 500
        new_w, new_h = int(base_w * scale_factor), int(base_h * scale_factor)
        self.master.geometry(f"{new_w}x{new_h}")

    def toggle_entries(self):
        if self.process_mode.get() == "batch":
            self.batch_start_entry.config(state="normal")
            self.batch_end_entry.config(state="normal")
            self.single_file_entry.config(state="disabled")
        else:
            self.batch_start_entry.config(state="disabled")
            self.batch_end_entry.config(state="disabled")
            self.single_file_entry.config(state="normal")

    def load_plot_choices(self):
        # Reload PLOT_CONFIGS here to ensure the latest choices are available
        load_plot_configs()
        try:
            return [cfg["name"] for cfg in PLOT_CONFIGS.values()]
        except:
            return ["(config error)"]

    def browse_folder(self):
        folder_selected = filedialog.askdirectory(initialdir=self.folder_path.get())
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.get_headers() # Automatically try to fetch headers when browsing

    def get_headers(self):
        folder = self.folder_path.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Invalid Folder Path.")
            return
            
        try:
            target_dir = os.path.join(folder, 'diags')
            if not os.path.isdir(target_dir):
                target_dir = folder
                
            headers = [d for d in os.listdir(target_dir) if os.path.isdir(os.path.join(target_dir, d))]
            headers = [h for h in headers if h not in ['plotting', '.ipynb_checkpoints']]
            
            reduced_dir = os.path.join(target_dir, 'reducedfiles')
            if os.path.isdir(reduced_dir) and any(f.endswith('.txt') for f in os.listdir(reduced_dir)):
                if 'reducedfiles' not in headers:
                    headers.append('reducedfiles')
            
            if headers:
                self.header_menu['values'] = headers
                if self.header_name.get() not in headers:
                    self.header_name.set(headers[0])
            else:
                self.header_menu['values'] = []
                messagebox.showwarning("Warning", "No header directories found in the selected folder.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get headers: {str(e)}")

    def get_fields(self):
        folder = self.folder_path.get()
        header = self.header_name.get()
        mode = self.process_mode.get()

        if not all([folder, header]):
            messagebox.showerror("Error", "Folder Path and Header Name must be set.")
            return

        if header == 'reducedfiles':
            target_dir = os.path.join(folder, 'diags', 'reducedfiles')
            if not os.path.exists(target_dir):
                target_dir = os.path.join(folder, 'reducedfiles')
            if os.path.exists(target_dir):
                files = [f for f in os.listdir(target_dir) if f.endswith('.txt')]
                if files:
                    self.plot_data_menu['values'] = files
                    self.plot_data.set(files[0])
                    return
            messagebox.showwarning("Warning", "No .txt files found in reducedfiles.")
            return

        try:
            if mode == "batch":
                file_num = int(self.batch_start.get())
            else: # mode == "single"
                file_num = int(self.single_file.get())
        except ValueError:
            messagebox.showerror("Error", "A valid 'Start #' or 'Single File #' must be provided to get fields.")
            return

        # We need to load the dataset to get the field list. We can use any field to do this.
        # The function will return the dataset object as the 4th element.
        # Here, we don't care about what yt_field we pass to _load_raw_data, as we just want the dataset.
        raw_data_tuple = _load_raw_data(folder, header, file_num, yt_field=None) 

        if not raw_data_tuple:
            messagebox.showerror("Error", f"Could not load data for file {file_num} to get fields.")
            return 
        
        _, _, _, dataset = raw_data_tuple # Unpack to get the dataset object

        if not dataset:
            messagebox.showerror("Error", "Failed to get dataset object.")
            return

        # Extract field names from the dataset's field_list
        # field_list is a list of tuples, e.g., [('boxlib', 'Ex'), ('boxlib', 'Ey'), ...]
        # We are interested in the second element of the tuple.
        # Use a set to get unique field names in case of duplicates.
        field_choices = sorted(list(set([f"{kind}_{obj}" for kind, obj in dataset.field_list])))
        
        if not field_choices:
            messagebox.showinfo("No Fields", "No plottable fields found in the dataset.")
            return

        # Update the Combobox with the new choices
        field_choices.insert(0, "all")
        self.plot_data_menu['values'] = field_choices
        # Set the first available choice as the default selection
        if field_choices:
            self.plot_data.set(field_choices[0])
        else:
            self.plot_data.set("all")

    def run_analysis(self):
        self.save_config()
        folder = self.folder_path.get()
        header = self.header_name.get()
        mode = self.process_mode.get()
        plot_data_field = self.plot_data.get()
        plot_type = self.plot_type.get()
        load_all_batch_mode = self.load_and_save_all_batch.get()
        analysis_mode = self.analysis_mode.get() if hasattr(self, 'analysis_mode') else "2D Snapshot"

        if analysis_mode == "Fluid Element":
            from data_loaders import load_fluid_element_series
            from plotters import plot_fluid_element_phase_space
            
            species = plot_data_field
            t, ux, uy, uz = load_fluid_element_series(folder, header, species)
            if t is not None:
                save_path = None
                if self.save_plot_enabled.get() or self.mimic_analysis_app_save.get():
                    if self.mimic_analysis_app_save.get():
                        save_dir = os.path.join(folder, "plotting", f"1d_{header}")
                    else:
                        save_dir = self.save_plot_path.get()
                        if not save_dir:
                            save_dir = os.path.join(folder, "plotting")
                    save_path = os.path.join(save_dir, f"fluid_orbit_{header}.png")
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                figs = plot_fluid_element_phase_space(t, ux, uy, uz, save_path=save_path, return_fig=True)
                
                if not hasattr(self, 'fluid_windows') or len(self.fluid_windows) != len(figs) or any(not w.winfo_exists() for w in self.fluid_windows):
                    if hasattr(self, 'fluid_windows'):
                        for w in self.fluid_windows:
                            if w and w.winfo_exists():
                                w.destroy()
                    self.fluid_windows = []
                    
                    if self.plot_window and self.plot_window.winfo_exists():
                        self.plot_window.destroy()
                        
                    for f in figs:
                        w = PlotWindow(self.master, fig=f, analysis_params={"start":0, "end":0, "config": {}, "static_plot": True}, analysis_gui_instance=self)
                        self.fluid_windows.append(w)
                else:
                    for w, f in zip(self.fluid_windows, figs):
                        w._display_figure(f)
            else:
                messagebox.showerror("Error", "Could not load fluid element data.")
            return

        elif analysis_mode == "Reduced File":
            from plotters import plot_reduced_file
            
            filename = plot_data_field
            target_dir = os.path.join(folder, 'diags', 'reducedfiles')
            if not os.path.exists(target_dir):
                target_dir = os.path.join(folder, 'reducedfiles')
            
            file_path = os.path.join(target_dir, filename)
            if not os.path.exists(file_path):
                messagebox.showerror("Error", f"Could not find {file_path}")
                return
            
            load_plot_configs()
            config_name = self.plot_type.get()
            config = PLOT_CONFIGS.get(config_name, {})
            
            save_path = None
            if self.save_plot_enabled.get() or self.mimic_analysis_app_save.get():
                if self.mimic_analysis_app_save.get():
                    save_dir = os.path.join(folder, "plotting", "reducedfiles")
                else:
                    save_dir = self.save_plot_path.get()
                    if not save_dir:
                        save_dir = os.path.join(folder, "plotting")
                save_path = os.path.join(save_dir, f"{filename[:-4]}.png")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
            fig = plot_reduced_file(file_path, config, save_path=save_path, return_fig=True)
            
            if self.plot_window and self.plot_window.winfo_exists() and self.plot_window.analysis_params.get("static_plot"):
                self.plot_window._display_figure(fig)
                self.plot_window.analysis_params = {"start":0, "end":0, "config": {}, "static_plot": True}
            else:
                if self.plot_window and self.plot_window.winfo_exists():
                    self.plot_window.destroy()
                self.plot_window = PlotWindow(self.master, fig=fig, analysis_params={"start":0, "end":0, "config": {}, "static_plot": True}, analysis_gui_instance=self)
                
            return

        elif analysis_mode == "1D Line Probe":
            from data_loaders import load_time_series_field
            from plotters import plot_time_space_colormap
            
            field_name = plot_data_field
            clean_name = field_name
            if clean_name.startswith('openpmd_'):
                clean_name = clean_name[len('openpmd_'):]
                
            base_field = clean_name[0] if clean_name in ['Ex', 'Ey', 'Ez', 'Bx', 'By', 'Bz', 'ex', 'ey', 'ez', 'bx', 'by', 'bz'] else clean_name
            coord = clean_name[1].lower() if clean_name in ['Ex', 'Ey', 'Ez', 'Bx', 'By', 'Bz', 'ex', 'ey', 'ez', 'bx', 'by', 'bz'] else None
            if clean_name in ['Jx', 'Jy', 'Jz', 'jx', 'jy', 'jz']:
                base_field = clean_name[0]
                coord = clean_name[1].lower()
            
            data_tx, t_arr, s_arr, extent = load_time_series_field(folder, header, base_field, coord=coord)
            if data_tx is not None:
                cfg = {"plot_title": f"{clean_name} Time-Space", "cmap": "RdBu_r", "vmin": None, "vmax": None, "cscale_val": 1.0, "xscale_val": 1.0, "yscale_val": 1.0}
                save_path = None
                if self.save_plot_enabled.get() or self.mimic_analysis_app_save.get():
                    if self.mimic_analysis_app_save.get():
                        save_dir = os.path.join(folder, "plotting", "1d_line_probe")
                    else:
                        save_dir = self.save_plot_path.get()
                        if not save_dir:
                            save_dir = os.path.join(folder, "plotting")
                    save_path = os.path.join(save_dir, f"line_probe_{clean_name}.png")
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                fig = plot_time_space_colormap(data_tx, t_arr, extent, cfg, save_path=save_path, return_fig=True)
                
                if self.plot_window and self.plot_window.winfo_exists() and self.plot_window.analysis_params.get("static_plot"):
                    self.plot_window._display_figure(fig)
                    self.plot_window.analysis_params = {"start":0, "end":0, "config": {}, "static_plot": True}
                else:
                    if self.plot_window and self.plot_window.winfo_exists():
                        self.plot_window.destroy()
                    self.plot_window = PlotWindow(self.master, fig=fig, analysis_params={"start":0, "end":0, "config": {}, "static_plot": True}, analysis_gui_instance=self)
            else:
                messagebox.showerror("Error", "Could not load 1D line probe data.")
            return

        # --- Original 2D Snapshot Logic below ---
        if not all([folder, header, plot_data_field]):
            messagebox.showerror("Error", "Folder Path, Header Name, and Plot Data must be set.")
            return
        if plot_data_field != "all" and not plot_type:
            messagebox.showerror("Error", "Plot Type must be set.")
            return

        fields_to_process = []
        if plot_data_field == "all":
            try:
                if mode == "batch":
                    file_num = int(self.batch_start.get())
                else:
                    file_num = int(self.single_file.get())
            except ValueError:
                messagebox.showerror("Error", "A valid 'Start #' or 'Single File #' must be provided to get fields.")
                return
                
            raw_data_tuple = _load_raw_data(folder, header, file_num, yt_field=None) 
            if not raw_data_tuple or not raw_data_tuple[3]:
                messagebox.showerror("Error", f"Could not load data or dataset for file {file_num}.")
                return 
                
            dataset = raw_data_tuple[3]
            field_choices = sorted(list(set([f"{kind}_{obj}" for kind, obj in dataset.field_list])))
            load_plot_configs()
            
            for field in field_choices:
                if field in PLOT_CONFIGS:
                    fields_to_process.append((field, field))
                    
            if not fields_to_process:
                messagebox.showinfo("No Matches", "No plot configurations found matching the available dataset names.")
                return
        else:
            fields_to_process = [(plot_data_field, plot_type)]

        if not hasattr(self, 'all_mode_windows'):
            self.all_mode_windows = []

        if plot_data_field != "all":
            if self.plot_window and self.plot_window.winfo_exists():
                self.plot_window.destroy()
        else:
            for w in self.all_mode_windows:
                if w and w.winfo_exists():
                    w.destroy()
            self.all_mode_windows = []

        try:
            for current_field, current_plot_type in fields_to_process:
                load_plot_configs()
                config = PLOT_CONFIGS.get(current_plot_type)
                
                if not config:
                    if plot_data_field == "all": 
                        continue
                    messagebox.showinfo("Default Config", f"No specific plot configuration found for '{current_plot_type}'. Using a default configuration.")
                    config = {
                        "name": current_plot_type, "yt_field": current_field, "cscale": "1.0", "cscale_val": 1.0,
                        "xscale": "1.0", "xscale_val": 1.0, "yscale": "1.0", "yscale_val": 1.0,
                        "plot_title": f"{current_field} at time {{time:.1f}} TL", "cmap": "viridis", "vmin": None,
                        "vmax": None, "clabel": current_field, "xlabel": "x [$\\mu m$]", "ylabel": "y [$\\mu m$]",
                        "resolution_factor": 1, "xlim": None, "ylim": None
                    }
                    PLOT_CONFIGS[current_plot_type] = config
                
                # Make a copy so we don't modify the global config permanently if we change yt_field
                config = config.copy()
                config['yt_field'] = current_field
                
                if mode == "single":
                    file_num = int(self.single_file.get())
                    raw_data_tuple_with_dataset = _load_raw_data(folder, header, file_num, config["yt_field"])
                    if raw_data_tuple_with_dataset:
                        raw_cdata, raw_xydata, raw_time, _ = raw_data_tuple_with_dataset
                        cdata, xydata, params = process_raw_data_for_plotting(raw_cdata, raw_xydata, raw_time, config)
                        
                        save_path = None
                        if self.save_plot_enabled.get() or self.mimic_analysis_app_save.get():
                            if self.mimic_analysis_app_save.get():
                                save_dir = os.path.join(folder, "plotting", f"2d_{config['name']}")
                            else:
                                save_dir = self.save_plot_path.get()
                                if not save_dir:
                                    save_dir = os.path.join(folder, "plotting")
                            save_path = os.path.join(save_dir, f"{config['name']}_{file_num:04d}.png")
                            os.makedirs(os.path.dirname(save_path), exist_ok=True)
                            
                        fig = plot_2d_image(cdata, xydata, params, return_fig=True, save_path=save_path)
                        
                        analysis_params = {
                            "folder": folder, "header": header,
                            "start": file_num, "end": file_num, "config": config,
                            "preloaded_data": [(raw_cdata, raw_xydata, raw_time)],
                            "mimic_analysis_app_save": self.mimic_analysis_app_save.get(),
                            "raw_data_preloaded": True
                        }
                        w = PlotWindow(self.master, fig=fig, analysis_params=analysis_params, analysis_gui_instance=self)
                        if plot_data_field == "all":
                            self.all_mode_windows.append(w)
                        else:
                            self.plot_window = w
                    else:
                        if plot_data_field != "all":
                            messagebox.showinfo("No Data", f"Could not generate plot data for file {file_num}.")
    
                elif mode == "batch":
                    start = int(self.batch_start.get())
                    end = int(self.batch_end.get())
                    
                    analysis_params = {
                        "folder": folder, "header": header,
                        "start": start, "end": end, "config": config,
                        "mimic_analysis_app_save": self.mimic_analysis_app_save.get(),
                        "plots_pre_saved": False,
                        "raw_data_preloaded": False
                    }
    
                    if self.load_and_save_all_batch.get():
                        import multiprocessing
                        for file_num in range(start, end + 1):
                            p = multiprocessing.Process(
                                target=_process_one_file_worker,
                                args=(
                                    folder, header, file_num, config["yt_field"], config,
                                    self.mimic_analysis_app_save.get(),
                                    self.save_plot_enabled.get(),
                                    self.save_plot_path.get()
                                )
                            )
                            p.start()
                            p.join()
                            if p.exitcode != 0:
                                print(f"Warning: Worker for file {file_num} exited with code {p.exitcode}")
                    
                    if plot_data_field == "all":
                        w = PlotWindow(self.master, analysis_params=analysis_params, analysis_gui_instance=self)
                        self.all_mode_windows.append(w)
                    else:
                        if self.plot_window and self.plot_window.winfo_exists() and not self.plot_window.analysis_params.get("static_plot"):
                            self.plot_window.analysis_params = analysis_params
                            self.plot_window.start = analysis_params["start"]
                            self.plot_window.end = analysis_params["end"]
                            self.plot_window.raw_data_preloaded = analysis_params.get("raw_data_preloaded", False)
                            if "preloaded_data" in analysis_params:
                                self.plot_window.preloaded_data = analysis_params["preloaded_data"]
                            else:
                                self.plot_window.preloaded_data = None
                                
                            if hasattr(self.plot_window, 'slider'):
                                self.plot_window.slider.config(from_=self.plot_window.start, to=self.plot_window.end)
                                self.plot_window.current_file.set(self.plot_window.start)
                            self.plot_window.update_plot(self.plot_window.start)
                        else:
                            if self.plot_window and self.plot_window.winfo_exists():
                                self.plot_window.destroy()
                            self.plot_window = PlotWindow(self.master, analysis_params=analysis_params, analysis_gui_instance=self)

            if plot_data_field == "all":
                from plotters import plot_reduced_file
                target_dir = os.path.join(folder, 'diags', 'reducedfiles')
                if not os.path.exists(target_dir):
                    target_dir = os.path.join(folder, 'reducedfiles')
                
                if os.path.exists(target_dir):
                    for filename in os.listdir(target_dir):
                        if filename.endswith('.txt') and filename in PLOT_CONFIGS:
                            config_rf = PLOT_CONFIGS[filename]
                            file_path = os.path.join(target_dir, filename)
                            
                            save_path = None
                            if self.save_plot_enabled.get() or self.mimic_analysis_app_save.get():
                                if self.mimic_analysis_app_save.get():
                                    save_dir = os.path.join(folder, "plotting", "reducedfiles")
                                else:
                                    save_dir = self.save_plot_path.get()
                                    if not save_dir:
                                        save_dir = os.path.join(folder, "plotting")
                                save_path = os.path.join(save_dir, f"{filename[:-4]}.png")
                                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                                
                            fig = plot_reduced_file(file_path, config_rf, save_path=save_path, return_fig=True)
                            w = PlotWindow(self.master, fig=fig, analysis_params={"start":0, "end":0, "config": config_rf, "static_plot": True}, analysis_gui_instance=self)
                            self.all_mode_windows.append(w)

        except ValueError:
            messagebox.showerror("Error", "File numbers must be integers.")
        except Exception as e:
            messagebox.showerror("Analysis Error", str(e))

    def open_settings_window(self):
        SettingsWindow(self.master, self)

    def open_config_window(self):
        ConfigWindow(self.master, self)

class SettingsWindow(tk.Toplevel):
    def __init__(self, master, parent_gui):
        super().__init__(master)
        self.title("Settings")
        scale_factor = parent_gui.get_scale_factor()
        self.geometry(f"{int(500 * scale_factor)}x{int(250 * scale_factor)}") # Increased size to accommodate new widgets
        self.parent_gui = parent_gui # Reference to the main GUI

        settings_frame = ttk.Frame(self, padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True)

        settings_frame.columnconfigure(1, weight=1) # Allow entry fields to expand

        # Load all plot files in batch mode setting
        ttk.Checkbutton(settings_frame, 
                        text="Load and save all plot files first in batch mode",
                        variable=self.parent_gui.load_and_save_all_batch).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5) # Changed columnspan to 3
        
        # Save Plot settings
        self.save_plot_checkbox = ttk.Checkbutton(settings_frame,
                                                  text="Enable Plot Saving",
                                                  variable=self.parent_gui.save_plot_enabled,
                                                  command=self._toggle_save_path_entry)
        self.save_plot_checkbox.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # New: Mimic analysis_app saving behavior
        self.mimic_save_checkbox = ttk.Checkbutton(settings_frame,
                                                  text="Mimic analysis_app auto-saving",
                                                  variable=self.parent_gui.mimic_analysis_app_save,
                                                  command=self._toggle_save_path_entry)
        self.mimic_save_checkbox.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # New: Skip plotting to display (to avoid memory crashes during batch runs)
        self.skip_display_checkbox = ttk.Checkbutton(settings_frame,
                                                    text="Do not show plot (only read, plot, and save to PNG)",
                                                    variable=self.parent_gui.skip_display_plot)
        self.skip_display_checkbox.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)

        ttk.Label(settings_frame, text="Save Path:").grid(row=4, column=0, sticky=tk.W, padx=(20,0))
        self.save_path_entry = ttk.Entry(settings_frame, textvariable=self.parent_gui.save_plot_path, width=40)
        self.save_path_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5)

        self.browse_path_button = ttk.Button(settings_frame, text="Browse...", command=self._browse_save_path)
        self.browse_path_button.grid(row=4, column=2, sticky=tk.W)

        # Initial state setup
        self._toggle_save_path_entry()

        # Add a protocol for closing the window to save settings
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _toggle_save_path_entry(self):
        if self.parent_gui.mimic_analysis_app_save.get():
            state = "disabled"
        else:
            state = "normal" if self.parent_gui.save_plot_enabled.get() else "disabled"
        self.save_path_entry.config(state=state)
        self.browse_path_button.config(state=state)

    def _browse_save_path(self):
        path = filedialog.askdirectory(initialdir=self.folder_path.get())
        if path:
            self.parent_gui.save_plot_path.set(path)

    def on_closing(self):
        self.parent_gui.save_config() # Save settings when window is closed
        print("Settings window closed.")
        self.destroy()

class ConfigWindow(tk.Toplevel):
    def __init__(self, master, parent_gui):
        super().__init__(master)
        self.title("Plot Configuration")
        scale_factor = parent_gui.get_scale_factor()
        self.geometry(f"{int(700 * scale_factor)}x{int(500 * scale_factor)}")
        self.parent_gui = parent_gui

        self.raw_plot_configs = self._load_raw_plot_configs() # Load raw list
        self.plot_config_names = [cfg["name"] for cfg in self.raw_plot_configs]
        self.current_selection = tk.StringVar()
        self.entries = {}
        self.original_types = {} # To store original types for conversion

        # --- Layout ---
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Select Plot Config:").pack(side=tk.LEFT)
        self.config_selector = ttk.Combobox(top_frame, textvariable=self.current_selection, 
                                            values=self.plot_config_names)
        self.config_selector.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.config_selector.bind("<<ComboboxSelected>>", self.populate_entries)

        self.entries_frame = ttk.Frame(self, padding="10")
        self.entries_frame.pack(fill=tk.BOTH, expand=True)

        bottom_frame = ttk.Frame(self, padding="10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(bottom_frame, text="Update", command=self.update_plot_and_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Close", command=self.on_closing).pack(side=tk.RIGHT)
        ttk.Button(bottom_frame, text="New", command=self.new_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Delete", command=self.delete_config).pack(side=tk.LEFT, padx=5)

        # Select the first item if available
        if self.plot_config_names:
            self.current_selection.set(self.plot_config_names[0])
            self.populate_entries()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _load_raw_plot_configs(self):
        try:
            with open('plot_configs.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showerror("Error", "Could not load plot_configs.json. Please ensure it exists and is valid JSON.")
            return []

    def populate_entries(self, event=None):
        for widget in self.entries_frame.winfo_children():
            widget.destroy()
        
        self.entries.clear()
        self.original_types.clear()
        
        selection_name = self.current_selection.get()
        if not selection_name:
            return

        selected_config = next((cfg for cfg in self.raw_plot_configs if cfg["name"] == selection_name), None)
        if not selected_config:
            return

        for i, (key, value) in enumerate(selected_config.items()):
            ttk.Label(self.entries_frame, text=f"{key}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            entry_var = tk.StringVar(value=str(value))
            entry = ttk.Entry(self.entries_frame, textvariable=entry_var)
            entry.grid(row=i, column=1, sticky=(tk.W, tk.E), pady=2)
            self.entries[key] = entry_var
            self.original_types[key] = type(value)

        self.entries_frame.columnconfigure(1, weight=1)

    def new_config(self):
        new_name = "New_Config"
        i = 1
        while any(cfg["name"] == new_name for cfg in self.raw_plot_configs):
            new_name = f"New_Config_{i}"
            i += 1

        default_config = {
            "name": new_name,
            "yt_field": "Ex",
            "cscale": "Efield_unit",
            "xscale": "len_unit",
            "yscale": "len_unit",
            "plot_title": f"{new_name} at time {{time:.1f}} $T_L$",
            "cmap": "viridis",
            "vmin": None,
            "vmax": None,
            "clabel": new_name,
            "xlabel": "x [$\\mu m$]",
            "ylabel": "y [$\\mu m$]",
            "xlim": "None",
            "ylim": "None",
            "resolution_factor": 1
        }
        self.raw_plot_configs.append(default_config)
        self._update_config_selector()
        self.current_selection.set(new_name)
        self.populate_entries()
        self.update_and_save()
        messagebox.showinfo("New Config", f"Created new configuration: {new_name}")

    def delete_config(self):
        selection_name = self.current_selection.get()
        if not selection_name:
            messagebox.showwarning("Delete Config", "No configuration selected to delete.")
            return

        if messagebox.askyesno("Delete Config", f"Are you sure you want to delete '{selection_name}'?"):
            self.raw_plot_configs = [cfg for cfg in self.raw_plot_configs if cfg["name"] != selection_name]
            self._update_config_selector()
            if self.raw_plot_configs:
                self.current_selection.set(self.raw_plot_configs[0]["name"])
            else:
                self.current_selection.set("")
            self.populate_entries()
            self.update_and_save()
            messagebox.showinfo("Delete Config", f"Configuration '{selection_name}' deleted.")

    def _update_config_selector(self):
        self.plot_config_names = [cfg["name"] for cfg in self.raw_plot_configs]
        self.config_selector['values'] = self.plot_config_names

    def update_and_save(self):
        selection_name = self.current_selection.get()
        # Find the index of the selected config in the raw list
        config_index = -1
        for i, cfg in enumerate(self.raw_plot_configs):
            if cfg["name"] == selection_name:
                config_index = i
                break
        
        # If a config is selected and found, update its values
        if config_index != -1:
            # Update the raw config with new values from entries
            for key, var in self.entries.items():
                new_value_str = var.get()
                original_type = self.original_types.get(key)

                try:
                    if new_value_str.strip().lower() in ["none", ""]:
                        new_value = None
                    elif original_type == bool:
                        new_value = new_value_str.lower() in ['true', '1', 'yes']
                    elif original_type == int:
                        new_value = int(new_value_str)
                    elif original_type == float:
                        new_value = float(new_value_str)
                    elif original_type == list: # Handle lists like xlim, ylim
                        # Safely evaluate list-like strings (e.g., "[1, 2]")
                        new_value = json.loads(new_value_str)
                        if not isinstance(new_value, list):
                            raise ValueError("Expected a list.")

                    else: # Default to string
                        new_value = new_value_str
                except (ValueError, json.JSONDecodeError) as e:
                    messagebox.showwarning("Type Conversion Error", f"Could not convert '{new_value_str}' for key '{key}'. Error: {e}. Keeping as string.")
                    new_value = new_value_str # Keep as string if conversion fails
                
                self.raw_plot_configs[config_index][key] = new_value
        
        # Save the modified raw configs back to plot_configs.json
        try:
            with open('plot_configs.json', 'w') as f:
                json.dump(self.raw_plot_configs, f, indent=4)
            # messagebox.showinfo("Success", "Configuration updated and saved to plot_configs.json.")
            
            # Reload PLOT_CONFIGS in analysis_app to reflect changes
            load_plot_configs()
            # Also refresh the main GUI's plot type dropdown in case a config name was changed
            # Or if a config was added/deleted (though adding/deleting is not implemented yet)
            new_choices = self.parent_gui.load_plot_choices()
            self.parent_gui.plot_type_menu['values'] = new_choices # Update combobox values
            if new_choices and self.parent_gui.plot_type.get() not in new_choices:
                self.parent_gui.plot_type.set(new_choices[0])

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save plot_configs.json: {e}")

    def update_plot_and_save(self):
        self.update_and_save()
        if self.parent_gui.plot_window and self.parent_gui.plot_window.winfo_exists():
            if self.parent_gui.plot_window.analysis_params.get("static_plot"):
                self.parent_gui.run_analysis()
            else:
                current_file_num = self.parent_gui.plot_window.current_file.get()
                self.parent_gui.plot_window.update_plot(current_file_num)

    def on_closing(self):
        self.update_and_save()
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AnalysisGUI(root)
    root.mainloop()
