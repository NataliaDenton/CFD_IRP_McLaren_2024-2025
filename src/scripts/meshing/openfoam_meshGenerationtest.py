import sys
import pytest
from pathlib import Path

import argparse

FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts
import suppl_fcts


@pytest.fixture
def config_paths():
    # Provide your real config directory path here or copy the files into a test folder
    config_dir = Path(__file__).resolve().parent / "../../configs/AeroSUV"

    user_config_path = config_dir / "userConfig.yaml"
    advanced_config_path = config_dir / "advancedConfig.yaml"

    # Check that the config files actually exist for safety
    assert user_config_path.is_file(), f"{user_config_path} not found"
    assert advanced_config_path.is_file(), f"{advanced_config_path} not found"

    return user_config_path, advanced_config_path


def test_load_configs(config_paths):
    user_config_path, advanced_config_path = config_paths

    configU = IO_fcts.load_config(user_config_path)
    configA = IO_fcts.load_config(advanced_config_path)

    # Simple asserts to verify keys exist
    assert "advancedGeometrySettings" in configA
    assert "baseCellSize" in configA

    assert isinstance(configU, dict)
    assert isinstance(configA, dict)


def test_geometry_and_bounding_box(config_paths, tmp_path):
    _, advanced_config_path = config_paths

    configA = IO_fcts.load_config(advanced_config_path)



    geometry_file = Path("../../Openfoam/AeroSUV/") / configA["advancedGeometrySettings"]["filePath"]["mergedGeometry"]["file"]


    # Load geometry points (should be a list of coordinates)
    points = IO_fcts.load_geometry(geometry_file)
    assert len(points) > 0, "Loaded geometry points should not be empty"

    # Compute bounds
    scaling = configA["advancedGeometrySettings"]["scaling"]
    bounds = suppl_fcts.compute_extended_bounds(points, scaling)
    assert isinstance(bounds, dict)
    assert all(k in bounds for k in ["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"])

    # Format vertices and verify format
    vertices = suppl_fcts.format_vertices(bounds)
    assert isinstance(vertices, list) and len(vertices) > 0

    # Print vertices block (should not raise errors)
    suppl_fcts.print_vertices_block(vertices)

    # Save vertices to a temp file and verify file creation
    vertex_path = tmp_path / "vertices.vtk"
    IO_fcts.save_vertices(vertices, str(vertex_path))
    assert vertex_path.is_file()


def test_mesh_generation_and_surface_features(config_paths, tmp_path):
    _, advanced_config_path = config_paths
    configA = IO_fcts.load_config(advanced_config_path)

    geometry_file = Path("../../Openfoam/AeroSUV/") / configA["advancedGeometrySettings"]["filePath"]["mergedGeometry"]["file"]
    extract_angle = configA["advancedGeometrySettings"]["surfaceFeatureExtractDict"]["extractAngle"]
    base_cell_size = configA["baseCellSize"]

    # Reuse previous steps to get vertices
    points = IO_fcts.load_geometry(geometry_file)
    bounds = suppl_fcts.compute_extended_bounds(points, configA["advancedGeometrySettings"]["scaling"])
    vertices = suppl_fcts.format_vertices(bounds)

    # Estimate cell counts
    cell_counts = suppl_fcts.estimate_cell_counts(vertices, base_cell_size)
    assert all(isinstance(x, int) for x in cell_counts)

    # Generate blockMeshDict content and verify it's a string and non-empty
    blockMesh_content = populator_fcts.generate_blockMeshDict(vertices, cell_counts)
    assert isinstance(blockMesh_content, str) and len(blockMesh_content) > 0

    # Write blockMeshDict content to a temp file
    block_mesh_path = tmp_path / "blockMeshDict"
    block_mesh_path.write_text(blockMesh_content)
    assert block_mesh_path.is_file()

    # Generate surfaceFeatureExtractDict content and verify
    feature_extract_content = populator_fcts.generate_surfaceFeatureExtractDict(geometry_file, extract_angle)
    assert isinstance(feature_extract_content, str) and len(feature_extract_content) > 0

    # Write surfaceFeatureExtractDict to temp file
    surface_feature_path = tmp_path / "surfaceFeatureExtractDict"
    surface_feature_path.write_text(feature_extract_content)
    assert surface_feature_path.is_file()

