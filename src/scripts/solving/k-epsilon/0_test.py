import pytest
from pathlib import Path
import yaml
import sys

# Ensure functions path is accessible
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts
import suppl_fcts


@pytest.fixture(scope="session")
def aeroSUV_configs():
    """Load real AeroSUV configs as dicts."""
    config_dir = Path(__file__).resolve().parent / "../../../configs/AeroSUV"
    user_config_file = config_dir / "userConfig.yaml"
    advanced_config_file = config_dir / "advancedConfig.yaml"

    with open(user_config_file, "r") as f:
        configU = yaml.safe_load(f)
    with open(advanced_config_file, "r") as f:
        configA = yaml.safe_load(f)

    return configU, configA


@pytest.fixture
def temp_case_dir(tmp_path):
    """Create a temporary OpenFOAM case directory structure with dummy boundary."""
    case_dir = tmp_path / "case"
    boundary_file = case_dir / "constant" / "polyMesh" / "boundary"
    boundary_file.parent.mkdir(parents=True, exist_ok=True)

    # Minimal dummy boundary file, parseable by suppl_fcts
    boundary_file.write_text(
        "2\n(\ninlet\n{\n type patch;\n nFaces 20;\n startFace 0;\n}\n\n"
        "outlet\n{\n type patch;\n nFaces 20;\n startFace 20;\n}\n)"
    )

    return case_dir


def test_write_all_fields_real_configs(aeroSUV_configs, temp_case_dir):
    configU, configA = aeroSUV_configs

    # Determine fields to be generated
    user_fields = set(configU.get("fields", []))
    adv_fields = set(configA.get("fields", []))
    common_fields = user_fields & adv_fields
    print("\n=== EXPECTED FIELDS ===")
    print(f"User fields: {user_fields}")
    print(f"Advanced fields: {adv_fields}")
    print(f"Common fields: {common_fields}")
    assert common_fields, "No common fields found in AeroSUV configs!"

    # Run the actual function
    populator_fcts.write_all_fields(configU, configA, str(temp_case_dir))

    # Check all generated files in the 0/ directory
    zero_dir = temp_case_dir / "0"
    all_generated = list(zero_dir.glob("*"))
    print("\n=== GENERATED FILES ===")
    for f in all_generated:
        print(f"- {f.name}")

    # Ensure all expected field files exist
    for field in common_fields:
        field_file = zero_dir / field
        assert field_file.exists(), f"Expected field file {field} was not created."
        print(f"\n--- Contents of {field_file.name} ---")
        print("\n".join(field_file.read_text().splitlines()[:10]))  # print first 10 lines

        content = field_file.read_text()
        assert f"object      {field};" in content
        assert "FoamFile" in content
        assert "internalField" in content
        assert "boundaryField" in content


def test_write_field_file_individual(aeroSUV_configs, temp_case_dir):
    configU, configA = aeroSUV_configs
    common_fields = list(set(configU.get("fields", [])) & set(configA.get("fields", [])))
    assert common_fields, "No common fields found in AeroSUV configs!"

    field_name = common_fields[0]
    populator_fcts.write_field_file(field_name, configU, configA, str(temp_case_dir))

    field_file = temp_case_dir / "0" / field_name
    assert field_file.exists()

    print(f"\n--- Single field file created: {field_file.name} ---")
    print("\n".join(field_file.read_text().splitlines()[:10]))

    content = field_file.read_text()
    assert f"object      {field_name};" in content
    assert "internalField" in content
    assert "boundaryField" in content

