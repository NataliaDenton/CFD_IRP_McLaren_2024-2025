#!/bin/bash
set -eo pipefail

# ---- CONFIGURATION ----

PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_DIR_REL_TO_PROJECT_ROOT="src/Openfoam/AeroSUV_mergedGeom_case"
HOST_CASE_DIR="${PROJECT_ROOT}/${CASE_DIR_REL_TO_PROJECT_ROOT}"
CONTAINER="${PROJECT_ROOT}/containers/openfoam_dev_2406.sif"
OPENFOAM_ENV="source /openfoam/bash.rc"
PYTHON_VENV="/openfoam/venv/bin/python"

LOG_DIR="${HOST_CASE_DIR}/log"
MESH_LOG="${LOG_DIR}/blockMesh.log"
SNAPPY_LOG="${LOG_DIR}/snappyHexMesh.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"
CHECK_LOG="${LOG_DIR}/check_tools.log"
RUN_LOG="${LOG_DIR}/pipeline.log"
CONFIG_DIR_REL="src/configs/Aero_SUV_mergedGeometry"  # adjust if your config is elsewhere
CONFIG_DIR="${PROJECT_ROOT}/${CONFIG_DIR_REL}"

TOOLS=( blockMesh snappyHexMesh surfaceFeatureExtract simpleFoam foamToVTK )

# ---- HELPERS ----

check_file_exists() {
    [[ -f "$1" ]] || { echo "❌ Required file not found: $1" | tee -a "$RUN_LOG"; exit 1; }
}

check_directory_exists() {
    [[ -d "$1" ]] || { echo "❌ Required directory not found: $1" | tee -a "$RUN_LOG"; exit 1; }
}

run_step() {
    local desc="$1" cmd="$2" logf="$3"
    echo "🔹 $desc..." | tee -a "$RUN_LOG"
    apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
      /bin/bash -c "${OPENFOAM_ENV} && cd /workspace/${CASE_DIR_REL_TO_PROJECT_ROOT} && ${cmd}" \
      2>&1 | tee -a "$logf"
    echo "✅ Finished: $desc" | tee -a "$RUN_LOG"
}

check_tool() {
    local tool="$1"
    echo "🔍 Checking $tool..." | tee -a "$CHECK_LOG"
    apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
      /bin/bash -c "${OPENFOAM_ENV} && ${tool} -help" >/dev/null 2>&1 \
      && echo "✅ $tool is available." | tee -a "$CHECK_LOG" \
      || { echo "❌ $tool is missing or not working." | tee -a "$CHECK_LOG"; exit 1; }
}

# Check if config directory exists
[[ -d "$CONFIG_DIR" ]] || { echo "❌ Config directory not found: $CONFIG_DIR" | tee -a "$RUN_LOG"; exit 1; }

# Check for required config files
[[ -f "$CONFIG_DIR/userConfig.yaml" ]] || { echo "❌ Missing userConfig.yaml in $CONFIG_DIR" | tee -a "$RUN_LOG"; exit 1; }
[[ -f "$CONFIG_DIR/advancedConfig.yaml" ]] || { echo "❌ Missing advancedConfig.yaml in $CONFIG_DIR" | tee -a "$RUN_LOG"; exit 1; }

echo "✅ Using config directory: $CONFIG_DIR" | tee -a "$RUN_LOG"

# ---- MAIN ----

mkdir -p "$LOG_DIR"
echo "🚀 Starting OpenFOAM tool checks..." | tee "$CHECK_LOG"
for tool in "${TOOLS[@]}"; do
    check_tool "$tool"
done
echo "🎉 All required tools are available." | tee -a "$CHECK_LOG"

echo "🚀 Starting OpenFOAM pipeline..." | tee "$RUN_LOG"

cd "$HOST_CASE_DIR" || { echo "❌ Cannot cd to $HOST_CASE_DIR" | tee -a "$RUN_LOG"; exit 1; }
echo "🔧 Using case directory: $(pwd)" | tee -a "$RUN_LOG"

echo "🧹 Cleaning up previous run artifacts..." | tee -a "$RUN_LOG"
rm -rf constant/polyMesh processor* postProcessing VTK* *.OpenFOAM "$LOG_DIR"/*.log 2>/dev/null || true
find . -maxdepth 1 -type d -regex './[0-9]+' -exec rm -rf {} \;
mkdir -p 0
echo "✅ Cleanup complete." | tee -a "$RUN_LOG"

echo "📝 Creating placeholder fields in 0/..." | tee -a "$RUN_LOG"
fields=( U p k epsilon nut T alphat )
for f in "${fields[@]}"; do
  touch "0/${f}"
done
ls -lh 0/ | tee -a "$RUN_LOG"
echo "✅ Placeholders created." | tee -a "$RUN_LOG"

echo "🔍 Checking required files & dirs..." | tee -a "$RUN_LOG"
check_file_exists "system/blockMeshDict"
check_file_exists "system/snappyHexMeshDict"
check_file_exists "system/controlDict"
check_directory_exists "constant/triSurface"
echo "✅ Sanity checks passed." | tee -a "$RUN_LOG"

echo "📦 Merging STL geometry..." | tee -a "$RUN_LOG"
apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
  "$PYTHON_VENV" "/workspace/src/scripts/Geometry/mergeGeometry.py" \
  --configDir "/workspace/${CONFIG_DIR_REL}" \
  2>&1 | tee -a "$RUN_LOG"
echo "✅ Geometry merge complete." | tee -a "$RUN_LOG"

echo "📏 Scaling merged STL..." | tee -a "$RUN_LOG"
apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
  /bin/bash -c "${OPENFOAM_ENV} && cd /workspace/${CASE_DIR_REL_TO_PROJECT_ROOT} && \
    surfaceTransformPoints -scale \"(0.001 0.001 0.001)\" \
      constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
      constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl" \
  2>&1 | tee -a "$RUN_LOG"
echo "✅ Geometry scaled." | tee -a "$RUN_LOG"

echo "⚙️ Running OpenFOAM-setup Python scripts..." | tee -a "$RUN_LOG"
for script in meshGeneration.py constant.py system.py; do
  apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
    "$PYTHON_VENV" "/workspace/src/scripts/OpenFOAM/${script}" \
    --configDir "/workspace/${CONFIG_DIR_REL}" \
    2>&1 | tee -a "$RUN_LOG" || { echo "❌ $script failed." | tee -a "$RUN_LOG"; exit 1; }
done
echo "✅ Case setup scripts complete." | tee -a "$RUN_LOG"

echo "📏 Scaling merged STL..." | tee -a "$RUN_LOG"
apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
  /bin/bash -c "${OPENFOAM_ENV} && cd /workspace/${CASE_DIR_REL_TO_PROJECT_ROOT} && \
    surfaceTransformPoints -scale \"(0.001 0.001 0.001)\" \
      constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
      constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl" \
  2>&1 | tee -a "$RUN_LOG"
echo "✅ Geometry scaled." | tee -a "$RUN_LOG"

run_step "Running blockMesh" "blockMesh" "${MESH_LOG}"
run_step "Running surfaceFeatureExtract" "surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"
run_step "Running snappyHexMesh" "snappyHexMesh -overwrite" "${SNAPPY_LOG}"

echo "🔢 Setting initial conditions via 0.py..." | tee -a "$RUN_LOG"
apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
  "$PYTHON_VENV" "/workspace/src/scripts/OpenFOAM/0.py" \
  --configDir "/workspace/${CONFIG_DIR_REL}" \
  2>&1 | tee -a "$RUN_LOG" || { echo "❌ 0.py failed." | tee -a "$RUN_LOG"; exit 1; }
echo "✅ Initial conditions set." | tee -a "$RUN_LOG"

run_step "Running simpleFoam" "simpleFoam" "${SOLVER_LOG}"

echo "📊 Post-processing (foamToVTK & paraFoam)..." | tee -a "$RUN_LOG"
apptainer exec -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" \
  /bin/bash -c "${OPENFOAM_ENV} && cd /workspace/${CASE_DIR_REL_TO_PROJECT_ROOT} && foamToVTK && paraFoam" \
  2>&1 | tee -a "$RUN_LOG"

echo "🎉 All done! Logs are in ${LOG_DIR}" | tee -a "$RUN_LOG"
