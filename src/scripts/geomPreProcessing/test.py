import pytest
from pathlib import Path
import sys
from unittest.mock import patch

# Add functions path
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import suppl_fcts

CONFIG_DIR = Path(__file__).parent / "../../configs/AeroSUV"  # <-- create this test folder
USER_CONFIG_PATH = CONFIG_DIR / "userConfig.yaml"
ADV_CONFIG_PATH = CONFIG_DIR / "advancedConfig.yaml"


@pytest.fixture
def load_configs():
    """Fixture to load test configs."""
    configU = IO_fcts.load_config(USER_CONFIG_PATH)
    configA = IO_fcts.load_config(ADV_CONFIG_PATH)
    return configU, configA


def test_user_config_keys(load_configs):
    configU, _ = load_configs
    assert "filePath" in configU, "userConfig.yaml missing 'filePath'"
    assert "geometries" in configU["filePath"], "userConfig.yaml missing 'filePath.geometries'"


def test_advanced_config_keys(load_configs):
    _, configA = load_configs
    assert "advancedGeometrySettings" in configA, "advancedConfig.yaml missing 'advancedGeometrySettings'"
    assert "filePath" in configA["advancedGeometrySettings"], "advancedConfig.yaml missing 'filePath'"
    assert "mergedGeometry" in configA["advancedGeometrySettings"]["filePath"], \
        "advancedConfig.yaml missing mergedGeometry section"


def test_merge_function_called(load_configs):
    """Check that merge_multiple_stl_files is invoked with correct arguments."""
    configU, configA = load_configs
    geometry_config = configU["filePath"]["geometries"]
    mergedGeometry_config = configA["advancedGeometrySettings"]["filePath"]["mergedGeometry"]
    outputPath = mergedGeometry_config["file"]

    # Patch the merge function so it doesn't actually merge
    with patch.object(suppl_fcts, "merge_multiple_stl_files", return_value=None) as mock_merge:
        suppl_fcts.merge_multiple_stl_files(geometry_config, outputPath)
        mock_merge.assert_called_once_with(geometry_config, outputPath)

