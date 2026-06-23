import os
import numpy as np

_ts_cache = {}
_ts_usage_count = {}

def get_cached_ts(series_path):
    global _ts_cache, _ts_usage_count
    
    # Increment usage counter
    _ts_usage_count[series_path] = _ts_usage_count.get(series_path, 0) + 1
    
    # Recreate the ts object every 15 uses to prevent internal C++/HDF5 memory leaks from accumulating
    if series_path not in _ts_cache or _ts_usage_count[series_path] > 15:
        if series_path in _ts_cache:
            del _ts_cache[series_path]
            import gc
            gc.collect()
            
        from openpmd_viewer import OpenPMDTimeSeries
        _ts_cache[series_path] = OpenPMDTimeSeries(series_path)
        _ts_usage_count[series_path] = 1
        
    return _ts_cache[series_path]

def find_diag_file(folderPath, fileName, fileNumber, dataList, use_mean=None, mean_axis=2, verbose=False):
    '''
    Read a specific diag file of WarpX using openpmd_viewer.
    '''
    if fileNumber == 0: raise ValueError('fileNumber starts from 1')

    diags_dir = os.path.join(folderPath, 'diags')
    if not os.path.isdir(diags_dir):
        raise FileNotFoundError(f"Diagnostics directory not found at: {diags_dir}")

    # Check if fileName represents a directory (like fdiag)
    series_path = os.path.join(diags_dir, fileName)
    if not os.path.exists(series_path):
        series_path = diags_dir
        
    ts = get_cached_ts(series_path)
    
    if len(ts.iterations) == 0:
        print(f"No iterations found in openPMD series at '{series_path}'")
        return None, [], {}, None, None

    print(f"Working at file: {folderPath}\nTotal number of files: {len(ts.iterations)} \nWorking on {fileNumber}th file...")
    
    try:
        it = ts.iterations[fileNumber - 1]
    except IndexError:
        print(f"Out of range! There are only {len(ts.iterations)} data files.")
        raise
        
    avail_fields = ts.avail_fields
    if verbose:
        print(f"List of available openPMD fields: {avail_fields}")

    class MockDataset:
        def __init__(self, fields):
            self.field_list = []
            for f in fields:
                if f in ['E', 'B', 'e', 'b']:
                    self.field_list.extend([('openpmd', f'{f}x'), ('openpmd', f'{f}y'), ('openpmd', f'{f}z')])
                elif f in ['J', 'j']:
                    self.field_list.extend([('openpmd', f'{f}x'), ('openpmd', f'{f}y'), ('openpmd', f'{f}z')])
                else:
                    self.field_list.append(('openpmd', f))
            
    dataset = MockDataset(avail_fields)

    if dataList == [None]:
        print("No dataList specified. Returning the dataset.")
        return dataset, None, None, None, None
        
    readout_data = {}
    readout_names = []
    xydata = None
    time = ts.t[fileNumber - 1]

    for dataName in dataList:
        clean_name = dataName
        if clean_name.startswith('openpmd_'):
            clean_name = clean_name[len('openpmd_'):]

        base_field = clean_name
        coord = None
        
        if clean_name in ['Ex', 'Ey', 'Ez', 'Bx', 'By', 'Bz', 'ex', 'ey', 'ez', 'bx', 'by', 'bz']:
            base_field = clean_name[0]
            coord = clean_name[1].lower()
            field_name_in_mock = f"openpmd_{clean_name}"
        elif clean_name in ['Jx', 'Jy', 'Jz', 'jx', 'jy', 'jz']:
            base_field = clean_name[0]
            coord = clean_name[1].lower()
            field_name_in_mock = f"openpmd_{clean_name}"
        else:
            base_field = clean_name
            coord = None
            field_name_in_mock = f"openpmd_{clean_name}"

        # Handle 'rho' backwards compatibility 
        # WarpX openpmd sometimes writes 'rho' directly.
        if base_field not in avail_fields:
            if base_field == 'rho_electron' and 'rho' in avail_fields:
                base_field = 'rho'
            elif base_field == 'rho_hydrogen' and 'rho' in avail_fields:
                base_field = 'rho'

        if base_field in avail_fields:
            readout_names.append(field_name_in_mock)
            
            kwargs = {'field': base_field, 'iteration': it}
            if coord is not None:
                kwargs['coord'] = coord
            
            if clean_name == 'rho_electron' and base_field == 'rho':
                kwargs['species'] = 'electron'
            elif clean_name == 'rho_hydrogen' and base_field == 'rho':
                kwargs['species'] = 'hydrogen'
                
            try:
                data, info = ts.get_field(**kwargs)
            except Exception as e:
                print(f"Warning: Failed to fetch {dataName} ({kwargs}): {e}")
                continue
                
            if len(data.shape) == 3 and use_mean:
                data = data.mean(axis=mean_axis)
                
            # openpmd_viewer 2D data is returned as (z, x) or (y, x). 
            # We transpose it to match yt's (x, y) orientation that the existing plot functions expect.
            data = data.T 
            readout_data[field_name_in_mock] = data

            if xydata is None:
                axes_dict = {}
                for ax_name in ['x', 'y', 'z', 'r']:
                    if hasattr(info, ax_name):
                        ax_arr = getattr(info, ax_name)
                        if ax_arr is not None and hasattr(ax_arr, '__len__') and len(ax_arr) > 0:
                            d_ax = ax_arr[1] - ax_arr[0] if len(ax_arr) > 1 else 0
                            axes_dict[ax_name] = [ax_arr[0] - d_ax/2, ax_arr[-1] + d_ax/2]
                
                if 'x' in axes_dict and 'z' in axes_dict:
                    xydata = np.array([axes_dict['x'], axes_dict['z']])
                elif 'x' in axes_dict and 'y' in axes_dict:
                    xydata = np.array([axes_dict['x'], axes_dict['y']])
                elif 'r' in axes_dict and 'z' in axes_dict:
                    xydata = np.array([axes_dict['r'], axes_dict['z']])
                else:
                    bounds = list(axes_dict.values())
                    if len(bounds) == 2:
                        xydata = np.array(bounds)
                    elif len(bounds) >= 3:
                        keep = [i for i in range(min(3, len(bounds))) if i != mean_axis]
                        if len(keep) >= 2:
                            xydata = np.array([bounds[keep[0]], bounds[keep[1]]])
                        else:
                            xydata = np.array([bounds[0], bounds[1]])
                    else:
                        xydata = np.array([[0, 1], [0, 1]]) # Safe fallback

    return dataset, readout_names, readout_data, xydata, time

def _load_raw_data(folderPath, headerName, file_num, yt_field=None):
    """
    Loads raw data for a single file.
    Returns (raw_cdata, raw_xydata, raw_time, dataset) or None if data not found.
    """
    dataset, readout_names, data, xy_data, time = find_diag_file(
        folderPath,
        fileName=headerName,
        fileNumber=file_num,
        dataList=[yt_field], # dataList expects a list of dataNames
        use_mean=True,
        mean_axis=2,  # Assuming 3D data sliced along z-axis
        verbose=False
    )

    if not yt_field:
        return None, None, None, dataset

    if not data:
        print(f"No data found for file {file_num}. Skipping.")

    cdata = None
    for name, array in data.items(): # type: ignore
        if yt_field in name: # This check allows matching "Ex" to "openpmd_Ex"
            cdata = array
            break
    
    if cdata is None:
        print(f"Could not find field matching '{yt_field}' in file {file_num}. Available: {list(data.keys())}") # type: ignore
        return None

    return cdata, xy_data, time, dataset

def load_time_series_field(folderPath, diagName, field_name, coord=None):
    """
    Loads a field (e.g., 'E', 'x') over ALL iterations from an OpenPMD series.
    This is ideal for 1D line probes to generate a (time, space) 2D array.
    """
    series_path = os.path.join(folderPath, 'diags', diagName)
    if not os.path.exists(series_path):
        print(f"Error: Path {series_path} does not exist.")
        return None, None, None, None

    ts = get_cached_ts(series_path)
    
    if len(ts.iterations) == 0:
        return None, None, None, None

    # Read the first iteration to get spatial info and shape
    try:
        first_it = ts.iterations[0]
        if coord:
            data0, info0 = ts.get_field(field=field_name, coord=coord, iteration=first_it)
        else:
            data0, info0 = ts.get_field(field=field_name, iteration=first_it)
    except Exception as e:
        print(f"Error loading {field_name} {coord}: {e}")
        return None, None, None, None
    
    data0 = np.squeeze(data0)
    
    # Identify the primary spatial axis for 1D data
    spatial_axis = None
    spatial_extent = None
    max_len = 0
    
    for ax_name in ['x', 'y', 'z', 'r']:
        if hasattr(info0, ax_name):
            ax_arr = getattr(info0, ax_name)
            if ax_arr is not None and hasattr(ax_arr, '__len__'):
                l = len(ax_arr)
                if l > max_len:
                    max_len = l
                    spatial_axis = ax_arr
                    d_ax = ax_arr[1] - ax_arr[0] if l > 1 else 0.0
                    spatial_extent = [ax_arr[0] - d_ax/2, ax_arr[-1] + d_ax/2]
                
    if spatial_axis is None:
        spatial_axis = np.array([0.0]) # point probe
        spatial_extent = [0.0, 0.0]

    time_array = np.array(ts.t)
    
    # Allocate full array (Time, Space)
    all_data = np.zeros((len(time_array), len(spatial_axis)))
    
    for i, it in enumerate(ts.iterations):
        if coord:
            d, _ = ts.get_field(field=field_name, coord=coord, iteration=it)
        else:
            d, _ = ts.get_field(field=field_name, iteration=it)
            
        d = np.squeeze(d)
        # If after squeeze it's still > 1D (like (2000, 2)), we average over the shortest axes
        while len(d.shape) > 1:
            min_axis = np.argmin(d.shape)
            d = np.mean(d, axis=min_axis)
            
        all_data[i, :] = d
        
    return all_data, time_array, spatial_axis, spatial_extent


def load_fluid_element_series(folderPath, diagName, species_name="electrons"):
    """
    Loads particle data over ALL iterations for a localized ParticleDiagnostic.
    Averages the momentum (ux, uy, uz) weighted by 'w' to represent the fluid element.
    Returns (time_array, avg_ux, avg_uy, avg_uz)
    """
    series_path = os.path.join(folderPath, 'diags', diagName)
    if not os.path.exists(series_path):
        print(f"Error: Path {series_path} does not exist.")
        return None, None, None, None
        
    ts = get_cached_ts(series_path)
    if len(ts.iterations) == 0:
        return None, None, None, None

    time_array = np.array(ts.t)
    
    avg_ux = np.zeros(len(time_array))
    avg_uy = np.zeros(len(time_array))
    avg_uz = np.zeros(len(time_array))
    
    for i, it in enumerate(ts.iterations):
        try:
            # Load particle momenta and weights
            ux, uy, uz, w = ts.get_particle(species=species_name, var_list=["ux", "uy", "uz", "w"], iteration=it)
            if len(w) > 0:
                avg_ux[i] = np.average(ux, weights=w)
                avg_uy[i] = np.average(uy, weights=w)
                avg_uz[i] = np.average(uz, weights=w)
            else:
                avg_ux[i] = 0.0
                avg_uy[i] = 0.0
                avg_uz[i] = 0.0
        except Exception as e:
            print(f"Warning: Failed to load particle data at iteration {it}: {e}")
            
    return time_array, avg_ux, avg_uy, avg_uz
