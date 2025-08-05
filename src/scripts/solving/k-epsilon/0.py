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
ConfigU = IO_fcts.load_config(user_CONFIG_PATH)
ConfigA = IO_fcts.load_config(advanced_configs_PATH)
# === Determine case directory ===
from pathlib import Path

CASE_DIR = (Path(__file__).resolve().parent / "../../../" / ConfigU["filePath"]["caseDir"]).resolve()
print("Resolved CASE_DIR:", CASE_DIR)

print("Current working directory:", Path.cwd())
print("looking for directory:", CASE_DIR)


# === Run field writer ===
print("🔍 Keys in ConfigU:", list(ConfigU.keys()))
print("📦 Starting OpenFOAM '0/' population using config_0.yaml")
populator_module.write_all_fields(ConfigU, ConfigA, CASE_DIR)
print("✅ All fields in '0/' generated successfully.")

# === Print summaries ===
from os import listdir
from os.path import isfile, join

zero_path = CASE_DIR / "0"
field_files = [f for f in listdir(zero_path) if isfile(join(zero_path, f))]

print("🧪 Field files created:")
for f in field_files:
    with open(zero_path / f, 'r') as fp:
        header = ''.join([next(fp) for _ in range(4)])
    print(f" - {f} header:\n{header}")
