import sys
from pathlib import Path

# Add functions path dynamically (same as before)
FUNCTIONS_PATH = Path(__file__).resolve().parent.parent.parent / "functions"
sys.path.append(str(FUNCTIONS_PATH))

from IO_fcts import detect_mesh_type

def main():
    if len(sys.argv) != 2:
        print("Usage: python detect_inputmesh_type.py <input_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    file_type = detect_mesh_type(input_dir)
    print(file_type)

if __name__ == "__main__":
    main()

