#!/bin/bash

# Exit immediately on error
set -e

# Define names
DEF_FILE="Python_container.def"
SIF_FILE="container.sif"

# Build the container
echo "Building Apptainer container: $SIF_FILE from $DEF_FILE"
apptainer build "$SIF_FILE" "$DEF_FILE"

echo "Container build completed successfully."
