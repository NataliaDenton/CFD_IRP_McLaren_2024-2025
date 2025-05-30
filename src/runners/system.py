#!/usr/bin/env python3

import sys
from pathlib import Path

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts

CONFIG_PATH = Path(__file__).parent / "../configs/Aero_SUV_rearWheels/config_system.yaml"

print("🔧 Starting system file generation...")
config = IO_fcts.load_config(CONFIG_PATH)


# --- CONTROL DICT ---
control_dict_text = populator_fcts.generate_controlDict(config["control"])
IO_fcts.write_text_file(control_dict_text, config["filePath"]["controlDict"])
print(f"controlDict written to: {config['filePath']['controlDict']}")

# --- FV SCHEMES ---
fv_schemes_text = populator_fcts.generate_fvSchemes()
IO_fcts.write_text_file(fv_schemes_text, config["filePath"]["fvSchemes"])
print(f"fvSchemes written to: {config['filePath']['fvSchemes']}")

# --- FV SOLUTION ---
fv_solution_text = populator_fcts.generate_fvSolution()
IO_fcts.write_text_file(fv_solution_text, config["filePath"]["fvSolution"])
print(f"fvSolution written to: {config['filePath']['fvSolution']}")


print("Merged geometry not found! Using original geometry configuration from YAML.")
snappy_text = populator_fcts.generate_snappyHexMeshDict(config["snappyHexMeshDict"])

IO_fcts.write_text_file(snappy_text, config["filePath"]["snappyHexMeshDict"])
print(f"snappyHexMeshDict written to: {config['filePath']['snappyHexMeshDict']}")
