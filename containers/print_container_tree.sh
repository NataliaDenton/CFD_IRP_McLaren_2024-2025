#!/bin/bash

# === CONFIG ===
SIF="./openfoam_dev_2406.sif"
OUTPUT="./container_tree.txt"

echo "[INFO] Printing directory structure and binaries inside the container: $SIF"
echo "[INFO] Output will be saved to: $OUTPUT"

# Execute commands inside the container via apptainer exec.
# The commands are wrapped in a 'bash -c' block to ensure a single execution context.
apptainer exec "$SIF" bash -c '
  # Set environment for non-interactive locale/timezone to prevent prompts,
  # consistent with the container build and pipeline scripts.
  export TZ="UTC"
  export LANG="C.UTF-8"
  export LC_ALL="C.UTF-8"

  echo "=== General Directory Structure (maxdepth 3) ==="
  # Lists the general directory structure up to 3 levels deep.
  # Redirects stderr to /dev/null to suppress permission denied errors for system directories.
  find / -maxdepth 3 -print 2>/dev/null | sort

  echo ""
  echo "=== OpenFOAM Installation Structure (Recursive Listings) ==="
  # Recursively list contents of known OpenFOAM binary directories.
  # Shows permissions, owner, size, and timestamp for better inspection.

  echo "--- /root/OpenFOAM/OpenFOAM-v2406/bin/ ---"
  ls -lR /root/OpenFOAM/OpenFOAM-v2406/bin/ 2>/dev/null || echo "Directory not found or accessible: /root/OpenFOAM/OpenFOAM-v2406/bin/"

  echo ""
  echo "--- /root/OpenFOAM/OpenFOAM-v2406/platforms/linux64GccDPInt32Opt/bin/ ---"
  ls -lR /root/OpenFOAM/OpenFOAM-v2406/platforms/linux64GccDPInt32Opt/bin/ 2>/dev/null || echo "Directory not found or accessible: /root/OpenFOAM/OpenFOAM-v2406/platforms/linux64GccDPInt32Opt/bin/"

  echo ""
  echo "--- /root/OpenFOAM/OpenFOAM-v2406/wmake/ ---"
  ls -lR /root/OpenFOAM/OpenFOAM-v2406/wmake/ 2>/dev/null || echo "Directory not found or accessible: /root/OpenFOAM/OpenFOAM-v2406/wmake/"


  echo ""
  echo "=== Python Virtual Environment Binaries ==="
  echo "--- /root/OpenFOAM/pyenv/bin/ ---"
  ls -lR /root/OpenFOAM/pyenv/bin/ 2>/dev/null || echo "Directory not found or accessible: /root/OpenFOAM/pyenv/bin/"

  echo ""
  echo "=== All Executable Files within /root/OpenFOAM/ (Comprehensive Scan) ==="
  # Finds all regular files within the OpenFOAM installation directory that are executable.
  find /root/OpenFOAM -type f -executable -print 2>/dev/null | sort

  echo ""
  echo "=== All Executable Files within /usr/bin/ and /bin/ (Common System Binaries) ==="
  # Optionally, list common system binaries, though this might be extensive.
  find /usr/bin /bin -maxdepth 1 -type f -executable -print 2>/dev/null | sort

' > "$OUTPUT" # Redirect all output from the apptainer exec command to the OUTPUT file on the host.

echo "[SUCCESS] Directory structure and binary list saved to $OUTPUT"

