#!/bin/bash

# === CONFIG ===
DEF_FILE="openfoam-dev.def"
SIF_NAME="openfoam_dev_2406.sif"
LOG_FILE="build_openfoam.log"
CHECK_LOG="sanity_check.log"
TREE_SCRIPT="./print_container_tree.sh"

echo "[INFO] Starting container build..."
apptainer build --fakeroot "$SIF_NAME" "$DEF_FILE" | tee "$LOG_FILE"

if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    echo "[ERROR] Build failed. Check $LOG_FILE for details."
    exit 1
fi

echo "[SUCCESS] OpenFOAM container build complete!"
echo "         → $(pwd)/$SIF_NAME"
echo "[INFO] You can shell into the container with:"
echo "  apptainer shell \"$(pwd)/$SIF_NAME\""

# === Sanity checks ===
echo "[INFO] Running sanity checks inside the container..."
{
    echo "=== OpenFOAM container sanity check ==="
    date

    echo "🔹 Sourcing OpenFOAM environment..."
    source /usr/lib/openfoam/openfoam2406/etc/bashrc

    echo "🔹 Checking OpenFOAM bin path..."
    ls -l /usr/lib/openfoam/openfoam2406/platforms/linux64GccDPInt32Opt/bin

    echo "🔹 Checking OpenFOAM lib path..."
    ls -l /usr/lib/openfoam/openfoam2406/platforms/linux64GccDPInt32Opt/lib

    echo "🔹 Testing blockMesh..."
    which blockMesh
    blockMesh -help || echo "❌ blockMesh failed"

    echo "🔹 Testing simpleFoam..."
    which simpleFoam
    simpleFoam -help || echo "❌ simpleFoam failed"

    echo "🔹 Testing fluentMeshToFoam..."
    which fluentMeshToFoam
    fluentMeshToFoam -help || echo "❌ fluentMeshToFoam failed"

    echo "🔹 Testing cgnsToFoam..."
    which cgnsToFoam
    cgnsToFoam -help || echo "❌ cgnsToFoam failed"

    echo "🔹 Printing LD_LIBRARY_PATH..."
    echo $LD_LIBRARY_PATH

    echo "=== End of sanity check ==="
} | apptainer exec "$SIF_NAME" bash -s | tee "$CHECK_LOG"

echo "[INFO] Sanity check output saved to $CHECK_LOG"

# === Run container tree script ===
if [ -x "$TREE_SCRIPT" ]; then
    echo "[INFO] Running container tree script..."
    "$TREE_SCRIPT" "$SIF_NAME"
else
    echo "[WARNING] Container tree script not found or not executable: $TREE_SCRIPT"
fi

