#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

# === Add custom functions path ===
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts
import suppl_fcts

# === Parse command-line arguments ===
p = argparse.ArgumentParser()
p.add_argument("--configDir", required=True)
args = p.parse_args()

configDir = args.configDir

# === Define config paths ===
user_CONFIG_PATH = Path(configDir) / "userConfig.yaml"
advanced_configs_PATH = Path(configDir) / "advancedConfig.yaml"

# === Load config files ===
print('🔧 Loading configs...')
ConfigU = IO_fcts.load_config(user_CONFIG_PATH)
ConfigA = IO_fcts.load_config(advanced_configs_PATH)

# === ✅ ADDED: Optional skip for STL/mesh-specific bounding box logic ===
# Explanation:
# Fluent-mesh pipelines may not define filePath/caseDir or geometry structure
# We only use filePath["caseDir"] if it exists — this makes the script robust to both types of cases

if "filePath" not in ConfigU:
    print("⚠️  Skipping mesh-based dictionary population (bounding box, geometry, etc.)")
    # Fallback to default CASE_DIR if not provided — does not break anything
    CASE_DIR = str(Path(__file__).resolve().parent.parent / "Openfoam")
else:
    CASE_DIR = ConfigU["filePath"]["caseDir"]

# === ALWAYS generate wallDist dictionary ===
#print('📦 Starting population of constant/stream/wallDist')
#populator_fcts.populate_wallDist(ConfigU, ConfigA, CASE_DIR)

# === Proceed with standard population ===
print('📦 Starting population of constant/transportProperties')
populator_fcts.populate_transportProperties(ConfigU, ConfigA, CASE_DIR)

print('📦 Starting population of constant/turbulenceProperties')
populator_fcts.populate_turbulenceProperties(ConfigU, ConfigA, CASE_DIR)

