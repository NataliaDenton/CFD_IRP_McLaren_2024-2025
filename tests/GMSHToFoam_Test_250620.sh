#!/bin/bash
set -eo pipefail

# === CONFIG ===
PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_DIR_REL="src/Openfoam/GmshConvertedCase"
CASE_DIR="${PROJECT_ROOT}/${CASE_DIR_REL}"
CONTAINER="${PROJECT_ROOT}/containers/openfoam_dev_2406.sif"
MESH_FILE_REL="src/Openfoam/AeroSUV_mergedGeom_case/constant/triSurface/Box_1m.msh"
MESH_FILE="${PROJECT_ROOT}/${MESH_FILE_REL}"

SRC_CASE_REL="src/Openfoam/AeroSUV_mergedGeom_case"
SRC_CASE="${PROJECT_ROOT}/${SRC_CASE_REL}"

LOG_DIR="${CASE_DIR}/log"
VTK_OUT="${CASE_DIR}/VTK_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR" "$VTK_OUT" "$CASE_DIR"

# CORRECTED: Use the path confirmed by your manual debugging
OPENFOAM_ENV="source /root/OpenFOAM/OpenFOAM-v2406/etc/bashrc"
# CORRECTED: Use the path from container_tree.txt
PYTHON_VENV="/root/OpenFOAM/pyenv/bin/python"

echo "🚀 Starting Gmsh-to-Foam pipeline" | tee "$LOG_DIR/sanity_check.log"
[[ -f "$MESH_FILE" ]] || { echo "❌ Gmsh mesh file not found: $MESH_FILE" | tee -a "$LOG_DIR/sanity_check.log"; exit 1; }
echo "✅ Gmsh mesh file found: $MESH_FILE" | tee -a "$LOG_DIR/sanity_check.log"

# === Line ending conversion ===
if command -v dos2unix &>/dev/null; then
    echo "🔹 Converting mesh file line endings using dos2unix..." | tee -a "$LOG_DIR/sanity_check.log"
    dos2unix "$MESH_FILE" 2>&1 | tee -a "$LOG_DIR/sanity_check.log"
    echo "✅ dos2unix conversion complete." | tee -a "$LOG_DIR/sanity_check.log"
else
    echo "⚠️ dos2unix not found — skipping line ending conversion!" | tee -a "$LOG_DIR/sanity_check.log"
fi

# === Run inside container ===
apptainer shell -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" <<EOF
${OPENFOAM_ENV}
cd /workspace/${CASE_DIR_REL} || exit 1

echo "📂 Copying system and 0 directories from source case..."
cp -r /workspace/${SRC_CASE_REL}/system ./
cp -r /workspace/${SRC_CASE_REL}/0 ./

echo "🔹 Checking OpenFOAM tools..."
for tool in gmshToFoam simpleFoam foamToVTK; do
  if ! command -v \$tool &>/dev/null; then
    echo "❌ \$tool missing!" | tee -a log/sanity_check.log
    exit 1
  else
    echo "✅ \$tool available." | tee -a log/sanity_check.log
  fi
done

echo "📖 Dumping gmshToFoam help..."
gmshToFoam -help-full 2>&1 | tee -a log/gmshToFoam_help.log
echo "✅ Help output logged."

echo "📦 Converting Gmsh mesh to OpenFOAM format..."
rm -rf constant/polyMesh
gmshToFoam /workspace/${MESH_FILE_REL} 2>&1 | tee -a log/gmshToFoam.log
echo "✅ Mesh conversion done."

if [[ ! -d constant/polyMesh ]]; then
  echo "❌ polyMesh missing after conversion!" | tee -a log/sanity_check.log
  exit 1
fi

echo "🔹 Running simpleFoam..."
simpleFoam 2>&1 | tee -a log/simpleFoam.log
echo "✅ simpleFoam finished."

echo "🔹 Converting to VTK..."
foamToVTK -ascii 2>&1 | tee -a log/foamToVTK.log
echo "✅ foamToVTK finished."

EOF

# === Organize output ===
mv "$CASE_DIR/VTK"/* "$VTK_OUT" || true
rmdir "$CASE_DIR/VTK" || true

echo "🎉 Pipeline complete!"
echo "✅ Logs: $LOG_DIR"
echo "✅ VTK output saved in: $VTK_OUT"

