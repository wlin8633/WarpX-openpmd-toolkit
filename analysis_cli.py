import os
import argparse
from config_manager import PLOT_CONFIGS
from data_loaders import _load_raw_data
from plotters import process_raw_data_for_plotting, plot_2d_image

def _process_one_field_worker(folderPath, headerName, file_num, field_name, config):
    raw_data_tuple = _load_raw_data(folderPath, headerName, file_num, field_name)
    if raw_data_tuple:
        raw_cdata, raw_xydata, raw_time, _ = raw_data_tuple
        cdata_plotting, xy_data_plotting, plot_params = process_raw_data_for_plotting(
            raw_cdata, raw_xydata, raw_time, config
        )
        save_dir = os.path.join(folderPath, "plotting", f"2d_{config['name']}")
        save_path = os.path.join(save_dir, f"{config['name']}_{file_num:04d}.png")
        os.makedirs(save_dir, exist_ok=True)
        plot_2d_image(cdata_plotting, xy_data_plotting, plot_params, save_path=save_path)

def process_all_reduced_files(folderPath):
    from plotters import plot_reduced_file
    target_dir = os.path.join(folderPath, 'diags', 'reducedfiles')
    if not os.path.exists(target_dir):
        target_dir = os.path.join(folderPath, 'reducedfiles')
        
    if not os.path.exists(target_dir):
        return
        
    for filename in os.listdir(target_dir):
        if filename.endswith('.txt'):
            if filename in PLOT_CONFIGS:
                config = PLOT_CONFIGS[filename]
                file_path = os.path.join(target_dir, filename)
                save_dir = os.path.join(folderPath, "plotting", "reducedfiles")
                save_path = os.path.join(save_dir, f"{filename[:-4]}.png")
                os.makedirs(save_dir, exist_ok=True)
                print(f"Processing reduced file: {filename}")
                plot_reduced_file(file_path, config, save_path=save_path)


def run_from_cli():
    """
    Handles execution when the script is run from the command line.
    """
    parser = argparse.ArgumentParser(description="WarpX Simulation Analysis Tool")

    parser.add_argument("--folder", type=str, default=".",
                        help="Path to the simulation output directory (containing diags/). Defaults to current directory.")
    parser.add_argument("--headerName", type=str, default="plt",
                        help="Header name for diagnostic files (e.g., 'diagxy', 'plt'). Defaults to 'plt'.")
    
    # plotType and dataset are now optional.
    parser.add_argument("--plotType", type=str, choices=list(PLOT_CONFIGS.keys()), 
                        help="The type of plot to generate, as defined in plot_configs.json. Choices: " + ", ".join(PLOT_CONFIGS.keys()))
    parser.add_argument("--dataset", type=str,
                        help="The specific dataset key (e.g., 'Ex', 'rho') to plot. Overrides 'yt_field' in plotType config.")

    group = parser.add_mutually_exclusive_group() # Make file/batch optional initially
    group.add_argument("--file", type=int, help="A single file number to process.")
    group.add_argument("--batch", type=int, nargs=2, metavar=('START', 'END'),
                       help="A range of file numbers to process (e.g., --batch 1 50).")

    parser.add_argument("-np", type=int, default=1, help="Number of parallel processes to use. Default is 1.")

    args = parser.parse_args()

    # If not showing keys, then plotType or dataset must be specified for plotting
    if not args.plotType and not args.dataset:
        parser.error("You must specify either --plotType or --dataset to generate plots.")
    
    # If a plot is to be generated, either --file or --batch must be present
    if not (args.file or args.batch):
        parser.error("You must specify either --file or --batch to generate plots.")

    folderPath = args.folder
    headerName = args.headerName

    if args.file:
        start_file, end_file = args.file, args.file
    else:
        start_file, end_file = args.batch[0], args.batch[1]

    fields_to_process = []
    if args.dataset == "all":
        # Dynamically discover fields using the first file
        raw_data_tuple = _load_raw_data(folderPath, headerName, start_file, yt_field=None)
        if not raw_data_tuple or not raw_data_tuple[3]:
            parser.error(f"Could not load data or dataset for file {start_file} to discover fields.")
            
        dataset = raw_data_tuple[3]
        field_choices = sorted(list(set([f"{kind}_{obj}" for kind, obj in dataset.field_list])))
        
        for field in field_choices:
            if field in PLOT_CONFIGS:
                fields_to_process.append((field, PLOT_CONFIGS[field]))
                
        if not fields_to_process:
            print(f"No matching plot configs found for dataset names in file {start_file}.")
            return
    else:
        # Single dataset/plotType mode
        if args.plotType:
            config = PLOT_CONFIGS.get(args.plotType)
            if not config:
                parser.error(f"Plot type '{args.plotType}' not found in plot_configs.json.")
        else:
            config = {
                "name": args.dataset if args.dataset else "custom_plot",
                "yt_field": args.dataset,
                "cscale": "1.0", "cscale_val": 1.0,
                "xscale": "1.0", "xscale_val": 1.0,
                "yscale": "1.0", "yscale_val": 1.0,
                "plot_title": f"{args.dataset} at time {{time:.1f}} TL",
                "cmap": "viridis", "vmin": None, "vmax": None,
                "clabel": args.dataset, "xlabel": "x [$\\mu m$]", "ylabel": "y [$\\mu m$]",
                "resolution_factor": 1, "xlim": None, "ylim": None
            }
        
        # Override yt_field if --dataset is provided (and not 'all')
        if args.dataset:
            config["yt_field"] = args.dataset
            
        fields_to_process = [(config["yt_field"], config)]

    tasks = []
    for file_num in range(start_file, end_file + 1):
        for field_name, base_config in fields_to_process:
            config = base_config.copy()
            config["yt_field"] = field_name
            tasks.append((folderPath, headerName, file_num, field_name, config))

    import multiprocessing
    if args.np > 1:
        print(f"Starting parallel processing with {args.np} workers for {len(tasks)} tasks.")
        with multiprocessing.Pool(processes=args.np, maxtasksperchild=1) as pool:
            pool.starmap(_process_one_field_worker, tasks)
    else:
        print(f"Starting sequential processing for {len(tasks)} tasks.")
        for task in tasks:
            p = multiprocessing.Process(
                target=_process_one_field_worker,
                args=task
            )
            p.start()
            p.join()
            
            if p.exitcode != 0:
                print(f"Warning: Worker for file {task[2]}, field {task[3]} exited with code {p.exitcode}")

    if args.dataset == "all":
        process_all_reduced_files(folderPath)

    print("Finish!")

if __name__ == "__main__":
    run_from_cli()
