#!/bin/bash
set -eo pipefail

# === CONFIGURATION ===
PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_NAME="AeroSUV"  #remember to adjust this for each different case
CASE_DIR="${PROJECT_ROOT}/src/Openfoam/${CASE_NAME}"
CONFIG_DIR="${PROJECT_ROOT}/src/configs/${CASE_NAME}"
CONTAINER="${PROJECT_ROOT}/containers/container.sif"

# Log and output setup
LOG_DIR="${CASE_DIR}/log"
CHECK_LOG="${LOG_DIR}/sanity_check.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"
MESH_LOG="${LOG_DIR}/blockMesh.log"
SNAPPY_LOG="${LOG_DIR}/snappyHexMesh.log"

# === Load numProc and fields from YAML config (inside container) ===
userConfig="${CONFIG_DIR}/userConfig.yaml"
advancedConfig="${CONFIG_DIR}/advancedConfig.yaml"

if [[ ! -f "$userConfig" ]]; then
    echo "Error: userConfig.yaml not found in $CONFIG_DIR"
    exit 1
fi



numProc=$(singularity exec ../containers/container.sif python3 -c "
import yaml
with open('$userConfig') as f:
    print(yaml.safe_load(f).get('cores', 8))
")

turbulenceModel=$(singularity exec ../containers/container.sif python3 -c "
import yaml
with open('$userConfig') as f:
    config = yaml.safe_load(f)
    turbulence = config.get('turbulence', {})
    print(turbulence.get('model', 'defaultModel'))
")



# Optional: default fallback
if [[ -z "$numProc" ]]; then
    numProc=8
fi
echo "Number of processors set to $numProc"

# Fields array from YAML (inside container)
mapfile -t fields < <(
    singularity exec ../containers/container.sif python3 -c "
import yaml
with open('$userConfig') as f:
    for field in yaml.safe_load(f).get('fields', []):
        print(field)
"
)

echo "Using $numProc cores"
echo "Fields to initialize: ${fields[*]}"



# ---- FUNCTIONS ----
# Check if a file exists, if not create it (ensuring directory exists)
check_file_exists() {
    local file="$1"
    local dir
    dir=$(dirname "$file")

    # Ensure parent directory exists
    if [[ ! -d "$dir" ]]; then
        echo "Parent directory $dir not found. Creating it..."
        mkdir -p "$dir"
    fi

    # Create the file if missing
    if [[ ! -f "$file" ]]; then
        echo "Warning: $file not found. Creating an empty file."
        touch "$file"
    else
        echo "Found: $file"
    fi
}

# Check if a directory exists, if not create it
check_directory_exists() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        echo "Warning: $dir not found. Creating an empty directory."
        mkdir -p "$dir"
    else
        echo "Found: $dir"
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
check_directory_exists "constant/triSurface/Geometry/mergedGeometry"
# system folder files
check_file_exists "system/blockMeshDict"
check_file_exists "system/snappyHexMeshDict"
check_file_exists "system/controlDict"
check_file_exists "system/fvSchemes"
check_file_exists "system/fvSolution"
check_file_exists "system/decomposeParDict"
check_file_exists "system/surfaceFeatureExctractDict"

# constant folder files and directories
check_file_exists "constant/transportProperties"
check_file_exists "constant/turbulenceProperties"
check_directory_exists "constant/polyMesh"
check_directory_exists "constant/triSurface"

# 0 folder fields (placeholder files created earlier in your script)
for field in "${fields[@]}"; do
    check_file_exists "0/$field"
done



# Load OpenFOAM environment (if not already in shell config)
source $FOAM_BASH  # or use full path if needed
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/geomPreProcessing/mergeGeometry.py --configDir $CONFIG_DIR|| {
  echo "❌ Python script mergeGeometry.py failed"
  exit 1
}

surfaceTransformPoints \
  -scale "(0.004 0.004 0.004)" \
  constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
  constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl

# Make sure the Python script is executable or specify interpreter
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/meshing/openfoam_meshGeneration.py --configDir "$CONFIG_DIR" --modelType "$turbulenceModel"|| {
  echo "❌ Python script meshGeneration.py failed"
  exit 1
}


# Decide directory based on turbulence model
case "$turbulenceModel" in
    kEpsilon)
        modelDir="../../../src/scripts/solving/k-epsilon"
        ;;
    kOmegaSST|kOmega|SST)
        modelDir="../../../src/scripts/solving/k-omegaSST"
        ;;
    laminar)
        modelDir="../../../src/scripts/solving/laminar"
        ;;
    *)
        echo "⚠ Unknown turbulence model '$turbulenceModel', using default OpenFOAM templates."
        modelDir="../../../src/scripts/OpenFOAM"
        ;;
esac



echo "📂 Using script directory: $modelDir"



# Run your generation scripts
singularity exec ../../../containers/container.sif python3 "$modelDir/constant.py" --configDir "$CONFIG_DIR" --modelType "$turbulenceModel"|| {
  echo "❌ Python script constant.py failed"
  exit 1
}



singularity exec ../../../containers/container.sif python3 "$modelDir/system.py" --configDir "$CONFIG_DIR" --modelType "$turbulenceModel"|| {
  echo "❌ Python script system.py failed"
  exit 1
}

run_step "Running blockMesh" "blockMesh" "${MESH_LOG}"
# Serial steps


run_step "Running surfaceFeatureExtract" "surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"

# Run snappyHexMesh in serial
run_step "Running snappyHexMesh" "snappyHexMesh -overwrite" "${SNAPPY_LOG}"

singularity exec ../../../containers/container.sif python3 "$modelDir/0.py" --configDir "$CONFIG_DIR" --modelType "$turbulenceModel" || {
  echo "❌ Python script 0.py failed"
  exit 1
}


# Optional: Check mesh quality
run_step "Checking mesh quality" "checkMesh" "${LOG_DIR}/checkMesh.log"

# Now decompose for parallel solve
run_step "Decomposing for parallel solving" "decomposePar -force" "${LOG_DIR}/decomposePar.log"

# Run solver
run_step "Running simpleFoam in parallel" "mpirun -np ${numProc} simpleFoam -parallel" "${SOLVER_LOG}"

# Reconstruct final solution
run_step "Reconstructing solution fields" "reconstructPar" "${LOG_DIR}/reconstructPar.log"


singularity exec ../../../containers/container.sif python3 ../../../src/scripts/postProcessing/avarageForceCoeffs.py --configDir $CONFIG_DIR|| {
  echo "❌ Python script avarageForceCoeffs.py failed"
  exit 1
}


echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"



