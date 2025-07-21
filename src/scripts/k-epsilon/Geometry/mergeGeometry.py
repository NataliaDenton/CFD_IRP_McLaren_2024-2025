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


print("🔧 Starting system file generation...")
configU = IO_fcts.load_config(user_CONFIG_PATH)
configA = IO_fcts.load_config(advanced_configs_PATH)

geometry_config = configU["filePath"]["geometries"]
mergedGeometry_config = configA["advancedGeometrySettings"]["filePath"]["mergedGeometry"]

outputPath = mergedGeometry_config['file']

suppl_fcts.merge_multiple_stl_files(geometry_config, outputPath)
