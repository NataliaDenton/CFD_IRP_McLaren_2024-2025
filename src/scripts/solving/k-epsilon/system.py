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
# --- Generate controlDicts for different applications (snappy + solver) ---
if 'snappy' in configU.get('control', {}):
    print("📘 Writing snappyHexMesh controlDict...")
    snappy_control = populator_module.generate_controlDict(configU, configA, subkey="snappy")
    IO_fcts.write_text_file(snappy_control, paths['controlDict'])  # Default is for snappy
    print(f"✅ controlDict (snappyHexMesh) written to: {paths['controlDict']}")

if 'solver' in configU.get('control', {}):
    print("📘 Writing simpleFoam controlDict.simpleFoam...")
    solver_control = populator_module.generate_controlDict(configU, configA, subkey="solver")
    solver_path = paths['controlDict'].with_name("controlDict.simpleFoam")
    IO_fcts.write_text_file(solver_control, solver_path)
    print(f"✅ controlDict.simpleFoam written to: {solver_path}")
if 'pimpleInit' in configU.get('control', {}):
    print("📘 Writing pimpleFoam controlDict.pimpleInit...")
    pimple_control = populator_module.generate_controlDict(configU, configA, subkey="pimpleInit")
    pimple_path = paths['controlDict'].with_name("controlDict.pimpleInit")
    IO_fcts.write_text_file(pimple_control, pimple_path)
    print(f"✅ controlDict.pimpleInit written to: {pimple_path}")




#------------------------

IO_fcts.write_text_file(
    populator_module.decomposeParDict_populator(configU['cores'], configA['decomposeParDict']),
    paths['decomposeParDict']
)
print(f"decomposeParDict written to: {paths['decomposeParDict']}")

IO_fcts.write_text_file(
    populator_module.generate_fvSchemes(configU['fvSchemes'], configA['fvSchemes']),
    paths['fvSchemes']
)
print(f"fvSchemes written to: {paths['fvSchemes']}")

IO_fcts.write_text_file(
    populator_module.generate_fvSolution(configA['fvSolution']),
    paths['fvSolution']
)
print(f"fvSolution written to: {paths['fvSolution']}")

# === Mesh generation toggle based on user config ===
mesh_cfg = configU.get('mesh', {})
use_snappy = mesh_cfg.get('useSnappy', False)
use_cfmesh = mesh_cfg.get('useCfMesh', False)

# ✅ If Fluent mesh already exists, forcibly override mesh generation
boundary_file = Path("constant/polyMesh/boundary")
if boundary_file.exists():
    print("🧠 Fluent mesh detected — skipping snappyHexMesh and cfMesh generation.")
    use_snappy = False
    use_cfmesh = False


# === snappyHexMeshDict section ===
if use_snappy:
    print("🗜  Generating snappyHexMeshDict...")
    snappy_text = populator_module.generate_snappyHexMeshDict(configU, configA,
        configU['snappyHexMeshDict'], configA['snappyHexMeshDict']
    )
    IO_fcts.write_text_file(snappy_text, paths['snappyHexMeshDict'])
    print(f"snappyHexMeshDict written to: {paths['snappyHexMeshDict']}")
else:
    print("ℹ️  Skipping snappyHexMeshDict generation (disabled or undefined in userConfig)")

# === cfMesh section ===
if use_cfmesh:
    print("🗜  Generating cfMesh meshDict...")
    cfmesh_text = populator_module.generate_cfMeshDict(
        configU.get('meshDict', {}), configA.get('meshDict', {})
    )
    IO_fcts.write_text_file(cfmesh_text, paths['meshDict'])
    print(f"meshDict written to: {paths['meshDict']}")
else:
    print("ℹ️  Skipping meshDict generation (cfMesh disabled or undefined in userConfig)")


