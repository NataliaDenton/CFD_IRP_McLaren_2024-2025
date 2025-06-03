#!/usr/bin/env python3

import sys
from pathlib import Path

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import suppl_fcts
import populator_fcts

CONFIG_PATH = Path(__file__).parent / "../../configs/Aero_SUV_rearWheels/config.yaml"

print('🔧 Starting bounding box generation. Loading configs...')
config = IO_fcts.load_config(CONFIG_PATH)

# --- Extract config values ---
bbox_out_path = config["filePath"]["boundingBoxGeneration_res"]
blockMesh_path = config["filePath"]["blockMesh"]
extract_angle = config["surfaceFeatureExtractDict"]["extractAngle"]
dict_output_path = config["filePath"]["surfaceFeatureExtractDict"]
geometry_config = config["filePath"]["geometries"]

print('✅ Config load success. Loading geometries...')

# --- Aggregate all STL points ---
all_points = []
stl_points = IO_fcts.load_geometry(geometry_config["file"])  # A new helper that loads one 
all_points.extend(stl_points)



print('✅ All geometries loaded. Computing bounding box...')

# --- Compute bounds and mesh vertices ---
bounds = suppl_fcts.compute_extended_bounds(all_points, config["scaling"])
vertices = suppl_fcts.format_vertices(bounds)
suppl_fcts.print_vertices_block(vertices)

print('💾 Saving vertices...')
IO_fcts.save_vertices(vertices, bbox_out_path)
print(f'✅ Vertices saved to: {bbox_out_path}')

print('📐 Estimating cell counts and generating blockMeshDict...')
cell_counts = suppl_fcts.estimate_cell_counts(vertices, base_cell_size=0.05)
blockMesh_content = populator_fcts.generate_blockMeshDict(vertices, cell_counts)

with open(blockMesh_path, "w") as f:
    f.write(blockMesh_content)
print(f"✅ Generated blockMeshDict at {blockMesh_path}")

print(f"🧩 Generating surfaceFeatureExtractDict...")

# Support feature extract for multiple geometries
feature_dict = populator_fcts.generate_surfaceFeatureExtractDict(geometry_config["file"], extract_angle)

with open(dict_output_path, "w") as f:
    f.write(feature_dict)
print(f"✅ Wrote surfaceFeatureExtractDict to {dict_output_path}")

print('✅ meshGeneration.py complete')

