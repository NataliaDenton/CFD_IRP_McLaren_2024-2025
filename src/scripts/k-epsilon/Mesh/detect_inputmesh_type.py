# detect_inputmesh_type.py

import sys
import os
from pathlib import Path

# Dynamically add functions path to Python path
FUNCTIONS_PATH = Path(__file__).resolve().parent.parent.parent / "functions"
sys.path.append(str(FUNCTIONS_PATH))

from IO_fcts import detect_mesh_type

if len(sys.argv) != 2:
    print("Usage: python detect_inputmesh_type.py <input_dir>")
    sys.exit(1)

input_dir = sys.argv[1]
file_type = detect_mesh_type(input_dir)
print(file_type)
