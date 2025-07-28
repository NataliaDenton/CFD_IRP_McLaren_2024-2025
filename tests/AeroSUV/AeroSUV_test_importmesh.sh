#!/bin/bash
set -eo pipefail

# ---- CONFIGURATION ----
CASE_DIR="../src/Openfoam/AeroSUV_mergedGeom_case"
LOG_DIR="log"
MESH_LOG="${LOG_DIR}/blockMesh.log"
SNAPPY_LOG="${LOG_DIR}/snappyHexMesh.log"
POTENTIAL_LOG="${LOG_DIR}/potentialFoam.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"

# Calculate the absolute path to the project root.
# This assumes the script is run from the 'tests' directory,
# and the project root is two directories up (e.g., AHW/IRPOpenFOAM)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Path to OpenFOAM container, defined relative to the PROJECT_ROOT.
# This makes its location independent of the script's current working directory.
CONTAINER_RELATIVE="CFD_IRP_McLaren_2024-2025/containers/openfoam_python.sif"

# Function to run OpenFOAM commands inside the container.
# It binds the entire project root into the container at /project,
# and then changes the current directory inside the container to match the host's current working directory.
# OF() {
#     local cmd="$*" # The command string passed to the function
#     local current_host_dir=$(pwd) # Get the current absolute path on the host

#     singularity exec \
#         --bind "$PROJECT_ROOT":/project \
#         "${PROJECT_ROOT}/${CONTAINER_RELATIVE}" bash -c " # Use the full path for the container here
#             source /opt/openfoam2312/etc/bashrc &&
#             # Calculate the path of the current host directory relative to the project root.
#             # This allows us to cd into the correct location inside the container.
#             local relative_path_to_current_host_dir=\${current_host_dir#\$PROJECT_ROOT/}
#             cd /project/\${relative_path_to_current_host_dir} || {
#                 echo \"Error: Failed to change directory inside container to /project/\${relative_path_to_current_host_dir}\" >&2
#                 exit 1
#             } &&
#             # Execute the command
#             \$cmd
#         "
# }
#Temporary of fnction
# Function to run OpenFOAM commands inside the container.
OF() {
    local cmd="$*" # The command string passed to the function
    local current_host_dir=$(pwd) # Get the current absolute path on the host

    singularity exec \
        --bind "$PROJECT_ROOT":/project \
        "${PROJECT_ROOT}/${CONTAINER_RELATIVE}" bash -c "
            # Try to time just the source command
            time source /opt/openfoam2312/etc/bashrc &&
            echo \"OpenFOAM env sourced successfully and took a while!\" &&
            # The actual command (like python3 ...) will not run for this test
            echo \"Debug: Command was: \$cmd\"
        "
}




# ---- FUNCTIONS (retained from your original script) ----
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
    eval "$command" > "$log_file" 2>&1
    echo "✅ Finished: $description"
}

# ---- MAIN SCRIPT ----
echo "🔧 Moving to case directory: $CASE_DIR"
# Change directory on the host system to the case directory
cd "$CASE_DIR" || { echo "Error: Failed to change to case directory $CASE_DIR" >&2; exit 1; }
echo "✅ Finished moving to case directory"

echo "🧼 Cleaning old mesh and logs..."
rm -rf constant/polyMesh processor* postProcessing "${LOG_DIR}" 2>/dev/null || true
mkdir -p "${LOG_DIR}"
echo "✅ Finished cleaning mesh and logs"

echo "📦 Generating openfoam mesh scripts..."

echo "🔍 Detecting input mesh type..."
INPUT_DIR="constant/triSurface" # This path is relative to the current CWD (AeroSUV_mergedGeom_case)

# Call the detect_inputmesh_type.py script using the OF function.
# The path to the Python script (../../../src/scripts/Mesh/detect_inputmesh_type.py)
# is relative to the container's current working directory (which matches the host's)
# and should now correctly resolve within the /project bind-mount.
FILE_TYPE=$(OF python3 ../../../src/scripts/Mesh/detect_inputmesh_type.py "$INPUT_DIR")
echo "📁 Detected file type: $FILE_TYPE"
echo "✅ Finished mesh type detection"

if [[ "$FILE_TYPE" == "msh" ]]; then
    echo "🔄 Converting .msh to OpenFOAM..."
    MSH_FILE=$(find "$INPUT_DIR" -name "*.msh" | head -n 1)
    OF gmshToFoam "$MSH_FILE"
    echo "✅ Finished gmshToFoam"

elif [[ "$FILE_TYPE" == "cgns" ]]; then
    echo "🔄 Converting .cgns to OpenFOAM..."
    CGNS_FILE=$(find "$INPUT_DIR" -name "*.cgns" | head -n 1)
    OF cgnsToFoam "$CGNS_FILE"
    echo "✅ Finished cgnsToFoam"

elif [[ "$FILE_TYPE" == "h5" ]]; then
    echo "🔄 Converting .h5 to OpenFOAM..."
    # Note: Corrected variable name from $h5_FILE to $H5_FILE assuming common convention.
    # If the find command results in a different variable, ensure consistency.
    H5_FILE=$(find "$INPUT_DIR" -name "*.h5" | head -n 1)
    OF fluentMeshToFoam "$H5_FILE"
    echo "✅ Finished fluentMeshToFoam"

elif [[ "$FILE_TYPE" == "stl" ]]; then
    echo "📦 Detected STL geometry. Proceeding with full snappyHexMesh pipeline."
else
    echo "❌ Unsupported or unknown file type in $INPUT_DIR"
    exit 1
fi

check_file_exists "system/blockMeshDict"
check_file_exists "system/snappyHexMeshDict"
check_file_exists "system/controlDict"
check_directory_exists "constant/triSurface"
echo "✅ Finished basic file sanity checks"

if [[ "$FILE_TYPE" == "stl" ]]; then
    # Ensure all Python script calls are now using the OF function
    OF python3 ../../../src/scripts/Geometry/mergeGeometry.py || {
        echo "❌ Python script mergeGeometry.py failed"
        exit 1
    }
    echo "✅ Finished mergeGeometry.py"

    OF surfaceTransformPoints \
        -scale "(0.001 0.001 0.001)" \
        constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
        constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl
    echo "✅ Finished surfaceTransformPoints scaling"

    OF python3 ../../../src/scripts/OpenFOAM/meshGeneration.py || {
        echo "❌ Python script meshGeneration.py failed"
        exit 1
    }
    echo "✅ Finished meshGeneration.py"

    OF python3 ../../../src/scripts/OpenFOAM/constant.py || {
        echo "❌ Python script constant.py failed"
        exit 1
    }
    echo "✅ Finished constant.py"

    OF python3 ../../../src/scripts/OpenFOAM/system.py || {
        echo "❌ Python script system.py failed"
        exit 1
    }
    echo "✅ Finished system.py"

    run_step "Running blockMesh" "OF blockMesh" "$MESH_LOG"
    run_step "Running surfaceFeatureExtract" "OF surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"
    run_step "Running snappyHexMesh" "OF snappyHexMesh -overwrite" "$SNAPPY_LOG"
fi

# Ensure this last Python script call is also using the OF function
OF python3 ../../../src/scripts/OpenFOAM/0.py || {
  echo "❌ Python script 0.py failed"
  exit 1
}
echo "✅ Finished 0.py script for initial conditions"

run_step "Running simpleFoam" "OF simpleFoam" "$SOLVER_LOG"

echo "📤 Converting result to VTK format..."
OF foamToVTK
echo "✅ Finished foamToVTK"

echo "📊 Launching ParaView (if available)..."
if OF which paraFoam &> /dev/null; then
    OF paraFoam
    echo "✅ paraFoam launched"
else
    echo "⚠️ 'paraFoam' not available in container."
fi

echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"