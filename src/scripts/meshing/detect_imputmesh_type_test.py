import pytest
from pathlib import Path
import tempfile
import shutil
import sys
import os

# Dynamically add functions path to Python path
FUNCTIONS_PATH = Path(__file__).resolve().parent.parent.parent / "functions"
sys.path.append(str(FUNCTIONS_PATH))

from IO_fcts import detect_mesh_type
@pytest.fixture
def tmp_mesh_dir():
    # Create a temporary directory for mesh files
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

def create_dummy_file(directory, filename):
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        f.write("dummy content")
    return path


def test_detect_mesh_type_with_supported_extensions(tmp_path):
    # For each supported extension, create a dummy file and test detection
    extensions = {
        ".msh": "msh",
        ".cgns": "cgns",
        ".stl": "stl",
        ".h5": "h5"
    }
    for ext, expected_type in extensions.items():
        # Clear directory between tests
        for f in tmp_path.iterdir():
            f.unlink()
        create_dummy_file(tmp_path, f"mesh{ext}")
        detected = detect_mesh_type(str(tmp_path))
        assert detected == expected_type, f"For extension {ext}, expected {expected_type}, got {detected}"

def test_detect_mesh_type_with_no_supported_files(tmp_path):
    # Create unsupported file
    create_dummy_file(tmp_path, "file.txt")
    detected = detect_mesh_type(str(tmp_path))
    assert detected == "unknown"

def test_cli_usage_and_exit(monkeypatch):
    import detect_inputmesh_type
    import sys

    # Save original argv
    original_argv = sys.argv[:]

    # Test with incorrect args
    monkeypatch.setattr(sys, 'argv', ['detect_inputmesh_type.py'])
    with pytest.raises(SystemExit) as e:
        detect_inputmesh_type.main()
    assert e.value.code == 1

    # Restore argv
    sys.argv = original_argv
