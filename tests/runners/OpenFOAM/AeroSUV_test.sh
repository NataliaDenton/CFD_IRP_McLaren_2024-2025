#!/bin/bash
set -euo pipefail

# ---- CONFIGURATION ----
CASE_DIR="../../../src/Openfoam/AeroSUV_case"
LOG_DIR="log"
MESH_LOG="${LOG_DIR}/blockMesh.log"
SNAPPY_LOG="${LOG_DIR}/snappyHexMesh.log"
POTENTIAL_LOG="${LOG_DIR}/potentialFoam.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"

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
    $command > "$log_file" 2>&1
    echo "✅ Finished: $description"
}

# ---- MAIN SCRIPT ----



echo "🔧 Moving to case directory: $CASE_DIR"
cd "$CASE_DIR"

echo "🧼 Cleaning old mesh and logs..."
rm -rf constant/polyMesh processor* postProcessing ${LOG_DIR} 2>/dev/null || true
mkdir -p ${LOG_DIR}



# Sanity checks
check_file_exists "system/blockMeshDict"
check_file_exists "system/snappyHexMeshDict"
check_file_exists "system/controlDict"
check_directory_exists "constant/triSurface"

echo "Scaling STL..."
surfaceTransformPoints \
  -scale "(0.001 0.001 0.001)" \
  constant/triSurface/Geometry/frontWheels/17_wheels-front.stl \
  constant/triSurface/Geometry/frontWheels/17_wheels-front_scaled.stl


# Mesh Generation Steps
run_step "Running blockMesh" "blockMesh" "${MESH_LOG}"
run_step "Running surfaceFeatureExtract" "surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"
run_step "Running snappyHexMesh" "snappyHexMesh -overwrite" "${SNAPPY_LOG}"

# Optional: potentialFoam initialization
#run_step "Running potentialFoam" "potentialFoam" "${POTENTIAL_LOG}"

# Main Solver
run_step "Running simpleFoam" "simpleFoam" "${SOLVER_LOG}"

echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"

