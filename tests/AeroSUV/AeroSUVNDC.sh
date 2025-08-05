#!/bin/bash
set -eo pipefail

# === CONFIGURATION ===
PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_NAME="unitCube"  #remember to adjust this if needed
CASE_DIR="${PROJECT_ROOT}/src/Openfoam/${CASE_NAME}"
CONFIG_DIR="${PROJECT_ROOT}/src/configs/${CASE_NAME}"
CONTAINER="${PROJECT_ROOT}/containers/container.sif"

# Log and output setup
LOG_DIR="${CASE_DIR}/log"
CHECK_LOG="${LOG_DIR}/sanity_check.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"

# === Load numProc and fields from YAML config (inside container) ===
userConfig="${CONFIG_DIR}/userConfig.yaml"
advancedConfig="${CONFIG_DIR}/advancedConfig.yaml"
userConfig="${CONFIG_DIR}/userConfig.yaml"
advancedConfig="${CONFIG_DIR}/advancedConfig.yaml"

if [[ ! -f "$userConfig" ]]; then
    echo "Error: userConfig.yaml not found in $CONFIG_DIR"
    exit 1
fi

# Use singularity exec to run Python inside the container
numProc=$(singularity exec  $PYTHON_VENV -c "
import yaml
with open('$userConfig') as f:
    print(yaml.safe_load(f).get('cores', 8))
")

# Optional: default fallback
if [[ -z "$numProc" ]]; then
    numProc=8
fi
echo "Number of processors set to $numProc"

# Fields array from YAML (inside container)
mapfile -t fields < <(
    singularity exec "$CONTAINER" $PYTHON_VENV -c "
import yaml
with open('$userConfig') as f:
    for field in yaml.safe_load(f).get('fields', []):
        print(field)
"
)

echo "Using $numProc cores"
echo "Fields to initialize: ${fields[*]}"



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








# Load OpenFOAM environment (if not already in shell config)
source $FOAM_BASH  # or use full path if needed
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/Geometry/mergeGeometry.py --configDir $configDir|| {
  echo "❌ Python script mergeGeometry.py failed"
  exit 1
}

surfaceTransformPoints \
  -scale "(0.004 0.004 0.004)" \
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
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/0.py --configDir $configDir || {
  echo "❌ Python script 0.py failed"
  exit 1
}
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/system.py --configDir $configDir|| {
  echo "❌ Python script system.py failed"
  exit 1
}

# Serial steps
run_step "Running blockMesh" "blockMesh" "${MESH_LOG}"
run_step "Running surfaceFeatureExtract" "surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"

# Run snappyHexMesh in serial
run_step "Running snappyHexMesh" "snappyHexMesh -overwrite" "${SNAPPY_LOG}"

# Optional: Check mesh quality
run_step "Checking mesh quality" "checkMesh" "${LOG_DIR}/checkMesh.log"

# Now decompose for parallel solve
run_step "Decomposing for parallel solving" "decomposePar -force" "${LOG_DIR}/decomposePar.log"

# Run solver
run_step "Running simpleFoam in parallel" "mpirun -np ${numProc} simpleFoam -parallel" "${SOLVER_LOG}"

# Reconstruct final solution
run_step "Reconstructing solution fields" "reconstructPar" "${LOG_DIR}/reconstructPar.log"


singularity exec ../../../containers/container.sif python3 ../../../src/scripts/postProcessing/avarageForceCoeffs.py --configDir $configDir|| {
  echo "❌ Python script avarageForceCoeffs.py failed"
  exit 1
}


foamToVTK

paraFoam


echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"



