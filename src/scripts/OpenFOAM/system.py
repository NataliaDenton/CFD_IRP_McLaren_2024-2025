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


# Load configs
print("🔧 Starting system and mesh file generation...")
configU = IO_fcts.load_config(user_CONFIG_PATH)
configA = IO_fcts.load_config(advanced_configs_PATH)

# File paths
system_dir = Path("system")
paths = {
    'controlDict': system_dir / 'controlDict',
    'fvSchemes':  system_dir / 'fvSchemes',
    'fvSolution': system_dir / 'fvSolution',
    'snappyHexMeshDict': system_dir / 'snappyHexMeshDict',
    'meshDict':  system_dir / 'meshDict',
    'decomposeParDict': system_dir / 'decomposeParDict'
}

# --- Populate control and decomposition files ---
IO_fcts.write_text_file(
    populator_fcts.generate_controlDict(configU['control'], configA['control']),
    paths['controlDict']
)
print(f"controlDict written to: {paths['controlDict']}")

IO_fcts.write_text_file(
    populator_fcts.decomposeParDict_populator(configU['cores'], configA['decomposeParDict']),
    paths['decomposeParDict']
)
print(f"decomposeParDict written to: {paths['decomposeParDict']}")

IO_fcts.write_text_file(
    populator_fcts.generate_fvSchemes(configU['fvSchemes'], configA['fvSchemes']),
    paths['fvSchemes']
)
print(f"fvSchemes written to: {paths['fvSchemes']}")

IO_fcts.write_text_file(
    populator_fcts.generate_fvSolution(configA['fvSolution']),
    paths['fvSolution']
)
print(f"fvSolution written to: {paths['fvSolution']}")

# --- Mesh generation toggle based on user config ---
mesh_cfg = configU.get('mesh', {})
use_snappy = mesh_cfg.get('useSnappy', False)
use_cfmesh = mesh_cfg.get('useCfMesh', False)

if use_snappy:
    print("🗜  Generating snappyHexMeshDict...")
    snappy_text = populator_fcts.generate_snappyHexMeshDict(configU, configA,
        configU['snappyHexMeshDict'], configA['snappyHexMeshDict']
    )
    IO_fcts.write_text_file(snappy_text, paths['snappyHexMeshDict'])
    print(f"snappyHexMeshDict written to: {paths['snappyHexMeshDict']}")
else:
    print("ℹ️  Skipping snappyHexMeshDict generation (disabled in userConfig)")

if use_cfmesh:
    print("🗜  Generating cfMesh meshDict...")
    cfmesh_text = populator_fcts.generate_cfMeshDict(
        configU.get('meshDict', {}), configA.get('meshDict', {})
    )
    IO_fcts.write_text_file(cfmesh_text, paths['meshDict'])
    print(f"meshDict written to: {paths['meshDict']}")
else:
    print("ℹ️  Skipping meshDict generation (cfMesh disabled in userConfig)")

