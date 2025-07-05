#!/bin/bash

# === CONFIG ===
DEF_FILE="openfoam-dev.def"
SIF_NAME="openfoam_dev_2406.sif"
LOG_FILE="build_openfoam.log"
CHECK_LOG="sanity_check.log"
TREE_SCRIPT="./print_container_tree.sh" # Assuming this script exists and is executable

# Define the absolute path to the bashrc inside the container
# Based on previous troubleshooting, this is the correct path.
OPENFOAM_BASHRC="/root/OpenFOAM/OpenFOAM-v2406/etc/bashrc"

echo "[INFO] Starting container build..."
# Use exec to replace the current shell with the tee command, ensuring all output goes to log.
# This helps capture build output even if the build process has its own stderr.
apptainer build --fakeroot "$SIF_NAME" "$DEF_FILE" 2>&1 | tee "$LOG_FILE"

if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    echo "[ERROR] Build failed. Check $LOG_FILE for details."
    exit 1
fi

echo "[SUCCESS] OpenFOAM container build complete!"
echo "          → $(pwd)/$SIF_NAME"
echo "[INFO] You can shell into the container with:"
echo "  apptainer exec \"$(pwd)/$SIF_NAME\" bash" # Added 'bash' for a cleaner interactive shell

# === Sanity checks ===
echo "[INFO] Running sanity checks inside the container..."
{
    echo "=== OpenFOAM container sanity check ==="
    date

    echo "🔹 Checking existence of OpenFOAM bashrc: ${OPENFOAM_BASHRC}"
    ls -l "${OPENFOAM_BASHRC}" || echo "❌ bashrc not found at ${OPENFOAM_BASHRC}"

    echo "🔹 Sourcing OpenFOAM environment inside container..."
    # Source the bashrc. Use 'set +e' to prevent script exit if sourcing itself errors
    # and then immediately 'set -e' to re-enable strict error checking for subsequent commands.
    set +e
    source "${OPENFOAM_BASHRC}" || echo "❌ Failed to source ${OPENFOAM_BASHRC}"
    set -e

    echo "🔹 Displaying PATH after sourcing OpenFOAM environment:"
    echo "$PATH"

    echo "🔹 Checking OpenFOAM bin path..."
    ls -l /root/OpenFOAM/OpenFOAM-v2406/platforms/linux64GccDPInt32Opt/bin || echo "❌ Bin directory not found or accessible"

    echo "🔹 Checking OpenFOAM lib path..."
    ls -l /root/OpenFOAM/OpenFOAM-v2406/platforms/linux64GccDPInt32Opt/lib || echo "❌ Lib directory not found or accessible"

    # Define tools to check
    TOOLS_TO_CHECK=( blockMesh simpleFoam fluentMeshToFoam cgnsToFoam )

    for tool in "${TOOLS_TO_CHECK[@]}"; do
        echo "🔹 Testing ${tool}..."
        # Use 'command -v' to find if the tool is in PATH
        # Then attempt to run with -help
        if command -v "${tool}" >/dev/null 2>&1; then
            echo "  ✔ ${tool} found at $(command -v "${tool}")"
            "${tool}" -help >/dev/null 2>&1 \
                && echo "  ✔ ${tool} -help OK" \
                || echo "  ❌ ${tool} -help failed (tool might be present but not fully functional)"
        else
            echo "  ❌ ${tool} not found in PATH"
            # Exit with error if a critical tool like blockMesh or simpleFoam is missing
            if [[ "$tool" == "blockMesh" || "$tool" == "simpleFoam" ]]; then
                echo "Critical tool ${tool} missing. Exiting sanity check with error."
                exit 1
            fi
        fi
    done

    echo "🔹 Printing LD_LIBRARY_PATH..."
    echo "$LD_LIBRARY_PATH"

    echo "=== End of sanity check ==="
} | apptainer exec "$SIF_NAME" bash -l -s | tee "$CHECK_LOG" # Use -l for login shell, -s to read from stdin

if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    echo "[ERROR] Sanity checks failed. Check $CHECK_LOG for details."
    exit 1
else
    echo "[SUCCESS] Sanity checks passed!"
fi

# === Run container tree script ===
# Ensure the tree script is executable on the host if it's being called directly.
if [ -x "$TREE_SCRIPT" ]; then
    echo "[INFO] Running container tree script..."
    "$TREE_SCRIPT" "$SIF_NAME" # Pass SIF name to the tree script
else
    echo "[WARNING] Container tree script not found or not executable: $TREE_SCRIPT"
fi

