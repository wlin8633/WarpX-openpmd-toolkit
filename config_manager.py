import scipy.constants as sc
import json
import numpy as np

# -----> Physical Constants and Units
lambda_L    = 0.8e-6 # m
freq_L      = sc.c / lambda_L # 1/s
T_L         = 1 / freq_L # s
omega_L     = 2 * sc.pi * freq_L # rad./s
nc          = sc.epsilon_0 * sc.m_e * omega_L ** 2 / sc.e ** 2
E0          = (sc.m_e * omega_L * sc.c) / sc.e

len_unit    = 1e-6 
time_unit   = T_L 
Efield_unit = E0
Bfield_unit = E0 / sc.c
jfield_unit = sc.e * nc * sc.c
rho_unit    = sc.e * nc
energy_unit = 1e6 * sc.e # MeV
moment_unit = sc.m_p * sc.c 
angle_unit  = 1e-3 # mrad

# Map string names to their actual unit values
UNIT_MAP = {
    "len_unit": len_unit,
    "time_unit": time_unit,
    "Efield_unit": Efield_unit,
    "Bfield_unit": Bfield_unit,
    "jfield_unit": jfield_unit,
    "rho_unit": rho_unit,
    "energy_unit": energy_unit,
    "moment_unit": moment_unit,
    "angle_unit": angle_unit,
}

# Module-level variable for plot configurations
PLOT_CONFIGS = {}

def load_plot_configs():
    """
    Loads plot configurations from 'plot_configs.json' and resolves unit names by
    evaluating them as expressions. Updates the global PLOT_CONFIGS dictionary.
    """
    global PLOT_CONFIGS
    try:
        with open('plot_configs.json', 'r') as f:
            json_configs = json.load(f)
        
        # Prepare a safe environment for eval()
        safe_globals = {
            'sc': sc,
            'np': np,
        }
        safe_globals.update(UNIT_MAP) # Add all predefined units

        PLOT_CONFIGS.clear() # Clear existing configs before reloading
        for cfg in json_configs:
            processed_cfg = cfg.copy() # Create a copy to modify
            
            # Evaluate the scaling expressions if they exist
            for key in ["cscale", "xscale", "yscale"]:
                if key in processed_cfg:
                    expression = str(processed_cfg[key]).strip()
                    is_log = False
                    
                    if expression.lower().startswith("log:") or expression.lower().startswith("log|"):
                        is_log = True
                        expression = expression[4:].strip()
                        
                    try:
                        # Evaluate the expression within the safe context
                        processed_cfg[key + "_val"] = eval(expression, safe_globals)
                    except Exception as e:
                        print(f"Warning: Could not evaluate expression '{expression}' for config '{processed_cfg['name']}' ({key}). Defaulting to 1.0. Error: {e}")
                        processed_cfg[key + "_val"] = 1.0
                        
                    processed_cfg[key + "_is_log"] = is_log
            
            PLOT_CONFIGS[processed_cfg["name"]] = processed_cfg

    except FileNotFoundError:
        print("Error: plot_configs.json not found. Please create it with your plot configurations.")
        PLOT_CONFIGS.clear()
    except json.JSONDecodeError:
        print("Error: Could not decode plot_configs.json. Check for syntax errors in the JSON file.")
        PLOT_CONFIGS.clear()

# Initial load of plot configurations
load_plot_configs()
