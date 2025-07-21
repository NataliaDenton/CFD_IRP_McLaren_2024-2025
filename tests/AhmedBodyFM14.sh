#!/bin/bash
set -eo pipefail

# === CONFIGURATION ===
PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_NAME="AhmedBodyFM14"
CASE_DIR="${PROJECT_ROOT}/src/Openfoam/${CASE_NAME}"
CONFIG_DIR="${PROJECT_ROOT}/src/configs/${CASE_NAME}"
CONTAINER="${PROJECT_ROOT}/containers/openfoam_dev_2406.sif"

# Fluent mesh input (compressed)
MESH_FILE_GZ_REL="src/ext_mesh/AhmedBody_Hexcore_3.msh.gz"
MESH_FILE_GZ="${PROJECT_ROOT}/${MESH_FILE_GZ_REL}"
MESH_FILE="${MESH_FILE_GZ%.gz}"

# Log and output setup
LOG_DIR="${CASE_DIR}/log"
CHECK_LOG="${LOG_DIR}/sanity_check.log"
CONVERT_LOG="${LOG_DIR}/fluent3DMeshToFoam.log"
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
    echo "🔹 $description..."
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
echo "🔧 Moving to case directory: $CASE_DIR"
cd "$CASE_DIR"

echo "🧼 Cleaning old logs and post-processing output..."
rm -rf processor* postProcessing ${LOG_DIR} VTK* *.OpenFOAM *.foam
find . -maxdepth 1 -type d -regex './[0-9]+' -exec rm -rf {} \;
mkdir -p "${LOG_DIR}" 0

# === Check controlDict ===
echo "🕵️ Verifying controlDict..." | tee -a "$CHECK_LOG"
check_file_exists "$CASE_DIR/system/controlDict"
head -n 5 "$CASE_DIR/system/controlDict" | tee -a "$CHECK_LOG"

# === Mesh Handling ===
ORIGINAL_MESH_DIR=$(dirname "$MESH_FILE")/polyMesh
POLYMESH_TARGET="$CASE_DIR/constant/polyMesh"
MESH_FILES=(points faces owner neighbour boundary)

echo "📦 Checking for existing mesh at: $ORIGINAL_MESH_DIR"
mesh_complete=true
for f in "${MESH_FILES[@]}"; do
    [[ -f "$ORIGINAL_MESH_DIR/$f" ]] || { mesh_complete=false; break; }
done

if $mesh_complete; then
    echo "✅ Existing polyMesh found. Copying to case..."
    mkdir -p "$(dirname "$POLYMESH_TARGET")"
    cp -r "$ORIGINAL_MESH_DIR" "$POLYMESH_TARGET"
else
    echo "📦 No mesh found. Converting Fluent mesh..." | tee -a "$CHECK_LOG"
    check_file_exists "$MESH_FILE_GZ"
    gunzip -c "$MESH_FILE_GZ" > "$MESH_FILE"
    run_step "Converting Fluent mesh to OpenFOAM" "fluent3DMeshToFoam \"$MESH_FILE\" -scale 0.001 -case \"$CASE_DIR\"" "$CONVERT_LOG"
fi

# === Validate polyMesh ===
echo "📂 Verifying mesh files..."
for f in "${MESH_FILES[@]}"; do
    [[ -f "$POLYMESH_TARGET/$f" ]] || { echo "❌ Missing $f in polyMesh. Aborting."; exit 1; }
    echo "✔️ Found: $f"
done

# === Generate .foam file ===
echo "🧩 Creating .foam file for ParaView..."
touch "$FOAM_FILE"
echo "✅ .foam file: $(basename "$FOAM_FILE")"

# === Generate system/constant/0 files ===
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/constant.py --configDir ${CONFIG_DIR}" || exit 1
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/system.py --configDir ${CONFIG_DIR}" || exit 1
run_python_in_container "${PROJECT_ROOT}/src/scripts/OpenFOAM/0.py --configDir ${CONFIG_DIR} --caseDir ${CASE_DIR}" || exit 1



# === Confirm field files ===
FIELDS=("p" "U" "k" "epsilon" "nut")
for f in "${FIELDS[@]}"; do
    [[ -f "0/$f" ]] || { echo "❌ Field missing: 0/$f"; exit 1; }
done
echo "✅ All field files present in 0/"

# === Solver Execution ===
run_step "Checking mesh quality" "checkMesh -constant" "${LOG_DIR}/checkMesh.log"
#run_step "Checking mesh quality" "checkMesh -allGeometry -allTopology" "${LOG_DIR}/checkMesh.log" # additional mesh checks - 250709

# === Optional: transient initialisation using pimpleFoam ===
#echo "🔹 Running transient stabilisation (pimpleFoam)..."
#run_step "Initialising transient solution with pimpleFoam" "pimpleFoam" "${LOG_DIR}/pimpleFoam.log"




# === Optional: potentialFoam initialisation === #   inittialise the foam field with potential foam first and then move on to simple
echo "🔹 Initialising fields with potentialFoam..."
run_step "Running potentialFoam" "potentialFoam -writePhi -writep" "${LOG_DIR}/potentialFoam.log"


# === Swap in solver-specific controlDict ===
echo "🔁 Switching to solver controlDict..."
#just to have a new control dict for the simple foam # -this should not affect any workflow for snappy....
cp system/controlDict.simpleFoam system/controlDict




run_step "Decomposing domain (scotch)" "decomposePar -force" "${LOG_DIR}/decomposePar.log"
run_step "Running simpleFoam in parallel" "mpirun -np ${numProc} simpleFoam -parallel" "${SOLVER_LOG}"
run_step "Reconstructing solution" "reconstructPar" "${LOG_DIR}/reconstructPar.log"
run_step "Converting foam to VTK" "foamToVTK" "${LOG_DIR}/foamToVTK.log"

# === Post-processing ===
run_python_in_container "${PROJECT_ROOT}/src/scripts/postProcessing/avarageForceCoeffs.py --configDir ${CONFIG_DIR}" || exit 1
run_in_container "foamToVTK -latestTime"
# === Post-process residuals === # plot residuals graph for better visualisation
run_python_in_container "${PROJECT_ROOT}/src/scripts/postProcessing/extract_residuals.py --logFile ${SOLVER_LOG} --outDir ${LOG_DIR}" || echo "⚠️ Residual plotting failed, continuing..."



echo "🎉 Simulation complete."

