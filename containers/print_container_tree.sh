#!/bin/bash

SIF="/mnt/d/IRPOpenFOAM/CFD_IRP_McLaren_2024-2025/containers/openfoam_dev_2406.sif"
OUTPUT="/mnt/d/IRPOpenFOAM/CFD_IRP_McLaren_2024-2025/containers/container_tree.txt"

echo "[INFO] Printing directory structure inside the container: $SIF"
echo "[INFO] Output will be saved to: $OUTPUT"

apptainer exec "$SIF" bash -c '
  find / -maxdepth 3 2>/dev/null | sort
' > "$OUTPUT"

echo "[SUCCESS] Directory structure saved to $OUTPUT"
