#!/usr/bin/env python3

import sys
from pathlib import Path

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import suppl_fcts
import IO_fcts
CONFIG_PATH = Path(__file__).parent / "../../configs/Aero_SUV_mergedGeometry/config.yaml"

print("🔧 Starting mergedGeometry.slt file generation...")
config = IO_fcts.load_config(CONFIG_PATH)

geometry_config = config["filePath"]["geometries"]
mergedGeometry_config = config["filePath"]["mergedGeometry"]

outputPath = mergedGeometry_config['file']

suppl_fcts.merge_multiple_stl_files(geometry_config, outputPath)
