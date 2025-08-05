#!/usr/bin/env python3
import sys, argparse, importlib
from pathlib import Path

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../../functions"
sys.path.append(str(FUNCTIONS_PATH))

p = argparse.ArgumentParser()
p.add_argument("--configDir", required=True)
p.add_argument("--modelType", required=True)
args = p.parse_args()

configDir = args.configDir
modelType = args.modelType

populatorFUNCTIONS_PATH = FUNCTIONS_PATH / modelType
sys.path.append(str(populatorFUNCTIONS_PATH))

import IO_fcts, suppl_fcts
populator_module = importlib.import_module(f"populator_{modelType}")

print(f"✅ Loaded populator for model: {modelType}")

user_CONFIG_PATH = Path(__file__).parent / configDir / "userConfig.yaml"
advanced_configs_PATH = Path(__file__).parent / configDir / "advancedConfig.yaml"

print('🔧 Starting bounding box generation. Loading configs...')
configU = IO_fcts.load_config(user_CONFIG_PATH)
configA = IO_fcts.load_config(advanced_configs_PATH)
# === ✅ ADDED: Optional skip for STL/mesh-specific bounding box logic ===
# Explanation:
# Fluent-mesh pipelines may not define filePath/caseDir or geometry structure
# We only use filePath["caseDir"] if it exists — this makes the script robust to both types of cases

if "filePath" not in configU:
    print("⚠️  Skipping mesh-based dictionary population (bounding box, geometry, etc.)")
    # Fallback to default CASE_DIR if not provided — does not break anything
    CASE_DIR = str(Path(__file__).resolve().parent.parent / "Openfoam")
else:
    CASE_DIR = configU["filePath"]["caseDir"]


print("Current working directory:", Path.cwd())


# === Proceed with standard population ===
print('📦 Starting population of constant/transportProperties')
populator_module.populate_transportProperties(configU, configA, CASE_DIR)

print('📦 Starting population of constant/turbulenceProperties')
populator_module.populate_turbulenceProperties(configU, configA, CASE_DIR)

