#!/usr/bin/env python3

import sys
from pathlib import Path

# Extend path to access functions
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import populator_fcts
import IO_fcts

user_CONFIG_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/userConfig.yaml"

advanced_configs_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/advancedConfig.yaml" 

ConfigU = IO_fcts.load_config(user_CONFIG_PATH)
ConfigA = IO_fcts.load_config(advanced_configs_PATH)


CASE_DIR = ConfigU["filePath"]["caseDir"]

print("📦 Starting OpenFOAM '0/' population using config_0.yaml")
populator_fcts.write_all_fields(ConfigU,ConfigA, CASE_DIR)
print("✅ All fields in '0/' generated successfully.")

