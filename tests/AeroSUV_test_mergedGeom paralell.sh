#!/bin/bash
set -eo pipefail

# ---- CONFIGURATION ----
CASE_DIR="../src/Openfoam/AeroSUV_mergedGeom_case"
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
# Load OpenFOAM environment (if not already in shell config)
source $FOAM_BASH  # or use full path if needed

echo "🧼 Cleaning old mesh and logs..."
rm -rf constant/polyMesh processor* postProcessing ${LOG_DIR} 2>/dev/null || true
mkdir -p ${LOG_DIR}

echo "📦 Generating openfoam mesh scripts..."


# Sanity checks
check_file_exists "system/blockMeshDict"
check_file_exists "system/snappyHexMeshDict"
check_file_exists "system/controlDict"
check_directory_exists "constant/triSurface"





singularity exec ../../../containers/container.sif python3 ../../../src/scripts/Geometry/mergeGeometry.py || {
  echo "❌ Python script mergeGeometry.py failed"
  exit 1
}


surfaceTransformPoints \
  -scale "(0.001 0.001 0.001)" \
  constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
  constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl

# Make sure the Python script is executable or specify interpreter
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/meshGeneration.py || {
  echo "❌ Python script meshGeneration.py failed"
  exit 1
}

singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/constant.py || {
  echo "❌ Python script constant.py failed"
  exit 1
}


singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/system.py || {
  echo "❌ Python script system.py failed"
  exit 1
}

# Mesh Generation Steps
run_step "Running blockMesh" "blockMesh" "${MESH_LOG}"

#### snappy step
run_step "Decomposing the domain" "decomposePar" "${LOG_DIR}/decomposePar.log"

run_step "Running surfaceFeatureExtract" "surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"


run_step "Running snappyHexMesh in parallel" "mpirun -np 6 snappyHexMesh -parallel -overwrite" "${SNAPPY_LOG}"

# running the initial conditions creator 
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/0.py || {
  echo "❌ Python script 0.py failed"
  exit 1
}

run_step "Running simpleFoam in parallel" "mpirun -np 6 simpleFoam -parallel" "${SOLVER_LOG}"

run_step "Reconstructing solution fields" "reconstructPar" "${LOG_DIR}/reconstructPar.log"



foamToVTK

paraFoam


echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"



