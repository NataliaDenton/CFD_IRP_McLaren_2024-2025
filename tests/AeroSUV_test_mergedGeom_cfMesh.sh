#!/bin/bash
set -eo pipefail

# ---- CONFIGURATION ----
CASE_DIR="../src/Openfoam/AeroSUV_mergedGeom_case_cfMesh"
LOG_DIR="log"
MESH_LOG="${LOG_DIR}/blockMesh.log"
CFMESH_LOG="${LOG_DIR}/cfmesh.log"
POTENTIAL_LOG="${LOG_DIR}/potentialFoam.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"
configDir="../../../src/configs/exampleConfigs/cfMesh"
# ---- FUNCTIONS ----

function check_file_exists() {
    if [[ ! -f "$1" ]]; then
        echo "❌ Required file not found: $1"
        exit 1
    fi
}

function check_directory_exists() {
    if [[ ! -d "$1" ]]; then
        echo "❌ Required directory not found: $1"
        exit 1
    fi
}

function run_step() {
    local description="$1"
    local command="$2"
    local log_file="$3"

    echo "🔹 $description..."
    bash -c "$command" 2>&1 | tee "$log_file"
    echo "✅ Finished: $description"
}

# ---- MAIN SCRIPT ----

echo "🔧 Moving to case directory: $CASE_DIR"
cd "$CASE_DIR"

source $FOAM_BASH  # Adjust if needed

echo "🧼 Cleaning old mesh, logs, and cached files..."
rm -rf constant/polyMesh processor* postProcessing VTK* *.OpenFOAM 2>/dev/null || true
find . -maxdepth 1 -type d -regex './[0-9]+' -exec rm -rf {} \;
rm -rf ${LOG_DIR} && mkdir -p ${LOG_DIR}

# 0 directory and fields
mkdir -p 0
fields=("U" "p" "k" "epsilon" "nut" "T" "alphat")
for field in "${fields[@]}"; do
    touch "0/$field"
done
echo "📁 Created empty 0/ folder with placeholder field files:"
ls -lh 0/

# Sanity checks
check_file_exists "system/meshDict"
check_file_exists "system/controlDict"
check_directory_exists "constant/triSurface"

# Pre-processing
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/Geometry/mergeGeometry.py --configDir $configDir || {
    echo "❌ Python script mergeGeometry.py failed"
    exit 1
}

surfaceTransformPoints \
    -scale "(0.001 0.001 0.001)" \
    constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
    constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl

# Regenerate system/constant files if needed
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/meshGeneration.py --configDir $configDir || {
    echo "❌ Python script meshGeneration.py failed"
    exit 1
}

singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/constant.py --configDir $configDir || {
    echo "❌ Python script constant.py failed"
    exit 1
}

singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/system.py --configDir $configDir || {
    echo "❌ Python script system.py failed"
    exit 1
}

# Run meshing with cfMesh
run_step "Running cartesianMesh (cfMesh)" "cartesianMesh" "${CFMESH_LOG}"

# Initial condition setup
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/0.py --configDir $configDir || {
    echo "❌ Python script 0.py failed"
    exit 1
}

# Solver
run_step "Running simpleFoam" "simpleFoam" "${SOLVER_LOG}"

foamToVTK
paraFoam

echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"

