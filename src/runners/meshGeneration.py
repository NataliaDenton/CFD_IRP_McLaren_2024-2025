#!/usr/bin/env python3
"""
Generate OpenFOAM bounding box from STL using a hardcoded config.
"""

import sys
from pathlib import Path

# Add '../../functions/' to sys.path
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import suppl_fcts
import populator_fcts

# --- Hardcoded YAML path ---
CONFIG_PATH = Path(__file__).parent / "../configs/config.yaml"


print('Starting bounding box generation. Loading configs...')

config = IO_fcts.load_config(CONFIG_PATH)
# Get output paths from config
bbox_out_path = config["filePath"]["boundingBoxGeneration_res"]
blockMesh_path = config["filePath"]["blockMesh"]
cell_counts = tuple(config.get("cell_counts", (20, 20, 20)))
geometry_path = config["filePath"]["geometry"]
extract_angle = config["surfaceFeatureExtractDict"]["extractAngle"]
dict_output_path = config["filePath"]["surfaceFeatureExtractDict"]



print('Config load succsess. Loading Geometry...')

points = IO_fcts.load_geometry(config["filePath"]["geometry"])

print('Geometry Load success, computing bounds...')

bounds = suppl_fcts.compute_extended_bounds(points, config["scaling"])

print('bounds computed successfully. Formatting verticies...')

vertices = suppl_fcts.format_vertices(bounds)
suppl_fcts.print_vertices_block(vertices)

print('verticies formatted successfully. Saving...')

IO_fcts.save_vertices(vertices, bbox_out_path)

print(f'verticies saved to: {bbox_out_path}')
print(f'starting population of blockMeshDict...')
cell_counts = suppl_fcts.estimate_cell_counts(vertices, base_cell_size=0.05)

blockMesh_content = populator_fcts.generate_blockMeshDict(vertices, cell_counts)
with open(blockMesh_path, "w") as f:
    f.write(blockMesh_content)

print(f"Generated blockMeshDict at {blockMesh_path}")

print(f"generating surfaceFeatureExctractDict")
# Generate dict content
sfe_dict = generate_surfaceFeatureExtractDict(geometry_path, extract_angle)

# Write to file
with open(dict_output_path, "w") as f:
    f.write(sfe_dict)



print('meshGeneration.py complete')



