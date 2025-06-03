#!/bin/bash
set -eo pipefail

# ---- CONFIGURATION ----
CASE_DIR="../src/Openfoam/AeroSUV_rearWheels_case"
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

echo "Scaling STL..."

surfaceTransformPoints \
  -scale "(0.001 0.001 0.001)" \
  constant/triSurface/Geometry/rearWheels/18_wheels-rear.stl \
  constant/triSurface/Geometry/rearWheels/18_wheels-rear_scaled.stl




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
echo "🔹Running blockMesh..."
blockMesh > blockMesh.log 2>&1
tail -f blockMesh.log
echo "✅ Finished: blockMesh" 

echo "🔹Running surfaceFeatureExtract..."
surfaceFeatureExtract > surfaceFeatureExtract.log 2>&1
tail -f surfaceFeatureExtract.log
echo "✅ Finished: surfaceFeatureExtract" 


echo "🔹Running snappyHexMesh..."
snappyHexMesh > snappyHexMesh.log 2>&1
tail -f snappyHexMesh.log
echo "✅ Finished: snappyHexMesh" 


# running the initial conditions creator 
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/0.py || {
  echo "❌ Python script 0.py failed"
  exit 1
}

# Optional: potentialFoam initialization
#run_step "Running potentialFoam" "potentialFoam" "${POTENTIAL_LOG}"

# Main Solver
run_step "Running simpleFoam" "simpleFoam" "${SOLVER_LOG}"

echo "🔹Running simpleFoam..."
simpleFoam > simpleFoam.log 2>&1
tail -f simpleFoam.log
echo "✅ Finished: snappyHexMesh" 

echo "🔹Running foamToVTK..."
foamToVTK > foamToVTK.log 2>&1
tail -f foamToVTK.log
echo "✅ Finished: foamToVTK" 

paraFoam


echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"



