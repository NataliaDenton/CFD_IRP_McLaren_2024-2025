#!/bin/bash
set -eo pipefail

# ---- CONFIGURATION ----
CASE_DIR="../src/Openfoam/AeroSUV_mergedGeom_case"
LOG_DIR="log"
MESH_LOG="${LOG_DIR}/blockMesh.log"
SNAPPY_LOG="${LOG_DIR}/snappyHexMesh.log"
POTENTIAL_LOG="${LOG_DIR}/potentialFoam.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"
configDir="../../../src/configs/Aero_SUV_mergedGeometry"
numProc="4"

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
    
    # Run the command, show output live and also write to log file
    bash -c "$command" 2>&1 | tee "$log_file"

    echo "✅ Finished: $description"
}












# ---- MAIN SCRIPT ----


echo "🔧 Moving to case directory: $CASE_DIR"
cd "$CASE_DIR"
# Load OpenFOAM environment (if not already in shell config)
source $FOAM_BASH  # or use full path if needed

echo "🧼 Cleaning old mesh, logs, and cached files..."

# Remove mesh files
rm -rf constant/polyMesh 2>/dev/null || true

# Remove processor decompositions (if parallel run used)
rm -rf processor* 2>/dev/null || true

# Remove logs
rm -rf ${LOG_DIR} 2>/dev/null || true
mkdir -p ${LOG_DIR}

# Remove post-processing output
rm -rf postProcessing 2>/dev/null || true

# Remove any OpenFOAM time directories (e.g., 0.5/, 1/, 100/)
find . -maxdepth 1 -type d -regex './[0-9]+' -exec rm -rf {} \;

# Remove potential leftover `.vtk` or `paraFoam` data
rm -rf VTK* *.OpenFOAM 2>/dev/null || true

echo "🧼 Cleanup complete."

# Create the 0 directory
mkdir -p 0

# Define your expected fields
fields=("U" "p" "k" "epsilon" "nut" "T" "alphat")

# Touch each as an empty placeholder
for field in "${fields[@]}"; do
    touch "0/$field"
done

echo "📁 Created empty 0/ folder with placeholder field files:"
ls -lh 0/


mkdir -p ${LOG_DIR} 

echo "📦 Generating openfoam mesh scripts..."


# Sanity checks
check_file_exists "system/blockMeshDict"
check_file_exists "system/snappyHexMeshDict"
check_file_exists "system/controlDict"
check_directory_exists "constant/triSurface"







singularity exec ../../../containers/container.sif python3 ../../../src/scripts/Geometry/mergeGeometry.py --configDir $configDir|| {
  echo "❌ Python script mergeGeometry.py failed"
  exit 1
}


surfaceTransformPoints \
  -scale "(0.001 0.001 0.001)" \
  constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
  constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl

# Make sure the Python script is executable or specify interpreter
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/meshGeneration.py --configDir $configDir|| {
  echo "❌ Python script meshGeneration.py failed"
  exit 1
}

singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/constant.py --configDir $configDir|| {
  echo "❌ Python script constant.py failed"
  exit 1
}


singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/system.py --configDir $configDir|| {
  echo "❌ Python script system.py failed"
  exit 1
}

# Mesh Generation Steps
run_step "Running blockMesh" "blockMesh" "${MESH_LOG}"

run_step "Running surfaceFeatureExtract" "surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"


# Parallel meshing
run_step "Running snappyHexMesh" "snappyHexMesh -overwrite" "${SNAPPY_LOG}"




# Generate serial initial conditions before decomposition
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/0.py --configDir $configDir || {
  echo "❌ Python script 0.py failed"
  exit 1
}


# Now decompose both mesh and fields
run_step "Decomposing the domain" "decomposePar -force" "${LOG_DIR}/decomposePar2.log"
# Solve
run_step "Running simpleFoam in parallel" "mpirun -np ${numProc} simpleFoam -parallel" "${SOLVER_LOG}"

run_step "Reconstructing solution fields" "reconstructPar" "${LOG_DIR}/reconstructPar.log"




foamToVTK

paraFoam


echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"



