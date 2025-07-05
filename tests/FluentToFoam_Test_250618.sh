#!/bin/bash
set -eo pipefail

# === CONFIG ===
PROJECT_ROOT=$(readlink -f "$(dirname "$0")/..")
CASE_DIR_REL="src/Openfoam/FluentConvertedCase"
CASE_DIR="${PROJECT_ROOT}/${CASE_DIR_REL}"
CONTAINER="${PROJECT_ROOT}/containers/openfoam_dev_2406.sif"
MESH_FILE_REL="src/Openfoam/AeroSUV_mergedGeom_case/constant/triSurface/Cume_ICEM.msh"
MESH_FILE="${PROJECT_ROOT}/${MESH_FILE_REL}"

LOG_DIR="${CASE_DIR}/log"
VTK_OUT="${CASE_DIR}/VTK_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR" "$VTK_OUT"

CONVERT_LOG="${LOG_DIR}/fluent3DMeshToFoam.log"
SOLVER_LOG="${LOG_DIR}/simpleFoam.log"
VTK_LOG="${LOG_DIR}/foamToVTK.log"
CHECK_LOG="${LOG_DIR}/sanity_check.log"

# CORRECTED: Use the path confirmed by your manual debugging
OPENFOAM_ENV="source /root/OpenFOAM/OpenFOAM-v2406/etc/bashrc"
# CORRECTED: Use the path from container_tree.txt
PYTHON_VENV="/root/OpenFOAM/pyenv/bin/python"

echo "🚀 Starting Fluent-to-Foam pipeline" | tee "$CHECK_LOG"
[[ -f "$MESH_FILE" ]] || { echo "❌ Fluent mesh file not found: $MESH_FILE" | tee -a "$CHECK_LOG"; exit 1; }
echo "✅ Fluent mesh file found: $MESH_FILE" | tee -a "$CHECK_LOG"

# === Line ending conversion ===
if command -v dos2unix &>/dev/null; then
    echo "🔹 Converting mesh file line endings using dos2unix..." | tee -a "$CHECK_LOG"
    dos2unix "$MESH_FILE" 2>&1 | tee -a "$CHECK_LOG"
    echo "✅ dos2unix conversion complete." | tee -a "$CHECK_LOG"
else
    echo "⚠️ dos2unix not found — skipping line ending conversion!" | tee -a "$CHECK_LOG"
fi

# === Run inside container ===
apptainer shell -B "${PROJECT_ROOT}:/workspace" "$CONTAINER" <<EOF
${OPENFOAM_ENV}
cd /workspace/${CASE_DIR_REL} || exit 1

echo "🔹 Checking OpenFOAM tools..."
for tool in fluent3DMeshToFoam simpleFoam foamToVTK; do
  if ! command -v \$tool &>/dev/null; then
    echo "❌ \$tool missing!" | tee -a log/sanity_check.log
    exit 1
  fi
done

echo "📦 Converting Fluent mesh to OpenFOAM format..."
rm -rf constant/polyMesh
fluent3DMeshToFoam -scale 0.001 /workspace/${MESH_FILE_REL} \
#fluent3DMeshToFoam -scale 0.001 -writeZones -writeSets /workspace/${MESH_FILE_REL} \
  2>&1 | tee -a log/fluent3DMeshToFoam.log
echo "✅ Mesh conversion done."

if [[ ! -d constant/polyMesh ]]; then
  echo "❌ polyMesh missing after conversion!" | tee -a log/sanity_check.log
  exit 1
fi

echo "📝 Setting up 0/ fields if missing..."
mkdir -p 0
for f in U p; do
  if [[ ! -f 0/\$f ]]; then
    echo "Creating placeholder 0/\$f"
    cp -r \$FOAM_TUTORIALS/incompressible/simpleFoam/pitzDaily/0/\$f 0/\$f
  fi
done

if [[ ! -f system/controlDict ]]; then
  echo "⚠️ No controlDict — creating minimal setup"
  mkdir -p system
  cat > system/controlDict <<EOC
FoamFile {
    version 2.0;
    format ascii;
    class dictionary;
    object controlDict;
}
application simpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 10;
deltaT 1;
writeControl timeStep;
writeInterval 5;
EOC
fi

if [[ ! -f system/fvSchemes ]]; then
  cat > system/fvSchemes <<EOC
FoamFile {
    version 2.0;
    format ascii;
    class dictionary;
    object fvSchemes;
}
divSchemes { default none; div(phi,U) Gauss upwind; }
laplacianSchemes { default Gauss linear corrected; }
EOC
fi

if [[ ! -f system/fvSolution ]]; then
  cat > system/fvSolution <<EOC
FoamFile {
    version 2.0;
    format ascii;
    class dictionary;
    object fvSolution;
}
solvers { p { solver PCG; tolerance 1e-6; relTol 0; } U { solver smoothSolver; tolerance 1e-5; relTol 0.1; } }
SIMPLE { nNonOrthogonalCorrectors 0; }
EOC
fi

echo "🔹 Running simpleFoam..."
simpleFoam 2>&1 | tee -a log/simpleFoam.log
echo "✅ simpleFoam finished."

echo "🔹 Converting to VTK..."
foamToVTK -ascii -output /workspace/${CASE_DIR_REL}/VTK_OUT 2>&1 | tee -a log/foamToVTK.log
echo "✅ foamToVTK finished."
EOF

# === Organize output ===
mv "$CASE_DIR/VTK_OUT"/* "$VTK_OUT" || true
rmdir "$CASE_DIR/VTK_OUT" || true

echo "🎉 Pipeline complete!"
echo "✅ Logs: $LOG_DIR"
echo "✅ VTK output saved in: $VTK_OUT"

