#!/bin/bash

# === CONFIG ===
DEF_FILE="openfoam-dev.def"
TMP_DEF="/tmp/$DEF_FILE"
SIF_NAME="openfoam_dev_2406.sif"
TMP_SIF="/tmp/$SIF_NAME"
FINAL_DIR="$HOME/containers/openfoam"
FINAL_SIF="$FINAL_DIR/$SIF_NAME"
LOG_FILE="build_openfoam.log"

echo "[INFO] Cleaning up old temporary files..."
sudo rm -f "$TMP_SIF" "$TMP_DEF"

echo "[INFO] Copying definition file to /tmp..."
cp "$DEF_FILE" "$TMP_DEF"

echo "[INFO] Starting container build..."
sudo apptainer build --fakeroot "$TMP_SIF" "$TMP_DEF" | tee "$LOG_FILE"

if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    echo "[ERROR] Build failed. Check $LOG_FILE for details."
    exit 1
fi

if [ ! -d "$FINAL_DIR" ]; then
    echo "[INFO] Creating final directory: $FINAL_DIR"
    mkdir -p "$FINAL_DIR"
fi

echo "[INFO] Moving SIF to final directory..."
sudo cp "$TMP_SIF" "$FINAL_SIF"
sudo chown "$USER:$USER" "$FINAL_SIF"

echo "[SUCCESS] OpenFOAM container build complete!"
echo "         → $FINAL_SIF"

cp "$FINAL_SIF" /mnt/d/IRPOpenFOAM/CFD_IRP_McLaren_2024-2025/containers/
echo "[SUCCESS] OPENFOAM container copied back to parent directory"

echo "[INFO] You can shell into the container with:"
echo "  apptainer shell \"$FINAL_SIF\""
