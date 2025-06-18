#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts
import suppl_fcts


p = argparse.ArgumentParser()
p.add_argument("--configDir", required = True)
args = p.parse_args()

configDir = args.configDir


user_CONFIG_PATH = Path(__file__).parent / configDir/"userConfig.yaml"

advanced_configs_PATH = Path(__file__).parent / configDir/"advancedConfig.yaml" 


ConfigU = IO_fcts.load_config(user_CONFIG_PATH)
ConfigA = IO_fcts.load_config(advanced_configs_PATH)


CASE_DIR = ConfigU["filePath"]["caseDir"]

print("📦 Starting OpenFOAM '0/' population using config_0.yaml")
populator_fcts.write_all_fields(ConfigU,ConfigA, CASE_DIR)
print("✅ All fields in '0/' generated successfully.")

