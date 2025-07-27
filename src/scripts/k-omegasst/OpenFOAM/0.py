#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

# === Load helper functions ===
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts
import suppl_fcts

# === Parse CLI arguments ===
p = argparse.ArgumentParser()
p.add_argument("--configDir", required=True)
p.add_argument("--caseDir", required=False)
args = p.parse_args()

configDir = args.configDir
user_CONFIG_PATH = Path(configDir) / "userConfig.yaml"
advanced_configs_PATH = Path(configDir) / "advancedConfig.yaml"

# === Load config files ===
ConfigU = IO_fcts.load_config(user_CONFIG_PATH)
ConfigA = IO_fcts.load_config(advanced_configs_PATH)

# === Determine case directory ===
if args.caseDir:
    CASE_DIR = Path(args.caseDir).resolve()
elif "filePath" in ConfigU and "caseDir" in ConfigU["filePath"]:
    CASE_DIR = Path(ConfigU["filePath"]["caseDir"]).resolve()
else:
    print("⚠️  No caseDir provided. Falling back to current working directory.")
    CASE_DIR = Path.cwd()

# === Run field writer ===
print("📦 Starting OpenFOAM '0/' population using config_0.yaml")
populator_fcts.write_all_fields(ConfigU, ConfigA, CASE_DIR)
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
