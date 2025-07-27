#!/bin/bash
set -eo pipefail

# === CONFIGURATION ===
PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_NAME="AhmedBodyAnsaM3"
CASE_DIR="${PROJECT_ROOT}/src/Openfoam/${CASE_NAME}"
CONFIG_DIR="${PROJECT_ROOT}/src/configs/${CASE_NAME}"
CONTAINER="${PROJECT_ROOT}/containers/openfoam_dev_2406.sif"

# Mesh location (from ANSA)
ANSA_MESH_DIR="/mnt/beegfs/home/a.wadekar/IRPOpenFOAM/CFD_IRP_McLaren_2024-2025/src/ext_mesh/AhmedBody_Ansa_M5/constant/polyMesh"
POLYMESH_TARGET="$CASE_DIR/constant/polyMesh"
MESH_FILES=(points faces owner neighbour boundary)

# Log and output setup
LOG_DIR="${CASE_DIR}/log"
CHECK_LOG="${LOG_DIR}/sanity_check.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"
FOAM_FILE="${CASE_DIR}/Ahmed_body_coarse.foam"

# OpenFOAM container environment
OPENFOAM_ENV="source /root/OpenFOAM/OpenFOAM-v2406/etc/bashrc"
PYTHON_VENV="/root/OpenFOAM/pyenv/bin/python"
numProc="16"

# === FUNCTION DEFINITIONS ===
function run_step() {
    local description="$1"
    local command="$2"
    local log_file="$3"
    echo "🔧 $description..."
    singularity exec --bind "${PROJECT_ROOT}:${PROJECT_ROOT}" "$CONTAINER" /bin/bash -c "$OPENFOAM_ENV && $command" 2>&1 | tee "$log_file"
    echo "✅ Finished: $description"
}

function run_in_container() {
    local cmd="$1"
    singularity exec --bind "${PROJECT_ROOT}:${PROJECT_ROOT}" "$CONTAINER" /bin/bash -c "$OPENFOAM_ENV && $cmd"
}

function run_python_in_container() {
    local py_command="$1"
    singularity exec --bind "${PROJECT_ROOT}:${PROJECT_ROOT}" "$CONTAINER" "$PYTHON_VENV" $py_command
}

function check_file_exists() {
    [[ -f "$1" ]] || { echo "❌ Required file not found: $1"; exit 1; }
}

# === MAIN PIPELINE ===
echo "📁 Moving to case directory: $CASE_DIR"
cd "$CASE_DIR"

echo "🧹 Cleaning old logs and post-processing output..."
rm -rf processor* postProcessing ${LOG_DIR} VTK* *.OpenFOAM *.foam
find . -maxdepth 1 -type d -regex './[0-9]+' -exec rm -rf {} \;
mkdir -p "${LOG_DIR}" 0

# === Check controlDict ===
echo "🧾 Verifying controlDict..." | tee -a "$CHECK_LOG"
check_file_exists "$CASE_DIR/system/controlDict"
head -n 5 "$CASE_DIR/system/controlDict" | tee -a "$CHECK_LOG"

# === Mesh Handling ===
echo "📦 Copying polyMesh from ANSA source..."
for f in "${MESH_FILES[@]}"; do
    check_file_exists "${ANSA_MESH_DIR}/${f}"
done

mkdir -p "$POLYMESH_TARGET"
cp -r "$ANSA_MESH_DIR/"* "$POLYMESH_TARGET/"




# === Validate polyMesh ===
echo "🔍 Verifying mesh files..."
for f in "${MESH_FILES[@]}"; do
    [[ -f "$POLYMESH_TARGET/$f" ]] || { echo "❌ Missing $f in polyMesh. Aborting."; exit 1; }
    echo "✅ Found: $f"
done

# === Generate .foam file for ParaView ===
echo "📄 Creating .foam file for ParaView..."
touch "$FOAM_FILE"
echo "✅ .foam file: $(basename "$FOAM_FILE")"

# === Generate system/constant/0 files ===
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/constant.py --configDir ${CONFIG_DIR}" || exit 1
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/system.py --configDir ${CONFIG_DIR}" || exit 1
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/0.py --configDir ${CONFIG_DIR} --caseDir ${CASE_DIR}" || exit 1

# === Confirm field files ===
FIELDS=("p" "U")
for f in "${FIELDS[@]}"; do
    [[ -f "0/$f" ]] || { echo "❌ Field missing: 0/$f"; exit 1; }
done
echo "✅ Required laminar field files present in 0/"

# === Mesh Quality Check ===
run_step "Checking mesh quality" "checkMesh -constant" "${LOG_DIR}/checkMesh.log"

# === Handle unused/nonManifold points ===
echo "🧠 Checking for unused and nonManifold points..."
SET_DIR="${POLYMESH_TARGET}/sets"
mkdir -p "$SET_DIR"

UNUSED_VTP="${CASE_DIR}/VTK/constant/pointSets/unusedPoints.vtp"
NONMANIFOLD_VTP="${CASE_DIR}/VTK/constant/pointSets/nonManifoldPoints.vtp"

echo "ℹ️ Skipping mesh cleanup to preserve mesh. Proceeding with point set visualisation only."

run_step "Converting unusedPoints to VTK" "foamToVTK -pointSet unusedPoints -time constant" "${LOG_DIR}/foamToVTK_unused.log" || echo "⚠️ unusedPoints conversion skipped."
run_step "Converting nonManifoldPoints to VTK" "foamToVTK -pointSet nonManifoldPoints -time constant" "${LOG_DIR}/foamToVTK_nonManifold.log" || echo "⚠️ nonManifoldPoints conversion skipped."

# === SIMPLE Solver Run ===
echo "⚙️ Switching to solver controlDict..."
cp system/controlDict.simpleFoam system/controlDict

run_step "Decomposing domain (scotch)" "decomposePar -force" "${LOG_DIR}/decomposePar.log"
run_step "Running simpleFoam in parallel" "mpirun -np ${numProc} simpleFoam -parallel" "${SOLVER_LOG}"
run_step "Reconstructing solution" "reconstructPar" "${LOG_DIR}/reconstructPar.log"
run_step "Converting foam to VTK" "foamToVTK" "${LOG_DIR}/foamToVTK.log"

# === Residual Plotting ===
run_python_in_container "${PROJECT_ROOT}/src/scripts/postProcessing/extract_residuals.py --logFile ${SOLVER_LOG} --outDir ${LOG_DIR}" || echo "⚠️ Residual plotting failed, continuing..."

echo "✅ Laminar simulation complete using ANSA mesh."

