#!/usr/bin/env python3

import sys
from pathlib import Path

# Extend path to access functions
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import populator_fcts
import IO_fcts

# --- Hardcoded path to config_0.yaml ---
user_CONFIG_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/userConfig.yaml"

advanced_configs_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/advancedConfig.yaml" 
print('🔧 Starting bounding box generation. Loading configs...')
ConfigU = IO_fcts.load_config(user_CONFIG_PATH)
ConfigA = IO_fcts.load_config(advanced_configs_PATH)


CASE_DIR = ConfigU["filePath"]["caseDir"]

print('starting population of transport properties')
populator_fcts.populate_transportProperties(ConfigU,ConfigA, CASE_DIR)
print('starting population of turbulanceBroperties')
populator_fcts.populate_turbulenceProperties(ConfigU,ConfigA, CASE_DIR)
