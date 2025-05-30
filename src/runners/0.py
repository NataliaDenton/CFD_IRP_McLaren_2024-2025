#!/usr/bin/env python3

import sys
from pathlib import Path

# Extend path to access functions
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../functions"
sys.path.append(str(FUNCTIONS_PATH))

import populator_fcts

# --- Hardcoded path to config_0.yaml ---
CONFIG_0_PATH = Path(__file__).parent / "../configs/Aero_SUV_frontWheels/config_0.yaml"
CASE_DIR = Path(__file__).parent / "../Openfoam/AeroSUV_frontWheels_case"

print("📦 Starting OpenFOAM '0/' population using config_0.yaml")
populator_fcts.write_all_fields(str(CONFIG_0_PATH), str(CASE_DIR))
print("✅ All fields in '0/' generated successfully.")

