import pytest
from pathlib import Path
import yaml
import shutil
import sys

# Ensure functions path is available
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts
import suppl_fcts


@pytest.fixture(scope="session")
def aeroSUV_configs():
    """Load AeroSUV configs from real YAMLs."""
    config_dir = Path(__file__).resolve().parent / "../../../configs/AeroSUV"
    user_config_file = config_dir / "userConfig.yaml"
    advanced_config_file = config_dir / "advancedConfig.yaml"

    ConfigU = IO_fcts.load_config(user_config_file)
    ConfigA = IO_fcts.load_config(advanced_config_file)
    return ConfigU, ConfigA


@pytest.fixture
def temp_case_dir(tmp_path):
    """Create a dummy OpenFOAM case structure for population."""
    case_dir = tmp_path / "case"
    (case_dir / "constant").mkdir(parents=True, exist_ok=True)

    # Persist files for debugging
    persistent_dir = Path.cwd() / "pytest_output_populators"
    if persistent_dir.exists():
        shutil.rmtree(persistent_dir)
    shutil.copytree(case_dir, persistent_dir)

    print(f"\n=== Debug case directory at: {persistent_dir} ===")
    return case_dir


def test_populate_transport_and_turbulence(aeroSUV_configs, temp_case_dir):
    """Test that transportProperties and turbulenceProperties are correctly created."""
    ConfigU, ConfigA = aeroSUV_configs

    # Provide CASE_DIR to populator
    CASE_DIR = str(temp_case_dir)

    # Call the functions directly (equivalent to script behavior)
    populator_fcts.populate_transportProperties(ConfigU, ConfigA, CASE_DIR)
    populator_fcts.populate_turbulenceProperties(ConfigU, ConfigA, CASE_DIR)

    # Check files exist
    transport_file = temp_case_dir / "constant" / "transportProperties"
    turbulence_file = temp_case_dir / "constant" / "turbulenceProperties"

    assert transport_file.exists(), "transportProperties file not created!"
    assert turbulence_file.exists(), "turbulenceProperties file not created!"

    for file in [transport_file, turbulence_file]:
        content = file.read_text()
        assert "FoamFile" in content, f"{file.name} missing FoamFile header!"
        assert "object" in content, f"{file.name} missing object keyword!"

        if file.name == "transportProperties":
            assert "transportModel" in content, f"{file.name} missing transportModel!"
            assert "nu" in content, f"{file.name} missing nu!"
        elif file.name == "turbulenceProperties":
            assert "simulationType" in content or "turbulence" in content, (
                f"{file.name} missing simulationType or turbulence keyword!"
            )

    print("\n=== Generated Files ===")
    for file in [transport_file, turbulence_file]:
        print(f"\n--- {file.name} ---\n{file.read_text()}\n")

