#!/usr/bin/env python3

import sys
from pathlib import Path

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts

CONFIG_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/config_system.yaml"

geometry_config_FilePath = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/config.yaml"

print("🔧 Starting system file generation...")
config = IO_fcts.load_config(CONFIG_PATH)




# --- filePaths ---
controlDict_filePath = "system/controlDict"
fvSchemes_filePath = "system/fvSchemes"
fvSolution_filePath = "system/fvSolution"
snappyHexMeshDict_filePath = "system/snappyHexMeshDict"

# --- configs ---

controlDict_config = config["control"]
fvSchemes_config = config["fvSchemes"]
fvSolution_config = config["fvSolution"]
snappyHexMesh_config = config["snappyHexMeshDict"]


# --- CONTROL DICT ---
control_dict_text = populator_fcts.generate_controlDict(controlDict_config)
IO_fcts.write_text_file(control_dict_text, controlDict_filePath)
print(f"controlDict written to: {controlDict_filePath}")

# --- FV SCHEMES ---
fv_schemes_text = populator_fcts.generate_fvSchemes(fvSchemes_config)
IO_fcts.write_text_file(fv_schemes_text, fvSchemes_filePath)
print(f"fvSchemes written to: {fvSchemes_filePath}")

# --- FV SOLUTION ---
fv_solution_text = populator_fcts.generate_fvSolution(fvSolution_config)
IO_fcts.write_text_file(fv_solution_text, fvSolution_filePath)
print(f"fvSolution written to: {fvSolution_filePath}")


# --- SNAPPY HEX MESH ---
snappy_text = populator_fcts.generate_snappyHexMeshDict(snappyHexMesh_config)

IO_fcts.write_text_file(snappy_text, snappyHexMeshDict_filePath)
print(f"snappyHexMeshDict written to: {snappyHexMeshDict_filePath}")
















