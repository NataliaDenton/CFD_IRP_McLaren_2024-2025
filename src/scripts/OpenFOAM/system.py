#!/usr/bin/env python3

import sys
from pathlib import Path

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts

user_CONFIG_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/userConfig.yaml"

advanced_configs_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/advancedConfig.yaml" 


print("🔧 Starting system file generation...")
configU = IO_fcts.load_config(user_CONFIG_PATH)
configA = IO_fcts.load_config(advanced_configs_PATH)



# --- filePaths ---
controlDict_filePath = "system/controlDict"
fvSchemes_filePath = "system/fvSchemes"
fvSolution_filePath = "system/fvSolution"
snappyHexMeshDict_filePath = "system/snappyHexMeshDict"
decomposeParDict_filePath = "system/decomposeParDict"
# --- userConfigs ---

controlDict_configU = configU["control"]
fvSchemes_configU = configU["fvSchemes"]

snappyHexMesh_configU = configU["snappyHexMeshDict"]
decomposeParDict_configU = configU["cores"]


# --- advancedConfigs ---

controlDict_configA = configA["control"]
fvSchemes_configA = configA["fvSchemes"]
fvSolution_configA = configA["fvSolution"]
snappyHexMesh_configA = configA["snappyHexMeshDict"]
decomposeParDict_configA = configA["decomposeParDict"]


# --- CONTROL DICT ---
control_dict_text = populator_fcts.generate_controlDict(controlDict_configU, controlDict_configA)
IO_fcts.write_text_file(control_dict_text, controlDict_filePath)
print(f"controlDict written to: {controlDict_filePath}")


# --- DECOMPOSE PAR DICT ---
decomposeParDict_text = populator_fcts.decomposeParDict_populator(decomposeParDict_configU, decomposeParDict_configA)
IO_fcts.write_text_file(decomposeParDict_text, decomposeParDict_filePath)
print(f"decomposeParDict written to: {decomposeParDict_filePath}")

# --- FV SCHEMES ---
fv_schemes_text = populator_fcts.generate_fvSchemes(fvSchemes_configU, fvSchemes_configA)
IO_fcts.write_text_file(fv_schemes_text, fvSchemes_filePath)
print(f"fvSchemes written to: {fvSchemes_filePath}")

# --- FV SOLUTION ---
fv_solution_text = populator_fcts.generate_fvSolution(fvSolution_configA)
IO_fcts.write_text_file(fv_solution_text, fvSolution_filePath)
print(f"fvSolution written to: {fvSolution_filePath}")


# --- SNAPPY HEX MESH ---
snappy_text = populator_fcts.generate_snappyHexMeshDict(snappyHexMesh_configU, snappyHexMesh_configA)

IO_fcts.write_text_file(snappy_text, snappyHexMeshDict_filePath)
print(f"snappyHexMeshDict written to: {snappyHexMeshDict_filePath}")
















