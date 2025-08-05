#!/bin/bash
set -eo pipefail

# === CONFIGURATION ===
PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_NAME="unitCube"
CASE_DIR="${PROJECT_ROOT}/src/Openfoam/${CASE_NAME}"
CONFIG_DIR="${PROJECT_ROOT}/src/configs/${CASE_NAME}"
CONTAINER="${PROJECT_ROOT}/containers/openfoam_dev_2406.sif"

# Log and output setup
LOG_DIR="${CASE_DIR}/log"
CHECK_LOG="${LOG_DIR}/sanity_check.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"
MESH_LOG="${LOG_DIR}/blockMesh.log"
SNAPPY_LOG="${LOG_DIR}/snappyHexMesh.log"

# OpenFOAM container environment
OPENFOAM_ENV="source /root/OpenFOAM/OpenFOAM-v2406/etc/bashrc"
PYTHON_VENV="/root/OpenFOAM/pyenv/bin/python"

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



# === FUNCTION DEFINITIONS ===
function run_step() {
    local description="$1"
    local command="$2"
    local log_file="$3"
    echo "?? $description..."
    singularity exec --bind "${PROJECT_ROOT}:${PROJECT_ROOT}" "$CONTAINER" /bin/bash -c "$OPENFOAM_ENV && $command" 2>&1 | tee "$log_file"
    echo "? Finished: $description"
}

function run_in_container() {
    local cmd="$1"
    singularity exec --bind "${PROJECT_ROOT}:${PROJECT_ROOT}" "$CONTAINER" /bin/bash -c "$OPENFOAM_ENV && $cmd"
}

function run_python_in_container() {
    local py_command="$1"
    singularity exec --bind "${PROJECT_ROOT}:${PROJECT_ROOT}" "$CONTAINER" "$PYTHON_VENV" $py_command
}

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


# === MAIN PIPELINE ===
echo "Moving to case directory: $CASE_DIR"
cd "$CASE_DIR"

echo "Cleaning old logs and post-processing output..."
rm -rf processor* postProcessing ${LOG_DIR} VTK* *.OpenFOAM *.foam
find . -maxdepth 1 -type d -regex './[0-9]+' -exec rm -rf {} \;
mkdir -p "${LOG_DIR}" 0





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






# === Generate system/constant/0 files ===
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/constant.py --configDir ${CONFIG_DIR}" || exit 1
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/system.py --configDir ${CONFIG_DIR}" || exit 1
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/0.py --configDir ${CONFIG_DIR} --caseDir ${CASE_DIR}" || exit 1

# === Confirm field files ===
# === Confirm required field files for laminar ===
FIELDS=("p" "U")
for f in "${FIELDS[@]}"; do
    [[ -f "0/$f" ]] || { echo "? Field missing: 0/$f"; exit 1; }
done
echo "? Required laminar field files present in 0/"

# === Mesh Quality Check ===
run_step "Checking mesh quality" "checkMesh -constant" "${LOG_DIR}/checkMesh.log"

# .. === Post-checkMesh: Handle unused and nonManifold points ===
echo ".. Checking for unused and nonManifold points..."
SET_DIR="${CASE_DIR}/constant/polyMesh/sets"
mkdir -p "$SET_DIR"

UNUSED_VTP="${CASE_DIR}/VTK/constant/pointSets/unusedPoints.vtp"
NONMANIFOLD_VTP="${CASE_DIR}/VTK/constant/pointSets/nonManifoldPoints.vtp"

echo ".. Skipping mesh cleanup to preserve mesh. Proceeding with point set visualisation only."


# .. Convert unused points to VTK (if found)
#if grep -q "Writing.*unusedPoints" "${LOG_DIR}/checkMesh.log"; then
#    echo "...  Detected unused points. Applying cleanup using foamCleanPolyMesh..."
#    run_step "Cleaning unused mesh points" "foamCleanPolyMesh" "${LOG_DIR}/foamCleanPolyMesh.log"
#
#    echo ".. Re-checking mesh after cleanup..."
#    run_step "Re-running checkMesh after cleaning" "checkMesh -constant" "${LOG_DIR}/checkMesh_afterClean.log"
#fi

# .. Convert point sets (if exist) to VTK
echo ".. Converting pointSets to VTK for ParaView..."
run_step "Converting unusedPoints to VTK" "foamToVTK -pointSet unusedPoints -time constant" "${LOG_DIR}/foamToVTK_unused.log" || echo "..  unusedPoints conversion skipped."
run_step "Converting nonManifoldPoints to VTK" "foamToVTK -pointSet nonManifoldPoints -time constant" "${LOG_DIR}/foamToVTK_nonManifold.log" || echo "..  nonManifoldPoints conversion skipped."

# === SIMPLE Solver ===
echo "?? Switching to solver controlDict..."
cp system/controlDict.simpleFoam system/controlDict

run_step "Decomposing domain (scotch)" "decomposePar -force" "${LOG_DIR}/decomposePar.log"
run_step "Running simpleFoam in parallel" "mpirun -np ${numProc} simpleFoam -parallel" "${SOLVER_LOG}"
run_step "Reconstructing solution" "reconstructPar" "${LOG_DIR}/reconstructPar.log"
run_step "Converting foam to VTK" "foamToVTK" "${LOG_DIR}/foamToVTK.log"

# === Optional residual plotting ===
run_python_in_container "${PROJECT_ROOT}/src/scripts/postProcessing/extract_residuals.py --logFile ${SOLVER_LOG} --outDir ${LOG_DIR}" || echo "?? Residual plotting failed, continuing..."

echo "?? Laminar simulation complete."
