#!/bin/bash

# === CONFIG ===
DEF_FILE="openfoam-dev.def"
SIF_NAME="openfoam_dev_2406.sif"
LOG_FILE="build_openfoam.log"
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

# === Run container tree script ===
if [ -x "$TREE_SCRIPT" ]; then
    echo "[INFO] Running container tree script..."
    "$TREE_SCRIPT" "$SIF_NAME"
else
    echo "[WARNING] Container tree script not found or not executable: $TREE_SCRIPT"
fi

