#!/usr/bin/env python3

import sys
from pathlib import Path

# Extend path to access functions
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../functions"
sys.path.append(str(FUNCTIONS_PATH))

import populator_fcts

# --- Hardcoded path to config_0.yaml ---
CONFIG_constant_PATH = Path(__file__).parent / "../configs/Aero_SUV_frontWheels/config_constant.yaml"
CASE_DIR = Path(__file__).parent / "../Openfoam/AeroSUV_frontWheels_case"
print('starting population of transport properties')
populator_fcts.populate_transportProperties(CONFIG_constant_PATH, CASE_DIR)
print('starting population of turbulanceBroperties')
populator_fcts.populate_turbulenceProperties(CONFIG_constant_PATH, CASE_DIR)
