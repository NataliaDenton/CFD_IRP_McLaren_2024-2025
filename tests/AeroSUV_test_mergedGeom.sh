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


echo "🔍 Detecting input mesh type..."
INPUT_DIR="constant/triSurface"
FILE_TYPE=$(singularity exec ../../../containers/container.sif python3 -c \
"from detect_inputmesh_type import detect_mesh_type; print(detect_mesh_type('${INPUT_DIR}'))")

echo "📁 Detected file type: $FILE_TYPE"

if [[ "$FILE_TYPE" == "msh" ]]; then
    echo "🔄 Converting .msh to OpenFOAM..."
    MSH_FILE=$(find "$INPUT_DIR" -name "*.msh" | head -n 1)
    gmshToFoam "$MSH_FILE"

elif [[ "$FILE_TYPE" == "cgns" ]]; then
    echo "🔄 Converting .cgns to OpenFOAM..."
    CGNS_FILE=$(find "$INPUT_DIR" -name "*.cgns" | head -n 1)
    cgnsToFoam "$CGNS_FILE"

elif [[ "$FILE_TYPE" == "stl" ]]; then
    echo "📦 Detected STL geometry. Proceeding with full snappyHexMesh pipeline."

else
    echo "❌ Unsupported or unknown file type in $INPUT_DIR"
    exit 1
fi



# Sanity checks
check_file_exists "system/blockMeshDict"
check_file_exists "system/snappyHexMeshDict"
check_file_exists "system/controlDict"
check_directory_exists "constant/triSurface"



if [[ "$FILE_TYPE" == "stl" ]]; then
  singularity exec ../../../containers/container.sif python3 ../../../src/scripts/Geometry/mergeGeometry.py || {
    echo "❌ Python script mergeGeometry.py failed"
    exit 1
  }

  surfaceTransformPoints \
    -scale "(0.001 0.001 0.001)" \
    constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl \
    constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl

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

  # Mesh Generation Steps for STL only
  run_step "Running blockMesh" "blockMesh" "${MESH_LOG}"
  run_step "Running surfaceFeatureExtract" "surfaceFeatureExtract" "${LOG_DIR}/surfaceFeatureExtract.log"
  run_step "Running snappyHexMesh" "snappyHexMesh -overwrite" "${SNAPPY_LOG}"
fi



# running the initial conditions creator 
singularity exec ../../../containers/container.sif python3 ../../../src/scripts/OpenFOAM/0.py || {
  echo "❌ Python script 0.py failed"
  exit 1
}
# Optional: potentialFoam initialization
#run_step "Running potentialFoam" "potentialFoam" "${POTENTIAL_LOG}"

# Main Solver
run_step "Running simpleFoam" "simpleFoam" "${SOLVER_LOG}"

foamToVTK

paraFoam


echo "🎉 Simulation complete! Logs saved in '${LOG_DIR}'"



