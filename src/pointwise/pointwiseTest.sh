#!/bin/bash

# === CONFIGURABLE VARIABLES ===
POINTWISE_DIR="/apps2/software/pointwise/2024.2.1/linux_x86_64"
SCRIPT_NAME="meshing.tcl"
TCL_PATH="$POINTWISE_DIR/lib/pointwise.tcl"

# Add Pointwise bin directory to LD_LIBRARY_PATH for shared libs
export LD_LIBRARY_PATH="$POINTWISE_DIR/bin:$LD_LIBRARY_PATH"

echo "[INFO] Using Pointwise at: $POINTWISE_DIR"
echo "[INFO] LD_LIBRARY_PATH is: $LD_LIBRARY_PATH"

# === STEP 2: Run the script with Pointwise in batch mode ===
"$POINTWISE_DIR/bin/pointwise" -b "$SCRIPT_NAME" > pointwise_run.log 2>&1

# === STEP 3: Check result ===
if grep -q "Geometry loaded" pointwise_run.log; then
    echo "[SUCCESS] Script ran and geometry loaded."
else
    echo "[WARNING] Check log for errors:"
    tail -n 10 pointwise_run.log
fi

